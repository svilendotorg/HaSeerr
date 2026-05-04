"""Voice-intent handler for haseerr (multi-turn)."""

from __future__ import annotations

import logging
import time
from typing import ClassVar

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_URL,
    DOMAIN,
    PENDING_CONFIRM_KEY,
    PENDING_CONFIRM_TTL_S,
    SVC_REQUEST,
)
from .hub import SeerrClient

_LOGGER = logging.getLogger(__name__)


def _is_bg(intent_obj) -> bool:
    return (intent_obj.language or "en").lower().startswith("bg")


class RequestMediaIntentHandler(intent.IntentHandler):
    intent_type = "RequestMedia"
    slot_schema: ClassVar[dict] = {"title": str, "season": str}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        slots = self.async_validate_slots(intent_obj.slots)
        title = slots["title"]["value"]

        hass = intent_obj.hass
        entries = hass.config_entries.async_entries(DOMAIN)
        response = intent_obj.create_response()
        bg = _is_bg(intent_obj)
        if not entries:
            msg = (
                "HaSeerr не е конфигуриран." if bg else "HaSeerr is not configured."  # noqa: RUF001
            )
            response.async_set_speech(msg)
            return response

        entry = entries[0]
        session = async_get_clientsession(hass)
        client = SeerrClient(session, entry.data[CONF_URL], entry.data[CONF_API_KEY])
        results = await client.search(title, limit=3)

        if not results:
            msg = (
                "Не намерих нищо подходящо."  # noqa: RUF001
                if bg
                else "I couldn't find anything matching that."
            )
            response.async_set_speech(msg)
            return response

        top = results[0]
        # Store pending state, keyed by user (or "_anon" if no user context)
        user_id = (intent_obj.context.user_id if intent_obj.context else None) or "_anon"
        hass.data.setdefault(DOMAIN, {}).setdefault(PENDING_CONFIRM_KEY, {})
        hass.data[DOMAIN][PENDING_CONFIRM_KEY][user_id] = {
            "tmdb_id": top["tmdb_id"],
            "media_type": top["media_type"],
            "title": top["title"],
            "expires_at": time.time() + PENDING_CONFIRM_TTL_S,
        }

        if bg:
            media_word = "филм" if top["media_type"] == "movie" else "сериал"
            speech = f"Имаш предвид {top['title']} от {top['year']}, {media_word}а?"  # noqa: RUF001
        else:
            media_word = "movie" if top["media_type"] == "movie" else "show"
            speech = f"Did you mean {top['title']} from {top['year']}, the {media_word}?"
        response.async_set_speech(speech)
        return response


class ConfirmRequestIntentHandler(intent.IntentHandler):
    intent_type = "ConfirmRequest"
    slot_schema: ClassVar[dict] = {}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass = intent_obj.hass
        bg = _is_bg(intent_obj)
        response = intent_obj.create_response()

        user_id = (intent_obj.context.user_id if intent_obj.context else None) or "_anon"
        pending_all = hass.data.get(DOMAIN, {}).get(PENDING_CONFIRM_KEY, {})
        pending = pending_all.pop(user_id, None)

        if not pending or time.time() > pending["expires_at"]:
            msg = "Няма какво да потвърдя." if bg else "Nothing to confirm."
            response.async_set_speech(msg)
            return response

        try:
            await hass.services.async_call(
                DOMAIN,
                SVC_REQUEST,
                {
                    "tmdb_id": pending["tmdb_id"],
                    "media_type": pending["media_type"],
                    "title": pending["title"],
                },
                blocking=True,
                return_response=True,
                context=intent_obj.context,
            )
        except Exception as err:
            _LOGGER.warning("ConfirmRequest submit failed: %s", err)
            msg = (
                f"Заявката за {pending['title']} не успя."
                if bg
                else f"Failed to request {pending['title']}."
            )
            response.async_set_speech(msg)
            return response

        msg = f"Заявих {pending['title']}." if bg else f"Requested {pending['title']}."
        response.async_set_speech(msg)
        return response


class CancelRequestIntentHandler(intent.IntentHandler):
    intent_type = "CancelRequest"
    slot_schema: ClassVar[dict] = {}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass = intent_obj.hass
        bg = _is_bg(intent_obj)
        user_id = (intent_obj.context.user_id if intent_obj.context else None) or "_anon"
        pending_all = hass.data.get(DOMAIN, {}).get(PENDING_CONFIRM_KEY, {})
        pending_all.pop(user_id, None)

        response = intent_obj.create_response()
        msg = "Отказано." if bg else "Cancelled."
        response.async_set_speech(msg)
        return response


async def async_setup_intents(hass: HomeAssistant) -> None:
    hass.data.setdefault(DOMAIN, {}).setdefault(PENDING_CONFIRM_KEY, {})
    intent.async_register(hass, RequestMediaIntentHandler())
    intent.async_register(hass, ConfirmRequestIntentHandler())
    intent.async_register(hass, CancelRequestIntentHandler())
