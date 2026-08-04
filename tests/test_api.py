"""Tests for the V2C Trydan API client."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest
from aiohttp import ClientConnectionError

from custom_components.v2c_trydan import api as api_module
from custom_components.v2c_trydan.api import (
    V2CTrydanApi,
    V2CTrydanCommandError,
    V2CTrydanConnectionError,
    V2CTrydanInvalidResponseError,
    device_identifier,
    parse_realtime_data,
)


class FakeResponse:
    """Minimal aiohttp response context manager."""

    def __init__(
        self,
        text: str = "{}",
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

    def raise_for_status(self) -> None:
        """Raise for an HTTP error."""
        if self.status >= 400:
            raise ClientConnectionError(f"HTTP {self.status}")


class FakeSession:
    """Return a sequence of fake responses or exceptions."""

    def __init__(
        self,
        results: Iterable[FakeResponse | Exception],
        *,
        closed: bool = False,
    ) -> None:
        """Initialize the session."""
        self._results = iter(results)
        self.urls: list[str] = []
        self.closed = closed

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Return the next configured result."""
        self.urls.append(url)
        result = next(self._results)
        if isinstance(result, Exception):
            raise result
        return result


def test_parse_valid_payload_and_duplicate_key() -> None:
    """Valid JSON is parsed and the final duplicate key wins."""
    payload = '{"FirmwareVersion":"1.0","FirmwareVersion":"1.1","ID":"abc"}'
    assert parse_realtime_data(payload) == {
        "FirmwareVersion": "1.1",
        "ID": "abc",
    }


def test_parse_repairs_missing_ready_state_comma() -> None:
    """The known firmware defect is repaired narrowly."""
    payload = '{"FirmwareVersion":"1.1" "ReadyState":1,"ChargeState":2}'
    assert parse_realtime_data(payload)["ReadyState"] == 1


@pytest.mark.parametrize("payload", ("[]", "not-json", '{"broken":}'))
def test_parse_rejects_invalid_payload(payload: str) -> None:
    """Non-object and malformed payloads are rejected."""
    with pytest.raises(V2CTrydanInvalidResponseError):
        parse_realtime_data(payload)


def test_device_identifier_uses_hardware_id_or_fallback() -> None:
    """A usable hardware ID is preferred over the fallback."""
    assert device_identifier({"ID": " trydan-1 "}, "entry") == "trydan-1"
    assert device_identifier({"ID": ""}, "entry") == "entry"
    assert device_identifier({}, "entry") == "entry"


async def test_read_retries_transient_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """A temporary network failure is retried before returning data."""

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(api_module.asyncio, "sleep", no_sleep)
    session = FakeSession(
        (
            ClientConnectionError("offline"),
            FakeResponse('{"ID":"charger"}'),
        )
    )
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]

    assert await api.async_get_realtime_data() == {
        "ID": "charger",
    }
    assert len(session.urls) == 2


async def test_read_reports_exhausted_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exhausted retry attempts become a domain connection error."""

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(api_module.asyncio, "sleep", no_sleep)
    session = FakeSession(ClientConnectionError("offline") for _ in range(3))
    api = V2CTrydanApi(session, "192.0.2.10")  # type: ignore[arg-type]

    with pytest.raises(V2CTrydanConnectionError):
        await api.async_get_realtime_data()
    assert len(session.urls) == 3


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
    session = FakeSession((FakeResponse('{"ID":"charger"}'),))
    api = V2CTrydanApi(session, "2001:db8::10")  # type: ignore[arg-type]

    await api.async_get_realtime_data()
    assert session.urls == ["http://[2001:db8::10]/RealTimeData"]
