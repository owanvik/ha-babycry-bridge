from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import time

from pytapo import Tapo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ALARM_TYPES,
    CONF_CLOUD_PASSWORD,
    CONF_HOLD_SECONDS,
    CONF_POLL_SECONDS,
    DEFAULT_ALARM_TYPES,
    DEFAULT_HOLD_SECONDS,
    DEFAULT_POLL_SECONDS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class BabyCryData:
    is_on: bool
    events_in_window: int
    alarm_types_seen: list[int]
    cry_events_in_window: int
    last_checked: datetime
    last_triggered: datetime | None


class BabyCryCoordinator(DataUpdateCoordinator[BabyCryData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        cfg = {**entry.data, **entry.options}
        self._host = cfg[CONF_HOST]
        self._user = cfg[CONF_USERNAME]
        self._password = cfg[CONF_PASSWORD]
        self._cloud_password = cfg.get(CONF_CLOUD_PASSWORD, "")
        self._poll_seconds = int(cfg.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS))
        self._hold_seconds = int(cfg.get(CONF_HOLD_SECONDS, DEFAULT_HOLD_SECONDS))
        self._alarm_types = {
            int(x.strip())
            for x in str(cfg.get(CONF_ALARM_TYPES, DEFAULT_ALARM_TYPES)).split(",")
            if x.strip().isdigit()
        }
        if not self._alarm_types:
            self._alarm_types = {7}

        self._cam: Tapo | None = None
        self._last_checked = int(time.time()) - 20
        self._last_on_at = 0

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=self._poll_seconds),
        )

    def _build_cam(self) -> Tapo:
        return Tapo(self._host, self._user, self._password, self._cloud_password)

    async def _ensure_cam(self) -> Tapo:
        if self._cam is None:
            self._cam = await self.hass.async_add_executor_job(self._build_cam)
        return self._cam

    async def _async_update_data(self) -> BabyCryData:
        try:
            cam = await self._ensure_cam()
            now = int(time.time())
            window_start = max(self._last_checked - 2, now - 120)

            events = await self.hass.async_add_executor_job(cam.getEvents, window_start, now)
            events = events or []
            alarm_types_seen = [e.get("alarm_type") for e in events if "alarm_type" in e]
            cry_events = [e for e in events if e.get("alarm_type") in self._alarm_types]

            if cry_events:
                self._last_on_at = now

            is_on = (now - self._last_on_at) <= self._hold_seconds
            self._last_checked = now

            last_triggered = (
                datetime.fromtimestamp(self._last_on_at, tz=timezone.utc)
                if self._last_on_at
                else None
            )

            return BabyCryData(
                is_on=is_on,
                events_in_window=len(events),
                alarm_types_seen=sorted({int(x) for x in alarm_types_seen if x is not None}),
                cry_events_in_window=len(cry_events),
                last_checked=datetime.now(timezone.utc),
                last_triggered=last_triggered,
            )
        except Exception as err:
            self._cam = None
            raise UpdateFailed(f"Tapo update failed: {err}") from err
