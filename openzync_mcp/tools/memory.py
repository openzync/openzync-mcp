"""Memory tools — add_memory, get_context, search_memory, delete_memory.

delete_memory is NOT part of the default LLM toolset: it is destructive
(admin-only) and requires explicit allowlisting via
``OPENZYN_MCP_ALLOW_WIPE=true``. Without that env var the tool fails loud
instead of wiping.
"""

from __future__ import annotations

import logging
import os
import uuid

from fastmcp import Context

from openzync_mcp.server import get_client, mcp
from openzync_mcp.tools._log import log_error, log_invoke, log_success

logger = logging.getLogger("openzync.mcp.tools.memory")


def _is_wipe_allowlisted() -> bool:
    """Return True only when the operator explicitly allowlisted wipes.

    Destructive tools must never be on by default for LLM callers —
    the operator opts in with ``OPENZYN_MCP_ALLOW_WIPE=true`` (admin only).
    """
    return os.environ.get("OPENZYN_MCP_ALLOW_WIPE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


@mcp.tool
async def add_memory(
    ctx: Context,
    # ⚠️ BREAKING: project_id parameter removed — the SDK resolves the
    # project from the API key; the param was never used.
    messages: list[dict],
    session_id: str,
    idempotency_key: str | None = None,
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
        idempotency_key: Optional key for safe caller-level retries — pass
            the same key when retrying a timed-out or ambiguous call. When
            omitted a fresh key is generated per call: transport retries of
            this call reuse it, but a new tool call is a new episode.

    Returns:
        A confirmation message with the job ID and episode count.
    """
    if not messages:
        raise ValueError("At least one message is required.")
    if len(messages) > 1000:
        raise ValueError("Maximum 1000 messages per call.")

    start = log_invoke(
        "add_memory",
        " message_count=%d session_id=%s",
        len(messages),
        session_id,
    )

    client = get_client(ctx)
    try:
        # One key per call, reused across this call's transport retries —
        # pass idempotency_key explicitly to dedupe caller-level retries.
        new_uuid = getattr(uuid, "uuid7", None) or uuid.uuid4
        response = await client.memory.ingest(
            messages=messages,
            session_id=session_id,
            idempotency_key=idempotency_key or new_uuid().hex,
        )
        log_success(
            "add_memory",
            start,
            " episode_count=%d job_id=%s",
            response.episode_count,
            response.job_id,
        )
        return (
            f"Memory recorded. {response.episode_count} messages ingested (job: {response.job_id})."
        )
    except Exception:
        log_error(
            "add_memory",
            start,
            "",
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

    start = log_invoke(
        "get_context",
        " query_length=%d limit=%d",
        len(query),
        limit,
    )

    client = get_client(ctx)
    try:
        response = await client.memory.get_context(
            query=query,
            limit=limit,
        )
        log_success(
            "get_context",
            start,
            " context_length=%d",
            len(response.context),
        )
        return response.context
    except Exception:
        log_error(
            "get_context",
            start,
            "",
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

    start = log_invoke(
        "search_memory",
        " query_length=%d types=%s limit=%d",
        len(query),
        types,
        limit,
    )

    client = get_client(ctx)
    try:
        results = await client.graph.search(
            query=query,
            types=types,
            limit=limit,
        )

        log_success(
            "search_memory",
            start,
            " result_count=%d",
            len(results),
        )

        if not results:
            return "No results found."

        lines = [f"Found {len(results)} result(s):"]
        for r in results:
            content = (r.get("content") or "")[:200]
            score = r.get("rrf_score") or r.get("score") or 0.0
            lines.append(f"  [{score:.4f}] {content}")

        return "\n".join(lines)
    except Exception:
        log_error(
            "search_memory",
            start,
            "",
        )
        raise


# ⚠️ BREAKING: project_id parameter removed — resolved from the API key.
# Admin-only + explicit-allowlist gate: NOT in the default LLM toolset.
@mcp.tool
async def delete_memory(ctx: Context, confirm: str) -> str:
    """Delete all memory for your project (soft-delete, confirm-gated).

    ⚠️  Destructive admin-only operation — NOT in the default LLM toolset.
        Requires explicit allowlisting via ``OPENZYN_MCP_ALLOW_WIPE=true``;
        without it this tool fails loud and deletes nothing.

    Soft-deletes all episodes (messages) and facts for the project
    resolved from the API key. Sessions remain intact. This is the
    GDPR memory-wipe operation and is **irreversible** — deleted data
    is marked inactive but preserved for a 30-day grace period before
    hard-purge.

    Args:
        confirm: Must equal the project ID — the server rejects any other
            value with 422. There is no default; pass the project ID
            explicitly to prove intent.

    Returns:
        A confirmation message.

    Raises:
        ValueError: If ``confirm`` is empty.
        PermissionError: If wipes are not explicitly allowlisted (admin only).
    """
    if not confirm or not confirm.strip():
        raise ValueError("confirm must be the project ID to confirm deletion.")
    if not _is_wipe_allowlisted():
        logger.warning("mcp.tool.rejected tool=%s reason=%s", "delete_memory", "not_allowlisted")
        raise PermissionError(
            "delete_memory is not allowlisted — set OPENZYN_MCP_ALLOW_WIPE=true "
            "(admin only) to explicitly enable this destructive tool."
        )
    start = log_invoke("delete_memory")

    client = get_client(ctx)
    try:
        await client.memory.delete(confirm=confirm)
        log_success("delete_memory", start)
        return "Memory deleted successfully."
    except Exception:
        log_error(
            "delete_memory",
            start,
            "",
        )
        raise
