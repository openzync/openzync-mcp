"""User tools — create_user.

Provides dashboard user creation by caller-defined external ID.
"""

from __future__ import annotations

from fastmcp import Context

from openzync_mcp.server import get_client, mcp
from openzync_mcp.tools._log import log_error, log_invoke, log_success


@mcp.tool
async def create_user(
    ctx: Context,
    external_id: str,
    name: str | None = None,
) -> str:
    """Create a user by caller-defined external ID.

    Args:
        external_id: Caller-defined user identifier (must be non-empty).
        name: Optional display name.

    Returns:
        A formatted string confirming creation with IDs.
    """
    if not external_id or not external_id.strip():
        raise ValueError("external_id must be a non-empty string.")

    start = log_invoke(
        "create_user",
        " external_id=%s",
        external_id,
    )

    client = get_client(ctx)
    try:
        user = await client.users.create(
            external_id=external_id,
            name=name,
        )

        log_success(
            "create_user",
            start,
            " user_id=%s",
            user.id,
        )

        lines = [
            "User created successfully.",
            f"ID: {user.id}",
            f"External ID: {user.external_id}",
        ]
        if user.name is not None:
            lines.append(f"Name: {user.name}")
        return "\n".join(lines)
    except Exception:
        log_error(
            "create_user",
            start,
            "",
        )
        raise
