"""Config flow for haseerr."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, CONF_URL, CONF_WEBHOOK_ID, DOMAIN
from .hub import SeerrAuthError, SeerrClient, SeerrConnectionError, SeerrError

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_KEY): str,
    }
)


class HaSeerrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = SeerrClient(session, user_input[CONF_URL], user_input[CONF_API_KEY])
            try:
                status = await client.status()
            except SeerrAuthError:
                errors["base"] = "invalid_auth"
            except SeerrConnectionError:
                errors["base"] = "cannot_connect"
            except SeerrError:
                errors["base"] = "unknown"
            else:
                fingerprint = (
                    status.get("commitTag") or status.get("version") or user_input[CONF_URL]
                )
                unique_id = f"{user_input[CONF_URL].lower().rstrip('/')}|{fingerprint}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                user_input[CONF_WEBHOOK_ID] = secrets.token_hex(32)
                return self.async_create_entry(title="HaSeerr", data=user_input)

        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA, errors=errors)

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry):
        from .options_flow import HaSeerrOptionsFlow

        return HaSeerrOptionsFlow(config_entry)
