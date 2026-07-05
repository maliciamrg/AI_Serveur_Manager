from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Type

import paramiko


@dataclass(slots=True)
class SSHConfig:
    host: str
    port: int
    username: str
    private_key_path: Path
    known_hosts_path: Path
    timeout_seconds: int
    sudo_password: str


class SSHService:
    def __init__(self, config: SSHConfig) -> None:
        self.config = config

    async def run_command(self, command: str, use_sudo: bool = False) -> tuple[int, str, str]:
        return await asyncio.to_thread(self._run_command_sync, command, use_sudo)

    def _run_command_sync(self, command: str, use_sudo: bool) -> tuple[int, str, str]:
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        if self.config.known_hosts_path.exists():
            ssh.load_host_keys(str(self.config.known_hosts_path))
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = self._load_private_key(self.config.private_key_path)
        ssh.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.username,
            pkey=private_key,
            timeout=self.config.timeout_seconds,
            auth_timeout=self.config.timeout_seconds,
            banner_timeout=self.config.timeout_seconds,
        )
        try:
            if use_sudo:
                command = f"sudo -S -p '' {command}"
            stdin, stdout, stderr = ssh.exec_command(command, timeout=self.config.timeout_seconds)
            if use_sudo and self.config.sudo_password:
                stdin.write(f"{self.config.sudo_password}\n")
                stdin.flush()
            output = stdout.read().decode("utf-8", errors="ignore")
            err = stderr.read().decode("utf-8", errors="ignore")
            code = stdout.channel.recv_exit_status()
            return code, output.strip(), err.strip()
        finally:
            ssh.close()

    @staticmethod
    def _load_private_key(private_key_path: Path) -> paramiko.PKey:
        key_classes: tuple[Type[paramiko.PKey], ...] = (
            paramiko.RSAKey,
            paramiko.Ed25519Key,
            paramiko.ECDSAKey,
            paramiko.DSSKey,
        )
        for key_class in key_classes:
            try:
                return key_class.from_private_key_file(str(private_key_path))
            except paramiko.SSHException:
                continue
        raise paramiko.SSHException(f"Unsupported or invalid private key format: {private_key_path}")
