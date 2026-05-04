"""Tests for haseerr voice intent."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent

from custom_components.haseerr.intent import async_setup_intents


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def test_intent_top_result(hass: HomeAssistant):
    sample = [
        {
            "tmdb_id": 693134,
            "title": "Dune: Part Two",
            "year": 2024,
            "media_type": "movie",
            "overview": "x",
            "poster_url": None,
            "status": "not_requested",
        },
    ]
    # Register a fake config entry so the intent handler can find it
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.haseerr.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={},
    )
    entry.add_to_hass(hass)

    with patch("custom_components.haseerr.hub.SeerrClient.search", return_value=sample):
        await async_setup_intents(hass)
        response = await intent.async_handle(
            hass, "test", "RequestMedia", {"title": {"value": "Dune Part Two"}}
        )
    text = response.speech["plain"]["speech"]
    assert "Dune: Part Two" in text
    assert "2024" in text


async def test_intent_top_result_bg(hass: HomeAssistant):
    sample = [
        {
            "tmdb_id": 693134,
            "title": "Дюн: Част втора",
            "year": 2024,
            "media_type": "movie",
            "overview": "x",
            "poster_url": None,
            "status": "not_requested",
        },
    ]
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.haseerr.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.haseerr.hub.SeerrClient.search", return_value=sample):
        await async_setup_intents(hass)
        response = await intent.async_handle(
            hass,
            "test",
            "RequestMedia",
            {"title": {"value": "Дюн"}},
            language="bg",
        )
    text = response.speech["plain"]["speech"]
    assert "Имаш предвид" in text
    assert "Дюн: Част втора" in text
    assert "филм" in text


async def test_intent_no_results(hass: HomeAssistant):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.haseerr.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.haseerr.hub.SeerrClient.search", return_value=[]):
        await async_setup_intents(hass)
        response = await intent.async_handle(
            hass, "test", "RequestMedia", {"title": {"value": "Nothing matches this"}}
        )
    text = response.speech["plain"]["speech"].lower()
    assert "couldn't find" in text or "no results" in text or "nothing" in text


async def test_intent_multi_turn_confirm(hass: HomeAssistant):
    """Turn 1 (RequestMedia) primes pending state; turn 2 (ConfirmRequest) submits."""
    from homeassistant.core import Context
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.haseerr.const import DOMAIN, OPT_USER_MAPPING

    sample = [
        {
            "tmdb_id": 693134,
            "title": "Dune: Part Two",
            "year": 2024,
            "media_type": "movie",
            "overview": "x",
            "poster_url": None,
            "status": "not_requested",
        },
    ]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={OPT_USER_MAPPING: {"ha-1": 4}},
    )
    entry.add_to_hass(hass)
    ctx = Context(user_id="ha-1")
    fake_user = SimpleNamespace(id="ha-1", is_admin=False)

    with (
        patch("custom_components.haseerr.hub.SeerrClient.search", return_value=sample),
        patch.object(hass.auth, "async_get_user", return_value=fake_user),
        patch(
            "custom_components.haseerr.hub.SeerrClient.request",
            return_value={
                "request_id": 99,
                "status": "pending",
                "seerr_user_id": 4,
                "seerr_user_display": "Bob",
            },
        ) as m_req,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_intents(hass)

        r1 = await intent.async_handle(
            hass,
            "test",
            "RequestMedia",
            {"title": {"value": "Dune Part Two"}},
            language="en",
            context=ctx,
        )
        assert "Did you mean" in r1.speech["plain"]["speech"]

        r2 = await intent.async_handle(
            hass,
            "test",
            "ConfirmRequest",
            {},
            language="en",
            context=ctx,
        )
        assert "Requested Dune: Part Two" in r2.speech["plain"]["speech"]

    m_req.assert_called_once()


async def test_intent_multi_turn_cancel(hass: HomeAssistant):
    """CancelRequest after RequestMedia clears pending without submitting."""
    from homeassistant.core import Context
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.haseerr.const import DOMAIN

    sample = [
        {
            "tmdb_id": 693134,
            "title": "Dune: Part Two",
            "year": 2024,
            "media_type": "movie",
            "overview": "x",
            "poster_url": None,
            "status": "not_requested",
        },
    ]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={},
    )
    entry.add_to_hass(hass)
    ctx = Context(user_id="ha-1")

    with (
        patch("custom_components.haseerr.hub.SeerrClient.search", return_value=sample),
        patch("custom_components.haseerr.hub.SeerrClient.request") as m_req,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_intents(hass)

        await intent.async_handle(
            hass,
            "test",
            "RequestMedia",
            {"title": {"value": "Dune Part Two"}},
            language="en",
            context=ctx,
        )
        r2 = await intent.async_handle(
            hass,
            "test",
            "CancelRequest",
            {},
            language="en",
            context=ctx,
        )
        assert "Cancelled" in r2.speech["plain"]["speech"]

    m_req.assert_not_called()


async def test_intent_confirm_with_no_pending(hass: HomeAssistant):
    """ConfirmRequest with empty state returns 'Nothing to confirm.'"""
    from homeassistant.core import Context
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.haseerr.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await async_setup_intents(hass)

    ctx = Context(user_id="ha-1")
    r = await intent.async_handle(
        hass,
        "test",
        "ConfirmRequest",
        {},
        language="en",
        context=ctx,
    )
    assert "Nothing to confirm" in r.speech["plain"]["speech"]


async def test_intent_pending_expires(hass: HomeAssistant):
    """Expired pending entry → 'Nothing to confirm.'"""
    import time as _t

    from homeassistant.core import Context
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.haseerr.const import DOMAIN, PENDING_CONFIRM_KEY

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://x:5055", "api_key": "k"},
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await async_setup_intents(hass)

    ctx = Context(user_id="ha-1")
    hass.data[DOMAIN][PENDING_CONFIRM_KEY]["ha-1"] = {
        "tmdb_id": 1,
        "media_type": "movie",
        "title": "X",
        "expires_at": _t.time() - 1,
    }
    r = await intent.async_handle(
        hass,
        "test",
        "ConfirmRequest",
        {},
        language="en",
        context=ctx,
    )
    assert "Nothing to confirm" in r.speech["plain"]["speech"]
