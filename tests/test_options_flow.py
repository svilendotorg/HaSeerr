"""Tests for options flow (user-mapping wizard)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haseerr.const import DOMAIN, OPT_USER_MAPPING


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def configured_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://test.local:5055", "api_key": "abc"},
        options={},
    )
    entry.add_to_hass(hass)
    return entry


async def test_options_flow_renders_with_suggestions(
    hass: HomeAssistant, configured_entry: MockConfigEntry
):
    fake_ha_users = [
        SimpleNamespace(id="ha-1", name="Bob", credentials=[], system_generated=False),
        SimpleNamespace(id="ha-2", name="Alice", credentials=[], system_generated=False),
    ]
    fake_seerr_users = [
        {"id": 4, "display_name": "Bob", "email": None},
        {"id": 1, "display_name": "Alice", "email": None},
    ]
    with (
        patch.object(hass.auth, "async_get_users", return_value=fake_ha_users),
        patch(
            "custom_components.haseerr.hub.SeerrClient.list_users",
            return_value=fake_seerr_users,
        ),
    ):
        result = await hass.config_entries.options.async_init(configured_entry.entry_id)
        assert result["type"] == "form"
        # Schema uses indexed keys (user_0, user_1, ...) so labels can be translated
        schema_keys = {str(k) for k in result["data_schema"].schema}
        assert "user_0" in schema_keys
        assert "user_1" in schema_keys
        assert "web_url" in schema_keys
        # description_placeholders carry the friendly labels
        placeholders = result.get("description_placeholders") or {}
        assert "Bob" in placeholders.get("user_0", "")
        assert "Alice" in placeholders.get("user_1", "")


async def test_options_flow_save_persists_mapping(
    hass: HomeAssistant, configured_entry: MockConfigEntry
):
    fake_ha_users = [SimpleNamespace(id="ha-1", name="Bob", credentials=[], system_generated=False)]
    fake_seerr_users = [{"id": 4, "display_name": "Bob", "email": None}]

    with (
        patch.object(hass.auth, "async_get_users", return_value=fake_ha_users),
        patch(
            "custom_components.haseerr.hub.SeerrClient.list_users",
            return_value=fake_seerr_users,
        ),
    ):
        result = await hass.config_entries.options.async_init(configured_entry.entry_id)
        # Submit form: indexed key user_0 → seerr id 4
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"user_0": 4})

    assert result["type"] == "create_entry"
    # Internally the indexed key is translated back to the HA user_id
    assert result["data"][OPT_USER_MAPPING] == {"ha-1": 4}
    assert result["data"]["web_url"] == ""


async def test_options_flow_persists_web_url(
    hass: HomeAssistant, configured_entry: MockConfigEntry
):
    """User-provided web_url is normalized (stripped, no trailing slash) and persisted."""
    fake_ha_users = [SimpleNamespace(id="ha-1", name="Bob", credentials=[], system_generated=False)]
    fake_seerr_users = [{"id": 4, "display_name": "Bob", "email": None}]

    with (
        patch.object(hass.auth, "async_get_users", return_value=fake_ha_users),
        patch(
            "custom_components.haseerr.hub.SeerrClient.list_users",
            return_value=fake_seerr_users,
        ),
    ):
        result = await hass.config_entries.options.async_init(configured_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"user_0": 4, "web_url": "  https://seerr.example.com/  "},
        )

    assert result["data"]["web_url"] == "https://seerr.example.com"
    assert result["data"][OPT_USER_MAPPING] == {"ha-1": 4}


async def test_options_flow_skip_sentinel_excluded_from_mapping(
    hass: HomeAssistant, configured_entry: MockConfigEntry
):
    """Users left at -- skip -- (sentinel -1) are excluded from the saved mapping."""
    fake_ha_users = [
        SimpleNamespace(id="ha-1", name="Bob", credentials=[], system_generated=False),
        SimpleNamespace(id="ha-2", name="Guest", credentials=[], system_generated=False),
    ]
    fake_seerr_users = [{"id": 4, "display_name": "Bob", "email": None}]

    with (
        patch.object(hass.auth, "async_get_users", return_value=fake_ha_users),
        patch(
            "custom_components.haseerr.hub.SeerrClient.list_users",
            return_value=fake_seerr_users,
        ),
    ):
        result = await hass.config_entries.options.async_init(configured_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"user_0": 4, "user_1": -1}
        )

    assert result["data"][OPT_USER_MAPPING] == {"ha-1": 4}  # ha-2 dropped
