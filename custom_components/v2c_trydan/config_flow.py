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
from .scheduling.presentation import async_block_choices, async_schedule_summary


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


def _block_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Share the native form between adding and replacing a time block."""
    return vol.Schema(
        {
            vol.Required(
                "days", default=defaults.get("days", list(DAYS[:5]))
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(DAYS), multiple=True, translation_key="weekdays"
                )
            ),
            vol.Required(
                "start", default=defaults.get("start", "00:00:00")
            ): selector.TimeSelector(),
            vol.Required(
                "end", default=defaults.get("end", "08:00:00")
            ): selector.TimeSelector(),
            vol.Required(
                "period", default=defaults.get("period", "off_peak")
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(PERIODS), translation_key="tariff"
                )
            ),
        }
    )


def _with_navigation(schema: vol.Schema) -> vol.Schema:
    """HA owns footer buttons; provide an explicit, translated menu action."""
    return vol.Schema(
        {
            vol.Required("navigation", default="continue"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["continue", "back", "cancel"],
                    translation_key="options_navigation",
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            **schema.schema,
        }
    )


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
        self._edit_index: int | None = None

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if self._draft is None:
            self._draft = deepcopy(self.config_entry.options.get(OPTION_KEY, {}))
            self._draft.setdefault("enabled", False)
            self._draft.setdefault("allowed", ["off_peak"])
            self._draft.setdefault("blocks", [])
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "settings",
                "add_block",
                "edit_block",
                "remove_block",
                "save",
                "cancel",
            ],
        )

    async def _async_navigation(
        self, user_input: dict[str, Any]
    ) -> ConfigFlowResult | None:
        """Consume UI-only actions before validation or changing the draft."""
        action = user_input.pop("navigation", "continue")
        if action == "cancel":
            return await self.async_step_cancel()
        if action == "back":
            self._edit_index = None
            return await self.async_step_init()
        return None

    async def async_step_cancel(self, user_input=None) -> ConfigFlowResult:
        """Discard the entire in-memory draft without updating entry options."""
        self._draft = None
        self._edit_index = None
        return self.async_abort(reason="changes_cancelled")

    async def async_step_settings(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            user_input = dict(user_input)
            if (result := await self._async_navigation(user_input)) is not None:
                return result
            self._draft.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="settings",
            data_schema=_with_navigation(
                vol.Schema(
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
                )
            ),
        )

    async def async_step_add_block(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            user_input = dict(user_input)
            if (result := await self._async_navigation(user_input)) is not None:
                return result
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
            data_schema=_with_navigation(_block_schema(user_input or {})),
        )

    async def async_step_edit_block(self, user_input=None) -> ConfigFlowResult:
        """Select an existing draft block, without removing it first."""
        if not self._draft["blocks"]:
            return await self.async_step_init()
        if user_input is not None:
            user_input = dict(user_input)
            if (result := await self._async_navigation(user_input)) is not None:
                return result
            if "block" not in user_input:
                return await self._async_block_selection(
                    "edit_block", {"block": "choose_block"}
                )
            self._edit_index = int(user_input["block"])
            return await self.async_step_edit_details()
        return await self._async_block_selection("edit_block")

    async def async_step_edit_details(self, user_input=None) -> ConfigFlowResult:
        """Validate a replacement against the other blocks before changing draft."""
        if self._edit_index is None or not 0 <= self._edit_index < len(
            self._draft["blocks"]
        ):
            return await self.async_step_edit_block()
        errors = {}
        if user_input is not None:
            user_input = dict(user_input)
            if (result := await self._async_navigation(user_input)) is not None:
                return result
            candidate = deepcopy(self._draft)
            candidate["blocks"][self._edit_index] = user_input
            try:
                WeeklySchedule.from_options(candidate)
            except ValueError:
                errors["base"] = "invalid_schedule"
            else:
                self._draft = candidate
                self._edit_index = None
                return await self.async_step_init()
        return self.async_show_form(
            step_id="edit_details",
            errors=errors,
            data_schema=_with_navigation(
                _block_schema(user_input or self._draft["blocks"][self._edit_index])
            ),
        )

    async def async_step_remove_block(self, user_input=None) -> ConfigFlowResult:
        blocks = self._draft["blocks"]
        if not blocks:
            return await self.async_step_init()
        if user_input is not None:
            user_input = dict(user_input)
            if (result := await self._async_navigation(user_input)) is not None:
                return result
            if "block" not in user_input:
                return await self._async_block_selection(
                    "remove_block", {"block": "choose_block"}
                )
            blocks.pop(int(user_input["block"]))
            return await self.async_step_init()
        return await self._async_block_selection("remove_block")

    async def _async_block_selection(
        self, step_id: str, errors=None
    ) -> ConfigFlowResult:
        options = await async_block_choices(
            self.hass,
            self._draft["blocks"],
            self.context.get("language") or self.hass.config.language,
        )
        return self.async_show_form(
            step_id=step_id,
            errors=errors or {},
            data_schema=_with_navigation(
                vol.Schema(
                    {
                        vol.Optional("block"): selector.SelectSelector(
                            selector.SelectSelectorConfig(options=options)
                        )
                    }
                )
            ),
        )

    async def async_step_save(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            user_input = dict(user_input)
            if (result := await self._async_navigation(user_input)) is not None:
                return result
        try:
            schedule = WeeklySchedule.from_options(self._draft)
            if self._draft["enabled"] and not self._draft["blocks"]:
                raise ValueError("Configure at least one block")
        except ValueError:
            return self.async_show_form(
                step_id="save_error",
                errors={"base": "invalid_schedule"},
                data_schema=_with_navigation(vol.Schema({})),
            )
        if user_input is not None and user_input.get("confirm") is True:
            return self.async_create_entry(
                title="", data={**self.config_entry.options, OPTION_KEY: self._draft}
            )
        summary = await async_schedule_summary(
            self.hass,
            self._draft,
            schedule,
            self.context.get("language") or self.hass.config.language,
        )
        return self.async_show_form(
            step_id="save",
            description_placeholders=summary,
            errors={"base": "confirm_required"} if user_input is not None else {},
            data_schema=_with_navigation(
                vol.Schema(
                    {
                        vol.Required(
                            "confirm", default=False
                        ): selector.BooleanSelector(),
                    }
                )
            ),
        )

    async def async_step_save_error(self, user_input=None) -> ConfigFlowResult:
        if (
            user_input is not None
            and (result := await self._async_navigation(dict(user_input))) is not None
        ):
            return result
        return await self.async_step_init()
