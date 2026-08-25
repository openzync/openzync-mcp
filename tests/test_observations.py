"""Tests for the observations tool: list_observations."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from openzync.models.observation import ObservationListResponse, ObservationResponse


def make_observation(**overrides) -> ObservationResponse:
    defaults = {
        "id": "obs-1",
        "subject_entity_id": "ent-1",
        "observation_type": "co_occurrence",
        "content": "Alice and Bob frequently co-occur.",
        "confidence": 0.8,
        "created_at": "2026-01-01T00:00:00Z",
    }
    return ObservationResponse(**(defaults | overrides))


async def test_list_observations_success(mcp_client, mock_client) -> None:
    mock_client.observations.list.return_value = ObservationListResponse(
        data=[
            make_observation(),
            make_observation(
                id="obs-2",
                subject_entity_id="ent-2",
                subject_entity_name="Alice",
                related_entity_id="ent-3",
                related_entity_name="Bob",
                observation_type="temporal_pattern",
            ),
        ],
        total=2,
    )

    result = await mcp_client.call_tool("list_observations", {"limit": 10})

    mock_client.observations.list.assert_awaited_once_with(
        subject_entity_id=None, observation_type=None, limit=10
    )
    text = result.content[0].text
    assert "Found 2 observation(s):" in text
    # Unresolved names fall back to truncated entity IDs.
    assert "[co_occurrence] ent-1" in text
    # Resolved names are preferred over IDs.
    assert "[temporal_pattern] Alice ↔ Bob (0.80)" in text


async def test_list_observations_no_results(mcp_client, mock_client) -> None:
    mock_client.observations.list.return_value = ObservationListResponse(data=[], total=0)

    result = await mcp_client.call_tool("list_observations", {})

    assert result.content[0].text == "No observations found."


async def test_list_observations_filters_passthrough(mcp_client, mock_client) -> None:
    mock_client.observations.list.return_value = ObservationListResponse(data=[], total=0)

    await mcp_client.call_tool(
        "list_observations",
        {
            "subject_entity_id": "ent-9",
            "observation_type": "behavioral_pattern",
        },
    )

    mock_client.observations.list.assert_awaited_once_with(
        subject_entity_id="ent-9", observation_type="behavioral_pattern", limit=50
    )


async def test_list_observations_validation(mcp_client, mock_client) -> None:
    with pytest.raises(ToolError, match="Invalid observation_type: bogus"):
        await mcp_client.call_tool("list_observations", {"observation_type": "bogus"})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("list_observations", {"limit": 201})

    mock_client.observations.list.assert_not_called()
