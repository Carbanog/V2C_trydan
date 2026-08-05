"""Config flow for V2C Trydan."""

from __future__ import annotations

import ipaddress
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    V2CTrydanApi,
    V2CTrydanConnectionError,
    V2CTrydanInvalidResponseError,
    device_identifier,
)
from .const import DOMAIN


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
