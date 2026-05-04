"""Tests for sensor.haseerr_status."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haseerr.const import (
    DOMAIN,
    OPT_USER_MAPPING,
    STATE_CONNECTED,
    STATE_ERROR,
    STATE_UNMAPPED_USER,
    SVC_REQUEST,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def _get_status_state(hass: HomeAssistant, entry_id: str):
    """Return the state of the haseerr status sensor for a given entry."""
    ent_reg = er.async_get(hass)
    unique_id = f"{entry_id}_status"
    entry = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entry is not None, f"sensor with unique_id {unique_id!r} not found in registry"
    return hass.states.get(entry)


async def test_sensor_connected(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={OPT_USER_MAPPING: {"ha-1": 4}},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = _get_status_state(hass, entry.entry_id)
    assert state is not None
    assert state.state == STATE_CONNECTED
    assert state.attributes["mapped_users_count"] == 1


async def test_sensor_unmapped_user(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={OPT_USER_MAPPING: {}},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = _get_status_state(hass, entry.entry_id)
    assert state is not None
    assert state.state == STATE_UNMAPPED_USER


async def test_sensor_entity_id_is_haseerr_status(hass: HomeAssistant):
    """Entity id must be sensor.haseerr_status, not sensor.status."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={OPT_USER_MAPPING: {"ha-1": 4}},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.haseerr_status")
    assert state is not None, "entity_id sensor.haseerr_status not found"


async def test_request_service_updates_sensor_attributes(hass: HomeAssistant):
    """After a request service call, last_request_id and last_request_at must be populated."""
    from homeassistant.core import Context

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={OPT_USER_MAPPING: {"ha-1": 4}},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ctx = Context(user_id="ha-1")
    with patch(
        "custom_components.haseerr.hub.SeerrClient.request",
        return_value={
            "request_id": 9999,
            "status": "pending",
            "seerr_user_id": 4,
            "seerr_user_display": "TestUser",
        },
    ):
        await hass.services.async_call(
            DOMAIN,
            SVC_REQUEST,
            {"tmdb_id": 12345, "media_type": "movie"},
            blocking=True,
            return_response=True,
            context=ctx,
        )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.haseerr_status")
    assert state is not None
    assert state.attributes["last_request_id"] == 9999
    assert state.attributes["last_request_at"] is not None
    assert state.attributes["last_error"] is None


async def test_failed_request_sets_last_error(hass: HomeAssistant):
    """After a failed request, last_error attribute must be populated."""
    from homeassistant.core import Context

    from custom_components.haseerr.hub import SeerrApiError

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={OPT_USER_MAPPING: {"ha-1": 4}},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ctx = Context(user_id="ha-1")
    with patch(
        "custom_components.haseerr.hub.SeerrClient.request",
        side_effect=SeerrApiError("500: Internal Server Error"),
    ):
        with pytest.raises(SeerrApiError):
            await hass.services.async_call(
                DOMAIN,
                SVC_REQUEST,
                {"tmdb_id": 12345, "media_type": "movie"},
                blocking=True,
                return_response=True,
                context=ctx,
            )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.haseerr_status")
    assert state is not None
    assert state.state == STATE_ERROR
    assert state.attributes["last_error"] is not None
