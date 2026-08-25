"""Project tools — update_project_member.

Member management for the project resolved from the API key.
"""

from __future__ import annotations

import logging
import time

from fastmcp import Context

from openzync_mcp.server import mcp

logger = logging.getLogger("openzync.mcp.tools.projects")

_ALLOWED_ROLES = {"owner", "member"}


@mcp.tool
async def update_project_member(
    ctx: Context,
    user_id: str,
    role: str = "member",
) -> str:
    """Change a member's role within your project.

    Requires a credential with the ``project:manage`` permission —
    member-level credentials are rejected by the backend.

    Args:
        user_id: The UUID of the user whose role to change.
        role: New project role (``"owner"`` or ``"member"``).

    Returns:
        A confirmation message with the updated membership.
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id must be a non-empty string.")
    if role not in _ALLOWED_ROLES:
        raise ValueError(f"Invalid role: {role}. Allowed: {', '.join(sorted(_ALLOWED_ROLES))}.")

    start = time.monotonic()
    logger.info(
        "mcp.tool.invoke tool=%s user_id=%s role=%s", "update_project_member", user_id, role
    )

    client = ctx.lifespan_context["client"]
    try:
        member = await client.projects.update_member(user_id, role=role)

        elapsed = time.monotonic() - start
        logger.info(
            "mcp.tool.success tool=%s duration_ms=%d user_id=%s role=%s",
            "update_project_member",
            round(elapsed * 1000),
            user_id,
            role,
        )
        return f"Project member updated.\n  User ID: {member.user_id}\n  Role: {member.role}"
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "mcp.tool.error tool=%s duration_ms=%d user_id=%s role=%s",
            "update_project_member",
            round(elapsed * 1000),
            user_id,
            role,
            exc_info=True,
        )
        raise
