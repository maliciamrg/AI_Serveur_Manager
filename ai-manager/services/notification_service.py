from __future__ import annotations

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.timeout = httpx.Timeout(8.0)

    async def notify(self, title: str, body: str) -> None:
        payload = {"title": title, "message": body}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            await self._send_discord(client, payload)
            await self._send_home_assistant(client, payload)
            await self._send_ntfy(client, payload)

    async def _send_discord(self, client: httpx.AsyncClient, payload: dict[str, str]) -> None:
        if not self.settings.discord_webhook_url:
            return
        try:
            await client.post(self.settings.discord_webhook_url, json={"content": f"**{payload['title']}**\n{payload['message']}"})
        except httpx.HTTPError as exc:
            logger.exception("discord_notification_failed", extra={"action": "discord_notification", "details": str(exc)})

    async def _send_home_assistant(self, client: httpx.AsyncClient, payload: dict[str, str]) -> None:
        if not self.settings.home_assistant_webhook_url:
            return
        try:
            await client.post(self.settings.home_assistant_webhook_url, json=payload)
        except httpx.HTTPError as exc:
            logger.exception("home_assistant_notification_failed", extra={"action": "ha_notification", "details": str(exc)})

    async def _send_ntfy(self, client: httpx.AsyncClient, payload: dict[str, str]) -> None:
        if not self.settings.ntfy_url or not self.settings.ntfy_topic:
            return
        url = f"{self.settings.ntfy_url.rstrip('/')}/{self.settings.ntfy_topic}"
        try:
            await client.post(url, content=payload["message"], headers={"Title": payload["title"]})
        except httpx.HTTPError as exc:
            logger.exception("ntfy_notification_failed", extra={"action": "ntfy_notification", "details": str(exc)})
