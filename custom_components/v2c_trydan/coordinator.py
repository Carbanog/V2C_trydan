import logging
import asyncio
from datetime import timedelta
import json
import re
import aiohttp
from aiohttp import ClientError, client_exceptions
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

def arreglar_json_invalido(json_str: str) -> dict:
    """Fix malformed JSON responses from V2C Trydan devices."""
    # Remove duplicate FirmwareVersion fields (keep the last one)
    firmware_pattern = r'"FirmwareVersion":"[^"]*",'
    matches = list(re.finditer(firmware_pattern, json_str))
    if len(matches) > 1:
        for match in matches[:-1]:
            json_str = json_str[:match.start()] + json_str[match.end():]

    # Fix missing comma before ReadyState
    json_str = json_str.replace('"ReadyState":', ',"ReadyState":')

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        _LOGGER.error(f"Error al parsear JSON: {str(e)}\nJSON: {json_str}")
        raise UpdateFailed(f"Error al parsear los datos JSON: {str(e)}")


class V2CtrydanDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, ip_address):
        self.ip_address = ip_address
        self.error_reportado = False
        self._session = None
        self._consecutive_errors = 0
        self.MAX_CONSECUTIVE_ERRORS = 5

        super().__init__(
            hass,
            _LOGGER,
            name="v2c_trydan",
            update_interval=timedelta(seconds=15),
            always_update=False
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            if self._session is None:
                self._session = async_get_clientsession(self.hass)

            data = await self._async_get_json(
                self._session,
                f"http://{self.ip_address}/RealTimeData"
            )

            # Reset error tracking on successful update
            if self.error_reportado or self._consecutive_errors > 0:
                self.error_reportado = False
                self._consecutive_errors = 0
                _LOGGER.info(f"Conexión con {self.ip_address} restaurada")

            return data

        except UpdateFailed:
            raise
        except Exception as e:
            self._consecutive_errors += 1
            if self._consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                if not self.error_reportado:
                    self.error_reportado = True
                    _LOGGER.error(
                        f"Problemas persistentes con {self.ip_address} "
                        f"tras {self._consecutive_errors} intentos fallidos."
                    )
            else:
                _LOGGER.debug(f"Error temporal comunicando con {self.ip_address}: {e}")
            raise UpdateFailed(f"Error obteniendo datos de {self.ip_address}: {e}")

    async def _async_get_json(self, session, url):
        """Get JSON data from API with native retry logic."""
        last_error = None
        for attempt in range(3):
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            _LOGGER.debug("JSON malformado, intentando reparar")
                            return arreglar_json_invalido(text)
                    else:
                        response.raise_for_status()

            except (client_exceptions.ClientConnectorError,
                    client_exceptions.ServerTimeoutError,
                    ClientError) as err:
                last_error = err
                _LOGGER.debug(
                    f"Intento {attempt + 1}/3 fallido para {self.ip_address}: {err}"
                )
                if attempt < 2:
                    await asyncio.sleep(2)

            except Exception as e:
                _LOGGER.debug(f"Error inesperado en intento {attempt + 1}/3: {e}")
                last_error = e
                if attempt < 2:
                    await asyncio.sleep(2)

        raise UpdateFailed(f"Fallaron los 3 intentos para {self.ip_address}: {last_error}")
