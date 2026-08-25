"""Session tools — list_sessions, get_session_facts, get_session_messages.

Provides session listing and per-session fact/message retrieval for
project conversation sessions.
"""

from __future__ import annotations

import logging
import time

from fastmcp import Context

from openzync_mcp.server import mcp

logger = logging.getLogger("openzync.mcp.tools.sessions")


@mcp.tool
async def list_sessions(
    ctx: Context,
    # ⚠️ BREAKING: project_id parameter removed — the SDK resolves the
    # project from the API key; the param was never used.
    limit: int = 50,
    cursor: str | None = None,
) -> str:
    """List sessions for your project.

    Each session groups a sequence of conversation messages (episodes).
    Sessions are soft-deletable and have an optional external ID set by
    the caller.

    Pagination: pass the ``cursor`` value from a previous response to
    retrieve the next page.  When ``cursor`` is omitted, the first page
    is returned.

    Args:
        limit: Maximum sessions to return per page (default 50, max 200).
        cursor: Opaque pagination cursor from a previous response.
            Omit to fetch the first page.

    Returns:
        A formatted string listing sessions with IDs and message counts,
        plus a pagination hint if more pages are available.
    """
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s limit=%d cursor=%s",
        "list_sessions",
        limit,
        cursor,
    )

    client = ctx.lifespan_context["client"]
    try:
        result = await client.sessions.list(
            limit=limit,
            cursor=cursor,
        )

        sessions = result.get("data", result.get("items", []))
        next_cursor = result.get("next_cursor")
        has_more = result.get("has_more", False)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d session_count=%d has_more=%s",
            "list_sessions",
            round(elapsed * 1000),
            len(sessions),
            has_more,
        )

        if not sessions:
            return "No sessions found."

        lines = [f"Found {len(sessions)} session(s):"]
        for s in sessions:
            sid = (s.get("id") or "")[:8]
            ext = s.get("external_id", "")
            msgs = s.get("message_count", 0)
            lines.append(f"  [{sid}] {ext} ({msgs} messages)")

        # Append pagination hint
        if has_more and next_cursor:
            lines.append(
                f'\nMore sessions available. Use cursor="{next_cursor}" for the next page.'
            )

        return "\n".join(lines)
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d",
            "list_sessions",
            round(elapsed * 1000),
            exc_info=True,
        )
        raise


@mcp.tool
async def get_session_facts(
    ctx: Context,
    session_id: str,
    limit: int = 50,
) -> str:
    """Get facts extracted from messages in a session (newest first).

    Only non-invalidated facts are included.

    Args:
        session_id: The internal UUID of the session.
        limit: Maximum facts per page (default 50, max 200).

    Returns:
        A formatted string of facts with confidence scores, plus a
        pagination hint if more pages are available.
    """
    if not session_id or not session_id.strip():
        raise ValueError("session_id must be a non-empty string.")
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s session_id=%s limit=%d",
        "get_session_facts",
        session_id,
        limit,
    )

    client = ctx.lifespan_context["client"]
    try:
        response = await client.sessions.facts(session_id, limit=limit)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d fact_count=%d has_more=%s",
            "get_session_facts",
            round(elapsed * 1000),
            len(response.data),
            response.has_more,
        )

        if not response.data:
            return "No facts found for this session."

        lines = [f"Found {len(response.data)} fact(s):"]
        for fact in response.data:
            lines.append(f"  [{fact.confidence:.2f}] {fact.content[:200]}")

        if response.has_more and response.next_cursor:
            lines.append(
                f'\nMore facts available. Use cursor="{response.next_cursor}" for the next page.'
            )

        return "\n".join(lines)
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d session_id=%s",
            "get_session_facts",
            round(elapsed * 1000),
            session_id,
            exc_info=True,
        )
        raise


@mcp.tool
async def get_session_messages(
    ctx: Context,
    session_id: str,
    limit: int = 50,
) -> str:
    """Get the messages (episodes) of a session in order.

    Args:
        session_id: The internal UUID of the session.
        limit: Maximum messages per page (default 50, max 200).

    Returns:
        A formatted string listing messages with role and content, plus
        a pagination hint if more pages are available.
    """
    if not session_id or not session_id.strip():
        raise ValueError("session_id must be a non-empty string.")
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s session_id=%s limit=%d",
        "get_session_messages",
        session_id,
        limit,
    )

    client = ctx.lifespan_context["client"]
    try:
        response = await client.sessions.messages(session_id, limit=limit)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d message_count=%d has_more=%s",
            "get_session_messages",
            round(elapsed * 1000),
            len(response.data),
            response.has_more,
        )

        if not response.data:
            return "No messages found for this session."

        lines = [f"Found {len(response.data)} message(s):"]
        for msg in response.data:
            content = msg.content.replace("\n", " ")[:200]
            lines.append(f"  [{msg.role}] {content}")

        if response.has_more and response.next_cursor:
            lines.append(
                f'\nMore messages available. Use cursor="{response.next_cursor}" '
                "for the next page."
            )

        return "\n".join(lines)
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d session_id=%s",
            "get_session_messages",
            round(elapsed * 1000),
            session_id,
            exc_info=True,
        )
        raise
