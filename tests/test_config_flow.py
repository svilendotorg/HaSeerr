"""Tests for config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.haseerr.const import CONF_WEBHOOK_ID, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def test_flow_happy_path(hass: HomeAssistant):
    with patch(
        "custom_components.haseerr.hub.SeerrClient.status",
        return_value={"version": "2.0.2"},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"url": "http://test.local:5055", "api_key": "abc"},
        )
        assert result["type"] == "create_entry"
        assert result["title"] == "HaSeerr"
        data = result["data"]
        assert data["url"] == "http://test.local:5055"
        assert data["api_key"] == "abc"
        # webhook_id is auto-generated: 64 hex chars
        assert CONF_WEBHOOK_ID in data
        assert len(data[CONF_WEBHOOK_ID]) == 64
        assert all(c in "0123456789abcdef" for c in data[CONF_WEBHOOK_ID])


async def test_flow_invalid_auth(hass: HomeAssistant):
    from custom_components.haseerr.hub import SeerrAuthError

    with patch(
        "custom_components.haseerr.hub.SeerrClient.status",
        side_effect=SeerrAuthError("nope"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"url": "http://test.local:5055", "api_key": "bad"},
        )
        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_auth"}


async def test_flow_unique_id_uses_fingerprint(hass: HomeAssistant):
    with patch(
        "custom_components.haseerr.hub.SeerrClient.status",
        return_value={"version": "2.0.2", "commitTag": "abc1234"},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"url": "http://test.local:5055", "api_key": "abc"},
        )
        assert result["type"] == "create_entry"
        # Verify the entry's unique_id contains both URL and the commitTag fingerprint
        entries = hass.config_entries.async_entries(DOMAIN)
        assert any("abc1234" in (e.unique_id or "") for e in entries)


async def test_flow_cannot_connect(hass: HomeAssistant):
    from custom_components.haseerr.hub import SeerrConnectionError

    with patch(
        "custom_components.haseerr.hub.SeerrClient.status",
        side_effect=SeerrConnectionError("dns"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"url": "http://nope.local:5055", "api_key": "abc"},
        )
        assert result["errors"] == {"base": "cannot_connect"}
