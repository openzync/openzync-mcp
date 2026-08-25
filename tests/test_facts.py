"""Tests for the fact tools: add_fact, list_facts, get_fact_history, retract_fact."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.facts import (
    FactBatchResponse,
    FactHistoryEvent,
    FactHistoryResponse,
    FactResponse,
    PaginatedFactsResponse,
)


def make_fact(**overrides) -> FactResponse:
    """Factory helper returning a FactResponse with a stable shape."""
    defaults = {
        "id": "fact-1",
        "content": "Alice works at OpenZync",
        "confidence": 0.9,
        "created_at": "2026-01-01T00:00:00Z",
    }
    return FactResponse(**(defaults | overrides))


async def test_add_fact_success(mcp_client, mock_client) -> None:
    mock_client.facts.add.return_value = FactBatchResponse(job_id="fact-job-7", accepted_count=3)

    result = await mcp_client.call_tool(
        "add_fact",
        {
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
            {"facts": [], "session_id": "session-1"},
        )

    # Over the 500-fact cap.
    too_many = [{"subject": "s", "predicate": "p", "object": "o"}] * 501
    with pytest.raises(ToolError, match="Maximum 500 facts per call."):
        await mcp_client.call_tool(
            "add_fact",
            {"facts": too_many, "session_id": "session-1"},
        )

    # Missing required keys (message lists them sorted: object, predicate).
    with pytest.raises(ToolError, match="missing required key") as exc_info:
        await mcp_client.call_tool(
            "add_fact",
            {
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
            {"facts": ["nope"], "session_id": "session-1"},
        )


async def test_list_facts_success(mcp_client, mock_client) -> None:
    mock_client.facts.list.return_value = PaginatedFactsResponse(
        data=[make_fact(), make_fact(id="fact-2", content="Bob likes Rust", confidence=0.5)],
        has_more=False,
    )

    result = await mcp_client.call_tool("list_facts", {"limit": 10})

    mock_client.facts.list.assert_awaited_once_with(as_of=None, limit=10)
    text = result.content[0].text
    assert "Found 2 fact(s):" in text
    assert "[0.90] Alice works at OpenZync" in text
    assert "[0.50] Bob likes Rust" in text


async def test_list_facts_as_of_passthrough(mcp_client, mock_client) -> None:
    mock_client.facts.list.return_value = PaginatedFactsResponse(data=[], has_more=False)

    await mcp_client.call_tool("list_facts", {"as_of": "2026-01-01T00:00:00Z"})

    mock_client.facts.list.assert_awaited_once_with(as_of="2026-01-01T00:00:00Z", limit=50)


async def test_list_facts_pagination_hint(mcp_client, mock_client) -> None:
    mock_client.facts.list.return_value = PaginatedFactsResponse(
        data=[make_fact()],
        next_cursor="50",
        has_more=True,
    )

    result = await mcp_client.call_tool("list_facts", {})

    assert "Use offset=50 for the next page." in result.content[0].text


async def test_list_facts_no_results(mcp_client, mock_client) -> None:
    mock_client.facts.list.return_value = PaginatedFactsResponse(data=[], has_more=False)

    result = await mcp_client.call_tool("list_facts", {})

    assert result.content[0].text == "No facts found."


async def test_list_facts_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("list_facts", {"limit": 0})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("list_facts", {"limit": 201})

    mock_client.facts.list.assert_not_called()


async def test_get_fact_history_success(mcp_client, mock_client) -> None:
    mock_client.facts.history.return_value = FactHistoryResponse(
        fact=make_fact(invalid_at="2026-02-01T00:00:00Z"),
        events=[
            FactHistoryEvent(
                id="ev-1",
                old_fact_id="fact-1",
                kind="retracted",
                reason="outdated",
                at_time="2026-02-01T00:00:00Z",
            ),
        ],
    )

    result = await mcp_client.call_tool("get_fact_history", {"fact_id": "fact-1"})

    mock_client.facts.history.assert_awaited_once_with("fact-1")
    text = result.content[0].text
    assert "Alice works at OpenZync" in text
    assert "[retracted] at 2026-02-01T00:00:00Z — outdated" in text


async def test_get_fact_history_no_events(mcp_client, mock_client) -> None:
    mock_client.facts.history.return_value = FactHistoryResponse(fact=make_fact(), events=[])

    result = await mcp_client.call_tool("get_fact_history", {"fact_id": "fact-1"})

    assert "No invalidation events" in result.content[0].text


async def test_get_fact_history_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="fact_id must be a non-empty string."):
        await mcp_client.call_tool("get_fact_history", {"fact_id": ""})

    mock_client.facts.history.assert_not_called()


async def test_retract_fact_success(mcp_client, mock_client) -> None:
    mock_client.facts.retract.return_value = make_fact(invalid_at="2026-02-01T00:00:00Z")

    result = await mcp_client.call_tool(
        "retract_fact", {"fact_id": "fact-1", "reason": "wrong info"}
    )

    mock_client.facts.retract.assert_awaited_once_with("fact-1", reason="wrong info")
    text = result.content[0].text
    assert "Fact retracted." in text
    assert "Invalid at: 2026-02-01T00:00:00Z" in text


async def test_retract_fact_already_closed(mcp_client, mock_client) -> None:
    # Idempotent no-op — backend returns the unchanged fact with null invalid_at.
    mock_client.facts.retract.return_value = make_fact()

    result = await mcp_client.call_tool("retract_fact", {"fact_id": "fact-1"})

    mock_client.facts.retract.assert_awaited_once_with("fact-1", reason=None)
    assert "already closed" in result.content[0].text


async def test_retract_fact_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="fact_id must be a non-empty string."):
        await mcp_client.call_tool("retract_fact", {"fact_id": ""})

    mock_client.facts.retract.assert_not_called()
