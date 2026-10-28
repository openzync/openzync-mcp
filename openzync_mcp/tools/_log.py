"""Shared MCP tool logging — invoke/success/error lines in one place.

Replaces the copy-pasted ``time.monotonic()`` + ``logger.{info,error}``
blocks in every tool module.  Log format and logger hierarchy are
unchanged (``openzync.mcp.tools``), so existing log parsing keeps
working.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("openzync.mcp.tools")


def log_invoke(tool: str, detail: str = "", *args: object) -> float:
    """Log tool start; return the start timestamp for success/error.

    Args:
        tool: Tool name (``mcp.tool.invoke tool=<tool>``).
        detail: Extra format string appended after the tool segment.
        *args: Format args for *detail*.

    Returns:
        Monotonic start time to pass to :func:`log_success`/ :func:`log_error`.
    """
    start = time.monotonic()
    logger.info("mcp.tool.invoke tool=%s" + detail, tool, *args)
    return start


def log_success(tool: str, start: float, detail: str = "", *args: object) -> None:
    """Log successful tool completion with elapsed milliseconds.

    Args:
        tool: Tool name.
        start: Value returned by :func:`log_invoke`.
        detail: Extra format string appended after the duration segment.
        *args: Format args for *detail*.
    """
    logger.info(
        "mcp.tool.success tool=%s duration_ms=%d" + detail,
        tool,
        round((time.monotonic() - start) * 1000),
        *args,
    )


def log_error(tool: str, start: float, detail: str = "", *args: object) -> None:
    """Log tool failure with elapsed milliseconds (call, then re-raise).

    Args:
        tool: Tool name.
        start: Value returned by :func:`log_invoke`.
        detail: Extra format string appended after the duration segment.
        *args: Format args for *detail*.
    """
    logger.error(
        "mcp.tool.error tool=%s duration_ms=%d" + detail,
        tool,
        round((time.monotonic() - start) * 1000),
        *args,
        exc_info=True,
    )
