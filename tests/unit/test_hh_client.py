from typing import Any

import aiohttp
import pytest

from infrastructure.hh import HHClient, HHError


class Response:
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def json(self):
        return self.payload


class Session:
    responses: list[Any] = []
    headers = None
    calls = 0

    def __init__(self, *, timeout, headers):
        type(self).headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def get(self, _):
        type(self).calls += 1
        value = type(self).responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


@pytest.mark.asyncio
async def test_header_and_bounded_retry(monkeypatch):
    Session.responses = [Response(503, {}), Response(200, [{"id": "ru", "name": "Русский"}])]
    Session.calls = 0
    monkeypatch.setattr(aiohttp, "ClientSession", Session)
    client = HHClient(base_url="https://hh.invalid", user_agent="HAIntly/test", timeout=1, retries=1, backoff=0)
    assert (await client.languages())[0]["id"] == "ru"
    assert Session.headers == {"HH-User-Agent": "HAIntly/test"}
    assert Session.calls == 2


@pytest.mark.asyncio
async def test_timeout_stops_after_bound(monkeypatch):
    Session.responses = [TimeoutError(), TimeoutError(), TimeoutError()]
    Session.calls = 0
    monkeypatch.setattr(aiohttp, "ClientSession", Session)
    client = HHClient(base_url="https://hh.invalid", user_agent="agent", timeout=0.01, retries=2, backoff=0)
    with pytest.raises(HHError):
        await client.languages()
    assert Session.calls == 3


@pytest.mark.asyncio
async def test_invalid_nested_payload_rejected(monkeypatch):
    Session.responses = [Response(200, [{"id": "1", "name": "root", "areas": [{"id": "2"}]}])]
    monkeypatch.setattr(aiohttp, "ClientSession", Session)
    client = HHClient(base_url="https://hh.invalid", user_agent="agent", timeout=1, retries=0, backoff=0)
    with pytest.raises(HHError):
        await client.areas()
