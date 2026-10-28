"""User tool — create_user.

Provides user management operations for the OpenZync platform.
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
    """Create a new user in the system.

    Users represent end-users within an organization.  The ``external_id``
    is chosen by the calling application (e.g. a UUID from the customer's
    auth system).  The combination ``(organization_id, external_id)`` is
    unique within the platform.

    Requires a credential holding the ``members:write`` permission
    (ADR-007 unified permission model — org-admin JWT sessions and API
    keys with that scope both qualify).  Credentials without it are
    rejected by the backend.

    Args:
        external_id: Caller-defined user identifier
            (e.g. ``"customer-abc-123"``).  Must be non-empty.
        name: Optional display name for the user.

    Returns:
        A confirmation message with the created user's ID and details.
    """
    if not external_id or not external_id.strip():
        raise ValueError("external_id must be a non-empty string.")

    start = log_invoke("create_user", " external_id=%s name=%s", external_id, name)

    client = get_client(ctx)
    try:
        user = await client.users.create(
            external_id=external_id,
            name=name,
        )

        log_success(
            "create_user",
            start,
            " user_id=%s external_id=%s",
            user.id,
            user.external_id,
        )

        return (
            f"User created successfully.\n"
            f"  ID: {user.id}\n"
            f"  External ID: {user.external_id}\n"
            f"  Name: {user.name}"
        )
    except Exception:
        log_error(
            "create_user",
            start,
            " external_id=%s",
            external_id,
        )
        raise
