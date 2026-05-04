"""Full-stack integration tests for haseerr services.

These tests do NOT patch SeerrClient methods — they go through the real client
and mock at the HTTP layer with aioresponses. This catches bugs that would only
surface against a real Seerr instance (URL encoding, response-shape regressions,
None-body responses, etc.).
"""

from __future__ import annotations

import pytest
from aioresponses import aioresponses
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haseerr.const import (
    DOMAIN,
    OPT_USER_MAPPING,
    SVC_APPROVE_REQUEST,
    SVC_DECLINE_REQUEST,
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


async def test_search_handler_full_stack(hass: HomeAssistant, configured, fixture):
    """search service → SeerrClient.search → real GET to /api/v1/search."""
    with aioresponses() as m:
        m.get(
            "http://test.local:5055/api/v1/search?query=Dune",
            payload=fixture("search"),
            status=200,
        )
        out = await hass.services.async_call(
            DOMAIN,
            SVC_SEARCH,
            {"query": "Dune"},
            blocking=True,
            return_response=True,
        )
    # 4 raw → 3 after person filter
    assert len(out["results"]) == 3
    assert {r["media_type"] for r in out["results"]} == {"movie", "tv"}


async def test_search_query_with_spaces_uses_percent_encoding(hass: HomeAssistant, configured):
    """Regression: Seerr rejects '+' for spaces; we must use %20."""
    with aioresponses() as m:
        m.get(
            "http://test.local:5055/api/v1/search?query=Dune%20Part%20Two",
            payload={"results": []},
            status=200,
        )
        out = await hass.services.async_call(
            DOMAIN,
            SVC_SEARCH,
            {"query": "Dune Part Two"},
            blocking=True,
            return_response=True,
        )
        # If our SeerrClient regressed to '+' encoding, aioresponses would 404
        # because it didn't match our pattern; service call would raise.
    assert out["results"] == []
    assert out["seerr_url"] == "http://test.local:5055"


async def test_request_handler_full_stack(hass: HomeAssistant, configured, fixture):
    """request service → SeerrClient.request → real POST. Asserts event payload."""
    events = []
    hass.bus.async_listen("haseerr_request_submitted", lambda e: events.append(e))
    ctx = Context(user_id="ha-1")
    with aioresponses() as m:
        m.post(
            "http://test.local:5055/api/v1/request",
            payload=fixture("request_movie"),
            status=201,
        )
        out = await hass.services.async_call(
            DOMAIN,
            SVC_REQUEST,
            {"tmdb_id": 693134, "media_type": "movie", "title": "Dune: Part Two"},
            blocking=True,
            return_response=True,
            context=ctx,
        )
    assert out["request_id"] == 1247
    assert out["status"] == "pending"
    await hass.async_block_till_done()
    assert len(events) == 1
    evt = events[0].data
    assert evt["title"] == "Dune: Part Two"
    assert evt["tmdb_id"] == 693134
    assert evt["seerr_user_id"] == 4


async def test_approve_204_no_content(hass: HomeAssistant, configured):
    """Regression: Seerr's approve endpoint returns 204; SeerrClient must not crash."""
    with aioresponses() as m:
        m.post(
            "http://test.local:5055/api/v1/request/1247/approve",
            status=204,
        )
        out = await hass.services.async_call(
            DOMAIN,
            SVC_APPROVE_REQUEST,
            {"request_id": 1247},
            blocking=True,
            return_response=True,
        )
    assert out == {"ok": True, "status": "approved"}


async def test_decline_with_reason_full_stack(hass: HomeAssistant, configured):
    """decline service → POST with json body containing reason."""
    with aioresponses() as m:
        m.post(
            "http://test.local:5055/api/v1/request/1247/decline",
            payload={"id": 1247, "status": 3},
            status=200,
        )
        out = await hass.services.async_call(
            DOMAIN,
            SVC_DECLINE_REQUEST,
            {"request_id": 1247, "reason": "too violent"},
            blocking=True,
            return_response=True,
        )
    assert out == {"ok": True, "status": "declined"}
