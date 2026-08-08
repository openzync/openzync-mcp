"""SDK-failure propagation — every tool must surface backend errors loudly.

Per the fallback-discipline rule: no silent degradation.  A failing SDK
call must propagate as a ToolError (FastMCP wraps the raised exception),
never a masked success.
"""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

# (tool name, call args, mock path to fail)
TOOL_FAILURES = [
    (
        "add_memory",
        {
            "project_id": "p",
            "messages": [{"role": "user", "content": "hi"}],
            "session_id": "s",
        },
        "memory.ingest",
    ),
    ("get_context", {"project_id": "p", "query": "ml"}, "memory.get_context"),
    ("search_memory", {"project_id": "p", "query": "ml"}, "graph.search"),
    ("delete_memory", {"project_id": "p"}, "memory.delete"),
    ("get_user_graph", {"project_id": "p"}, "graph.nodes"),
    (
        "add_fact",
        {
            "project_id": "p",
            "facts": [{"subject": "a", "predicate": "p", "object": "b"}],
            "session_id": "s",
        },
        "facts.add",
    ),
    ("list_facts", {"project_id": "p", "query": "ml"}, "graph.search"),
    ("list_sessions", {"project_id": "p"}, "sessions.list"),
    ("create_user", {"external_id": "ext-1"}, "users.create"),
]


@pytest.mark.parametrize(("tool", "args", "mock_path"), TOOL_FAILURES)
async def test_sdk_failure_propagates(mcp_client, mock_client, tool, args, mock_path) -> None:
    """A failing SDK call must raise ToolError, never a silent fallback."""
    target = mock_client
    for part in mock_path.split("."):
        target = getattr(target, part)
    target.side_effect = RuntimeError("backend down")

    with pytest.raises(ToolError, match="backend down"):
        await mcp_client.call_tool(tool, args)

    target.assert_awaited()
