from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import AppContainer
from app.dependencies import get_container, get_db_session
from database.repositories import ActivityRepository, InferenceRepository, SnapshotRepository
from services.health_service import HealthProbeResult

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    username = request.session.get("user")
    if not username:
        return RedirectResponse(url="/login", status_code=303)
    snapshot = await SnapshotRepository(session).latest()
    last_inference = await InferenceRepository(session).latest()
    live_probe = await _safe_live_probe(container)
    context = _build_context(request, container, str(username), snapshot, last_inference, live_probe)
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)


@router.get("/partials/status", response_class=HTMLResponse)
async def dashboard_status_partial(
    request: Request,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    username = request.session.get("user")
    if not username:
        return RedirectResponse(url="/login", status_code=303)
    snapshot = await SnapshotRepository(session).latest()
    last_inference = await InferenceRepository(session).latest()
    live_probe = await _safe_live_probe(container)
    context = _build_context(request, container, str(username), snapshot, last_inference, live_probe)
    return templates.TemplateResponse(request=request, name="partials/status_card.html", context=context)


@router.get("/timeline", response_class=HTMLResponse)
async def timeline_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    username = request.session.get("user")
    if not username:
        return RedirectResponse(url="/login", status_code=303)
    activities = await ActivityRepository(session).list_recent(limit=150)
    return templates.TemplateResponse(
        request=request,
        name="timeline.html",
        context={
            "request": request,
            "username": str(username),
            "activities": activities,
        },
    )


@router.get("/login-redirect")
async def login_redirect() -> RedirectResponse:
    return RedirectResponse("/login")


async def _safe_live_probe(container: AppContainer) -> HealthProbeResult | None:
    try:
        return await container.health_service.run_probes()
    except (TimeoutError, OSError):
        return None


def _build_context(request: Request, container: AppContainer, username: str, snapshot, inference, live_probe: HealthProbeResult | None) -> dict:
    idle_remaining = container.activity_service.idle_seconds_remaining(container.settings.idle_timeout)
    return {
        "request": request,
        "username": username,
        "settings": container.settings,
        "server_state": container.server_control_service.state.value,
        "idle_seconds_remaining": idle_remaining,
        "snapshot": snapshot,
        "inference": inference,
        "live_probe": live_probe,
        "enable_timeline": container.settings.enable_timeline,
        "enable_dark_mode": container.settings.enable_dark_mode,
    }
