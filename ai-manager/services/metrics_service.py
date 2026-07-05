from __future__ import annotations

from dataclasses import dataclass
import logging

import paramiko

from app.config import Settings
from models.entities import Snapshot
from services.health_service import HealthProbeResult
from services.ssh_service import SSHService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ServerMetrics:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    disk_percent: float = 0.0
    gpu_percent: float = 0.0
    vram_percent: float = 0.0
    temperature_c: float = 0.0


class MetricsService:
    def __init__(self, settings: Settings, ssh_service: SSHService) -> None:
        self.settings = settings
        self.ssh_service = ssh_service

    async def collect_server_metrics(self) -> ServerMetrics:
        metrics = ServerMetrics()

        cpu_command = "top -bn1 | awk '/Cpu\\(s\\)/ {print $2+$4}'"
        ram_command = "free | awk '/Mem:/ {print ($3/$2)*100}'"
        disk_command = "df / | awk 'NR==2 {print $5}' | tr -d '%'"
        gpu_command = "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits"

        cpu_result = await self._safe_run_command(cpu_command)
        if cpu_result is None:
            return metrics
        code, cpu_out, _ = cpu_result
        if code == 0 and cpu_out:
            metrics.cpu_percent = _parse_float(cpu_out)

        ram_result = await self._safe_run_command(ram_command)
        if ram_result is None:
            return metrics
        code, ram_out, _ = ram_result
        if code == 0 and ram_out:
            metrics.ram_percent = _parse_float(ram_out)

        disk_result = await self._safe_run_command(disk_command)
        if disk_result is None:
            return metrics
        code, disk_out, _ = disk_result
        if code == 0 and disk_out:
            metrics.disk_percent = _parse_float(disk_out)

        gpu_result = await self._safe_run_command(gpu_command)
        if gpu_result is None:
            return metrics
        code, gpu_out, _ = gpu_result
        if code == 0 and gpu_out:
            parts = [segment.strip() for segment in gpu_out.split(",")]
            if len(parts) >= 4:
                metrics.gpu_percent = _parse_float(parts[0])
                used = _parse_float(parts[1])
                total = _parse_float(parts[2])
                metrics.vram_percent = (used / total * 100.0) if total > 0 else 0.0
                metrics.temperature_c = _parse_float(parts[3])
        return metrics

    async def _safe_run_command(self, command: str) -> tuple[int, str, str] | None:
        try:
            return await self.ssh_service.run_command(command)
        except (FileNotFoundError, OSError, TimeoutError, paramiko.SSHException) as exc:
            logger.warning(
                "metrics_ssh_command_failed",
                extra={"action": "metrics_ssh", "details": f"{type(exc).__name__}:{exc}"},
            )
            return None

    async def build_snapshot(
        self,
        probe: HealthProbeResult,
        metrics: ServerMetrics,
        uptime_seconds: int,
        energy_kwh_total: float,
        state_value: str,
    ) -> Snapshot:
        return Snapshot(
            server_state=state_value,
            ping_latency_ms=probe.ping_ms,
            cpu_percent=metrics.cpu_percent,
            ram_percent=metrics.ram_percent,
            disk_percent=metrics.disk_percent,
            gpu_percent=metrics.gpu_percent,
            vram_percent=metrics.vram_percent,
            temperature_c=metrics.temperature_c,
            docker_ok=1 if probe.docker_ok else 0,
            ollama_ok=1 if probe.ollama_ok else 0,
            openwebui_ok=1 if probe.openwebui_ok else 0,
            loaded_model=probe.loaded_model,
            running_containers=probe.running_containers,
            uptime_seconds=uptime_seconds,
            energy_kwh_total=energy_kwh_total,
        )


def _parse_float(value: str) -> float:
    try:
        return float(value.strip())
    except ValueError:
        return 0.0
