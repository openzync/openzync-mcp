"""Tests for the lifespan's real-client creation path (no mock injection).

Covers server.py lines ~59-70: when ``_oz_client`` is NOT pre-set and
``OPENZYN_API_KEY`` is present, the lifespan constructs a real
``AsyncOpenZync`` from the env values and closes it on shutdown.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastmcp.client import Client

from openzync_mcp import server


@pytest.fixture
def fake_openzync(monkeypatch) -> Iterator[tuple[list, list]]:
    """Replace openzync.client.AsyncOpenZync with a recording fake."""
    calls: list[tuple[str, str]] = []
    instances: list = []

    class FakeAsyncOpenZync:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            calls.append((api_key, base_url))
            self.close = AsyncMock()
            instances.append(self)

    monkeypatch.setattr("openzync.client.AsyncOpenZync", FakeAsyncOpenZync)
    yield calls, instances


async def test_lifespan_creates_and_closes_real_client(monkeypatch, fake_openzync) -> None:
    monkeypatch.setenv("OPENZYN_API_KEY", "test-key-123")
    monkeypatch.setenv("OPENZYN_BASE_URL", "http://fake:9000")
    monkeypatch.delattr(server.mcp, "_oz_client", raising=False)

    calls, instances = fake_openzync
    async with Client(server.mcp):
        pass

    # Constructed once with exactly the env values.
    assert calls == [("test-key-123", "http://fake:9000")]
    assert len(instances) == 1
    # Owned by the lifespan — it must close the real client on shutdown.
    instances[0].close.assert_awaited_once()
    # Lifespan resets the attribute after teardown.
    assert server.mcp._oz_client is None


async def test_lifespan_no_key_no_client(monkeypatch, fake_openzync) -> None:
    """Without an API key and without injection, no client is created."""
    monkeypatch.delenv("OPENZYN_API_KEY", raising=False)
    monkeypatch.delenv("OPENZYN_BASE_URL", raising=False)
    monkeypatch.delattr(server.mcp, "_oz_client", raising=False)
    calls, instances = fake_openzync
    async with Client(server.mcp):
        pass

    assert calls == []
    assert instances == []
