"""Tests for the graph tool: get_user_graph.

Edges are mocked as RAW DICTS — matching the real SDK contract where
``graph.edges()`` yields unwrapped dicts (``nodes()`` wraps GraphNode, but
``edges()`` does not).  Mocking GraphEdge objects here would certify a
crash path green.
"""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from tests.conftest import async_iter, make_edge_dict, make_node

PROJECT_ID = "proj-123"


async def test_get_user_graph_success(mcp_client, mock_client) -> None:
    alice = make_node(name="Alice", type_="Person")
    bob = make_node(name="Bob", type_="Person")
    mock_client.graph.nodes.side_effect = lambda **kw: async_iter([alice, bob])
    # One dict edge per entity source; a fresh iterator per call
    # (asyncio.gather awaits edges once per entity — a shared iterator
    # would be consumed).
    mock_client.graph.edges.side_effect = lambda **kw: async_iter(
        [make_edge_dict(source_id=alice.id, target_id=bob.id, type_="knows")]
    )

    result = await mcp_client.call_tool("get_user_graph", {"project_id": PROJECT_ID})

    mock_client.graph.nodes.assert_awaited_once_with(entity_type=None, limit=50)
    assert mock_client.graph.edges.await_count == 2  # one per entity
    text = result.content[0].text
    assert "Found 2 entity(ies):" in text
    assert "[Person] Alice" in text
    assert "[Person] Bob" in text
    assert "1 edge(s)" in text
    assert "[knows]" in text


async def test_get_user_graph_no_entities(mcp_client, mock_client) -> None:
    mock_client.graph.nodes.side_effect = lambda **kw: async_iter([])

    result = await mcp_client.call_tool("get_user_graph", {"project_id": PROJECT_ID})

    assert result.content[0].text == "No entities found in the graph."
    # Edge fetching must not be attempted when there are no entities.
    mock_client.graph.edges.assert_not_called()


async def test_get_user_graph_validation(mcp_client) -> None:
    with pytest.raises(ToolError, match="project_id is required."):
        await mcp_client.call_tool("get_user_graph", {"project_id": ""})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("get_user_graph", {"project_id": PROJECT_ID, "limit": 0})

    with pytest.raises(ToolError, match="limit must be between 1 and 200."):
        await mcp_client.call_tool("get_user_graph", {"project_id": PROJECT_ID, "limit": 201})


async def test_get_user_graph_with_entity_type(mcp_client, mock_client) -> None:
    node = make_node(name="OpenZync Inc", type_="Organization")
    mock_client.graph.nodes.side_effect = lambda **kw: async_iter([node])
    mock_client.graph.edges.side_effect = lambda **kw: async_iter([])

    result = await mcp_client.call_tool(
        "get_user_graph", {"project_id": PROJECT_ID, "entity_type": "Organization"}
    )

    mock_client.graph.nodes.assert_awaited_once_with(entity_type="Organization", limit=50)
    assert "No relationships found" in result.content[0].text


async def test_get_user_graph_partial_edge_failure(mcp_client, mock_client) -> None:
    """One failing entity source must not lose the other entities' edges."""
    alice = make_node(name="Alice", type_="Person")
    bob = make_node(name="Bob", type_="Person")
    mock_client.graph.nodes.side_effect = lambda **kw: async_iter([alice, bob])

    def edges_side_effect(subject_id=None, **kw):
        if subject_id == bob.id:
            raise RuntimeError("edge fetch failed")
        return async_iter([make_edge_dict(source_id=alice.id, target_id=bob.id, type_="knows")])

    mock_client.graph.edges.side_effect = edges_side_effect

    result = await mcp_client.call_tool("get_user_graph", {"project_id": PROJECT_ID})

    text = result.content[0].text
    assert "Found 2 entity(ies):" in text
    assert "[Person] Alice" in text
    assert "1 edge(s) (from 2 entity sources, 1 skipped due to error)" in text
