import pytest

from app.config import Settings
from services.metrics_service import MetricsService


class FailingSSHService:
    async def run_command(self, command: str):  # noqa: ARG002
        raise FileNotFoundError("missing ssh key")


@pytest.mark.asyncio
async def test_collect_server_metrics_handles_missing_ssh_key(tmp_path):
    settings = Settings(
        APP_NAME="AI Manager Test",
        ENVIRONMENT="test",
        HOST="127.0.0.1",
        PORT=8000,
        SECRET_KEY="test-secret-key-123456",
        LOG_LEVEL="INFO",
        LOG_PATH=tmp_path / "ai-manager.log",
        LOG_MAX_BYTES=1024 * 1024,
        LOG_BACKUP_COUNT=1,
        DATABASE_URL=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        AI_SERVER_NAME="AI Test Server",
        AI_SERVER_IP="127.0.0.1",
        AI_SERVER_MAC="AA:BB:CC:DD:EE:FF",
        SSH_PORT=22,
        SSH_USER="test",
        SSH_PRIVATE_KEY=tmp_path / "id_rsa",
        SSH_KNOWN_HOSTS=tmp_path / "known_hosts",
        SSH_TIMEOUT=1,
        SSH_SUDO_PASSWORD="",
        OLLAMA_URL="http://127.0.0.1:11434",
        OPENWEBUI_URL="http://127.0.0.1:3000",
        PING_TIMEOUT=1,
        BOOT_TIMEOUT=120,
        IDLE_TIMEOUT=60,
        KEEPALIVE_EXTENSION_SECONDS=60,
        GPU_THRESHOLD=10.0,
        CPU_THRESHOLD=10.0,
        HEALTH_CHECK_INTERVAL_SECONDS=120,
        METRICS_INTERVAL_SECONDS=120,
        IDLE_CHECK_INTERVAL_SECONDS=120,
        DATA_RETENTION_DAYS=30,
        PROMETHEUS_ENABLED=True,
        PROMETHEUS_PATH="/prometheus",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD_HASH="$2b$12$uVhHdFesCpWogjhLdRrwl.sO4/72MDzwfOJnxSIsC13BdGoSx9MJK",
        ENERGY_KW_ESTIMATE=0.35,
        DISCORD_WEBHOOK_URL="",
        HOME_ASSISTANT_WEBHOOK_URL="",
        NTFY_URL="",
        NTFY_TOPIC="",
        ENABLE_TIMELINE=True,
        ENABLE_DARK_MODE=True,
    )
    service = MetricsService(settings=settings, ssh_service=FailingSSHService())
    metrics = await service.collect_server_metrics()
    assert metrics.cpu_percent == 0.0
    assert metrics.ram_percent == 0.0
    assert metrics.disk_percent == 0.0
    assert metrics.gpu_percent == 0.0
