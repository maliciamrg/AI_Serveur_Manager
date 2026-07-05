from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from database.session import Database
from services.activity_service import ActivityService
from services.health_service import HealthService
from services.metrics_service import MetricsService
from services.notification_service import NotificationService
from services.server_control_service import ServerControlService
from services.ssh_service import SSHConfig, SSHService


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    database: Database
    ssh_service: SSHService
    health_service: HealthService
    metrics_service: MetricsService
    activity_service: ActivityService
    server_control_service: ServerControlService
    notification_service: NotificationService


def build_container(settings: Settings) -> AppContainer:
    database = Database(settings.database_url)
    ssh_service = SSHService(
        SSHConfig(
            host=settings.ai_server_ip,
            port=settings.ssh_port,
            username=settings.ssh_user,
            private_key_path=settings.ssh_private_key,
            known_hosts_path=settings.ssh_known_hosts,
            timeout_seconds=settings.ssh_timeout,
            sudo_password=settings.ssh_sudo_password,
        )
    )
    notification_service = NotificationService(settings)
    health_service = HealthService(settings, ssh_service=ssh_service)
    metrics_service = MetricsService(settings, ssh_service=ssh_service)
    activity_service = ActivityService(keepalive_extension_seconds=settings.keepalive_extension_seconds)
    server_control_service = ServerControlService(
        settings=settings,
        ssh_service=ssh_service,
        notification_service=notification_service,
    )
    return AppContainer(
        settings=settings,
        database=database,
        ssh_service=ssh_service,
        health_service=health_service,
        metrics_service=metrics_service,
        activity_service=activity_service,
        server_control_service=server_control_service,
        notification_service=notification_service,
    )

