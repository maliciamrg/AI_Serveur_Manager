from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import AppContainer
from database.repositories import SnapshotRepository
from models.entities import AuditLog
from models.enums import ServerState
from services.prometheus_metrics import (
    cpu_gauge,
    energy_gauge,
    gpu_gauge,
    ping_gauge,
    ram_gauge,
    server_state_gauge,
    vram_gauge,
)

logger = logging.getLogger(__name__)

STATE_TO_CODE = {
    ServerState.OFF: 0,
    ServerState.BOOTING: 1,
    ServerState.READY: 2,
    ServerState.BUSY: 3,
    ServerState.IDLE: 4,
    ServerState.STOPPING: 5,
    ServerState.ERROR: 6,
}


def register_scheduler_jobs(container: AppContainer) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _health_check_job,
        trigger="interval",
        seconds=container.settings.health_check_interval_seconds,
        kwargs={"container": container},
        id="health_check",
        replace_existing=True,
        coalesce=True,
    )
    scheduler.add_job(
        _collect_metrics_job,
        trigger="interval",
        seconds=container.settings.metrics_interval_seconds,
        kwargs={"container": container},
        id="metrics_collection",
        replace_existing=True,
        coalesce=True,
    )
    scheduler.add_job(
        _idle_check_job,
        trigger="interval",
        seconds=container.settings.idle_check_interval_seconds,
        kwargs={"container": container},
        id="idle_check",
        replace_existing=True,
        coalesce=True,
    )
    scheduler.add_job(
        _cleanup_job,
        trigger="cron",
        hour=3,
        minute=15,
        kwargs={"container": container},
        id="cleanup",
        replace_existing=True,
        coalesce=True,
    )
    return scheduler


async def _health_check_job(container: AppContainer) -> None:
    probe = await container.health_service.run_probes()
    control = container.server_control_service
    previous_state = control.state

    if probe.state == ServerState.OFF:
        await control.set_off()
        return

    if probe.state == ServerState.READY:
        await control.set_ready()
        if previous_state != ServerState.READY:
            await container.notification_service.notify(
                "AI Manager boot complete",
                f"{container.settings.ai_server_name} is READY",
            )
    else:
        await control.set_booting()

    if probe.state == ServerState.BOOTING and control.boot_requested_at is not None:
        elapsed = (datetime.now(tz=timezone.utc) - control.boot_requested_at).total_seconds()
        if elapsed > container.settings.boot_timeout:
            await container.notification_service.notify(
                "AI Manager boot timeout",
                f"{container.settings.ai_server_name} did not become ready within timeout",
            )

    if not probe.ssh_ok:
        await container.notification_service.notify("AI Manager SSH failure", "SSH check failed")
    if not probe.ollama_ok:
        await container.notification_service.notify("AI Manager Ollama unavailable", "Ollama health probe failed")
    if not probe.openwebui_ok:
        await container.notification_service.notify("AI Manager OpenWebUI unavailable", "OpenWebUI health probe failed")


async def _collect_metrics_job(container: AppContainer) -> None:
    probe = await container.health_service.run_probes()
    if probe.state == ServerState.OFF:
        return

    server_metrics = await container.metrics_service.collect_server_metrics()
    is_busy = server_metrics.gpu_percent >= container.settings.gpu_threshold or server_metrics.cpu_percent >= container.settings.cpu_threshold
    await container.server_control_service.set_busy_or_idle(is_busy)
    energy = await container.server_control_service.recalculate_energy()
    uptime = await container.server_control_service.uptime_seconds()

    snapshot = await container.metrics_service.build_snapshot(
        probe=probe,
        metrics=server_metrics,
        uptime_seconds=uptime,
        energy_kwh_total=energy,
        state_value=container.server_control_service.state.value,
    )
    async for session in container.database.session():
        session = session  # type: AsyncSession
        repo = SnapshotRepository(session)
        await repo.add(snapshot)
        break

    server_state_gauge.set(STATE_TO_CODE[container.server_control_service.state])
    ping_gauge.set(probe.ping_ms)
    cpu_gauge.set(server_metrics.cpu_percent)
    ram_gauge.set(server_metrics.ram_percent)
    gpu_gauge.set(server_metrics.gpu_percent)
    vram_gauge.set(server_metrics.vram_percent)
    energy_gauge.set(energy)


async def _idle_check_job(container: AppContainer) -> None:
    activity = container.activity_service
    if activity.should_shutdown_for_idle(container.settings.idle_timeout):
        ok, message = await container.server_control_service.shutdown_server(reason="idle_timeout")
        async for session in container.database.session():
            session = session  # type: AsyncSession
            session.add(AuditLog(action="idle_shutdown", details=message if ok else f"failed:{message}"))
            await session.commit()
            break


async def _cleanup_job(container: AppContainer) -> None:
    async for session in container.database.session():
        session = session  # type: AsyncSession
        snapshots = SnapshotRepository(session)
        removed_snapshots = await snapshots.prune(container.settings.data_retention_days)
        logger.info(
            "cleanup_finished",
            extra={"action": "cleanup", "details": f"removed_snapshots={removed_snapshots}"},
        )
        break
