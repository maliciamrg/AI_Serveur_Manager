from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(alias="APP_NAME", default="AI Manager")
    environment: str = Field(alias="ENVIRONMENT", default="production")
    host: str = Field(alias="HOST", default="0.0.0.0")
    port: int = Field(alias="PORT", default=8000)
    secret_key: str = Field(alias="SECRET_KEY", default="change-this-secret-key", min_length=16)

    log_level: str = Field(alias="LOG_LEVEL", default="INFO")
    log_path: Path = Field(alias="LOG_PATH", default=Path("/data/logs/ai-manager.log"))
    log_max_bytes: int = Field(alias="LOG_MAX_BYTES", default=10_485_760)
    log_backup_count: int = Field(alias="LOG_BACKUP_COUNT", default=5)

    database_url: str = Field(alias="DATABASE_URL", default="sqlite+aiosqlite:////data/ai_manager.db")

    ai_server_name: str = Field(alias="AI_SERVER_NAME", default="AI Server")
    ai_server_ip: str = Field(alias="AI_SERVER_IP", default="127.0.0.1")
    ai_server_mac: str = Field(alias="AI_SERVER_MAC", default="AA:BB:CC:DD:EE:FF")
    ssh_port: int = Field(alias="SSH_PORT", default=22)
    ssh_user: str = Field(alias="SSH_USER", default="aiadmin")
    ssh_private_key: Path = Field(alias="SSH_PRIVATE_KEY", default=Path("/run/secrets/ssh_private_key"))
    ssh_known_hosts: Path = Field(alias="SSH_KNOWN_HOSTS", default=Path("/data/known_hosts"))
    ssh_timeout: int = Field(alias="SSH_TIMEOUT", default=8)
    ssh_sudo_password: str = Field(alias="SSH_SUDO_PASSWORD", default="")

    ollama_url: AnyHttpUrl = Field(alias="OLLAMA_URL", default="http://127.0.0.1:11434")
    openwebui_url: AnyHttpUrl = Field(alias="OPENWEBUI_URL", default="http://127.0.0.1:3000")

    ping_timeout: int = Field(alias="PING_TIMEOUT", default=2)
    boot_timeout: int = Field(alias="BOOT_TIMEOUT", default=600)
    idle_timeout: int = Field(alias="IDLE_TIMEOUT", default=3600)
    keepalive_extension_seconds: int = Field(alias="KEEPALIVE_EXTENSION_SECONDS", default=3600)
    gpu_threshold: float = Field(alias="GPU_THRESHOLD", default=10.0)
    cpu_threshold: float = Field(alias="CPU_THRESHOLD", default=10.0)

    health_check_interval_seconds: int = Field(alias="HEALTH_CHECK_INTERVAL_SECONDS", default=20)
    metrics_interval_seconds: int = Field(alias="METRICS_INTERVAL_SECONDS", default=60)
    idle_check_interval_seconds: int = Field(alias="IDLE_CHECK_INTERVAL_SECONDS", default=60)
    data_retention_days: int = Field(alias="DATA_RETENTION_DAYS", default=30)

    prometheus_enabled: bool = Field(alias="PROMETHEUS_ENABLED", default=True)
    prometheus_path: str = Field(alias="PROMETHEUS_PATH", default="/prometheus")

    admin_username: str = Field(alias="ADMIN_USERNAME", default="admin")
    admin_password_hash: str = Field(
        alias="ADMIN_PASSWORD_HASH",
        default="$2b$12$0AdkzfmWfFh8D6h0bI5cfesf6Q5h8obgD4DTNsEmMYhGG6B0A8by2",
    )

    energy_kw_estimate: float = Field(alias="ENERGY_KW_ESTIMATE", default=0.35)

    discord_webhook_url: str = Field(alias="DISCORD_WEBHOOK_URL", default="")
    home_assistant_webhook_url: str = Field(alias="HOME_ASSISTANT_WEBHOOK_URL", default="")
    ntfy_url: str = Field(alias="NTFY_URL", default="")
    ntfy_topic: str = Field(alias="NTFY_TOPIC", default="")

    enable_timeline: bool = Field(alias="ENABLE_TIMELINE", default=True)
    enable_dark_mode: bool = Field(alias="ENABLE_DARK_MODE", default=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
