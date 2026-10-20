"""FastMCP server exposing OpenZync as LLM-accessible tools.

This replaces the previous custom JSON-RPC 2.0 implementation with the
FastMCP framework (https://gofastmcp.com).  FastMCP handles protocol
compliance, transport negotiation (stdio/SSE/HTTP), schema generation,
and input validation automatically.

Usage:
    python -m openzync_mcp --transport stdio

The OpenZync SDK client lifecycle is managed via a FastMCP lifespan.
Tools access the client through the ``get_client(ctx)`` helper, which
reads the lifespan context injected by FastMCP and fails loud when the
API key was never configured.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from openzync_mcp._config import DEFAULT_BASE_URL, validate_base_url

# ═══════════════════════════════════════════════════════════════════════════
# Lifespan — create the SDK client on server startup, close on shutdown
# ═══════════════════════════════════════════════════════════════════════════
#
# The lifespan function is called by FastMCP when the server starts
# (``mcp.run()`` or ``Client(mcp)``).  It reads the API key and base URL
# from environment variables set by ``__main__.py``.
#
# The created client is yielded as part of the lifespan context dict,
# accessible via ``get_client(ctx)`` in tool handlers.  The dict always
# contains the ``"client"`` key (``None`` when keyless) so tools get a
# fail-loud RuntimeError instead of a KeyError.
#
# For test injection, pre-set ``server._oz_client`` before creating
# ``Client(mcp)`` — the lifespan will pick it up without creating a
# new one and will NOT close it on shutdown.


def get_client(ctx: Any) -> Any:
    """Return the SDK client from the lifespan context, failing loud.

    Args:
        ctx: FastMCP request context carrying ``lifespan_context``.

    Returns:
        The configured ``AsyncOpenZync`` client (or test double).

    Raises:
        RuntimeError: When no API key was configured and no test client
            was injected — the lifespan yields ``{"client": None}``.
    """
    client = ctx.lifespan_context.get("client")
    if client is None:
        raise RuntimeError("missing OPENZYN_API_KEY — set the OPENZYN_API_KEY env var")
    return client


@asynccontextmanager
async def openzync_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Set up the OpenZync SDK client on server startup and tear it down on stop.

    Reads ``OPENZYN_API_KEY`` and ``OPENZYN_BASE_URL`` from the environment
    (set by ``__main__.py`` before ``mcp.run()``).

    The base URL is validated before the client is built: the API key is
    sent as a bearer token on every request, so a base URL pointing at
    the wrong host is a credential leak, not a typo.  A rejected URL
    raises here and the server refuses to start.

    For test injection, pre-set ``server._oz_client`` with a mock client
    before creating ``Client(mcp)``.  The lifespan will use it as-is and
    will NOT close it on shutdown (test fixtures own the lifecycle).
    """
    api_key = os.environ.get("OPENZYN_API_KEY", "")
    base_url = os.environ.get("OPENZYN_BASE_URL", DEFAULT_BASE_URL)

    validate_base_url(base_url)

    # Allow pre-set client for test injection
    client: Any = getattr(server, "_oz_client", None)
    created = False

    if client is None and api_key:
        from openzync.client import AsyncOpenZync

        client = AsyncOpenZync(api_key=api_key, base_url=base_url)
        server._oz_client = client
        created = True

    try:
        yield {"client": client}
    finally:
        if created:
            await client.close()
        server._oz_client = None


# ═══════════════════════════════════════════════════════════════════════════
# FastMCP server singleton
# ═══════════════════════════════════════════════════════════════════════════
# Imported by tools/ modules to register themselves via @mcp.tool, and by
# __main__.py to run the server.

mcp = FastMCP(
    "OpenZync-mcp",
    instructions=(
        "OpenZync agent memory platform — persist, query, and manage "
        "agent memory.  Provides tools to ingest conversation messages, "
        "retrieve context for LLM prompts, search across episodes and "
        "facts, manage facts, explore the knowledge graph, and manage "
        "users and sessions."
    ),
    version="1.0.0b2",
    lifespan=openzync_lifespan,
)

# ── Register tool modules (import triggers @mcp.tool decoration) ──────────

from openzync_mcp.tools import (  # noqa: F401, E402
    classifications,
    extractions,
    facts,
    graph,
    memory,
    observations,
    projects,
    search,
    sessions,
    users,
)

__all__ = ["get_client", "mcp"]
