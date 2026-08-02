"""Asynchronous client for the local V2C Trydan HTTP API."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout

from .const import (
    COMMAND_TIMEOUT,
    OPTIONAL_READ_EVERY_POLLS,
    OPTIONAL_READ_KEYS,
    OPTIONAL_READ_TIMEOUT,
    READ_RETRY_DELAY,
    READ_RETRY_LIMIT,
    READ_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

_MISSING_READY_STATE_COMMA = re.compile(
    r'(?P<value>(?:"[^"]*"|-?\d+(?:\.\d+)?|true|false|null|\}|\]))'
    r'(?P<space>\s*)("ReadyState"\s*:)',
    flags=re.IGNORECASE,
)


class V2CTrydanError(Exception):
    """Base exception for V2C Trydan communication errors."""


class V2CTrydanConnectionError(V2CTrydanError):
    """Raised when the charger cannot be reached."""


class V2CTrydanInvalidResponseError(V2CTrydanError):
    """Raised when the charger returns an unusable response."""


class V2CTrydanCommandError(V2CTrydanError):
    """Raised when the charger rejects a write command."""


def parse_realtime_data(payload: str) -> dict[str, Any]:
    """Parse a RealTimeData response, repairing a known firmware defect.

    Some firmware versions omit the comma immediately before ``ReadyState``.
    Duplicate JSON keys, including ``FirmwareVersion``, are valid JSON and the
    standard decoder intentionally keeps the final value.
    """
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as original_error:
        repaired_payload = _MISSING_READY_STATE_COMMA.sub(
            r"\g<value>,\g<space>\3", payload
        )
        if repaired_payload == payload:
            raise V2CTrydanInvalidResponseError(
                "The charger returned malformed JSON"
            ) from original_error

        try:
            parsed = json.loads(repaired_payload)
        except json.JSONDecodeError as repaired_error:
            raise V2CTrydanInvalidResponseError(
                "The charger returned malformed JSON that could not be repaired"
            ) from repaired_error

    if not isinstance(parsed, dict):
        raise V2CTrydanInvalidResponseError(
            "The charger response must be a JSON object"
        )
    return parsed


def parse_scalar(payload: str) -> int | float | str:
    """Parse a scalar response returned by the charger's read endpoint."""
    value = payload.strip()
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


class V2CTrydanApi:
    """Small, reusable client for one charger.

    A lock serializes reads and writes. This matters on PLC and weak Wi-Fi
    links, where overlapping requests can make the charger unresponsive.
    """

    def __init__(self, session: ClientSession, host: str) -> None:
        """Initialize the API client."""
        self._session = session
        self._request_lock = asyncio.Lock()
        self._optional_values: dict[str, Any] = {}
        self._unsupported_optional_keys: set[str] = set()
        self._poll_count = 0
        self.host = host

    @property
    def base_url(self) -> str:
        """Return the charger's base URL."""
        url_host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{url_host}"

    async def async_get_realtime_data(self) -> dict[str, Any]:
        """Fetch all charger data, retrying transient connection failures."""
        last_error: Exception | None = None

        async with self._request_lock:
            for attempt in range(READ_RETRY_LIMIT):
                try:
                    async with self._session.get(
                        f"{self.base_url}/RealTimeData",
                        timeout=ClientTimeout(total=READ_TIMEOUT),
                    ) as response:
                        self._raise_for_status(response)
                        data = parse_realtime_data(await response.text())
                    break
                except V2CTrydanInvalidResponseError:
                    raise
                except RuntimeError as err:
                    # Home Assistant may close its shared client session while a
                    # final coordinator refresh is being cancelled at shutdown.
                    # Normalize only that known lifecycle condition; unrelated
                    # programming errors must remain visible to developers.
                    if getattr(self._session, "closed", False):
                        raise V2CTrydanConnectionError(
                            "Home Assistant HTTP session is closed"
                        ) from err
                    raise
                except (
                    V2CTrydanConnectionError,
                    ClientError,
                    TimeoutError,
                ) as err:
                    last_error = err
                    if attempt < READ_RETRY_LIMIT - 1:
                        await asyncio.sleep(READ_RETRY_DELAY)
            else:
                raise V2CTrydanConnectionError(
                    f"Unable to reach {self.host} after {READ_RETRY_LIMIT} attempts"
                ) from last_error

            await self._async_supplement_optional_data(data)
            self._poll_count += 1
            return data

    async def async_write(self, key: str, value: int) -> None:
        """Set one charger value and validate the command response."""
        async with self._request_lock:
            try:
                async with self._session.get(
                    f"{self.base_url}/write/{key}={value}",
                    timeout=ClientTimeout(total=COMMAND_TIMEOUT),
                ) as response:
                    self._raise_for_status(response)
                    response_text = (await response.text()).strip()
            except (ClientError, TimeoutError) as err:
                raise V2CTrydanConnectionError(
                    f"Unable to write {key} on {self.host}"
                ) from err
            except RuntimeError as err:
                if getattr(self._session, "closed", False):
                    raise V2CTrydanConnectionError(
                        "Home Assistant HTTP session is closed"
                    ) from err
                raise

        if response_text.upper() == "ERROR":
            raise V2CTrydanCommandError(f"The charger rejected {key}={value}")
        if key in OPTIONAL_READ_KEYS:
            self._optional_values[key] = value

    async def _async_supplement_optional_data(self, data: dict[str, Any]) -> None:
        """Add optional values without making the main poll depend on them.

        Older firmware omits LED values from ``RealTimeData`` while still
        exposing them through ``/read``. Supported values are refreshed once
        per minute and cached between polls, limiting traffic on weak links.
        """
        for key in OPTIONAL_READ_KEYS:
            if key in data:
                self._optional_values[key] = data[key]

        should_refresh = self._poll_count % OPTIONAL_READ_EVERY_POLLS == 0
        if should_refresh:
            for key in OPTIONAL_READ_KEYS:
                if key in data or key in self._unsupported_optional_keys:
                    continue
                await self._async_read_optional_key(key)

        data.update(self._optional_values)

    async def _async_read_optional_key(self, key: str) -> None:
        """Read one optional keyword, isolating failures from core data."""
        try:
            async with self._session.get(
                f"{self.base_url}/read/{key}",
                timeout=ClientTimeout(total=OPTIONAL_READ_TIMEOUT),
            ) as response:
                if response.status == 404:
                    self._unsupported_optional_keys.add(key)
                    return
                self._raise_for_status(response)
                self._optional_values[key] = parse_scalar(await response.text())
        except (
            V2CTrydanConnectionError,
            ClientError,
            TimeoutError,
        ) as err:
            _LOGGER.debug(
                "Optional V2C keyword %s is temporarily unavailable: %s", key, err
            )

    @staticmethod
    def _raise_for_status(response: ClientResponse) -> None:
        """Convert an HTTP error to a domain-specific connection error."""
        try:
            response.raise_for_status()
        except ClientError as err:
            raise V2CTrydanConnectionError(
                f"Charger returned HTTP {response.status}"
            ) from err


def device_identifier(data: Mapping[str, Any], fallback: str) -> str:
    """Return the stable hardware identifier or a config-entry fallback."""
    raw_identifier = data.get("ID")
    if raw_identifier is None:
        return fallback
    identifier = str(raw_identifier).strip()
    return identifier or fallback
