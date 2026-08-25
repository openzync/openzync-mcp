"""Tests for the structured extraction tools."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.extraction import (
    StructuredExtractionListResponse,
    StructuredExtractionResponse,
)


def make_extraction(**overrides) -> StructuredExtractionResponse:
    defaults = {
        "id": "ext-1",
        "session_id": "sess-uuid-1",
        "episode_id": "ep-1",
        "schema_id": None,
        "data": {"topic": "pricing", "sentiment": "positive"},
        "created_at": "2026-01-01T00:00:00Z",
    }
    return StructuredExtractionResponse(**(defaults | overrides))


async def test_list_structured_extractions_success(mcp_client, mock_client) -> None:
    mock_client.structured_extractions.list.return_value = StructuredExtractionListResponse(
        items=[make_extraction()], total=1
    )

    result = await mcp_client.call_tool(
        "list_structured_extractions", {"session_id": "sess-uuid-1"}
    )

    mock_client.structured_extractions.list.assert_awaited_once_with("sess-uuid-1")
    text = result.content[0].text
    assert "Found 1 extraction(s):" in text
    assert '"topic": "pricing"' in text


async def test_list_structured_extractions_empty(mcp_client, mock_client) -> None:
    mock_client.structured_extractions.list.return_value = StructuredExtractionListResponse(
        items=[], total=0
    )

    result = await mcp_client.call_tool(
        "list_structured_extractions", {"session_id": "sess-uuid-1"}
    )

    assert result.content[0].text == "No structured extractions found for this session."


async def test_list_structured_extractions_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="session_id must be a non-empty string."):
        await mcp_client.call_tool("list_structured_extractions", {"session_id": ""})

    mock_client.structured_extractions.list.assert_not_called()


async def test_get_structured_extraction_success(mcp_client, mock_client) -> None:
    mock_client.structured_extractions.get_by_episode.return_value = make_extraction()

    result = await mcp_client.call_tool(
        "get_structured_extraction", {"session_id": "sess-uuid-1", "episode_id": "ep-1"}
    )

    mock_client.structured_extractions.get_by_episode.assert_awaited_once_with(
        "sess-uuid-1", "ep-1"
    )
    text = result.content[0].text
    assert "Structured extraction for episode ep-1:" in text
    assert "Schema: —" in text
    assert '"sentiment": "positive"' in text


async def test_get_structured_extraction_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="session_id must be a non-empty string."):
        await mcp_client.call_tool(
            "get_structured_extraction", {"session_id": "", "episode_id": "e"}
        )

    with pytest.raises(ToolError, match="episode_id must be a non-empty string."):
        await mcp_client.call_tool(
            "get_structured_extraction", {"session_id": "s", "episode_id": ""}
        )

    mock_client.structured_extractions.get_by_episode.assert_not_called()
