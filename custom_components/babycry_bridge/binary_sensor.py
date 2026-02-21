from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import BabyCryCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BabyCryCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BabyCryBinarySensor(coordinator, entry)])


class BabyCryBinarySensor(CoordinatorEntity[BabyCryCoordinator], BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.SOUND
    _attr_has_entity_name = True
    _attr_icon = "mdi:emoticon-cry-outline"

    def __init__(self, coordinator: BabyCryCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"babycry_direct_{entry.entry_id}"
        self._attr_name = DEFAULT_NAME

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_on

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "source": "tapo_direct",
            "events_in_window": data.events_in_window,
            "alarm_types_seen": data.alarm_types_seen,
            "cry_events_in_window": data.cry_events_in_window,
            "last_checked": data.last_checked.isoformat(),
            "last_triggered": data.last_triggered.isoformat() if data.last_triggered else None,
            "event_log_path": data.event_log_path,
            "hold_seconds": self.coordinator._hold_seconds,
            "trigger_delay_seconds": self.coordinator._trigger_delay_seconds,
        }
