"""Search tool — global_search.

Organization-wide resource search across projects, users, and sessions.
"""

from __future__ import annotations


from fastmcp import Context

from openzync_mcp.server import get_client, mcp
from openzync_mcp.tools._log import log_error, log_invoke, log_success


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

    start = log_invoke(
        "global_search",
        " query_length=%d limit=%d",
        len(query),
        limit,
    )

    client = get_client(ctx)
    try:
        response = await client.search.global_search(query=query, limit=limit)

        log_success(
            "global_search",
            start,
            " result_count=%d",
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
        log_error(
            "global_search",
            start,
            "",
        )
        raise
