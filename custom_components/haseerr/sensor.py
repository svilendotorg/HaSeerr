"""Diagnostic sensor for haseerr."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    OPT_USER_MAPPING,
    STATE_CONNECTED,
    STATE_ERROR,
    STATE_UNMAPPED_USER,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    sensor = HaSeerrStatusSensor(entry)
    hass.data[DOMAIN][entry.entry_id]["sensor"] = sensor
    async_add_entities([sensor], update_before_add=False)


class HaSeerrStatusSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:movie-search"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="HaSeerr",
        )
        self._last_request_id: int | None = None
        self._last_request_at: str | None = None
        self._last_error: str | None = None

    @property
    def native_value(self) -> str:
        mapping = self._entry.options.get(OPT_USER_MAPPING, {})
        if self._last_error:
            return STATE_ERROR
        if not mapping:
            return STATE_UNMAPPED_USER
        return STATE_CONNECTED

    @property
    def extra_state_attributes(self) -> dict:
        mapping = self._entry.options.get(OPT_USER_MAPPING, {})
        return {
            "mapped_users_count": len(mapping),
            "last_request_id": self._last_request_id,
            "last_request_at": self._last_request_at,
            "last_error": self._last_error,
        }

    def record_request(self, request_id: int) -> None:
        """Called by the request service on success."""
        self._last_request_id = request_id
        self._last_request_at = datetime.now(UTC).isoformat()
        self._last_error = None
        self.async_write_ha_state()

    def record_error(self, error: str) -> None:
        """Called by the request service on Seerr error."""
        self._last_error = error
        self.async_write_ha_state()
