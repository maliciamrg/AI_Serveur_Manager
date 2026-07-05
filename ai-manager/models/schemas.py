from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from models.enums import ServerState


class HealthComponent(BaseModel):
    ok: bool
    detail: str


class StatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    state: ServerState
    last_activity_at: datetime | None
    idle_seconds: int
    idle_seconds_remaining: int
    uptime_seconds: int
    energy_kwh_total: float
    components: dict[str, HealthComponent]
    metrics: dict[str, float | int | str | None]
    last_inference: dict[str, Any] | None


class MetricsPoint(BaseModel):
    created_at: datetime
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    gpu_percent: float
    vram_percent: float
    ping_latency_ms: float
    uptime_seconds: int
    energy_kwh_total: float
    loaded_model: str | None


class ActionResponse(BaseModel):
    status: str
    message: str


class LoginForm(BaseModel):
    username: str
    password: str

