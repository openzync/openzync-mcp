"""Structured extraction tools — list_structured_extractions, get_structured_extraction.

Session-scoped structured-extraction result queries.
"""

from __future__ import annotations

import json
import logging
import time

from fastmcp import Context

from openzync_mcp.server import mcp

logger = logging.getLogger("openzync.mcp.tools.extractions")


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

    start = time.monotonic()
    logger.info("mcp.tool.invoke tool=%s session_id=%s", "list_structured_extractions", session_id)

    client = ctx.lifespan_context["client"]
    try:
        response = await client.structured_extractions.list(session_id)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d extraction_count=%d total=%d",
            "list_structured_extractions",
            round(elapsed * 1000),
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
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d session_id=%s",
            "list_structured_extractions",
            round(elapsed * 1000),
            session_id,
            exc_info=True,
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

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s session_id=%s episode_id=%s",
        "get_structured_extraction",
        session_id,
        episode_id,
    )

    client = ctx.lifespan_context["client"]
    try:
        ex = await client.structured_extractions.get_by_episode(session_id, episode_id)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d episode_id=%s",
            "get_structured_extraction",
            round(elapsed * 1000),
            episode_id,
        )

        return (
            f"Structured extraction for episode {episode_id}:\n"
            f"  Schema: {ex.schema_id or '—'}\n"
            f"  Data: {json.dumps(ex.data)}"
        )
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d session_id=%s episode_id=%s",
            "get_structured_extraction",
            round(elapsed * 1000),
            session_id,
            episode_id,
            exc_info=True,
        )
        raise
