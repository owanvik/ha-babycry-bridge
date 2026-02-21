from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.service import SupportsResponse

from .const import DOMAIN, PLATFORMS
from .coordinator import BabyCryCoordinator


type BabyCryConfigEntry = ConfigEntry

SERVICE_GET_RECENT_LOGS = "get_recent_logs"
GET_RECENT_LOGS_SCHEMA = vol.Schema({vol.Optional("lines", default=200): vol.Coerce(int)})


async def async_setup_entry(hass: HomeAssistant, entry: BabyCryConfigEntry) -> bool:
    coordinator = BabyCryCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    if not hass.services.has_service(DOMAIN, SERVICE_GET_RECENT_LOGS):

        async def _handle_get_recent_logs(call: ServiceCall) -> dict:
            lines = int(call.data.get("lines", 200))
            coordinators: dict[str, BabyCryCoordinator] = hass.data.get(DOMAIN, {})
            if not coordinators:
                return {"entries": [], "count": 0}

            result_entries: list[dict] = []
            for entry_id, item in coordinators.items():
                logs = await item.async_get_recent_logs(lines)
                result_entries.append(
                    {
                        "entry_id": entry_id,
                        "camera_host": item._host,
                        "log_path": str(item._event_log_path),
                        "records": logs,
                        "count": len(logs),
                    }
                )

            return {"entries": result_entries, "count": len(result_entries)}

        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_RECENT_LOGS,
            _handle_get_recent_logs,
            schema=GET_RECENT_LOGS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BabyCryConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, SERVICE_GET_RECENT_LOGS):
            hass.services.async_remove(DOMAIN, SERVICE_GET_RECENT_LOGS)
    return ok


async def async_reload_entry(hass: HomeAssistant, entry: BabyCryConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
