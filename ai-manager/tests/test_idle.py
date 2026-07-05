from datetime import timedelta

from services.activity_service import ActivityService, utc_now


def test_idle_shutdown_logic():
    service = ActivityService(keepalive_extension_seconds=60)
    service.mark_activity(source="test", event_type="activity")
    assert service.should_shutdown_for_idle(idle_timeout=3600) is False

    service.last_activity_at = utc_now() - timedelta(seconds=3700)
    assert service.should_shutdown_for_idle(idle_timeout=3600) is True

    service.keep_alive()
    assert service.should_shutdown_for_idle(idle_timeout=3600) is False

