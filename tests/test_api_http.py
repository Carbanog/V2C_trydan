"""Exercise real aiohttp transport against a local test server, not a charger."""

import asyncio
import json
from pathlib import Path

import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer

from custom_components.v2c_trydan import api as api_module
from custom_components.v2c_trydan.api import (
    V2CTrydanApi,
    V2CTrydanCommandError,
    V2CTrydanConnectionError,
    V2CTrydanInvalidResponseError,
)

VALID_DATA = json.loads(
    (Path(__file__).parent / "fixtures" / "realtime_2_5_1_charging.json").read_text(
        encoding="utf-8"
    )
)


def use_local_server(monkeypatch: pytest.MonkeyPatch, server: TestServer) -> None:
    """Substitute only the endpoint so production request handling runs unchanged."""
    url = str(server.make_url("/")).rstrip("/")
    monkeypatch.setattr(V2CTrydanApi, "base_url", property(lambda _self: url))
    monkeypatch.setattr(api_module, "READ_RETRY_DELAY", 0)


async def test_real_http_failure_recovers_and_write_requires_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read, retry, parse, acknowledge, and reject use actual HTTP responses."""
    reads = 0
    writes: list[str] = []

    async def read_handler(_request: web.Request) -> web.Response:
        nonlocal reads
        reads += 1
        if reads == 1:
            return web.Response(status=503)
        # The device may serve JSON as text; parsing must not rely on its MIME type.
        return web.Response(text=json.dumps(VALID_DATA), content_type="text/plain")

    async def write_handler(request: web.Request) -> web.Response:
        writes.append(request.match_info["command"])
        return web.Response(text="OK" if len(writes) == 1 else "<html>OK</html>")

    app = web.Application()
    app.router.add_get("/RealTimeData", read_handler)
    app.router.add_get("/write/{command}", write_handler)
    async with TestServer(app) as server, ClientSession() as session:
        use_local_server(monkeypatch, server)
        api = V2CTrydanApi(session, "127.0.0.1")
        assert await api.async_get_realtime_data() == VALID_DATA
        assert reads == 2
        await api.async_write("Paused", 1)
        with pytest.raises(V2CTrydanCommandError):
            await api.async_write("Paused", 0)
        assert writes == ["Paused=1", "Paused=0"]


async def test_real_timeout_is_reported_after_bounded_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real transport timeouts must not be lost behind the generic final error."""

    async def slow_handler(_request: web.Request) -> web.Response:
        await asyncio.sleep(0.1)
        return web.json_response(VALID_DATA)

    app = web.Application()
    app.router.add_get("/RealTimeData", slow_handler)
    async with TestServer(app) as server, ClientSession() as session:
        use_local_server(monkeypatch, server)
        monkeypatch.setattr(api_module, "READ_TIMEOUT", 0.01)
        api = V2CTrydanApi(session, "127.0.0.1")
        with pytest.raises(V2CTrydanConnectionError, match=r"3 attempts.*timed out"):
            await api.async_get_realtime_data()
        assert api.diagnostics["last_failed_read"]["attempts"] == 3


async def test_redirect_is_not_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A portal or redirected endpoint is not the configured charger API."""
    unexpected_requests = 0

    async def redirect_handler(_request: web.Request) -> web.Response:
        return web.Response(status=302, headers={"Location": "/unexpected"})

    async def unexpected_handler(_request: web.Request) -> web.Response:
        nonlocal unexpected_requests
        unexpected_requests += 1
        return web.json_response(VALID_DATA)

    app = web.Application()
    app.router.add_get("/RealTimeData", redirect_handler)
    app.router.add_get("/unexpected", unexpected_handler)
    async with TestServer(app) as server, ClientSession() as session:
        use_local_server(monkeypatch, server)
        api = V2CTrydanApi(session, "127.0.0.1")
        with pytest.raises(V2CTrydanConnectionError, match="HTTP 302"):
            await api.async_get_realtime_data()
        assert unexpected_requests == 0


@pytest.mark.parametrize("operation", ("read", "write"))
async def test_invalid_text_is_a_domain_error(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Actual decoding failures must not escape the integration's error contract."""
    requests = 0

    async def invalid_handler(_request: web.Request) -> web.Response:
        nonlocal requests
        requests += 1
        return web.Response(body=b"\xff", content_type="text/plain", charset="utf-8")

    app = web.Application()
    app.router.add_get("/RealTimeData", invalid_handler)
    app.router.add_get("/write/{command}", invalid_handler)
    async with TestServer(app) as server, ClientSession() as session:
        use_local_server(monkeypatch, server)
        api = V2CTrydanApi(session, "127.0.0.1")
        if operation == "read":
            with pytest.raises(V2CTrydanInvalidResponseError, match="not valid text"):
                await api.async_get_realtime_data()
        else:
            with pytest.raises(V2CTrydanCommandError, match="not valid text"):
                await api.async_write("Paused", 1)
        assert requests == 1
