"""Tests for the session tools: list_sessions, get_session_facts, get_session_messages."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.facts import PaginatedFactsResponse
from openzync.models.session import SessionMessagesResponse


def make_fact(**overrides):
    defaults = {
        "id": "fact-1",
        "content": "Alice works at OpenZync",
        "confidence": 0.9,
        "created_at": "2026-01-01T00:00:00Z",
    }
    from openzync.models.facts import FactResponse

    return FactResponse(**(defaults | overrides))


async def test_list_sessions_success(mcp_client, mock_client) -> None:
    mock_client.sessions.list.return_value = {
        "data": [{"id": "sess-1", "external_id": "ext-1", "message_count": 5}],
        "has_more": False,
    }

    result = await mcp_client.call_tool("list_sessions", {"limit": 10})

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

    result = await mcp_client.call_tool("list_sessions", {})

    text = result.content[0].text
    assert "Found 1 session(s):" in text
    assert 'Use cursor="cursor-abc" for the next page.' in text


async def test_list_sessions_no_sessions(mcp_client, mock_client) -> None:
    mock_client.sessions.list.return_value = {"data": [], "has_more": False}

    result = await mcp_client.call_tool("list_sessions", {})

    assert result.content[0].text == "No sessions found."


async def test_list_sessions_validation(mcp_client) -> None:
    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("list_sessions", {"limit": 0})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("list_sessions", {"limit": 201})


async def test_get_session_facts_success(mcp_client, mock_client) -> None:
    mock_client.sessions.facts.return_value = PaginatedFactsResponse(
        data=[make_fact()],
        has_more=False,
    )

    result = await mcp_client.call_tool(
        "get_session_facts", {"session_id": "sess-uuid-1", "limit": 10}
    )

    mock_client.sessions.facts.assert_awaited_once_with("sess-uuid-1", limit=10)
    text = result.content[0].text
    assert "Found 1 fact(s):" in text
    assert "[0.90] Alice works at OpenZync" in text


async def test_get_session_facts_pagination_hint(mcp_client, mock_client) -> None:
    mock_client.sessions.facts.return_value = PaginatedFactsResponse(
        data=[make_fact()],
        next_cursor="cur-9",
        has_more=True,
    )

    result = await mcp_client.call_tool("get_session_facts", {"session_id": "sess-uuid-1"})

    assert 'Use cursor="cur-9" for the next page.' in result.content[0].text


async def test_get_session_facts_no_results(mcp_client, mock_client) -> None:
    mock_client.sessions.facts.return_value = PaginatedFactsResponse(data=[], has_more=False)

    result = await mcp_client.call_tool("get_session_facts", {"session_id": "sess-uuid-1"})

    assert result.content[0].text == "No facts found for this session."


async def test_get_session_facts_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="session_id must be a non-empty string."):
        await mcp_client.call_tool("get_session_facts", {"session_id": ""})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("get_session_facts", {"session_id": "s", "limit": 201})

    mock_client.sessions.facts.assert_not_called()


async def test_get_session_messages_success(mcp_client, mock_client) -> None:
    msg = SessionMessagesResponse.MessageItem(
        id="msg-1",
        role="user",
        content="Hello\nworld",
        created_at="2026-01-01T00:00:00Z",
    )
    mock_client.sessions.messages.return_value = SessionMessagesResponse(data=[msg])

    result = await mcp_client.call_tool(
        "get_session_messages", {"session_id": "sess-uuid-1", "limit": 5}
    )

    mock_client.sessions.messages.assert_awaited_once_with("sess-uuid-1", limit=5)
    text = result.content[0].text
    assert "Found 1 message(s):" in text
    assert "[user] Hello world" in text  # newlines flattened


async def test_get_session_messages_no_results(mcp_client, mock_client) -> None:
    mock_client.sessions.messages.return_value = SessionMessagesResponse(data=[])

    result = await mcp_client.call_tool("get_session_messages", {"session_id": "sess-uuid-1"})

    assert result.content[0].text == "No messages found for this session."


async def test_get_session_messages_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="session_id must be a non-empty string."):
        await mcp_client.call_tool("get_session_messages", {"session_id": ""})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("get_session_messages", {"session_id": "s", "limit": 0})

    mock_client.sessions.messages.assert_not_called()
