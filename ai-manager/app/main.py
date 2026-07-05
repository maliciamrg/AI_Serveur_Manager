from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from api import api_router, auth_router, dashboard_router
from app.config import Settings, get_settings
from app.container import AppContainer, build_container
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware
from database.seed import seed_admin_user
from scheduler.jobs import register_scheduler_jobs
from services.prometheus_metrics import render_prometheus

logger = logging.getLogger(__name__)


def build_lifespan(settings: Settings, enable_scheduler: bool):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(
            log_level=settings.log_level,
            log_path=settings.log_path,
            max_bytes=settings.log_max_bytes,
            backup_count=settings.log_backup_count,
        )
        container: AppContainer = build_container(settings)
        app.state.container = container
        await container.database.init_models()
        async for session in container.database.session():
            await seed_admin_user(session, settings.admin_username, settings.admin_password_hash)
            break

        scheduler: AsyncIOScheduler | None = None
        if enable_scheduler:
            scheduler = register_scheduler_jobs(container)
            scheduler.start()
            app.state.scheduler = scheduler
        logger.info("application_started", extra={"action": "startup", "details": "ai_manager_started"})
        try:
            yield
        finally:
            if scheduler:
                scheduler.shutdown(wait=False)
            logger.info("application_stopped", extra={"action": "shutdown", "details": "ai_manager_stopped"})

    return lifespan


def create_app(settings: Settings | None = None, enable_scheduler: bool = True) -> FastAPI:
    resolved_settings = settings or get_settings()
    application = FastAPI(
        title=resolved_settings.app_name,
        version="1.0.0",
        description="On-demand AI appliance manager for homelab infrastructure.",
        lifespan=build_lifespan(resolved_settings, enable_scheduler),
    )
    application.add_middleware(SessionMiddleware, secret_key=resolved_settings.secret_key, same_site="lax", https_only=False)
    application.add_middleware(RequestContextMiddleware)
    application.mount("/static", StaticFiles(directory="static"), name="static")

    application.include_router(auth_router)
    application.include_router(dashboard_router)
    application.include_router(api_router)

    async def prometheus_endpoint(request: Request) -> Response:
        container = request.app.state.container
        if not container.settings.prometheus_enabled:
            return Response(status_code=404)
        body, content_type = render_prometheus()
        return Response(content=body, media_type=content_type)

    application.add_api_route(
        resolved_settings.prometheus_path,
        prometheus_endpoint,
        methods=["GET"],
        include_in_schema=False,
    )
    return application


app = create_app()
