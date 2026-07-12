"""OpenZync FastMCP Server — exposes memory capabilities as LLM-accessible tools.

Powered by FastMCP (https://gofastmcp.com), the standard framework for
building MCP applications.  Handles JSON-RPC protocol, schema generation,
input validation, and transport negotiation automatically.

Usage:
    python -m openzync_mcp --transport stdio
    python -m openzync_mcp --transport http --port 8100
"""

from openzync_mcp.server import mcp

__all__ = ["mcp"]
