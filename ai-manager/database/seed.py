from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import UserRepository


async def seed_admin_user(session: AsyncSession, username: str, password_hash: str) -> None:
    user_repo = UserRepository(session)
    await user_repo.upsert_admin(username=username, password_hash=password_hash)

