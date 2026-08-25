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
            "messages": [{"role": "user", "content": "hi"}],
            "session_id": "s",
        },
        "memory.ingest",
    ),
    ("get_context", {"query": "ml"}, "memory.get_context"),
    ("search_memory", {"query": "ml"}, "graph.search"),
    ("delete_memory", {}, "memory.delete"),
    ("get_user_graph", {}, "graph.nodes"),
    (
        "add_fact",
        {
            "facts": [{"subject": "a", "predicate": "p", "object": "b"}],
            "session_id": "s",
        },
        "facts.add",
    ),
    ("list_facts", {}, "facts.list"),
    ("list_sessions", {}, "sessions.list"),
    ("create_user", {"external_id": "ext-1"}, "users.create"),
    ("get_fact_history", {"fact_id": "f1"}, "facts.history"),
    ("retract_fact", {"fact_id": "f1"}, "facts.retract"),
    ("get_session_facts", {"session_id": "s1"}, "sessions.facts"),
    ("get_session_messages", {"session_id": "s1"}, "sessions.messages"),
    ("global_search", {"query": "ml"}, "search.global_search"),
    ("list_observations", {}, "observations.list"),
    ("list_classifications", {"session_id": "s1"}, "classifications.list"),
    (
        "get_classification",
        {"session_id": "s1", "episode_id": "e1"},
        "classifications.get_by_episode",
    ),
    (
        "list_structured_extractions",
        {"session_id": "s1"},
        "structured_extractions.list",
    ),
    (
        "get_structured_extraction",
        {"session_id": "s1", "episode_id": "e1"},
        "structured_extractions.get_by_episode",
    ),
    ("update_project_member", {"user_id": "u1"}, "projects.update_member"),
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
