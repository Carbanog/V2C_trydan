"""Config flow for V2C Trydan."""
from __future__ import annotations

import logging
import aiohttp

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
    }
)


class V2CtrydanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for V2C Trydan."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            ip_address = user_input[CONF_IP_ADDRESS]
            try:
                if await self._test_connection(ip_address):
                    await self.async_set_unique_id(ip_address)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"V2C Trydan ({ip_address})",
                        data=user_input,
                    )
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self, ip_address: str) -> bool:
        """Test connection to the V2C Trydan device."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{ip_address}/RealTimeData",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200
        except Exception:
            return False
