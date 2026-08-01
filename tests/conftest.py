"""Shared fixtures and helpers for the openzync-mcp test suite.

Tests exercise the tools end-to-end through an in-process FastMCP
``Client(mcp)`` with the SDK client replaced by an AsyncMock-based fake.
The fake is injected via the ``mcp._oz_client`` lifespan hook — the server
lifespan picks it up as-is and does not close it (test fixtures own its
lifecycle).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastmcp.client import Client

from openzync.models.graph import GraphNode
from openzync_mcp.server import mcp


class AsyncIterable:
    """A reusable async iterator over a fixed sequence.

    This fakes the SDK's paginated iterators (``AsyncPaginatedIterator``).
    The graph tool does ``await client.graph.nodes(...)`` and then
    ``async for`` over the result, so the mock must return an object that
    is awaitable and then async-iterable.  A bare async generator cannot be
    awaited, so we use a coroutine-returning side_effect (see
    ``async_iter``) that resolves to this object.
    """

    def __init__(self, items: list) -> None:
        self._items = iter(items)

    def __aiter__(self) -> AsyncIterator:
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def async_iter(items: list) -> AsyncIterable:
    """Return a fresh async-iterable over ``items``.

    Used as ``side_effect = lambda **kw: async_iter([...])`` on graph
    client mocks — a fresh instance per call is essential for
    ``client.graph.edges`` because ``get_user_graph`` awaits it once per
    entity via ``asyncio.gather``; a shared instance would be consumed by
    the first iteration.
    """
    return AsyncIterable(items)


def make_node(
    name: str = "Entity", type_: str = "Person", summary: str = "", id_: str | None = None
) -> GraphNode:
    """Factory helper returning a GraphNode with a stable shape."""
    return GraphNode(
        id=id_ or str(uuid.uuid4()),
        name=name,
        type=type_,
        summary=summary,
    )


def make_edge_dict(
    source_id: str | None = None,
    target_id: str | None = None,
    type_: str = "knows",
    id_: str | None = None,
) -> dict:
    """Factory helper returning an edge as the RAW DICT the SDK yields.

    The SDK's ``graph.edges()`` does not wrap items in ``GraphEdge`` (unlike
    ``nodes()``, which wraps ``GraphNode``) — mocks must mirror that exact
    contract or they certify a crash path green.
    """
    return {
        "id": id_ or str(uuid.uuid4()),
        "source_id": source_id or str(uuid.uuid4()),
        "target_id": target_id or str(uuid.uuid4()),
        "type": type_,
        "properties": {},
        "created_at": None,
    }


@pytest.fixture
def mock_client() -> MagicMock:
    """Fake SDK client with AsyncMock sub-clients for each domain."""
    client = MagicMock()
    client.memory = AsyncMock()
    client.graph = AsyncMock()
    client.facts = AsyncMock()
    client.sessions = AsyncMock()
    client.users = AsyncMock()
    return client


@pytest_asyncio.fixture
async def mcp_client(mock_client) -> AsyncIterator[Client]:
    """In-process FastMCP client with the mock SDK injected via lifespan."""
    mcp._oz_client = mock_client
    try:
        async with Client(mcp) as client:
            yield client
    finally:
        mcp._oz_client = None
