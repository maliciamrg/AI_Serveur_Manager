from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import paramiko
from wakeonlan import send_magic_packet

from app.config import Settings
from models.enums import ServerState
from services.notification_service import NotificationService
from services.ssh_service import SSHService


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ServerControlService:
    def __init__(self, settings: Settings, ssh_service: SSHService, notification_service: NotificationService) -> None:
        self.settings = settings
        self.ssh_service = ssh_service
        self.notification_service = notification_service
        self.state: ServerState = ServerState.OFF
        self.boot_requested_at: datetime | None = None
        self.started_at: datetime | None = None
        self.energy_kwh_total: float = 0.0
        self._state_lock = asyncio.Lock()

    async def start_server(self) -> None:
        async with self._state_lock:
            if self.state in {ServerState.BOOTING, ServerState.READY, ServerState.BUSY, ServerState.IDLE}:
                return
            send_magic_packet(self.settings.ai_server_mac)
            self.state = ServerState.BOOTING
            self.boot_requested_at = utc_now()
        await self.notification_service.notify("AI Manager", f"{self.settings.ai_server_name} wake signal sent")

    async def shutdown_server(self, reason: str = "manual") -> tuple[bool, str]:
        async with self._state_lock:
            self.state = ServerState.STOPPING
        command = "shutdown now"
        try:
            code, _, err = await self.ssh_service.run_command(command, use_sudo=True)
        except FileNotFoundError:
            async with self._state_lock:
                self.state = ServerState.ERROR
            message = (
                f"SSH key file not found at {self.settings.ssh_private_key}. "
                "Use an existing OpenSSH private key path."
            )
            await self.notification_service.notify("AI Manager", f"Shutdown failed: {message}")
            return False, message
        except (paramiko.SSHException, OSError, TimeoutError) as exc:
            async with self._state_lock:
                self.state = ServerState.ERROR
            message = self._format_ssh_error_message(str(exc))
            await self.notification_service.notify("AI Manager", f"Shutdown failed: {message}")
            return False, message
        if code == 0:
            async with self._state_lock:
                self.state = ServerState.OFF
                self.started_at = None
            await self.notification_service.notify("AI Manager", f"{self.settings.ai_server_name} shutdown started ({reason})")
            return True, "Shutdown command sent"
        async with self._state_lock:
            self.state = ServerState.ERROR
        await self.notification_service.notify("AI Manager", f"Shutdown failed: {err}")
        return False, err or "Shutdown command failed"

    async def restart_server(self) -> tuple[bool, str]:
        ok, message = await self.shutdown_server(reason="restart")
        if not ok:
            return False, message
        await asyncio.sleep(4)
        await self.start_server()
        return True, "Restart requested"

    async def set_ready(self) -> None:
        async with self._state_lock:
            if self.started_at is None:
                self.started_at = utc_now()
            self.state = ServerState.READY

    async def set_busy_or_idle(self, busy: bool) -> None:
        async with self._state_lock:
            if self.state in {ServerState.OFF, ServerState.BOOTING, ServerState.STOPPING}:
                return
            self.state = ServerState.BUSY if busy else ServerState.IDLE

    async def set_booting(self) -> None:
        async with self._state_lock:
            self.state = ServerState.BOOTING

    async def set_off(self) -> None:
        async with self._state_lock:
            self.state = ServerState.OFF
            self.started_at = None

    async def uptime_seconds(self) -> int:
        async with self._state_lock:
            if self.started_at is None:
                return 0
            return int((utc_now() - self.started_at).total_seconds())

    async def recalculate_energy(self) -> float:
        uptime_hours = await self.uptime_seconds() / 3600.0
        self.energy_kwh_total = uptime_hours * self.settings.energy_kw_estimate
        return self.energy_kwh_total

    def _format_ssh_error_message(self, raw_error: str) -> str:
        error_text = raw_error.lower()
        if "private key" in error_text or ".ppk" in error_text:
            return (
                "Invalid SSH private key format. Convert .ppk to OpenSSH key and update SSH_PRIVATE_KEY."
            )
        if "no such file" in error_text or "cannot find the file" in error_text:
            return f"SSH key file not found at {self.settings.ssh_private_key}."
        if "permission denied" in error_text:
            return "SSH authentication failed (permission denied)."
        if "timed out" in error_text:
            return "SSH connection timed out."
        if "name or service not known" in error_text or "nodename nor servname" in error_text:
            return f"SSH host resolution failed for {self.settings.ai_server_ip}."
        return f"SSH error: {raw_error}"
