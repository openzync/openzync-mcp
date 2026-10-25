"""User-dictated MCP tool tests.

Covers:
    - ``get_user_graph`` with ``limit`` on a large fixture returns at
      most ``limit`` entities.
    - ``search_memory`` with null scores renders without ``TypeError``.

Follows the repo's existing tool-test conventions (in-process FastMCP
client with the SDK replaced by the shared ``mock_client`` fake).
"""

from __future__ import annotations

from tests.conftest import async_iter, make_edge_dict, make_node


async def test_get_user_graph_limit_on_large_fixture(
    mcp_client, mock_client
) -> None:
    """150-entity graph with ``limit=50`` → at most 50 entities rendered."""
    nodes = [make_node(name=f"Entity-{i:03d}") for i in range(150)]
    mock_client.graph.nodes.side_effect = lambda **kw: async_iter(nodes)
    mock_client.graph.edges.side_effect = lambda **kw: async_iter([])

    result = await mcp_client.call_tool("get_user_graph", {"limit": 50})

    mock_client.graph.nodes.assert_awaited_once_with(
        entity_type=None, limit=50
    )
    text = result.content[0].text
    assert "Found 50 entity(ies):" in text
    assert text.count("[Person]") <= 50


async def test_search_memory_null_scores_render(mcp_client, mock_client) -> None:
    """Null ``rrf_score``/``score`` render as 0.0 instead of TypeError."""
    mock_client.graph.search.return_value = [
        {"content": "alpha memory", "rrf_score": None, "score": None},
        {"content": "beta memory"},
    ]

    result = await mcp_client.call_tool(
        "search_memory", {"query": "memory", "limit": 5}
    )

    mock_client.graph.search.assert_awaited_once_with(
        query="memory", types="episodes,facts", limit=5
    )
    text = result.content[0].text
    assert "Found 2 result(s):" in text
    assert "[0.0000] alpha memory" in text
    assert "[0.0000] beta memory" in text
