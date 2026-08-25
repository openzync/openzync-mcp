"""Memory tools — add_memory, get_context, search_memory, delete_memory.

These tools provide the core memory operations: ingest messages, retrieve
context for LLM prompting, hybrid search, and full memory wipe.
"""

from __future__ import annotations

import logging
import time

from fastmcp import Context

from openzync_mcp.server import mcp

logger = logging.getLogger("openzync.mcp.tools.memory")


@mcp.tool
async def add_memory(
    ctx: Context,
    # ⚠️ BREAKING: project_id parameter removed — the SDK resolves the
    # project from the API key; the param was never used.
    messages: list[dict],
    session_id: str,
) -> str:
    """Add messages to your project's memory.

    Messages are persisted immediately as episodes in PostgreSQL and
    queued for async enrichment (entity extraction, fact extraction,
    embedding, classification, and structured extraction).  The target
    project is resolved from the API key.

    Args:
        messages: List of message objects, each with ``role``
            (``"user"`` | ``"assistant"`` | ``"system"`` | ``"tool"``)
            and ``content`` (message body text).  At least 1 message
            required, maximum 1000.
        session_id: Session external ID — required, all ingestion targets
            an existing session.

    Returns:
        A confirmation message with the job ID and episode count.
    """
    if not messages:
        raise ValueError("At least one message is required.")
    if len(messages) > 1000:
        raise ValueError("Maximum 1000 messages per call.")

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s message_count=%d session_id=%s",
        "add_memory",
        len(messages),
        session_id,
    )

    client = ctx.lifespan_context["client"]
    try:
        response = await client.memory.ingest(
            messages=messages,
            session_id=session_id,
        )
        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d episode_count=%d job_id=%s",
            "add_memory",
            round(elapsed * 1000),
            response.episode_count,
            response.job_id,
        )
        return (
            f"Memory recorded. {response.episode_count} messages ingested (job: {response.job_id})."
        )
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d",
            "add_memory",
            round(elapsed * 1000),
            exc_info=True,
        )
        raise


@mcp.tool
async def get_context(
    ctx: Context,
    # ⚠️ BREAKING: project_id parameter removed — resolved from the API key.
    query: str,
    limit: int = 20,
) -> str:
    """Assemble a context block for LLM injection from a natural-language query.

    Returns recent episodes, extracted facts, and graph entities related
    to the query.  The context is assembled via hybrid search (vector +
    BM25 + graph traversal, fused via RRF) and formatted as plain text
    suitable for inclusion in an LLM prompt.

    Args:
        query: A natural-language query describing the needed context
            (e.g. "what does the user know about machine learning").
        limit: Maximum items per source type (1–100, default 20).

    Returns:
        The assembled context text block.
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string.")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s query_length=%d limit=%d",
        "get_context",
        len(query),
        limit,
    )

    client = ctx.lifespan_context["client"]
    try:
        response = await client.memory.get_context(
            query=query,
            limit=limit,
        )
        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d context_length=%d",
            "get_context",
            round(elapsed * 1000),
            len(response.context),
        )
        return response.context
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d",
            "get_context",
            round(elapsed * 1000),
            exc_info=True,
        )
        raise


@mcp.tool
async def search_memory(
    ctx: Context,
    # ⚠️ BREAKING: project_id parameter removed — resolved from the API key.
    query: str,
    types: str = "episodes,facts",
    limit: int = 20,
) -> str:
    """Search across your project's memory using hybrid retrieval.

    Searches episodes, facts, and optionally entities matching the query.
    Results are fused via RRF and returned sorted by relevance score.

    Args:
        query: Search query string.
        types: Comma-separated result types to include:
            ``"episodes"``, ``"facts"``, ``"entities"``
            (default: ``"episodes,facts"``).
        limit: Maximum results per type (default 20, max 100).

    Returns:
        A formatted string of search results with relevance scores.
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string.")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")

    # Validate types against allowed values
    allowed_types = {"episodes", "facts", "entities"}
    requested = {t.strip() for t in types.split(",")}
    if not requested:
        raise ValueError("types must be a non-empty comma-separated list.")
    invalid = requested - allowed_types
    if invalid:
        raise ValueError(
            f"Invalid type(s): {', '.join(sorted(invalid))}. "
            f"Allowed: {', '.join(sorted(allowed_types))}."
        )

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s query=%s types=%s limit=%d",
        "search_memory",
        query,
        types,
        limit,
    )

    client = ctx.lifespan_context["client"]
    try:
        results = await client.graph.search(
            query=query,
            types=types,
            limit=limit,
        )

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d result_count=%d",
            "search_memory",
            round(elapsed * 1000),
            len(results),
        )

        if not results:
            return "No results found."

        lines = [f"Found {len(results)} result(s):"]
        for r in results[:limit]:
            content = (r.get("content") or "")[:200]
            score = r.get("rrf_score", r.get("score", 0))
            lines.append(f"  [{score:.4f}] {content}")

        return "\n".join(lines)
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d",
            "search_memory",
            round(elapsed * 1000),
            exc_info=True,
        )
        raise


# ⚠️ BREAKING: project_id parameter removed — resolved from the API key.
@mcp.tool
async def delete_memory(ctx: Context) -> str:
    """Delete all memory for your project (soft-delete).

    Soft-deletes all episodes (messages) and facts for the project
    resolved from the API key.  Sessions remain intact.  This is the
    GDPR memory-wipe operation and is **not** reversible — deleted data
    is marked inactive but preserved for a 30-day grace period before
    hard-purge.

    Returns:
        A confirmation message.
    """
    start = time.monotonic()
    logger.info("mcp.tool.invoke tool=%s", "delete_memory")

    client = ctx.lifespan_context["client"]
    try:
        await client.memory.delete()
        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d", "delete_memory", round(elapsed * 1000)
        )
        return "Memory deleted successfully."
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d",
            "delete_memory",
            round(elapsed * 1000),
            exc_info=True,
        )
        raise
