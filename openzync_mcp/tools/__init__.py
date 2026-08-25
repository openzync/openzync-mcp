"""Tool handler modules for the OpenZync FastMCP server.

Each module registers one or more tools via ``@mcp.tool`` using the
server instance from ``openzync_mcp.server``.
"""

from openzync_mcp.tools import (
    classifications,
    extractions,
    facts,
    graph,
    memory,
    observations,
    projects,
    search,
    sessions,
    users,
)

__all__ = [
    "memory",
    "facts",
    "graph",
    "users",
    "sessions",
    "search",
    "observations",
    "classifications",
    "extractions",
    "projects",
]
