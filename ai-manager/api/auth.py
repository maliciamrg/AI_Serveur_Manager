from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import AppContainer
from app.dependencies import get_container, get_db_session
from database.repositories import AuditRepository
from models.entities import AuditLog
from services.auth_service import AuthService

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request, "error": ""})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    auth_service = AuthService(session)
    user = await auth_service.authenticate(username=username, password=password)
    audit = AuditRepository(session)
    if user is None:
        await audit.add(
            AuditLog(
                request_id=getattr(request.state, "request_id", None),
                username=username,
                action="login_failed",
                details="invalid_credentials",
            )
        )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request, "error": "Invalid credentials"},
        )
    request.session["user"] = user.username
    await audit.add(
        AuditLog(
            request_id=getattr(request.state, "request_id", None),
            username=user.username,
            action="login",
            details="user_login",
        )
    )
    response = RedirectResponse(url="/", status_code=303)
    return response


@router.post("/logout")
async def logout(request: Request, container: AppContainer = Depends(get_container)) -> RedirectResponse:
    username = request.session.get("user")
    request.session.clear()
    async for session in container.database.session():
        await AuditRepository(session).add(
            AuditLog(
                request_id=getattr(request.state, "request_id", None),
                username=username,
                action="logout",
                details="user_logout",
            )
        )
        break
    return RedirectResponse(url="/login", status_code=303)
