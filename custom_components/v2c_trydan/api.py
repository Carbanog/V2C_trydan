"""Asynchronous client for the local V2C Trydan HTTP API."""

from __future__ import annotations

import asyncio
import errno
import json
import logging
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from time import monotonic
from typing import Any

from aiohttp import (
    ClientConnectorError,
    ClientError,
    ClientResponse,
    ClientSession,
    ClientTimeout,
)

from .const import (
    COMMAND_TIMEOUT,
    READ_RETRY_DELAY,
    READ_RETRY_LIMIT,
    READ_TIMEOUT,
)
from .utils import value_as_float

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


class V2CTrydanHttpError(V2CTrydanConnectionError):
    """Preserve the status without exposing response bodies or request URLs."""

    def __init__(self, status: int) -> None:
        """Initialize an unsuccessful HTTP response."""
        self.status = status
        super().__init__(f"Charger returned HTTP {status}")

    @property
    def retryable(self) -> bool:
        """Only retry responses that can represent temporary server failures."""
        return self.status in (408, 429) or 500 <= self.status < 600


class V2CTrydanInvalidResponseError(V2CTrydanError):
    """Raised when the charger returns an unusable response."""


class V2CTrydanCommandError(V2CTrydanError):
    """Raised when the charger rejects a write command."""


@dataclass(frozen=True, slots=True)
class ReadDiagnostics:
    """One completed poll, excluding time queued behind another request."""

    attempts: int
    elapsed_seconds: float
    error: str | None
    http_status: int | None


def _failure_reason(error: Exception) -> str:
    """Describe failures without copying URLs, payloads, or arbitrary messages."""
    if isinstance(error, V2CTrydanHttpError):
        return f"HTTP {error.status}"
    if isinstance(error, TimeoutError):
        return f"{type(error).__name__}: request timed out"
    if isinstance(error, ClientConnectorError):
        os_error = error.os_error
    elif isinstance(error, OSError):
        os_error = error
    else:
        return type(error).__name__
    if os_error.errno is not None:
        name = errno.errorcode.get(os_error.errno, "unknown")
        return f"{type(error).__name__}: OS error {os_error.errno} ({name})"
    return type(error).__name__


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

    # Only require the long-standing fields used by the session tracker and
    # primary power sensor. Optional and future firmware fields remain optional.
    state = value_as_float(parsed.get("ChargeState"))
    if state is None or state < 0 or not state.is_integer():
        raise V2CTrydanInvalidResponseError("Missing or invalid ChargeState")
    for key in ("ChargePower", "ChargeEnergy", "ChargeTime"):
        value = value_as_float(parsed.get(key))
        if value is None or value < 0:
            raise V2CTrydanInvalidResponseError(f"Missing or invalid {key}")
    return parsed


class V2CTrydanApi:
    """Small, reusable client for one charger.

    A lock serializes reads and writes. This matters on PLC and weak Wi-Fi
    links, where overlapping requests can make the charger unresponsive.
    """

    def __init__(self, session: ClientSession, host: str) -> None:
        """Initialize the API client."""
        self._session = session
        self._request_lock = asyncio.Lock()
        self.host = host
        self._last_read: ReadDiagnostics | None = None
        self._last_failed_read: ReadDiagnostics | None = None
        self._failure_started: float | None = None
        self._failed_reads = 0
        self._last_recovery_seconds: float | None = None

    @property
    def diagnostics(self) -> dict[str, Any]:
        """Return support metadata without charger identity or response data."""
        return {
            "last_read": asdict(self._last_read) if self._last_read else None,
            "last_failed_read": (
                asdict(self._last_failed_read) if self._last_failed_read else None
            ),
            "consecutive_failed_reads": self._failed_reads,
            "last_recovery_seconds": self._last_recovery_seconds,
        }

    def _record_read(
        self, started: float, attempts: int, error: Exception | None = None
    ) -> ReadDiagnostics:
        """Keep the latest failure after recovery for later support downloads."""
        now = monotonic()
        result = ReadDiagnostics(
            attempts=attempts,
            elapsed_seconds=round(now - started, 3),
            error=_failure_reason(error) if error is not None else None,
            http_status=error.status if isinstance(error, V2CTrydanHttpError) else None,
        )
        self._last_read = result
        if error is not None:
            self._last_failed_read = result
            if self._failure_started is None:
                self._failure_started = started
            self._failed_reads += 1
        elif self._failure_started is not None:
            self._last_recovery_seconds = round(now - self._failure_started, 3)
            _LOGGER.info(
                "V2C Trydan communication recovered after %.1f seconds "
                "(%s failed polls)",
                self._last_recovery_seconds,
                self._failed_reads,
            )
            self._failure_started = None
            self._failed_reads = 0
        return result

    @property
    def base_url(self) -> str:
        """Return the charger's base URL."""
        url_host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{url_host}"

    async def async_get_realtime_data(self) -> dict[str, Any]:
        """Fetch all charger data, retrying transient connection failures."""
        async with self._request_lock:
            started = monotonic()
            for attempt in range(1, READ_RETRY_LIMIT + 1):
                try:
                    async with self._session.get(
                        f"{self.base_url}/RealTimeData",
                        timeout=ClientTimeout(total=READ_TIMEOUT),
                        allow_redirects=False,
                    ) as response:
                        self._raise_for_status(response)
                        data = parse_realtime_data(await response.text())
                except (V2CTrydanInvalidResponseError, UnicodeError) as err:
                    self._record_read(started, attempt, err)
                    if isinstance(err, UnicodeError):
                        raise V2CTrydanInvalidResponseError(
                            "The charger response is not valid text"
                        ) from err
                    raise
                except RuntimeError as err:
                    # Home Assistant may close its shared client session while a
                    # final coordinator refresh is being cancelled at shutdown.
                    # Normalize only that known lifecycle condition; unrelated
                    # programming errors must remain visible to developers.
                    if getattr(self._session, "closed", False):
                        self._record_read(started, attempt, err)
                        raise V2CTrydanConnectionError(
                            "Home Assistant HTTP session is closed"
                        ) from err
                    raise
                except (
                    V2CTrydanConnectionError,
                    ClientError,
                    TimeoutError,
                ) as err:
                    _LOGGER.debug(
                        "RealTimeData attempt %s/%s failed after %.1f seconds: %s",
                        attempt,
                        READ_RETRY_LIMIT,
                        monotonic() - started,
                        _failure_reason(err),
                    )
                    if (
                        isinstance(err, V2CTrydanHttpError) and not err.retryable
                    ) or attempt == READ_RETRY_LIMIT:
                        result = self._record_read(started, attempt, err)
                        raise V2CTrydanConnectionError(
                            f"Read failed after {attempt} attempts in "
                            f"{result.elapsed_seconds:.1f} seconds; "
                            f"last failure: {result.error}"
                        ) from err
                    await asyncio.sleep(READ_RETRY_DELAY)
                else:
                    self._record_read(started, attempt)
                    return data

        raise AssertionError("Read retry limit must be positive")

    async def async_write(self, key: str, value: int) -> None:
        """Set one charger value and validate the command response."""
        async with self._request_lock:
            try:
                async with self._session.get(
                    f"{self.base_url}/write/{key}={value}",
                    timeout=ClientTimeout(total=COMMAND_TIMEOUT),
                    allow_redirects=False,
                ) as response:
                    self._raise_for_status(response)
                    response_text = (await response.text()).strip()
            except (ClientError, TimeoutError) as err:
                raise V2CTrydanConnectionError(
                    f"Unable to write {key} on {self.host}"
                ) from err
            except UnicodeError as err:
                raise V2CTrydanCommandError(
                    "The charger acknowledgement is not valid text"
                ) from err
            except RuntimeError as err:
                if getattr(self._session, "closed", False):
                    raise V2CTrydanConnectionError(
                        "Home Assistant HTTP session is closed"
                    ) from err
                raise

        # Do not retry writes: a lost acknowledgement does not prove that the
        # charger failed to execute the command.
        if response_text.upper() != "OK":
            raise V2CTrydanCommandError(
                "The charger did not confirm the command with OK"
            )

    @staticmethod
    def _raise_for_status(response: ClientResponse) -> None:
        """Convert an HTTP error to a domain-specific connection error."""
        if response.status != 200:
            raise V2CTrydanHttpError(response.status)


def device_identifier(data: Mapping[str, Any], fallback: str) -> str:
    """Return the stable hardware identifier or a config-entry fallback."""
    raw_identifier = data.get("ID")
    if raw_identifier is None:
        return fallback
    identifier = str(raw_identifier).strip()
    return identifier or fallback
