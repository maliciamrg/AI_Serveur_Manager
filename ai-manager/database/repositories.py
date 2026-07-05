from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.entities import ActivityEvent, AuditLog, InferenceEvent, Snapshot, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> User | None:
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def upsert_admin(self, username: str, password_hash: str) -> User:
        user = await self.get_by_username(username)
        if user is None:
            user = User(username=username, password_hash=password_hash)
            self.session.add(user)
        else:
            user.password_hash = password_hash
        await self.session.commit()
        await self.session.refresh(user)
        return user


class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, snapshot: Snapshot) -> Snapshot:
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def latest(self) -> Snapshot | None:
        query = select(Snapshot).order_by(Snapshot.created_at.desc()).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 120) -> list[Snapshot]:
        query = select(Snapshot).order_by(Snapshot.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def prune(self, retention_days: int) -> int:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=retention_days)
        query = delete(Snapshot).where(Snapshot.created_at < cutoff)
        result = await self.session.execute(query)
        await self.session.commit()
        return int(result.rowcount or 0)


class InferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: InferenceEvent) -> InferenceEvent:
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def latest(self) -> InferenceEvent | None:
        query = select(InferenceEvent).order_by(InferenceEvent.created_at.desc()).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def count(self) -> int:
        query = select(func.count(InferenceEvent.id))
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def avg_duration_ms(self) -> float:
        query = select(func.coalesce(func.avg(InferenceEvent.duration_ms), 0.0))
        result = await self.session.execute(query)
        return float(result.scalar_one())

    async def list_recent(self, limit: int = 200) -> list[InferenceEvent]:
        query = select(InferenceEvent).order_by(InferenceEvent.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: ActivityEvent) -> ActivityEvent:
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def latest(self) -> ActivityEvent | None:
        query = select(ActivityEvent).order_by(ActivityEvent.created_at.desc()).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 200) -> list[ActivityEvent]:
        query = select(ActivityEvent).order_by(ActivityEvent.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, entry: AuditLog) -> AuditLog:
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def list_recent(self, limit: int = 200) -> list[AuditLog]:
        query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

