# OpenZync MCP Server

**Model Context Protocol server for the OpenZync agent memory platform.**

<p align="center">
  <img src="https://img.shields.io/badge/python-%3E%3D3.11-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="Apache 2.0">
  <img src="https://img.shields.io/badge/protocol-MCP-blueviolet" alt="MCP">
</p>

Expose [OpenZync](https://github.com/openzync/openzync-core) agent memory tools to any MCP-compatible LLM client — Claude Desktop, Cursor, VS Code Copilot, and more.

Built with [FastMCP](https://gofastmcp.com), which handles protocol compliance, transport negotiation (stdio/SSE/HTTP), schema generation, and input validation.

```mermaid
flowchart LR
    C1[Claude Desktop] --> M
    C2[Cursor] --> M
    C3[VS Code Copilot] --> M
    M[MCP Server (FastMCP, stdio/SSE/HTTP)] --> API[OpenZync Core API]
    API --> K1[memory.ingest]
    API --> K2[graph.search]
    API --> K3[facts.add]
    API --> K4[sessions.*]
```

## Tools

| Tool | Description |
|---|---|
| `memory.ingest` | Ingest conversation messages (episodes) into agent memory |
| `memory.get_context` | Retrieve relevant context for LLM prompts |
| `graph.search` | Hybrid search across episodes, facts, and entities |
| `graph.nodes` | List knowledge graph entities |
| `graph.edges` | List knowledge graph relationships |
| `graph.communities` | List community clusters |
| `graph.node_detail` | Get details of a specific graph node |
| `graph.delete_node` | Delete a graph node |
| `facts.add` | Add structured facts to agent memory |
| `sessions.create` | Create a new conversation session |
| `sessions.messages` | Retrieve session messages |
| `sessions.delete` | Delete a session |
| `users.create` | Create a user by external ID |
| `users.get` | Get user details |
| `users.update` | Update user metadata |
| `users.delete` | Delete a user |
| `users.list` | List users (paginated) |

## Quick Start

### Prerequisites

- Python 3.11+
- An OpenZync API key from a running [openzync-core](https://github.com/openzync/openzync-core) instance
- An MCP-compatible client (Claude Desktop, Cursor, etc.)

### Running

```bash
# Install
pip install openzync-mcp

# Environment variables
export OPENZYN_API_KEY="oz_live_your_api_key_here"
export OPENZYN_BASE_URL="http://localhost:8000"  # or your OpenZync deployment

# Start the server
python -m openzync_mcp --transport stdio
```

### Docker

```bash
# Pull — public since 2026-08-31, no login needed
docker pull ghcr.io/openzync/openzync-mcp:latest
docker run -e OPENZYN_API_KEY=... -e OPENZYN_BASE_URL=... ghcr.io/openzync/openzync-mcp:latest

# Or build locally
docker build -t openzync-mcp .
docker run -e OPENZYN_API_KEY=... -e OPENZYN_BASE_URL=... openzync-mcp
```

### Configuring with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "openzync": {
      "command": "python",
      "args": ["-m", "openzync_mcp", "--transport", "stdio"],
      "env": {
        "OPENZYN_API_KEY": "oz_live_your_api_key_here",
        "OPENZYN_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Architecture

```
Claude Desktop / MCP Client
    │
    ▼
FastMCP Server (stdio/SSE/HTTP)
    │
    ▼
OpenZync Python SDK (AsyncOpenZync)
    │
    ▼
openzync-core API (:8000)
```

The MCP server uses the OpenZync Python SDK under the hood. The SDK client lifecycle is managed via a FastMCP lifespan context — created on server startup, closed on shutdown.

## Development

```bash
# Install in editable mode
pip install -e .

# Run tests
pytest
```

## Related

- [openzync-sdk-python](https://github.com/openzync/openzync-sdk-python) — the SDK this server uses
- [FastMCP](https://gofastmcp.com) — the MCP framework powering this server

## License

Apache 2.0 — see [LICENSE](./LICENSE).
