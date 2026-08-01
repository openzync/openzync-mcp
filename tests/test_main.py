"""Tests for the __main__ entry point (arg parsing + transport dispatch)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import openzync_mcp.__main__ as entry
import openzync_mcp.server as server


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch) -> None:
    """Keep OPENZYN_API_KEY/BASE_URL from leaking between tests."""
    monkeypatch.delenv("OPENZYN_API_KEY", raising=False)
    monkeypatch.delenv("OPENZYN_BASE_URL", raising=False)


def _patch_run(monkeypatch) -> MagicMock:
    # FastMCP.run() is a sync blocking method — MagicMock, not AsyncMock.
    fake_run = MagicMock()
    monkeypatch.setattr(server.mcp, "run", fake_run)
    return fake_run


def test_missing_api_key_exits(monkeypatch, caplog) -> None:
    monkeypatch.setattr("sys.argv", ["openzync_mcp"])

    with pytest.raises(SystemExit) as exc_info:
        entry.main()

    assert exc_info.value.code == 1
    assert "API key is required" in caplog.text


def test_run_stdio_dispatch(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["openzync_mcp", "--transport", "stdio"])
    monkeypatch.setenv("OPENZYN_API_KEY", "test-key")
    fake_run = _patch_run(monkeypatch)

    entry.main()

    fake_run.assert_called_once_with()


def test_run_http_dispatch(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["openzync_mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8200"],
    )
    monkeypatch.setenv("OPENZYN_API_KEY", "test-key")
    fake_run = _patch_run(monkeypatch)

    entry.main()

    fake_run.assert_called_once_with(transport="http", host="0.0.0.0", port=8200)


def test_api_key_from_flag(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv", ["openzync_mcp", "--transport", "stdio", "--api-key", "flag-key"]
    )
    fake_run = _patch_run(monkeypatch)

    entry.main()

    fake_run.assert_called_once()
    # main() must propagate the flag value into the env the lifespan reads.
    import os

    assert os.environ["OPENZYN_API_KEY"] == "flag-key"
