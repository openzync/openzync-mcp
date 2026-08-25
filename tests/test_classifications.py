"""Tests for the classification tools: list_classifications, get_classification."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.classification import ClassificationListResponse, ClassificationResponse


def make_classification(**overrides) -> ClassificationResponse:
    defaults = {
        "id": "cls-1",
        "episode_id": "ep-1",
        "intent": "question",
        "emotion": "curiosity",
        "valence": "positive",
        "arousal": "low",
        "confidence": 0.95,
        "created_at": "2026-01-01T00:00:00Z",
    }
    return ClassificationResponse(**(defaults | overrides))


async def test_list_classifications_success(mcp_client, mock_client) -> None:
    mock_client.classifications.list.return_value = ClassificationListResponse(
        data=[make_classification()],
        total=1,
    )

    result = await mcp_client.call_tool("list_classifications", {"session_id": "sess-uuid-1"})

    mock_client.classifications.list.assert_awaited_once_with("sess-uuid-1")
    text = result.content[0].text
    assert "Found 1 classification(s):" in text
    assert "intent=question emotion=curiosity valence=positive (0.95)" in text


async def test_list_classifications_empty(mcp_client, mock_client) -> None:
    mock_client.classifications.list.return_value = ClassificationListResponse(data=[], total=0)

    result = await mcp_client.call_tool("list_classifications", {"session_id": "sess-uuid-1"})

    assert result.content[0].text == "No classifications found for this session."


async def test_list_classifications_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="session_id must be a non-empty string."):
        await mcp_client.call_tool("list_classifications", {"session_id": ""})

    mock_client.classifications.list.assert_not_called()


async def test_get_classification_success(mcp_client, mock_client) -> None:
    mock_client.classifications.get_by_episode.return_value = make_classification()

    result = await mcp_client.call_tool(
        "get_classification", {"session_id": "sess-uuid-1", "episode_id": "ep-1"}
    )

    mock_client.classifications.get_by_episode.assert_awaited_once_with("sess-uuid-1", "ep-1")
    text = result.content[0].text
    assert "Classification for episode ep-1:" in text
    assert "Intent: question" in text
    assert "Arousal: low" in text
    assert "Confidence: 0.95" in text


async def test_get_classification_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="session_id must be a non-empty string."):
        await mcp_client.call_tool("get_classification", {"session_id": "", "episode_id": "e"})

    with pytest.raises(ToolError, match="episode_id must be a non-empty string."):
        await mcp_client.call_tool("get_classification", {"session_id": "s", "episode_id": ""})

    mock_client.classifications.get_by_episode.assert_not_called()
