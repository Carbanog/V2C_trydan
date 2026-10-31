"""Config flow for V2C Trydan."""

from __future__ import annotations

import ipaddress
from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    V2CTrydanApi,
    V2CTrydanConnectionError,
    V2CTrydanInvalidResponseError,
    device_identifier,
)
from .const import DOMAIN
from .scheduling.policy import DAYS, OPTION_KEY, PERIODS, WeeklySchedule


def _normalize_ip_address(value: str) -> str:
    """Validate and normalize an IPv4 or IPv6 address."""
    return str(ipaddress.ip_address(value.strip()))


def _schema(default: str | None = None) -> vol.Schema:
    """Return the config form schema."""
    field = (
        vol.Required(CONF_IP_ADDRESS, default=default)
        if default
        else vol.Required(CONF_IP_ADDRESS)
    )
    return vol.Schema({field: str})


class V2CTrydanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for V2C Trydan."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Offer optional scheduling without creating helpers or automations."""
        return V2CTrydanOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a new charger entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            result = await self._async_validate_input(user_input, errors)
            if result is not None:
                host, unique_id = result
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"V2C Trydan ({host})",
                    data={CONF_IP_ADDRESS: host},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(
                user_input.get(CONF_IP_ADDRESS) if user_input else None
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the charger IP address."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            result = await self._async_validate_input(user_input, errors)
            if result is not None:
                host, unique_id = result
                await self.async_set_unique_id(unique_id)
                legacy_unique_id = entry.data[CONF_IP_ADDRESS]
                if entry.unique_id != legacy_unique_id:
                    self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    data_updates={CONF_IP_ADDRESS: host},
                )

        default = (
            user_input.get(CONF_IP_ADDRESS)
            if user_input
            else entry.data[CONF_IP_ADDRESS]
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(default),
            errors=errors,
        )

    async def _async_validate_input(
        self,
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> tuple[str, str] | None:
        """Validate the address and return it with the hardware ID."""
        try:
            host = _normalize_ip_address(user_input[CONF_IP_ADDRESS])
        except ValueError:
            errors["base"] = "invalid_ip"
            return None

        api = V2CTrydanApi(async_get_clientsession(self.hass), host)
        try:
            data = await api.async_get_realtime_data()
        except V2CTrydanConnectionError:
            errors["base"] = "cannot_connect"
            return None
        except V2CTrydanInvalidResponseError:
            errors["base"] = "invalid_response"
            return None

        identifier = device_identifier(data, "")
        if not identifier:
            errors["base"] = "invalid_response"
            return None
        return host, identifier


class V2CTrydanOptionsFlow(config_entries.OptionsFlow):
    """Edit a draft; nothing controls the charger until Save is selected."""

    def __init__(self) -> None:
        self._draft: dict[str, Any] | None = None

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if self._draft is None:
            self._draft = deepcopy(self.config_entry.options.get(OPTION_KEY, {}))
            self._draft.setdefault("enabled", False)
            self._draft.setdefault("allowed", ["off_peak"])
            self._draft.setdefault("blocks", [])
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "add_block", "remove_block", "save"],
        )

    async def async_step_settings(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._draft.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "enabled", default=self._draft["enabled"]
                    ): selector.BooleanSelector(),
                    vol.Required(
                        "allowed", default=self._draft["allowed"]
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(PERIODS),
                            multiple=True,
                            translation_key="tariff",
                        )
                    ),
                }
            ),
        )

    async def async_step_add_block(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            candidate = deepcopy(self._draft)
            candidate["blocks"].append(user_input)
            try:
                WeeklySchedule.from_options(candidate)
            except ValueError:
                errors["base"] = "invalid_schedule"
            else:
                self._draft = candidate
                return await self.async_step_init()
        return self.async_show_form(
            step_id="add_block",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "days", default=list(DAYS[:5])
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(DAYS),
                            multiple=True,
                            translation_key="weekdays",
                        )
                    ),
                    vol.Required("start", default="00:00:00"): selector.TimeSelector(),
                    vol.Required("end", default="08:00:00"): selector.TimeSelector(),
                    vol.Required("period", default="off_peak"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(PERIODS), translation_key="tariff"
                        )
                    ),
                }
            ),
        )

    async def async_step_remove_block(self, user_input=None) -> ConfigFlowResult:
        blocks = self._draft["blocks"]
        if not blocks:
            return await self.async_step_init()
        if user_input is not None:
            blocks.pop(int(user_input["block"]))
            return await self.async_step_init()
        options = [
            {
                "value": str(index),
                "label": (
                    f"{', '.join(block['days'])}: "
                    f"{block['start']} → {block['end']} ({block['period']})"
                ),
            }
            for index, block in enumerate(blocks)
        ]
        return self.async_show_form(
            step_id="remove_block",
            data_schema=vol.Schema(
                {
                    vol.Required("block"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options)
                    )
                }
            ),
        )

    async def async_step_save(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_init()
        try:
            WeeklySchedule.from_options(self._draft)
            if self._draft["enabled"] and not self._draft["blocks"]:
                raise ValueError("Configure at least one block")
        except ValueError:
            return self.async_show_form(
                step_id="save", errors={"base": "invalid_schedule"}
            )
        return self.async_create_entry(
            title="", data={**self.config_entry.options, OPTION_KEY: self._draft}
        )
