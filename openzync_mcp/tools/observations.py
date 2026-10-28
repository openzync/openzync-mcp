"""Observations tool — list_observations.

Read-only access to graph-topology analysis results computed by the
background worker.
"""

from __future__ import annotations


from fastmcp import Context

from openzync_mcp.server import get_client, mcp
from openzync_mcp.tools._log import log_error, log_invoke, log_success


_ALLOWED_OBSERVATION_TYPES = {"co_occurrence", "temporal_pattern", "behavioral_pattern"}


@mcp.tool
async def list_observations(
    ctx: Context,
    subject_entity_id: str | None = None,
    observation_type: str | None = None,
    limit: int = 50,
) -> str:
    """List observations from graph-topology analysis for your project.

    Observations are read-only snapshots computed by the background
    worker — e.g. entities that co-occur, temporal patterns, or
    behavioral patterns.

    Args:
        subject_entity_id: Optional filter by subject entity UUID.
        observation_type: Optional filter — ``co_occurrence``,
            ``temporal_pattern``, or ``behavioral_pattern``.
        limit: Maximum observations per page (default 50, max 200).

    Returns:
        A formatted string of observations with type, names, and
        confidence scores.
    """
    if observation_type is not None and observation_type not in _ALLOWED_OBSERVATION_TYPES:
        raise ValueError(
            f"Invalid observation_type: {observation_type}. "
            f"Allowed: {', '.join(sorted(_ALLOWED_OBSERVATION_TYPES))}."
        )
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")

    start = log_invoke(
        "list_observations",
        " subject_entity_id=%s observation_type=%s limit=%d",
        subject_entity_id,
        observation_type,
        limit,
    )

    client = get_client(ctx)
    try:
        response = await client.observations.list(
            subject_entity_id=subject_entity_id,
            observation_type=observation_type,
            limit=limit,
        )

        log_success(
            "list_observations",
            start,
            " observation_count=%d total=%d",
            len(response.data),
            response.total,
        )

        if not response.data:
            return "No observations found."

        lines = [f"Found {len(response.data)} observation(s):"]
        for obs in response.data:
            subject = obs.subject_entity_name or obs.subject_entity_id[:8]
            related = (
                f" ↔ {obs.related_entity_name or obs.related_entity_id[:8]}"
                if obs.related_entity_id
                else ""
            )
            lines.append(f"  [{obs.observation_type}] {subject}{related} ({obs.confidence:.2f})")
            lines.append(f"    {obs.content[:200]}")

        return "\n".join(lines)
    except Exception:
        log_error(
            "list_observations",
            start,
            " observation_type=%s",
            observation_type,
        )
        raise
