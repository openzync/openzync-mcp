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


async def test_update_project_member_default_role(mcp_client, mock_client) -> None:
    mock_client.projects.update_member.return_value = make_member(role="member")

    await mcp_client.call_tool("update_project_member", {"user_id": "user-uuid-1"})

    mock_client.projects.update_member.assert_awaited_once_with("user-uuid-1", role="member")


async def test_update_project_member_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="user_id must be a non-empty string."):
        await mcp_client.call_tool("update_project_member", {"user_id": ""})

    with pytest.raises(ToolError, match="Invalid role: admin."):
        await mcp_client.call_tool(
            "update_project_member", {"user_id": "user-uuid-1", "role": "admin"}
        )

    mock_client.projects.update_member.assert_not_called()
