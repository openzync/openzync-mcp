"""Classification tools — list_classifications, get_classification.

Session-scoped dialog classification queries (intent, emotion, valence,
arousal per episode).
"""

from __future__ import annotations


from fastmcp import Context

from openzync_mcp.server import get_client, mcp
from openzync_mcp.tools._log import log_error, log_invoke, log_success


@mcp.tool
async def list_classifications(ctx: Context, session_id: str) -> str:
    """List dialog classifications for all episodes in a session.

    Returns empty if no episodes have been classified yet (the
    classify_dialog worker may not have run).

    Args:
        session_id: The internal UUID of the session.

    Returns:
        A formatted string of classifications with intent, emotion,
        and confidence per episode.
    """
    if not session_id or not session_id.strip():
        raise ValueError("session_id must be a non-empty string.")

    start = log_invoke("list_classifications", " session_id=%s", session_id)

    client = get_client(ctx)
    try:
        response = await client.classifications.list(session_id)

        log_success(
            "list_classifications",
            start,
            " classification_count=%d total=%d",
            len(response.data),
            response.total,
        )

        if not response.data:
            return "No classifications found for this session."

        lines = [f"Found {len(response.data)} classification(s):"]
        for c in response.data:
            lines.append(
                f"  [{c.role}] intent={c.intent or '—'} emotion={c.emotion or '—'} "
                f"valence={c.valence or '—'} ({c.confidence:.2f})"
            )

        return "\n".join(lines)
    except Exception:
        log_error(
            "list_classifications",
            start,
            " session_id=%s",
            session_id,
        )
        raise


@mcp.tool
async def get_classification(ctx: Context, session_id: str, episode_id: str) -> str:
    """Get the classification for a specific episode in a session.

    Args:
        session_id: The internal UUID of the session.
        episode_id: The UUID of the episode.

    Returns:
        A formatted string with the episode's intent, emotion, valence,
        arousal, and classifier confidence.
    """
    if not session_id or not session_id.strip():
        raise ValueError("session_id must be a non-empty string.")
    if not episode_id or not episode_id.strip():
        raise ValueError("episode_id must be a non-empty string.")

    start = log_invoke(
        "get_classification",
        " session_id=%s episode_id=%s",
        session_id,
        episode_id,
    )

    client = get_client(ctx)
    try:
        c = await client.classifications.get_by_episode(session_id, episode_id)

        log_success(
            "get_classification",
            start,
            " episode_id=%s",
            episode_id,
        )

        return (
            f"Classification for episode {episode_id}:\n"
            f"  Role: {c.role}\n"
            f"  Intent: {c.intent or '—'}\n"
            f"  Emotion: {c.emotion or '—'}\n"
            f"  Valence: {c.valence or '—'}\n"
            f"  Arousal: {c.arousal or '—'}\n"
            f"  Confidence: {c.confidence:.2f}"
        )
    except Exception:
        log_error(
            "get_classification",
            start,
            " session_id=%s episode_id=%s",
            session_id,
            episode_id,
        )
        raise
