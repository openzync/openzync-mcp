"""Project tools — update_project_member.

Member management for the project resolved from the API key.
"""

from __future__ import annotations


from fastmcp import Context

from openzync_mcp.server import get_client, mcp
from openzync_mcp.tools._log import log_error, log_invoke, log_success


_ALLOWED_ROLES = {"owner", "member"}


@mcp.tool
async def update_project_member(
    ctx: Context,
    user_id: str,
    role: str,
) -> str:
    """Change a member's role within your project.

    Requires a credential with the ``project:manage`` permission —
    member-level credentials are rejected by the backend.

    Args:
        user_id: The UUID of the user whose role to change.
        role: New project role (``"owner"`` or ``"member"``).  Required —
            there is no default, because defaulting to ``"member"`` silently
            demoted an owner when the caller meant to change nothing.

    Returns:
        A confirmation message with the updated membership.
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id must be a non-empty string.")
    if role not in _ALLOWED_ROLES:
        raise ValueError(f"Invalid role: {role}. Allowed: {', '.join(sorted(_ALLOWED_ROLES))}.")

    start = log_invoke("update_project_member", " user_id=%s role=%s", user_id, role)

    client = get_client(ctx)
    try:
        member = await client.projects.update_member(user_id, role=role)

        log_success(
            "update_project_member",
            start,
            " user_id=%s role=%s",
            user_id,
            role,
        )
        return f"Project member updated.\n  User ID: {member.user_id}\n  Role: {member.role}"
    except Exception:
        log_error(
            "update_project_member",
            start,
            " user_id=%s role=%s",
            user_id,
            role,
        )
        raise
