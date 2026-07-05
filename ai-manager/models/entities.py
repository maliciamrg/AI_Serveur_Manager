from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from models.enums import ServerState


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    server_state: Mapped[str] = mapped_column(String(16), default=ServerState.OFF.value)
    ping_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    ram_percent: Mapped[float] = mapped_column(Float, default=0.0)
    disk_percent: Mapped[float] = mapped_column(Float, default=0.0)
    gpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    vram_percent: Mapped[float] = mapped_column(Float, default=0.0)
    temperature_c: Mapped[float] = mapped_column(Float, default=0.0)
    docker_ok: Mapped[int] = mapped_column(Integer, default=0)
    ollama_ok: Mapped[int] = mapped_column(Integer, default=0)
    openwebui_ok: Mapped[int] = mapped_column(Integer, default=0)
    loaded_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    running_containers: Mapped[int] = mapped_column(Integer, default=0)
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    energy_kwh_total: Mapped[float] = mapped_column(Float, default=0.0)


class InferenceEvent(Base):
    __tablename__ = "inference_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    source: Mapped[str] = mapped_column(String(64))
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    user_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    source: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(64))
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(128))
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

