"""Tests for the user tool: create_user."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastmcp.exceptions import ToolError


async def test_create_user_success(mcp_client, mock_client) -> None:
    mock_client.users.create.return_value = SimpleNamespace(
        id="user-1", external_id="customer-abc", name="Alice"
    )

    result = await mcp_client.call_tool(
        "create_user", {"external_id": "customer-abc", "name": "Alice"}
    )

    mock_client.users.create.assert_awaited_once_with(external_id="customer-abc", name="Alice")
    text = result.content[0].text
    assert "User created successfully." in text
    assert "ID: user-1" in text
    assert "External ID: customer-abc" in text
    assert "Name: Alice" in text


async def test_create_user_without_name(mcp_client, mock_client) -> None:
    mock_client.users.create.return_value = SimpleNamespace(
        id="user-2", external_id="customer-xyz", name=None
    )

    result = await mcp_client.call_tool("create_user", {"external_id": "customer-xyz"})

    mock_client.users.create.assert_awaited_once_with(external_id="customer-xyz", name=None)
    assert "External ID: customer-xyz" in result.content[0].text


async def test_create_user_validation(mcp_client) -> None:
    with pytest.raises(ToolError, match="external_id must be a non-empty string."):
        await mcp_client.call_tool("create_user", {"external_id": ""})

    with pytest.raises(ToolError, match="external_id must be a non-empty string."):
        await mcp_client.call_tool("create_user", {"external_id": "   "})
