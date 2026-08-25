"""Fact tools — add_fact, list_facts, get_fact_history, retract_fact.

These tools manage knowledge fact triples (subject-predicate-object)
extracted from or injected into a project's knowledge graph, including
their temporal validity and invalidation lineage.
"""

from __future__ import annotations

import logging
import time

from fastmcp import Context

from openzync_mcp.server import mcp

logger = logging.getLogger("openzync.mcp.tools.facts")


@mcp.tool
async def add_fact(
    ctx: Context,
    # ⚠️ BREAKING: project_id parameter removed — the SDK resolves the
    # project from the API key; the param was never used.
    facts: list[dict],
    session_id: str,
) -> str:
    """Add business fact triples to your project's knowledge graph.

    Each fact must be a triple with ``subject``, ``predicate``, and
    ``object`` keys.  Maximum 500 triples per call.

    Args:
        facts: List of fact dicts, each with ``subject`` (str),
            ``predicate`` (str), ``object`` (str), and optional
            ``confidence`` (float, default 1.0).
        session_id: Session external ID — required, the fact triples are
            attributed to an existing session.

    Returns:
        A confirmation message with accepted count and job ID.
    """
    if not facts:
        raise ValueError("At least one fact is required.")
    if len(facts) > 500:
        raise ValueError("Maximum 500 facts per call.")

    # Validate each fact has required keys
    for i, fact in enumerate(facts):
        if not isinstance(fact, dict):
            raise ValueError(f"Fact at index {i} must be a dict, got {type(fact).__name__}.")
        missing = {"subject", "predicate", "object"} - set(fact.keys())
        if missing:
            raise ValueError(
                f"Fact at index {i} is missing required key(s): {', '.join(sorted(missing))}."
            )

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s fact_count=%d session_id=%s",
        "add_fact",
        len(facts),
        session_id,
    )

    client = ctx.lifespan_context["client"]
    try:
        response = await client.facts.add(
            facts=facts,
            session_id=session_id,
        )
        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d accepted_count=%d job_id=%s",
            "add_fact",
            round(elapsed * 1000),
            response.accepted_count,
            response.job_id,
        )
        return (
            f"{response.accepted_count} fact(s) accepted for processing (job: {response.job_id})."
        )
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d fact_count=%d",
            "add_fact",
            round(elapsed * 1000),
            len(facts),
            exc_info=True,
        )
        raise


@mcp.tool
async def list_facts(
    ctx: Context,
    # ⚠️ BREAKING: project_id removed (resolved from the API key) and the
    # keyword-search signature replaced — this tool now calls the real
    # fact-list endpoint instead of faking search via graph.search.
    limit: int = 50,
    as_of: str | None = None,
) -> str:
    """List facts currently valid in your project's knowledge graph.

    Returns only facts whose validity range contains ``as_of``
    (default: now).  Superseded and retracted facts are excluded —
    use ``get_fact_history`` to inspect invalidated facts.

    Args:
        limit: Maximum facts to return per page (default 50, max 200).
        as_of: Optional effective-at timestamp (ISO-8601) to list facts
            as they were at that point in time.

    Returns:
        A formatted string of facts with confidence scores, plus a
        pagination hint if more pages are available.
    """
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s limit=%d as_of=%s",
        "list_facts",
        limit,
        as_of,
    )

    client = ctx.lifespan_context["client"]
    try:
        response = await client.facts.list(as_of=as_of, limit=limit)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d fact_count=%d has_more=%s",
            "list_facts",
            round(elapsed * 1000),
            len(response.data),
            response.has_more,
        )

        if not response.data:
            return "No facts found."

        lines = [f"Found {len(response.data)} fact(s):"]
        for fact in response.data:
            lines.append(f"  [{fact.confidence:.2f}] {fact.content[:200]}")

        if response.has_more and response.next_cursor:
            lines.append(
                f"\nMore facts available. Use offset={response.next_cursor} for the next page."
            )

        return "\n".join(lines)
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d",
            "list_facts",
            round(elapsed * 1000),
            exc_info=True,
        )
        raise


@mcp.tool
async def get_fact_history(ctx: Context, fact_id: str) -> str:
    """Get a fact plus its invalidation lineage (newest first).

    Shows how a fact evolved: supersession chains, retractions, and the
    reasons behind each invalidation event.

    Args:
        fact_id: The UUID of the fact whose lineage to fetch.

    Returns:
        A formatted string with the current fact state and its
        invalidation events.
    """
    if not fact_id or not fact_id.strip():
        raise ValueError("fact_id must be a non-empty string.")

    start = time.monotonic()
    logger.info("mcp.tool.invoke tool=%s fact_id=%s", "get_fact_history", fact_id)

    client = ctx.lifespan_context["client"]
    try:
        response = await client.facts.history(fact_id)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d event_count=%d",
            "get_fact_history",
            round(elapsed * 1000),
            len(response.events),
        )

        lines = [
            f"Fact {fact_id}:",
            f"  Content: {response.fact.content}",
            f"  Confidence: {response.fact.confidence:.2f}",
            f"  Valid from: {response.fact.valid_from or 'unknown'}",
            f"  Invalid at: {response.fact.invalid_at or '—'}",
        ]

        if not response.events:
            lines.append("\nNo invalidation events — fact is current.")
        else:
            lines.append(f"\n{len(response.events)} invalidation event(s):")
            for ev in response.events:
                reason = f" — {ev.reason}" if ev.reason else ""
                lines.append(f"  [{ev.kind}] at {ev.at_time}{reason}")

        return "\n".join(lines)
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d fact_id=%s",
            "get_fact_history",
            round(elapsed * 1000),
            fact_id,
            exc_info=True,
        )
        raise


@mcp.tool
async def retract_fact(
    ctx: Context,
    fact_id: str,
    reason: str | None = None,
) -> str:
    """Retract a fact by setting its invalid_at timestamp.

    Requires a credential with the ``project:write`` permission —
    read-only API keys are rejected by the backend.

    Idempotent — retracting an already-closed fact is a no-op returning
    the unchanged fact.

    Args:
        fact_id: The UUID of the fact to retract.
        reason: Optional human-readable explanation of the retraction.

    Returns:
        A confirmation message with the retraction timestamp.
    """
    if not fact_id or not fact_id.strip():
        raise ValueError("fact_id must be a non-empty string.")

    start = time.monotonic()
    logger.info("mcp.tool.invoke tool=%s fact_id=%s", "retract_fact", fact_id)

    client = ctx.lifespan_context["client"]
    try:
        fact = await client.facts.retract(fact_id, reason=reason)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d fact_id=%s invalid_at=%s",
            "retract_fact",
            round(elapsed * 1000),
            fact.id,
            fact.invalid_at,
        )
        return (
            f"Fact retracted.\n"
            f"  ID: {fact.id}\n"
            f"  Content: {fact.content}\n"
            f"  Invalid at: {fact.invalid_at or 'already closed'}"
        )
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d fact_id=%s",
            "retract_fact",
            round(elapsed * 1000),
            fact_id,
            exc_info=True,
        )
        raise
