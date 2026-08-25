"""Search tool — global_search.

Organization-wide resource search across projects, users, and sessions.
"""

from __future__ import annotations

import logging
import time

from fastmcp import Context

from openzync_mcp.server import mcp

logger = logging.getLogger("openzync.mcp.tools.search")


@mcp.tool
async def global_search(
    ctx: Context,
    query: str,
    limit: int = 10,
) -> str:
    """Search across projects, users, and sessions in your organization.

    Requires a principal with user attribution and the ``project:read``
    permission — anonymous or unattributed credentials are rejected by
    the backend.  Results are scoped to resources the credential can
    access.

    Args:
        query: Search query string (1–200 chars).
        limit: Maximum results (default 10, max 50).

    Returns:
        A formatted string of matching resources with type, label, and ID.
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string.")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50.")

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s query_length=%d limit=%d",
        "global_search",
        len(query),
        limit,
    )

    client = ctx.lifespan_context["client"]
    try:
        response = await client.search.global_search(query=query, limit=limit)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d result_count=%d",
            "global_search",
            round(elapsed * 1000),
            len(response.results),
        )

        if not response.results:
            return "No results found."

        lines = [f"Found {len(response.results)} result(s):"]
        for item in response.results:
            subtitle = f" — {item.subtitle}" if item.subtitle else ""
            lines.append(f"  [{item.type}] {item.label}{subtitle} ({item.id[:8]}...)")

        return "\n".join(lines)
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d",
            "global_search",
            round(elapsed * 1000),
            exc_info=True,
        )
        raise
