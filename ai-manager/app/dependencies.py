from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import AppContainer


def get_container(request: Request) -> AppContainer:
    return request.app.state.container  # type: ignore[no-any-return]


async def get_db_session(container: AppContainer = Depends(get_container)) -> AsyncIterator[AsyncSession]:
    async for session in container.database.session():
        yield session


def get_current_user(request: Request) -> str:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return str(user)

