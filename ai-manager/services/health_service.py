from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import time
from dataclasses import dataclass

import httpx
import paramiko

from app.config import Settings
from models.enums import ServerState
from services.ssh_service import SSHService


@dataclass(slots=True)
class HealthProbeResult:
    state: ServerState
    ping_ms: float
    ssh_ok: bool
    docker_ok: bool
    ollama_ok: bool
    openwebui_ok: bool
    loaded_model: str | None
    running_containers: int
    details: dict[str, str]


class HealthService:
    def __init__(self, settings: Settings, ssh_service: SSHService) -> None:
        self.settings = settings
        self.ssh_service = ssh_service
        self.http_timeout = httpx.Timeout(6.0)

    async def run_probes(self) -> HealthProbeResult:
        ping_ms, ping_ok = await self._ping()
        details = {"ping": "ok" if ping_ok else "unreachable"}
        if not ping_ok:
            return HealthProbeResult(
                state=ServerState.OFF,
                ping_ms=0.0,
                ssh_ok=False,
                docker_ok=False,
                ollama_ok=False,
                openwebui_ok=False,
                loaded_model=None,
                running_containers=0,
                details=details,
            )

        try:
            ssh_ok = await self._check_ssh()
        except (paramiko.SSHException, TimeoutError, OSError):
            ssh_ok = False
        details["ssh"] = "ok" if ssh_ok else "failed"

        docker_ok = False
        containers = 0
        try:
            if ssh_ok:
                docker_ok, containers = await self._check_docker()
        except (paramiko.SSHException, TimeoutError, OSError):
            docker_ok, containers = False, 0
        try:
            ollama_ok, loaded_model = await self._check_ollama()
        except (httpx.HTTPError, ValueError):
            ollama_ok, loaded_model = False, None
        try:
            openwebui_ok = await self._check_openwebui()
        except httpx.HTTPError:
            openwebui_ok = False
        details["docker"] = "ok" if docker_ok else "failed"
        details["ollama"] = "ok" if ollama_ok else "failed"
        details["openwebui"] = "ok" if openwebui_ok else "failed"

        is_ready = docker_ok and ollama_ok and openwebui_ok
        state = ServerState.READY if is_ready else ServerState.BOOTING
        return HealthProbeResult(
            state=state,
            ping_ms=ping_ms,
            ssh_ok=ssh_ok,
            docker_ok=docker_ok,
            ollama_ok=ollama_ok,
            openwebui_ok=openwebui_ok,
            loaded_model=loaded_model,
            running_containers=containers,
            details=details,
        )

    async def _ping(self) -> tuple[float, bool]:
        command = self._build_ping_command()
        started = time.perf_counter()
        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                timeout=max(1, self.settings.ping_timeout + 1),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return 0.0, False
        latency = (time.perf_counter() - started) * 1000
        if completed.returncode != 0:
            return 0.0, False
        out_text = completed.stdout or ""
        match = re.search(r"time[=<]\s*([\d.]+)\s*ms", out_text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1)), True
        return latency, True

    def _build_ping_command(self) -> list[str]:
        if sys.platform.startswith("win"):
            timeout_ms = max(1000, self.settings.ping_timeout * 1000)
            return ["ping", "-n", "1", "-w", str(timeout_ms), self.settings.ai_server_ip]
        return ["ping", "-c", "1", "-W", str(self.settings.ping_timeout), self.settings.ai_server_ip]

    async def _check_ssh(self) -> bool:
        code, _, _ = await self.ssh_service.run_command("echo ok")
        return code == 0

    async def _check_docker(self) -> tuple[bool, int]:
        code, output, _ = await self.ssh_service.run_command("docker ps --format '{{.ID}}' | wc -l")
        if code != 0:
            return False, 0
        try:
            return True, int(output.strip())
        except ValueError:
            return True, 0

    async def _check_ollama(self) -> tuple[bool, str | None]:
        base_url = str(self.settings.ollama_url).rstrip("/")
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            tags_response = await client.get(f"{base_url}/api/tags")
            if tags_response.status_code != 200:
                return False, None
            ps_response = await client.get(f"{base_url}/api/ps")
            if ps_response.status_code != 200:
                return True, None
            payload = ps_response.json()
            models = payload.get("models", [])
            if not models:
                return True, None
            return True, str(models[0].get("name"))

    async def _check_openwebui(self) -> bool:
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            response = await client.get(str(self.settings.openwebui_url))
            return response.status_code == 200
