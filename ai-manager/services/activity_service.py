from __future__ import annotations

from datetime import datetime, timedelta, timezone

from models.entities import ActivityEvent, InferenceEvent


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ActivityService:
    def __init__(self, keepalive_extension_seconds: int) -> None:
        self.keepalive_extension_seconds = keepalive_extension_seconds
        self.last_activity_at: datetime | None = None
        self.keepalive_until: datetime | None = None
        self.last_inference_at: datetime | None = None
        self.last_inference_user: str | None = None
        self.last_inference_model: str | None = None
        self.last_inference_duration_ms: float = 0.0
        self.inference_count: int = 0
        self.total_inference_duration_ms: float = 0.0

    def mark_activity(self, source: str, event_type: str, details: str | None = None) -> ActivityEvent:
        self.last_activity_at = utc_now()
        return ActivityEvent(source=source, event_type=event_type, details=details)

    def keep_alive(self) -> ActivityEvent:
        self.last_activity_at = utc_now()
        self.keepalive_until = self.last_activity_at + timedelta(seconds=self.keepalive_extension_seconds)
        return ActivityEvent(source="dashboard", event_type="keepalive", details=f"until={self.keepalive_until.isoformat()}")

    def mark_inference(self, source: str, duration_ms: float, user_name: str | None, model_name: str | None) -> InferenceEvent:
        now = utc_now()
        self.last_activity_at = now
        self.last_inference_at = now
        self.last_inference_user = user_name
        self.last_inference_model = model_name
        self.last_inference_duration_ms = duration_ms
        self.inference_count += 1
        self.total_inference_duration_ms += duration_ms
        return InferenceEvent(source=source, duration_ms=duration_ms, user_name=user_name, model_name=model_name)

    def idle_seconds(self) -> int:
        if self.last_activity_at is None:
            return 0
        return int((utc_now() - self.last_activity_at).total_seconds())

    def idle_seconds_remaining(self, idle_timeout: int) -> int:
        if self.last_activity_at is None:
            return idle_timeout
        if self.keepalive_until and utc_now() < self.keepalive_until:
            return int((self.keepalive_until - utc_now()).total_seconds())
        return max(0, idle_timeout - self.idle_seconds())

    def should_shutdown_for_idle(self, idle_timeout: int) -> bool:
        if self.last_activity_at is None:
            return False
        if self.keepalive_until and utc_now() < self.keepalive_until:
            return False
        return self.idle_seconds() >= idle_timeout

    def average_inference_duration_ms(self) -> float:
        if self.inference_count == 0:
            return 0.0
        return self.total_inference_duration_ms / self.inference_count

