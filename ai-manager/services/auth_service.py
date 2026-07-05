from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.security import verify_password
from database.repositories import UserRepository
from models.entities import User


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repo = UserRepository(session)

    async def authenticate(self, username: str, password: str) -> User | None:
        user = await self.user_repo.get_by_username(username)
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

