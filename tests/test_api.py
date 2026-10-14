"""Tests for the V2C Trydan API client."""

from __future__ import annotations

import asyncio
import errno
import json
import logging
from collections.abc import Iterable
from typing import Any

import pytest
from aiohttp import ClientConnectionError, ClientConnectorError, ClientOSError

from custom_components.v2c_trydan import api as api_module
from custom_components.v2c_trydan.api import (
    V2CTrydanApi,
    V2CTrydanCommandError,
    V2CTrydanConnectionError,
    V2CTrydanInvalidResponseError,
    device_identifier,
    parse_realtime_data,
)

VALID_DATA = {
    "ID": "charger",
    "ChargeState": 2,
    "ChargePower": 2992.34,
    "ChargeEnergy": 0.37,
    "ChargeTime": 454,
}
VALID_PAYLOAD = json.dumps(VALID_DATA)


@pytest.fixture(autouse=True)
def immediate_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid network backoff without replacing asyncio scheduling itself."""
    monkeypatch.setattr(api_module, "READ_RETRY_DELAY", 0)


class FakeResponse:
    """Minimal aiohttp response context manager."""

    def __init__(
        self,
        text: str = VALID_PAYLOAD,
        *,
        status: int = 200,
    ) -> None:
        """Initialize a response."""
        self._text = text
        self.status = status

    async def __aenter__(self) -> FakeResponse:
        """Enter the request context."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit the request context."""

    async def text(self) -> str:
        """Return response text."""
        return self._text


class FakeSession:
    """Return a sequence of fake responses or exceptions."""

    def __init__(
        self,
        results: Iterable[FakeResponse | BaseException],
        *,
        closed: bool = False,
    ) -> None:
        """Initialize the session."""
        self._results = iter(results)
        self.urls: list[str] = []
        self.options: list[dict[str, Any]] = []
        self.closed = closed

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Return the next configured result."""
        self.urls.append(url)
        self.options.append(kwargs)
        result = next(self._results)
        if isinstance(result, BaseException):
            raise result
        return result


def test_parse_valid_payload_and_duplicate_key() -> None:
    """Valid JSON is parsed and the final duplicate key wins."""
    payload = VALID_PAYLOAD[:-1] + ',"FirmwareVersion":"1.0","FirmwareVersion":"1.1"}'
    assert parse_realtime_data(payload) == {**VALID_DATA, "FirmwareVersion": "1.1"}


def test_parse_repairs_missing_ready_state_comma() -> None:
    """The known firmware defect is repaired narrowly."""
    payload = VALID_PAYLOAD[:-1] + ',"FirmwareVersion":"1.1" "ReadyState":1}'
    assert parse_realtime_data(payload)["ReadyState"] == 1


@pytest.mark.parametrize("payload", ("[]", "not-json", '{"broken":}', "{}"))
def test_parse_rejects_invalid_payload(payload: str) -> None:
    """Non-object and malformed payloads are rejected."""
    with pytest.raises(V2CTrydanInvalidResponseError):
        parse_realtime_data(payload)


def test_device_identifier_uses_hardware_id_or_fallback() -> None:
    """A usable hardware ID is preferred over the fallback."""
    assert device_identifier({"ID": " trydan-1 "}, "entry") == "trydan-1"
    assert device_identifier({"ID": ""}, "entry") == "entry"
    assert device_identifier({}, "entry") == "entry"


async def test_read_retries_transient_failures() -> None:
    """A temporary network failure is retried before returning data."""

    session = FakeSession(
        (
            ClientConnectionError("offline"),
            FakeResponse(),
        )
    )
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]

    assert await api.async_get_realtime_data() == VALID_DATA
    assert len(session.urls) == 2


async def test_read_reports_exhausted_retries() -> None:
    """Exhausted retry attempts become a domain connection error."""

    session = FakeSession(ClientConnectionError("offline") for _ in range(3))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]

    with pytest.raises(
        V2CTrydanConnectionError, match="ClientConnectionError"
    ) as error:
        await api.async_get_realtime_data()
    assert len(session.urls) == 3
    assert isinstance(error.value.__cause__, ClientConnectionError)
    assert api.diagnostics["last_failed_read"]["attempts"] == 3


async def test_closed_home_assistant_session_is_a_domain_error() -> None:
    """A shutdown race must not escape as an unexpected RuntimeError."""
    api = V2CTrydanApi(
        FakeSession((RuntimeError("Session is closed"),), closed=True),  # type: ignore[arg-type]
        "192.0.2.10",
    )

    with pytest.raises(V2CTrydanConnectionError, match="session is closed"):
        await api.async_get_realtime_data()


async def test_write_rejects_error_response() -> None:
    """An explicit charger rejection is surfaced to Home Assistant."""
    api = V2CTrydanApi(
        FakeSession((FakeResponse("ERROR"),)),  # type: ignore[arg-type]
        "192.0.2.10",
    )

    with pytest.raises(V2CTrydanCommandError):
        await api.async_write("Intensity", 16)


async def test_ipv6_host_is_bracketed_in_url() -> None:
    """IPv6 literal addresses produce valid HTTP URLs."""
    session = FakeSession((FakeResponse(),))
    api = V2CTrydanApi(session, "2001:db8::10")  # type: ignore[arg-type]

    await api.async_get_realtime_data()
    assert session.urls == ["http://[2001:db8::10]/RealTimeData"]


@pytest.mark.parametrize(
    "field", ("ChargeState", "ChargePower", "ChargeEnergy", "ChargeTime")
)
def test_missing_core_field_is_not_a_successful_poll(field: str) -> None:
    """A valid JSON object must still contain the core charger contract."""
    data = dict(VALID_DATA)
    data.pop(field)
    with pytest.raises(V2CTrydanInvalidResponseError, match=field):
        parse_realtime_data(json.dumps(data))


@pytest.mark.parametrize(
    "field", ("ChargeState", "ChargePower", "ChargeEnergy", "ChargeTime")
)
@pytest.mark.parametrize("value", (None, True, -1, "nan", "inf", "invalid"))
def test_invalid_core_value_is_rejected(field: str, value: Any) -> None:
    """Invalid counters cannot mutate session state or publish bogus values."""
    with pytest.raises(V2CTrydanInvalidResponseError, match=field):
        parse_realtime_data(json.dumps({**VALID_DATA, field: value}))


def test_fractional_charge_state_is_rejected() -> None:
    """Do not silently truncate an invalid state to a valid integer."""
    with pytest.raises(V2CTrydanInvalidResponseError, match="ChargeState"):
        parse_realtime_data(json.dumps({**VALID_DATA, "ChargeState": 1.5}))


@pytest.mark.parametrize("status", (301, 400, 401, 403, 404))
async def test_permanent_http_errors_do_not_retry(status: int) -> None:
    """A configuration/authentication failure must not load a weak link."""
    session = FakeSession((FakeResponse(status=status),))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    with pytest.raises(V2CTrydanConnectionError, match=f"HTTP {status}"):
        await api.async_get_realtime_data()
    assert len(session.urls) == 1
    assert api.diagnostics["last_failed_read"]["http_status"] == status


@pytest.mark.parametrize("status", (408, 429, 500, 502, 503, 504))
async def test_temporary_http_errors_retry(status: int) -> None:
    """Transient server failures can recover on the next bounded attempt."""
    session = FakeSession((FakeResponse(status=status), FakeResponse()))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    assert await api.async_get_realtime_data() == VALID_DATA
    assert len(session.urls) == 2


async def test_invalid_payload_is_not_retried() -> None:
    """Malformed data is a distinct failure rather than a network timeout."""
    session = FakeSession((FakeResponse("{}"),))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    with pytest.raises(V2CTrydanInvalidResponseError):
        await api.async_get_realtime_data()
    assert len(session.urls) == 1
    assert (
        api.diagnostics["last_failed_read"]["error"] == "V2CTrydanInvalidResponseError"
    )


async def test_recovery_keeps_failure_diagnostics_and_logs_duration(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Support downloads after recovery must retain the previous failure."""
    now = [100.0]
    monkeypatch.setattr(api_module, "monotonic", lambda: now[0])
    session = FakeSession((*[TimeoutError() for _ in range(3)], FakeResponse()))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    with pytest.raises(V2CTrydanConnectionError, match="request timed out"):
        await api.async_get_realtime_data()
    failed = api.diagnostics["last_failed_read"]
    assert api.diagnostics["consecutive_failed_reads"] == 1
    now[0] = 175.0
    with caplog.at_level(logging.INFO):
        await api.async_get_realtime_data()
    assert api.diagnostics["last_failed_read"] == failed
    assert api.diagnostics["last_read"]["error"] is None
    assert api.diagnostics["consecutive_failed_reads"] == 0
    assert api.diagnostics["last_recovery_seconds"] == 75
    assert "recovered after 75.0 seconds" in caplog.text


async def test_error_reports_elapsed_time_without_exposing_exception_text(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Diagnostics must expose categories, never arbitrary transport messages."""
    now = [100.0]
    monkeypatch.setattr(api_module, "monotonic", lambda: now[0])

    class TimedSession(FakeSession):
        def get(self, url: str, **kwargs: Any) -> FakeResponse:
            now[0] += 20
            return super().get(url, **kwargs)

    session = TimedSession(ClientConnectionError("private-response") for _ in range(3))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    with (
        caplog.at_level(logging.DEBUG),
        pytest.raises(V2CTrydanConnectionError) as error,
    ):
        await api.async_get_realtime_data()
    assert "3 attempts in 60.0 seconds" in str(error.value)
    assert "private-response" not in str(error.value) + caplog.text + str(
        api.diagnostics
    )


@pytest.mark.parametrize("connector_error", (True, False))
async def test_os_error_code_is_preserved_without_arbitrary_message(
    connector_error: bool,
) -> None:
    """Connection refusal/reset diagnosis needs the OS code, not sensitive text."""
    error: Exception = ClientOSError(errno.ECONNREFUSED, "private-response")
    if connector_error:
        error = ClientConnectorError(
            None,
            OSError(errno.ECONNREFUSED, "private-response"),  # type: ignore[arg-type]
        )
    api = V2CTrydanApi(FakeSession((error, error, error)), "192.0.2.10")  # type: ignore[arg-type]
    with pytest.raises(V2CTrydanConnectionError, match="ECONNREFUSED") as result:
        await api.async_get_realtime_data()
    assert "private-response" not in str(result.value) + str(api.diagnostics)


async def test_programming_error_is_not_hidden_as_offline() -> None:
    """Only the known closed-session RuntimeError is normalized."""
    api = V2CTrydanApi(FakeSession((RuntimeError("bug"),)), "192.0.2.10")  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="bug"):
        await api.async_get_realtime_data()
    assert api.diagnostics["last_failed_read"] is None


@pytest.mark.parametrize("body", ("", "ERROR", "<html>OK</html>", "{}", "OK error"))
async def test_write_requires_explicit_acknowledgement(body: str) -> None:
    """HTTP 200 alone cannot prove that a control action succeeded."""
    session = FakeSession((FakeResponse(body),))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    with pytest.raises(V2CTrydanCommandError):
        await api.async_write("Paused", 1)
    assert len(session.urls) == 1


@pytest.mark.parametrize("body", ("OK", " OK\r\n", "ok"))
async def test_write_accepts_acknowledgement(body: str) -> None:
    """Whitespace and letter case do not invalidate the firmware's OK reply."""
    api = V2CTrydanApi(FakeSession((FakeResponse(body),)), "192.0.2.10")  # type: ignore[arg-type]
    await api.async_write("Paused", 1)


async def test_ambiguous_write_timeout_is_not_retried() -> None:
    """The charger may have acted before its acknowledgement was lost."""
    session = FakeSession((TimeoutError(),))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    with pytest.raises(V2CTrydanConnectionError):
        await api.async_write("Paused", 1)
    assert len(session.urls) == 1


async def test_read_and_write_are_serialized() -> None:
    """A control cannot overtake an outstanding charger read."""
    entered = asyncio.Event()
    release = asyncio.Event()

    class PendingResponse(FakeResponse):
        async def text(self) -> str:
            entered.set()
            await release.wait()
            return VALID_PAYLOAD

    session = FakeSession((PendingResponse(), FakeResponse("OK")))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    read = asyncio.create_task(api.async_get_realtime_data())
    await entered.wait()
    write = asyncio.create_task(api.async_write("Paused", 1))
    await asyncio.sleep(0)
    assert len(session.urls) == 1
    release.set()
    await asyncio.gather(read, write)
    assert [url.rsplit("/", 1)[-1] for url in session.urls] == [
        "RealTimeData",
        "Paused=1",
    ]
    assert all(options["allow_redirects"] is False for options in session.options)


async def test_cancelled_read_releases_lock_without_retrying() -> None:
    """Reload/shutdown cancellation must propagate and release the connection lock."""
    entered = asyncio.Event()

    class PendingResponse(FakeResponse):
        async def text(self) -> str:
            entered.set()
            await asyncio.Event().wait()
            return VALID_PAYLOAD

    session = FakeSession((PendingResponse(), FakeResponse()))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]
    read = asyncio.create_task(api.async_get_realtime_data())
    await entered.wait()
    read.cancel()
    with pytest.raises(asyncio.CancelledError):
        await read
    assert api.diagnostics["consecutive_failed_reads"] == 0
    assert await api.async_get_realtime_data() == VALID_DATA
    assert len(session.urls) == 2
