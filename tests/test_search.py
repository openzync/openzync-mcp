"""Tests for the search tool: global_search."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.search import GlobalSearchItem, GlobalSearchResponse


async def test_global_search_success(mcp_client, mock_client) -> None:
    mock_client.search.global_search.return_value = GlobalSearchResponse(
        results=[
            GlobalSearchItem(
                type="project",
                id="proj-uuid-1",
                label="Acme Project",
                subtitle="2 members",
                href="/projects/proj-uuid-1",
            ),
            GlobalSearchItem(
                type="session",
                id="sess-uuid-1",
                label="Support chat",
                subtitle=None,
                href="/sessions/sess-uuid-1",
            ),
        ],
        query="acme",
    )

    result = await mcp_client.call_tool("global_search", {"query": "acme", "limit": 5})

    mock_client.search.global_search.assert_awaited_once_with(query="acme", limit=5)
    text = result.content[0].text
    assert "Found 2 result(s):" in text
    assert "[project] Acme Project — 2 members" in text
    assert "[session] Support chat" in text  # no subtitle → no dash


async def test_global_search_no_results(mcp_client, mock_client) -> None:
    mock_client.search.global_search.return_value = GlobalSearchResponse(results=[], query="x")

    result = await mcp_client.call_tool("global_search", {"query": "nothing"})

    assert result.content[0].text == "No results found."


async def test_global_search_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="query must be a non-empty string."):
        await mcp_client.call_tool("global_search", {"query": ""})

    with pytest.raises(ToolError, match="limit must be between 1 and 50."):
        await mcp_client.call_tool("global_search", {"query": "ml", "limit": 0})

    with pytest.raises(ToolError, match="limit must be between 1 and 50."):
        await mcp_client.call_tool("global_search", {"query": "ml", "limit": 51})

    mock_client.search.global_search.assert_not_called()
