from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    (tmp_path / "id_rsa").write_text("dummy", encoding="utf-8")
    (tmp_path / "known_hosts").write_text("", encoding="utf-8")
    return Settings(
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
        PROMETHEUS_PATH="/metrics",
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


@pytest.fixture
async def app(test_settings: Settings) -> AsyncIterator[FastAPI]:
    app = create_app(settings=test_settings, enable_scheduler=False)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
