"""Options flow — user mapping wizard."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, CONF_URL, OPT_USER_MAPPING, OPT_WEB_URL
from .hub import SeerrClient
from .matching import suggest_pairings

NO_MAPPING_SENTINEL = -1  # represents "skip" in dropdowns

# strings.json has data labels user_0 .. user_19; rendering more than this falls
# back to the raw key, but for typical households 20 is plenty.
MAX_LABELLED_USERS = 20


class HaSeerrOptionsFlow(config_entries.OptionsFlow):
    """Render a row per HA user with a Seerr-user dropdown pre-filled.

    The schema uses indexed keys (user_0, user_1, …) so the form labels can be
    sourced from translations and substituted via description_placeholders. HA
    user IDs (UUIDs) are kept in `_index_to_user_id` to map back on save.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._ha_users: list[dict] = []
        self._seerr_users: list[dict] = []
        self._suggestions: dict[str, tuple[int | None, str]] = {}
        self._index_to_user_id: list[str] = []

    @property
    def config_entry(self) -> config_entries.ConfigEntry:
        return self._config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            web_url = (user_input.pop(OPT_WEB_URL, "") or "").strip().rstrip("/")
            mapping: dict[str, int] = {}
            for key, value in user_input.items():
                if not key.startswith("user_") or value is None:
                    continue
                idx = int(key.split("_", 1)[1])
                if idx >= len(self._index_to_user_id):
                    continue
                seerr_id = int(value)
                if seerr_id == NO_MAPPING_SENTINEL:
                    continue
                mapping[self._index_to_user_id[idx]] = seerr_id
            return self.async_create_entry(
                title="",
                data={OPT_USER_MAPPING: mapping, OPT_WEB_URL: web_url},
            )

        # Fetch both sides
        await self._load_users()
        self._suggestions = suggest_pairings(ha_users=self._ha_users, seerr_users=self._seerr_users)

        return self.async_show_form(
            step_id="init",
            data_schema=self._build_schema(),
            description_placeholders=self._build_placeholders(),
        )

    async def _load_users(self) -> None:
        ha_users = await self.hass.auth.async_get_users()
        self._ha_users = [
            {
                "id": u.id,
                "name": u.name,
                "email": next((c.data.get("email") for c in u.credentials if c.data), None),
            }
            for u in ha_users
            if not getattr(u, "system_generated", False)
        ]
        self._index_to_user_id = [u["id"] for u in self._ha_users]

        session = async_get_clientsession(self.hass)
        client = SeerrClient(
            session,
            self._config_entry.data[CONF_URL],
            self._config_entry.data[CONF_API_KEY],
        )
        self._seerr_users = await client.list_users()

    def _build_schema(self) -> vol.Schema:
        existing = self._config_entry.options.get(OPT_USER_MAPPING, {})
        existing_web_url = self._config_entry.options.get(OPT_WEB_URL, "")

        # Seerr user choices
        choices: dict[int, str] = {NO_MAPPING_SENTINEL: "-- skip --"}
        for s in self._seerr_users:
            choices[int(s["id"])] = f"{s['display_name']} (id={s['id']})"

        schema_dict: dict = {}
        # Public web URL first
        schema_dict[vol.Optional(OPT_WEB_URL, default=existing_web_url)] = str
        # One entry per HA user, keyed by index for translatable labels
        for idx, ha in enumerate(self._ha_users):
            default = existing.get(
                ha["id"],
                self._suggestions.get(ha["id"], (NO_MAPPING_SENTINEL, ""))[0]
                or NO_MAPPING_SENTINEL,
            )
            key = f"user_{idx}"
            schema_dict[
                vol.Required(
                    key,
                    default=default,
                    description={"suggested_value": default},
                )
            ] = vol.In(choices)
        return vol.Schema(schema_dict)

    def _build_placeholders(self) -> dict[str, str]:
        """Map user_<idx> to a friendly 'Name (email)' label for the form."""
        out: dict[str, str] = {}
        for idx, ha in enumerate(self._ha_users[:MAX_LABELLED_USERS]):
            label = ha["name"] or "(unnamed user)"
            if ha.get("email"):
                label = f"{label} ({ha['email']})"
            out[f"user_{idx}"] = label
        # Fill any unused labels so HA's translator doesn't error on missing placeholders
        for idx in range(len(self._ha_users), MAX_LABELLED_USERS):
            out[f"user_{idx}"] = ""
        return out
