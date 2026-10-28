"""Structured extraction tools — list_structured_extractions, get_structured_extraction.

Session-scoped structured-extraction result queries.
"""

from __future__ import annotations

import json

from fastmcp import Context

from openzync_mcp.server import get_client, mcp
from openzync_mcp.tools._log import log_error, log_invoke, log_success


@mcp.tool
async def list_structured_extractions(ctx: Context, session_id: str) -> str:
    """List structured extractions for all episodes in a session.

    Returns empty if no episodes have been processed by the
    extract_structured worker yet.

    Args:
        session_id: The internal UUID of the session.

    Returns:
        A formatted string of extraction results with episode ID and
        extracted data payload.
    """
    if not session_id or not session_id.strip():
        raise ValueError("session_id must be a non-empty string.")

    start = log_invoke("list_structured_extractions", " session_id=%s", session_id)

    client = get_client(ctx)
    try:
        response = await client.structured_extractions.list(session_id)

        log_success(
            "list_structured_extractions",
            start,
            " extraction_count=%d total=%d",
            len(response.items),
            response.total,
        )

        if not response.items:
            return "No structured extractions found for this session."

        lines = [f"Found {len(response.items)} extraction(s):"]
        for ex in response.items:
            data = json.dumps(ex.data)
            lines.append(f"  [episode {ex.episode_id[:8]}] {data[:200]}")

        return "\n".join(lines)
    except Exception:
        log_error(
            "list_structured_extractions",
            start,
            " session_id=%s",
            session_id,
        )
        raise


@mcp.tool
async def get_structured_extraction(ctx: Context, session_id: str, episode_id: str) -> str:
    """Get the structured extraction for a specific episode in a session.

    Args:
        session_id: The internal UUID of the session.
        episode_id: The UUID of the episode.

    Returns:
        A formatted string with the extracted data payload.
    """
    if not session_id or not session_id.strip():
        raise ValueError("session_id must be a non-empty string.")
    if not episode_id or not episode_id.strip():
        raise ValueError("episode_id must be a non-empty string.")

    start = log_invoke(
        "get_structured_extraction",
        " session_id=%s episode_id=%s",
        session_id,
        episode_id,
    )

    client = get_client(ctx)
    try:
        ex = await client.structured_extractions.get_by_episode(session_id, episode_id)

        log_success(
            "get_structured_extraction",
            start,
            " episode_id=%s",
            episode_id,
        )

        return (
            f"Structured extraction for episode {episode_id}:\n"
            f"  Schema: {ex.schema_id or '—'}\n"
            f"  Data: {json.dumps(ex.data)}"
        )
    except Exception:
        log_error(
            "get_structured_extraction",
            start,
            " session_id=%s episode_id=%s",
            session_id,
            episode_id,
        )
        raise
