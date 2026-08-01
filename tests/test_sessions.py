"""Tests for the session tool: list_sessions."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

PROJECT_ID = "proj-123"


async def test_list_sessions_success(mcp_client, mock_client) -> None:
    mock_client.sessions.list.return_value = {
        "data": [{"id": "sess-1", "external_id": "ext-1", "message_count": 5}],
        "has_more": False,
    }

    result = await mcp_client.call_tool("list_sessions", {"project_id": PROJECT_ID, "limit": 10})

    mock_client.sessions.list.assert_awaited_once_with(limit=10, cursor=None)
    text = result.content[0].text
    assert "Found 1 session(s):" in text
    assert "[sess-1] ext-1 (5 messages)" in text
    # has_more=False → no pagination hint appended.
    assert "More sessions available" not in text


async def test_list_sessions_pagination_hint(mcp_client, mock_client) -> None:
    # "items" key fallback + has_more/cursor hint branch.
    mock_client.sessions.list.return_value = {
        "items": [{"id": "sess-2", "external_id": "ext-2", "message_count": 3}],
        "next_cursor": "cursor-abc",
        "has_more": True,
    }

    result = await mcp_client.call_tool("list_sessions", {"project_id": PROJECT_ID})

    text = result.content[0].text
    assert "Found 1 session(s):" in text
    assert 'Use cursor="cursor-abc" for the next page.' in text


async def test_list_sessions_no_sessions(mcp_client, mock_client) -> None:
    mock_client.sessions.list.return_value = {"data": [], "has_more": False}

    result = await mcp_client.call_tool("list_sessions", {"project_id": PROJECT_ID})

    assert result.content[0].text == "No sessions found."


async def test_list_sessions_validation(mcp_client) -> None:
    with pytest.raises(ToolError, match="project_id is required."):
        await mcp_client.call_tool("list_sessions", {"project_id": ""})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("list_sessions", {"project_id": PROJECT_ID, "limit": 0})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("list_sessions", {"project_id": PROJECT_ID, "limit": 201})
