"""Tests for the memory tools: add_memory, get_context, search_memory, delete_memory."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.memory import ContextResponse, IngestMemoryResponse


async def test_add_memory_success(mcp_client, mock_client) -> None:
    mock_client.memory.ingest.return_value = IngestMemoryResponse(episode_count=2, job_id="job-42")

    result = await mcp_client.call_tool(
        "add_memory",
        {
            "messages": [{"role": "user", "content": "hello"}],
            "session_id": "session-1",
        },
    )

    mock_client.memory.ingest.assert_awaited_once_with(
        messages=[{"role": "user", "content": "hello"}], session_id="session-1"
    )
    text = result.content[0].text
    assert "2 messages ingested" in text
    assert "job-42" in text


async def test_add_memory_validation(mcp_client) -> None:
    # Empty message list.
    with pytest.raises(ToolError, match="At least one message is required."):
        await mcp_client.call_tool(
            "add_memory",
            {"messages": [], "session_id": "session-1"},
        )

    # More than the 1000-message cap.
    too_many = [{"role": "user", "content": "x"}] * 1001
    with pytest.raises(ToolError, match="Maximum 1000 messages per call."):
        await mcp_client.call_tool(
            "add_memory",
            {"messages": too_many, "session_id": "session-1"},
        )


async def test_get_context_success(mcp_client, mock_client) -> None:
    mock_client.memory.get_context.return_value = ContextResponse(context="Relevant context block")

    result = await mcp_client.call_tool("get_context", {"query": "machine learning"})

    mock_client.memory.get_context.assert_awaited_once_with(query="machine learning", limit=20)
    assert result.content[0].text == "Relevant context block"


async def test_get_context_validation(mcp_client) -> None:
    with pytest.raises(ToolError, match="query must be a non-empty string."):
        await mcp_client.call_tool("get_context", {"query": ""})

    with pytest.raises(ToolError, match="query must be a non-empty string."):
        await mcp_client.call_tool("get_context", {"query": "   "})

    with pytest.raises(ToolError, match="limit must be between 1 and 100."):
        await mcp_client.call_tool("get_context", {"query": "ml", "limit": 0})

    with pytest.raises(ToolError, match="limit must be between 1 and 100."):
        await mcp_client.call_tool("get_context", {"query": "ml", "limit": 101})


async def test_search_memory_success(mcp_client, mock_client) -> None:
    mock_client.graph.search.return_value = [
        {"content": "episode about ML", "rrf_score": 0.42},
        {"content": "fact about transformers", "score": 0.11},
    ]

    result = await mcp_client.call_tool(
        "search_memory",
        {"query": "ml", "types": "episodes,facts", "limit": 5},
    )

    mock_client.graph.search.assert_awaited_once_with(query="ml", types="episodes,facts", limit=5)
    text = result.content[0].text
    assert "Found 2 result(s):" in text
    assert "[0.4200] episode about ML" in text  # rrf_score preferred
    assert "[0.1100] fact about transformers" in text  # falls back to score


async def test_search_memory_validation(mcp_client) -> None:
    with pytest.raises(ToolError, match="Invalid type\\(s\\): bogus"):
        await mcp_client.call_tool(
            "search_memory",
            {"query": "ml", "types": "episodes,bogus"},
        )

    # Whitespace-only segments strip to "" and are rejected as invalid types.
    with pytest.raises(ToolError, match="Invalid type\\(s\\)"):
        await mcp_client.call_tool(
            "search_memory",
            {"query": "ml", "types": " , "},
        )

    with pytest.raises(ToolError, match="limit must be between 1 and 100."):
        await mcp_client.call_tool("search_memory", {"query": "ml", "limit": 0})


async def test_delete_memory_success(mcp_client, mock_client) -> None:
    result = await mcp_client.call_tool("delete_memory", {})

    mock_client.memory.delete.assert_awaited_once_with()
    assert result.content[0].text == "Memory deleted successfully."


async def test_search_memory_empty_query(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="query must be a non-empty string."):
        await mcp_client.call_tool("search_memory", {"query": ""})

    # Validation must short-circuit before touching the SDK.
    mock_client.graph.search.assert_not_called()


async def test_search_memory_no_results(mcp_client, mock_client) -> None:
    mock_client.graph.search.return_value = []

    result = await mcp_client.call_tool("search_memory", {"query": "nothing"})

    assert result.content[0].text == "No results found."
