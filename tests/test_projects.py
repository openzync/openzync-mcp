"""Tests for the project tool: update_project_member."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.project import ProjectMemberResponse


def make_member(**overrides) -> ProjectMemberResponse:
    defaults = {
        "id": "mem-1",
        "project_id": "proj-uuid-1",
        "user_id": "user-uuid-1",
        "role": "owner",
        "created_at": "2026-01-01T00:00:00Z",
    }
    return ProjectMemberResponse(**(defaults | overrides))


async def test_update_project_member_success(mcp_client, mock_client) -> None:
    mock_client.projects.update_member.return_value = make_member(role="owner")

    result = await mcp_client.call_tool(
        "update_project_member", {"user_id": "user-uuid-1", "role": "owner"}
    )

    mock_client.projects.update_member.assert_awaited_once_with("user-uuid-1", role="owner")
    text = result.content[0].text
    assert "Project member updated." in text
    assert "User ID: user-uuid-1" in text
    assert "Role: owner" in text


async def test_update_project_member_role_required(mcp_client, mock_client) -> None:
    """``role`` is required — there is no default.

    The old default (``"member"``) silently demoted a project OWNER when
    the caller meant to change nothing, so the parameter must be supplied
    explicitly.
    """
    mock_client.projects.update_member.return_value = make_member(role="member")

    with pytest.raises(ToolError, match="Missing required argument") as exc_info:
        await mcp_client.call_tool("update_project_member", {"user_id": "user-uuid-1"})
    assert "role" in str(exc_info.value)

    # No silent default is invented and the SDK is never reached.
    mock_client.projects.update_member.assert_not_called()

    # An explicit role is forwarded verbatim.
    mock_client.projects.update_member.return_value = make_member(role="owner")
    result = await mcp_client.call_tool(
        "update_project_member", {"user_id": "user-uuid-1", "role": "owner"}
    )

    mock_client.projects.update_member.assert_awaited_once_with("user-uuid-1", role="owner")
    assert "Role: owner" in result.content[0].text


async def test_update_project_member_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="user_id must be a non-empty string."):
        await mcp_client.call_tool("update_project_member", {"user_id": "", "role": "member"})

    with pytest.raises(ToolError, match="Invalid role: admin."):
        await mcp_client.call_tool(
            "update_project_member", {"user_id": "user-uuid-1", "role": "admin"}
        )

    mock_client.projects.update_member.assert_not_called()
