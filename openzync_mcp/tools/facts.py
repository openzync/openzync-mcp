"""Fact tools — add_fact, list_facts, get_fact_history, retract_fact.

These tools manage knowledge fact triples (subject-predicate-object)
extracted from or injected into a project's knowledge graph, including
their temporal validity and invalidation lineage.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastmcp import Context

from openzync_mcp.server import get_client, mcp
from openzync_mcp.tools._log import log_error, log_invoke, log_success


def _iso(value: datetime | None) -> str:
    """Render a timestamp as an RFC-3339 string (UTC as ``Z``).

    The SDK models type temporal fields as ``datetime``.  Interpolating one
    straight into a tool's text emits Python's ``str()`` form
    (``2026-02-01 00:00:00+00:00``) — a shape no other OpenZync surface
    emits, so an agent parsing RFC-3339 fails on it.

    Args:
        value: The timestamp to render, or ``None``.

    Returns:
        An RFC-3339 timestamp, or ``""`` when ``value`` is ``None``.
    """
    if value is None:
        return ""
    if value.tzinfo is None:
        # Backend timestamps are UTC (per the SDK model docstrings); a
        # naive value would render without an offset, which is not RFC-3339.
        value = value.replace(tzinfo=UTC)
    return value.isoformat().replace("+00:00", "Z")


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

    start = log_invoke(
        "add_fact",
        " fact_count=%d session_id=%s",
        len(facts),
        session_id,
    )

    client = get_client(ctx)
    try:
        response = await client.facts.add(
            facts=facts,
            session_id=session_id,
        )
        log_success(
            "add_fact",
            start,
            " accepted_count=%d job_id=%s",
            response.accepted_count,
            response.job_id,
        )
        return (
            f"{response.accepted_count} fact(s) accepted for processing (job: {response.job_id})."
        )
    except Exception:
        log_error(
            "add_fact",
            start,
            " fact_count=%d",
            len(facts),
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
    offset: int = 0,
    cursor: str | None = None,
) -> str:
    """List facts currently valid in your project's knowledge graph.

    Returns only facts whose validity range contains ``as_of``
    (default: now).  Superseded and retracted facts are excluded —
    use ``get_fact_history`` to inspect invalidated facts.

    Args:
        limit: Maximum facts to return per page (default 50, max 200).
        as_of: Optional effective-at timestamp (ISO-8601) to list facts
            as they were at that point in time.
        offset: Number of facts to skip (default 0). Ignored when
            ``cursor`` is set.
        cursor: Opaque cursor from a previous response for the next page.

    Returns:
        A formatted string of facts with confidence scores, plus a
        pagination hint if more pages are available.
    """
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")
    if offset < 0:
        raise ValueError("offset must be >= 0.")

    start = log_invoke(
        "list_facts",
        " limit=%d as_of=%s offset=%d cursor=%s",
        limit,
        as_of,
        offset,
        cursor,
    )

    client = get_client(ctx)
    try:
        response = await client.facts.list(as_of=as_of, limit=limit, offset=offset, cursor=cursor)

        log_success(
            "list_facts",
            start,
            " fact_count=%d has_more=%s",
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
                f'\nMore facts available. Use cursor="{response.next_cursor}" for the next page.'
            )

        return "\n".join(lines)
    except Exception:
        log_error(
            "list_facts",
            start,
            "",
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

    start = log_invoke("get_fact_history", " fact_id=%s", fact_id)

    client = get_client(ctx)
    try:
        response = await client.facts.history(fact_id)

        log_success(
            "get_fact_history",
            start,
            " event_count=%d",
            len(response.events),
        )

        lines = [
            f"Fact {fact_id}:",
            f"  Content: {response.fact.content}",
            f"  Confidence: {response.fact.confidence:.2f}",
            f"  Valid from: {_iso(response.fact.valid_from) or 'unknown'}",
            f"  Invalid at: {_iso(response.fact.invalid_at) or '—'}",
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
        log_error(
            "get_fact_history",
            start,
            " fact_id=%s",
            fact_id,
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

    start = log_invoke("retract_fact", " fact_id=%s", fact_id)

    client = get_client(ctx)
    try:
        fact = await client.facts.retract(fact_id, reason=reason)

        log_success(
            "retract_fact",
            start,
            " fact_id=%s invalid_at=%s",
            fact.id,
            _iso(fact.invalid_at),
        )
        return (
            f"Fact retracted.\n"
            f"  ID: {fact.id}\n"
            f"  Content: {fact.content}\n"
            f"  Invalid at: {_iso(fact.invalid_at) or 'already closed'}"
        )
    except Exception:
        log_error(
            "retract_fact",
            start,
            " fact_id=%s",
            fact_id,
        )
        raise
