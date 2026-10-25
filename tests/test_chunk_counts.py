"""MCP chunk counts — search_memory renders one line per result (no I/O)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from openzync_mcp.tools.memory import search_memory


def _ctx_with_results(results: list[dict]) -> MagicMock:
    client = MagicMock()
    client.graph.search = AsyncMock(return_value=results)
    ctx = MagicMock()
    from openzync_mcp.tools import memory as mem_mod
    import unittest.mock as mock

    ctx._client = client
    return ctx, mem_mod, mock, client


@pytest.mark.unit
class TestMCPChunkCounts:
    @pytest.mark.asyncio
    async def test_line_count_matches_results(self) -> None:
        import unittest.mock as mock

        results = [
            {"content": f"chunk-{i} " + "x" * 500, "rrf_score": 0.9 - i * 0.1}
            for i in range(5)
        ]
        client = MagicMock()
        client.graph.search = AsyncMock(return_value=results)
        ctx = MagicMock()
        with mock.patch(
            "openzync_mcp.tools.memory.get_client", return_value=client
        ):
            out = await search_memory(ctx, query="q", limit=20)
        lines = out.splitlines()
        # header + one line per chunk
        assert len(lines) == 1 + len(results)
        assert lines[0] == f"Found {len(results)} result(s):"
        # content truncated to 200 chars per chunk
        for line in lines[1:]:
            assert len(line) <= 4 + 8 + 200  # score prefix + content

    @pytest.mark.asyncio
    async def test_empty_results_single_line(self) -> None:
        import unittest.mock as mock

        client = MagicMock()
        client.graph.search = AsyncMock(return_value=[])
        ctx = MagicMock()
        with mock.patch(
            "openzync_mcp.tools.memory.get_client", return_value=client
        ):
            out = await search_memory(ctx, query="q")
        assert out == "No results found."
