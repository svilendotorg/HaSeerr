"""Webhook receiver for Seerr status notifications."""

from __future__ import annotations

import logging

from aiohttp.web import Request, Response
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_WEBHOOK_ID, DOMAIN, EVT_REQUEST_STATUS_CHANGED

_LOGGER = logging.getLogger(__name__)

# Map Seerr's notification_type strings to our normalized status.
_STATUS_MAP = {
    "MEDIA_PENDING": "pending",
    "MEDIA_APPROVED": "approved",
    "MEDIA_AVAILABLE": "available",
    "MEDIA_DECLINED": "declined",
    "MEDIA_FAILED": "failed",
    "MEDIA_AUTO_APPROVED": "approved",
    "MEDIA_AUTO_REQUESTED": "pending",
}


async def _handle_webhook(hass: HomeAssistant, webhook_id: str, request: Request) -> Response:
    """Receive a Seerr webhook POST and emit a normalized HA event."""
    try:
        payload = await request.json()
    except Exception:
        return Response(status=400, text="invalid JSON")

    notif = payload.get("notification_type", "")
    status = _STATUS_MAP.get(notif)
    if status is None:
        # Ignore notifications we don't model (e.g. TEST_NOTIFICATION).
        return Response(status=200)

    media = payload.get("media", {}) or {}
    req = payload.get("request", {}) or {}
    hass.bus.async_fire(
        EVT_REQUEST_STATUS_CHANGED,
        {
            "tmdb_id": media.get("tmdbId"),
            "media_type": media.get("media_type"),
            "request_id": req.get("request_id"),
            "status": status,
            "requested_by": req.get("requestedBy_username"),
            "title": payload.get("subject"),
        },
    )
    return Response(status=200)


async def async_register_webhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the Seerr webhook with HA's webhook component."""
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if not webhook_id:
        _LOGGER.warning("Entry has no webhook_id; skipping webhook registration")
        return
    try:
        webhook.async_register(hass, DOMAIN, "HaSeerr Seerr webhook", webhook_id, _handle_webhook)
    except ValueError:
        # Already registered (idempotent).
        pass
    url = async_get_webhook_url(hass, entry)
    if url:
        _LOGGER.info(
            "HaSeerr webhook URL: %s — paste into Seerr → Settings → Notifications → Webhook",
            url,
        )


async def async_unregister_webhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unregister the Seerr webhook."""
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if not webhook_id:
        return
    try:
        webhook.async_unregister(hass, webhook_id)
    except (KeyError, ValueError):
        pass


def async_get_webhook_url(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Return the public webhook URL for the user to paste into Seerr."""
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if not webhook_id:
        return None
    return webhook.async_generate_url(hass, webhook_id)
