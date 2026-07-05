from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import AppContainer
from app.dependencies import get_container, get_current_user, get_db_session
from database.repositories import ActivityRepository, AuditRepository, InferenceRepository, SnapshotRepository
from models.entities import AuditLog
from models.schemas import ActionResponse, HealthComponent, MetricsPoint, StatusResponse
from services.prometheus_metrics import (
    inference_counter,
    inference_duration,
)

router = APIRouter(tags=["api"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/status", response_model=StatusResponse)
async def get_status(
    _: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> StatusResponse:
    snapshot = await SnapshotRepository(session).latest()
    last_inference = await InferenceRepository(session).latest()
    idle_seconds = container.activity_service.idle_seconds()
    idle_remaining = container.activity_service.idle_seconds_remaining(container.settings.idle_timeout)
    uptime = await container.server_control_service.uptime_seconds()
    energy = await container.server_control_service.recalculate_energy()
    components = {
        "ping": HealthComponent(ok=(snapshot.ping_latency_ms > 0 if snapshot else False), detail=f"{snapshot.ping_latency_ms:.1f} ms" if snapshot else "no data"),
        "docker": HealthComponent(ok=(snapshot.docker_ok == 1 if snapshot else False), detail="running" if snapshot and snapshot.docker_ok else "down"),
        "ollama": HealthComponent(ok=(snapshot.ollama_ok == 1 if snapshot else False), detail="healthy" if snapshot and snapshot.ollama_ok else "down"),
        "openwebui": HealthComponent(ok=(snapshot.openwebui_ok == 1 if snapshot else False), detail="healthy" if snapshot and snapshot.openwebui_ok else "down"),
    }
    metrics = {
        "cpu_percent": snapshot.cpu_percent if snapshot else 0.0,
        "ram_percent": snapshot.ram_percent if snapshot else 0.0,
        "disk_percent": snapshot.disk_percent if snapshot else 0.0,
        "gpu_percent": snapshot.gpu_percent if snapshot else 0.0,
        "vram_percent": snapshot.vram_percent if snapshot else 0.0,
        "temperature_c": snapshot.temperature_c if snapshot else 0.0,
        "loaded_model": snapshot.loaded_model if snapshot else None,
        "running_containers": snapshot.running_containers if snapshot else 0,
    }
    inference_payload = None
    if last_inference:
        inference_payload = {
            "at": last_inference.created_at,
            "source": last_inference.source,
            "duration_ms": last_inference.duration_ms,
            "user_name": last_inference.user_name,
            "model_name": last_inference.model_name,
        }
    return StatusResponse(
        state=container.server_control_service.state,
        last_activity_at=container.activity_service.last_activity_at,
        idle_seconds=idle_seconds,
        idle_seconds_remaining=idle_remaining,
        uptime_seconds=uptime,
        energy_kwh_total=energy,
        components=components,
        metrics=metrics,
        last_inference=inference_payload,
    )


@router.get("/metrics", response_model=list[MetricsPoint])
async def get_metrics(
    _: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[MetricsPoint]:
    snapshots = await SnapshotRepository(session).list_recent(limit=180)
    return [
        MetricsPoint(
            created_at=item.created_at,
            cpu_percent=item.cpu_percent,
            ram_percent=item.ram_percent,
            disk_percent=item.disk_percent,
            gpu_percent=item.gpu_percent,
            vram_percent=item.vram_percent,
            ping_latency_ms=item.ping_latency_ms,
            uptime_seconds=item.uptime_seconds,
            energy_kwh_total=item.energy_kwh_total,
            loaded_model=item.loaded_model,
        )
        for item in snapshots
    ]


@router.get("/history")
async def get_history(
    _: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    activities = await ActivityRepository(session).list_recent(limit=120)
    audits = await AuditRepository(session).list_recent(limit=120)
    return {
        "activity": [
            {"at": row.created_at, "source": row.source, "event_type": row.event_type, "details": row.details}
            for row in activities
        ],
        "audit": [
            {"at": row.created_at, "user": row.username, "action": row.action, "details": row.details}
            for row in audits
        ],
    }


@router.post("/server/start", response_model=ActionResponse)
async def server_start(
    request: Request,
    username: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> ActionResponse:
    await container.server_control_service.start_server()
    await AuditRepository(session).add(
        AuditLog(
            request_id=getattr(request.state, "request_id", None),
            username=username,
            action="server_start",
            details="wake_on_lan_sent",
        )
    )
    return ActionResponse(status="accepted", message="Wake-on-LAN signal sent")


@router.post("/server/shutdown", response_model=ActionResponse)
async def server_shutdown(
    request: Request,
    username: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> ActionResponse:
    ok, message = await container.server_control_service.shutdown_server(reason="manual")
    await AuditRepository(session).add(
        AuditLog(
            request_id=getattr(request.state, "request_id", None),
            username=username,
            action="server_shutdown",
            details=message,
        )
    )
    return ActionResponse(status="success" if ok else "error", message=message)


@router.post("/server/restart", response_model=ActionResponse)
async def server_restart(
    request: Request,
    username: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> ActionResponse:
    ok, message = await container.server_control_service.restart_server()
    await AuditRepository(session).add(
        AuditLog(
            request_id=getattr(request.state, "request_id", None),
            username=username,
            action="server_restart",
            details=message,
        )
    )
    return ActionResponse(status="success" if ok else "error", message=message)


@router.post("/keepalive", response_model=ActionResponse)
async def keepalive(
    request: Request,
    username: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> ActionResponse:
    activity_event = container.activity_service.keep_alive()
    await ActivityRepository(session).add(activity_event)
    await AuditRepository(session).add(
        AuditLog(
            request_id=getattr(request.state, "request_id", None),
            username=username,
            action="keepalive",
            details="dashboard_keepalive",
        )
    )
    return ActionResponse(status="success", message="Keep alive extended")


@router.post("/activity/inference")
async def inference_activity(
    request: Request,
    source: str = "ollama",
    user_name: str | None = None,
    model_name: str | None = None,
    duration_ms: float = 0.0,
    _: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    started = time.perf_counter()
    inference_event = container.activity_service.mark_inference(
        source=source,
        duration_ms=duration_ms,
        user_name=user_name,
        model_name=model_name,
    )
    await InferenceRepository(session).add(inference_event)
    activity_event = container.activity_service.mark_activity(source=source, event_type="inference")
    await ActivityRepository(session).add(activity_event)
    elapsed = max(duration_ms / 1000.0, time.perf_counter() - started)
    inference_counter.inc()
    inference_duration.observe(elapsed)
    return JSONResponse({"status": "ok", "recorded_at": datetime.now(tz=timezone.utc).isoformat()})


@router.post("/activity/openwebui")
async def openwebui_activity(
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    event = container.activity_service.mark_activity(source="openwebui", event_type="request")
    await ActivityRepository(session).add(event)
    return {"status": "ok"}


@router.post("/activity/ollama")
async def ollama_activity(
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    event = container.activity_service.mark_activity(source="ollama", event_type="request")
    await ActivityRepository(session).add(event)
    return {"status": "ok"}
