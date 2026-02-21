from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
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
    CONF_TRIGGER_DELAY_SECONDS,
    DEFAULT_ALARM_TYPES,
    DEFAULT_HOLD_SECONDS,
    DEFAULT_POLL_SECONDS,
    DEFAULT_TRIGGER_DELAY_SECONDS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

EVENT_LOG_FILENAME = "babycry_bridge_events.jsonl"
EVENT_LOG_MAX_BYTES = 10 * 1024 * 1024


@dataclass
class BabyCryData:
    is_on: bool
    events_in_window: int
    alarm_types_seen: list[int]
    cry_events_in_window: int
    last_checked: datetime
    last_triggered: datetime | None
    event_log_path: str


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
        self._trigger_delay_seconds = int(
            cfg.get(CONF_TRIGGER_DELAY_SECONDS, DEFAULT_TRIGGER_DELAY_SECONDS)
        )
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
        self._pending_since = 0
        self._event_log_path = Path(self.hass.config.path(EVENT_LOG_FILENAME))

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

    def _append_event_log(self, payload: dict) -> None:
        self._event_log_path.parent.mkdir(parents=True, exist_ok=True)
        if self._event_log_path.exists() and self._event_log_path.stat().st_size >= EVENT_LOG_MAX_BYTES:
            rotated = self._event_log_path.with_suffix(".jsonl.1")
            try:
                if rotated.exists():
                    rotated.unlink()
                self._event_log_path.rename(rotated)
            except OSError as err:
                _LOGGER.warning("Failed to rotate babycry event log: %s", err)

        with self._event_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    async def _log_poll(self, now: int, window_start: int, events: list[dict], cry_events: list[dict]) -> None:
        payload = {
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "camera_host": self._host,
            "window_start": window_start,
            "window_end": now,
            "event_count": len(events),
            "cry_event_count": len(cry_events),
            "alarm_types": sorted(self._alarm_types),
            "events": events,
        }
        await self.hass.async_add_executor_job(self._append_event_log, payload)

    def _read_recent_logs_sync(self, lines: int) -> list[dict]:
        if not self._event_log_path.exists():
            return []

        with self._event_log_path.open("r", encoding="utf-8") as handle:
            selected = handle.readlines()[-lines:]

        out: list[dict] = []
        for line in selected:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({"parse_error": True, "raw": line})
        return out

    async def async_get_recent_logs(self, lines: int = 100) -> list[dict]:
        safe_lines = max(1, min(lines, 1000))
        return await self.hass.async_add_executor_job(self._read_recent_logs_sync, safe_lines)

    async def _async_update_data(self) -> BabyCryData:
        try:
            cam = await self._ensure_cam()
            now = int(time.time())
            window_start = max(self._last_checked - 2, now - 120)

            events = await self.hass.async_add_executor_job(cam.getEvents, window_start, now)
            events = events or []
            alarm_types_seen = [e.get("alarm_type") for e in events if "alarm_type" in e]
            cry_events = [e for e in events if e.get("alarm_type") in self._alarm_types]
            try:
                await self._log_poll(now, window_start, events, cry_events)
            except Exception as log_err:  # pragma: no cover - defensive logging
                _LOGGER.warning("Failed writing babycry event log: %s", log_err)

            if cry_events:
                if self._pending_since == 0:
                    self._pending_since = now
                if (now - self._pending_since) >= self._trigger_delay_seconds:
                    self._last_on_at = now
            else:
                self._pending_since = 0

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
                event_log_path=str(self._event_log_path),
            )
        except Exception as err:
            self._cam = None
            raise UpdateFailed(f"Tapo update failed: {err}") from err
