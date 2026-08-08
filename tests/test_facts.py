"""Tests for the fact tools: add_fact, list_facts."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.facts import FactBatchResponse

PROJECT_ID = "proj-123"


async def test_add_fact_success(mcp_client, mock_client) -> None:
    mock_client.facts.add.return_value = FactBatchResponse(job_id="fact-job-7", accepted_count=3)

    result = await mcp_client.call_tool(
        "add_fact",
        {
            "project_id": PROJECT_ID,
            "facts": [{"subject": "Alice", "predicate": "works_at", "object": "OpenZync"}],
            "session_id": "session-1",
        },
    )

    mock_client.facts.add.assert_awaited_once_with(
        facts=[{"subject": "Alice", "predicate": "works_at", "object": "OpenZync"}],
        session_id="session-1",
    )
    text = result.content[0].text
    assert "3 fact(s) accepted" in text
    assert "fact-job-7" in text


async def test_add_fact_validation(mcp_client) -> None:
    # Empty facts list.
    with pytest.raises(ToolError, match="At least one fact is required."):
        await mcp_client.call_tool(
            "add_fact",
            {"project_id": PROJECT_ID, "facts": [], "session_id": "session-1"},
        )

    # Over the 500-fact cap.
    too_many = [{"subject": "s", "predicate": "p", "object": "o"}] * 501
    with pytest.raises(ToolError, match="Maximum 500 facts per call."):
        await mcp_client.call_tool(
            "add_fact",
            {"project_id": PROJECT_ID, "facts": too_many, "session_id": "session-1"},
        )

    # Missing required keys (message lists them sorted: object, predicate).
    with pytest.raises(ToolError, match="missing required key") as exc_info:
        await mcp_client.call_tool(
            "add_fact",
            {
                "project_id": PROJECT_ID,
                "facts": [{"subject": "Alice"}],
                "session_id": "session-1",
            },
        )
    assert "object" in str(exc_info.value)
    assert "predicate" in str(exc_info.value)

    # Non-dict entry — rejected by FastMCP's list[dict] schema validation
    # at the boundary, before the tool fn runs (its isinstance guard is
    # defensive dead code).
    with pytest.raises(ToolError, match="Input should be a valid dictionary"):
        await mcp_client.call_tool(
            "add_fact",
            {"project_id": PROJECT_ID, "facts": ["nope"], "session_id": "session-1"},
        )


async def test_list_facts_success(mcp_client, mock_client) -> None:
    mock_client.graph.search.return_value = [
        {"content": "Alice works at OpenZync", "confidence": 0.9},
    ]

    result = await mcp_client.call_tool(
        "list_facts", {"project_id": PROJECT_ID, "query": "Alice", "limit": 10}
    )

    mock_client.graph.search.assert_awaited_once_with(query="Alice", types="facts", limit=10)
    text = result.content[0].text
    assert "Found 1 fact(s):" in text
    assert "[0.90] Alice works at OpenZync" in text


async def test_list_facts_no_results(mcp_client, mock_client) -> None:
    mock_client.graph.search.return_value = []

    result = await mcp_client.call_tool(
        "list_facts", {"project_id": PROJECT_ID, "query": "nonexistent"}
    )

    mock_client.graph.search.assert_awaited_once_with(query="nonexistent", types="facts", limit=20)
    assert result.content[0].text == "No facts found."


async def test_list_facts_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="query must be a non-empty string."):
        await mcp_client.call_tool("list_facts", {"project_id": PROJECT_ID, "query": ""})

    with pytest.raises(ToolError, match="limit must be between 1 and 100."):
        await mcp_client.call_tool(
            "list_facts", {"project_id": PROJECT_ID, "query": "ml", "limit": 0}
        )

    with pytest.raises(ToolError, match="limit must be between 1 and 100."):
        await mcp_client.call_tool(
            "list_facts", {"project_id": PROJECT_ID, "query": "ml", "limit": 101}
        )

    mock_client.graph.search.assert_not_called()
