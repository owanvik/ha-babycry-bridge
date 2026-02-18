from __future__ import annotations

import voluptuous as vol
from pytapo import Tapo

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

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


def _schema(data: dict | None = None) -> vol.Schema:
    data = data or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=data.get(CONF_HOST, "")): str,
            vol.Required(CONF_USERNAME, default=data.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD, default=data.get(CONF_PASSWORD, "")): str,
            vol.Optional(
                CONF_CLOUD_PASSWORD, default=data.get(CONF_CLOUD_PASSWORD, "")
            ): str,
            vol.Optional(
                CONF_POLL_SECONDS, default=data.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS)
            ): vol.Coerce(int),
            vol.Optional(
                CONF_HOLD_SECONDS, default=data.get(CONF_HOLD_SECONDS, DEFAULT_HOLD_SECONDS)
            ): vol.Coerce(int),
            vol.Optional(
                CONF_ALARM_TYPES, default=data.get(CONF_ALARM_TYPES, DEFAULT_ALARM_TYPES)
            ): str,
        }
    )


class BabyCryBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(
                    self._validate_login,
                    user_input[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input.get(CONF_CLOUD_PASSWORD, ""),
                )
                await self.async_set_unique_id(
                    f"babycry_{user_input[CONF_HOST]}_{user_input[CONF_USERNAME]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"BabyCry {user_input[CONF_HOST]}", data=user_input
                )
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", data_schema=_schema(user_input), errors=errors)

    @staticmethod
    def _validate_login(host: str, username: str, password: str, cloud_password: str):
        cam = Tapo(host, username, password, cloud_password)
        cam.getBasicInfo()

    async def async_get_options_flow(self, config_entry):
        return BabyCryBridgeOptionsFlow(config_entry)


class BabyCryBridgeOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(current))
