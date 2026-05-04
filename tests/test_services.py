"""Tests for haseerr services."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haseerr.const import (
    DOMAIN,
    OPT_USER_MAPPING,
    SVC_REQUEST,
    SVC_SEARCH,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
async def configured(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://test.local:5055", "api_key": "abc"},
        options={OPT_USER_MAPPING: {"ha-1": 4}},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry


async def test_search_service_returns_results(hass: HomeAssistant, configured):
    sample = [{"tmdb_id": 1, "title": "X", "media_type": "movie"}]
    with patch("custom_components.haseerr.hub.SeerrClient.search", return_value=sample):
        out = await hass.services.async_call(
            DOMAIN,
            SVC_SEARCH,
            {"query": "X"},
            blocking=True,
            return_response=True,
        )
    assert out["results"] == sample
    assert out["seerr_url"] == "http://test.local:5055"


async def test_search_service_uses_web_url_when_configured(hass: HomeAssistant):
    """When web_url is set in options, search response prefers it over the API URL."""
    from custom_components.haseerr.const import OPT_USER_MAPPING, OPT_WEB_URL

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://test.local:5055", "api_key": "abc"},
        options={
            OPT_USER_MAPPING: {"ha-1": 4},
            OPT_WEB_URL: "https://seerr.public.example.com",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sample = [{"tmdb_id": 1, "title": "X", "media_type": "movie"}]
    with patch("custom_components.haseerr.hub.SeerrClient.search", return_value=sample):
        out = await hass.services.async_call(
            DOMAIN,
            SVC_SEARCH,
            {"query": "X"},
            blocking=True,
            return_response=True,
        )
    assert out["seerr_url"] == "https://seerr.public.example.com"


async def test_request_resolves_mapped_user(hass: HomeAssistant, configured):
    fake_user = SimpleNamespace(id="ha-1", is_admin=False)
    from homeassistant.core import Context

    ctx = Context(user_id="ha-1")
    with (
        patch.object(hass.auth, "async_get_user", return_value=fake_user),
        patch(
            "custom_components.haseerr.hub.SeerrClient.request",
            return_value={
                "request_id": 1247,
                "status": "pending",
                "seerr_user_id": 4,
                "seerr_user_display": "Bob",
            },
        ) as m_req,
    ):
        out = await hass.services.async_call(
            DOMAIN,
            SVC_REQUEST,
            {"tmdb_id": 693134, "media_type": "movie"},
            blocking=True,
            return_response=True,
            context=ctx,
        )
    m_req.assert_called_once()
    kwargs = m_req.call_args.kwargs
    assert kwargs["user_id"] == 4
    assert out["status"] == "pending"


async def test_request_event_includes_title(hass: HomeAssistant, configured):
    fake_user = SimpleNamespace(id="ha-1", is_admin=False)
    from homeassistant.core import Context

    ctx = Context(user_id="ha-1")
    events = []
    hass.bus.async_listen("haseerr_request_submitted", lambda e: events.append(e))
    with (
        patch.object(hass.auth, "async_get_user", return_value=fake_user),
        patch(
            "custom_components.haseerr.hub.SeerrClient.request",
            return_value={
                "request_id": 1247,
                "status": "pending",
                "seerr_user_id": 4,
                "seerr_user_display": "Bob",
            },
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            SVC_REQUEST,
            {"tmdb_id": 693134, "media_type": "movie", "title": "Dune: Part Two"},
            blocking=True,
            return_response=True,
            context=ctx,
        )
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["title"] == "Dune: Part Two"


async def test_request_rejects_unmapped_user(hass: HomeAssistant, configured):
    from homeassistant.core import Context

    ctx = Context(user_id="ha-other")
    with patch("custom_components.haseerr.hub.SeerrClient.request"):
        with pytest.raises(Exception, match="not mapped"):
            await hass.services.async_call(
                DOMAIN,
                SVC_REQUEST,
                {"tmdb_id": 1, "media_type": "movie"},
                blocking=True,
                context=ctx,
                return_response=True,
            )
