"""Tests for the haseerr Seerr webhook receiver."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haseerr.const import (
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVT_REQUEST_STATUS_CHANGED,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
async def configured(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k", CONF_WEBHOOK_ID: "abc123def456"},
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry


async def _post_webhook(hass: HomeAssistant, webhook_id: str, payload: dict, hass_client_no_auth):
    """Helper: POST a JSON payload to the registered webhook endpoint."""
    client = await hass_client_no_auth()
    return await client.post(f"/api/webhook/{webhook_id}", json=payload)


async def test_webhook_emits_event_on_approval(
    hass: HomeAssistant, configured, hass_client_no_auth
):
    events = []
    hass.bus.async_listen(EVT_REQUEST_STATUS_CHANGED, lambda e: events.append(e))
    payload = {
        "notification_type": "MEDIA_APPROVED",
        "subject": "Dune: Part Two",
        "media": {"media_type": "movie", "tmdbId": 693134},
        "request": {"request_id": 1247, "requestedBy_username": "Bob"},
    }
    resp = await _post_webhook(hass, "abc123def456", payload, hass_client_no_auth)
    assert resp.status == 200
    await hass.async_block_till_done()
    assert len(events) == 1
    e = events[0].data
    assert e["status"] == "approved"
    assert e["title"] == "Dune: Part Two"
    assert e["request_id"] == 1247
    assert e["tmdb_id"] == 693134
    assert e["requested_by"] == "Bob"


async def test_webhook_ignores_unknown_notification_type(
    hass: HomeAssistant, configured, hass_client_no_auth
):
    events = []
    hass.bus.async_listen(EVT_REQUEST_STATUS_CHANGED, lambda e: events.append(e))
    payload = {"notification_type": "TEST_NOTIFICATION"}
    resp = await _post_webhook(hass, "abc123def456", payload, hass_client_no_auth)
    assert resp.status == 200
    await hass.async_block_till_done()
    assert events == []


async def test_webhook_handles_available(hass: HomeAssistant, configured, hass_client_no_auth):
    events = []
    hass.bus.async_listen(EVT_REQUEST_STATUS_CHANGED, lambda e: events.append(e))
    payload = {
        "notification_type": "MEDIA_AVAILABLE",
        "subject": "The Bear",
        "media": {"media_type": "tv", "tmdbId": 136315},
        "request": {"request_id": 2000, "requestedBy_username": "Alice"},
    }
    resp = await _post_webhook(hass, "abc123def456", payload, hass_client_no_auth)
    assert resp.status == 200
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["status"] == "available"


async def test_webhook_invalid_json_returns_400(
    hass: HomeAssistant, configured, hass_client_no_auth
):
    client = await hass_client_no_auth()
    resp = await client.post("/api/webhook/abc123def456", data="not-json")
    assert resp.status == 400
