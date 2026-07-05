import pytest

from models.enums import ServerState
from services.health_service import HealthService


class DummySSHService:
    async def run_command(self, command: str):  # noqa: ARG002
        return 1, "", "ssh unavailable"


class ProbeHealthService(HealthService):
    async def _ping(self) -> tuple[float, bool]:
        return 3.2, True

    async def _check_ssh(self) -> bool:
        return False

    async def _check_ollama(self) -> tuple[bool, str | None]:
        return True, "llama3.1:8b"

    async def _check_openwebui(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_probe_checks_ollama_even_when_ssh_fails(test_settings):
    service = ProbeHealthService(settings=test_settings, ssh_service=DummySSHService())
    result = await service.run_probes()
    assert result.state == ServerState.BOOTING
    assert result.ssh_ok is False
    assert result.docker_ok is False
    assert result.ollama_ok is True
    assert result.openwebui_ok is True
    assert result.loaded_model == "llama3.1:8b"
