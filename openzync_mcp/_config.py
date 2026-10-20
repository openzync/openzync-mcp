"""Base-URL validation for the OpenZync MCP server.

The OpenZync API key travels in an ``Authorization: Bearer`` header on
every request, so the configured base URL decides *where a production
credential is sent*.  An MCP client config is a JSON file that agents
routinely write, so an unvalidated base URL is an exfiltration
primitive: point it at a hostile host and the first tool call hands over
the key — with no error and no log line.

Both entry points (the ``--base-url`` flag and the ``OPENZYN_BASE_URL``
environment variable) go through :func:`validate_base_url`, so the CLI
and the server lifespan cannot drift apart.
"""

from __future__ import annotations

import ipaddress
import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger("openzync.mcp.config")

DEFAULT_BASE_URL = "http://localhost:8000"
"""Loopback HTTP — the local-development default."""

ALLOWED_HOSTS_ENV = "OPENZYN_MCP_ALLOWED_HOSTS"
"""Comma-separated host allowlist.  Unset means "no allowlist"."""


def _is_loopback(host: str) -> bool:
    """Return True when ``host`` refers to the local machine.

    The host is parsed as an IP address, never matched as a string prefix:
    ``127.attacker.test`` starts with ``127.`` but is a DNS name owned by
    whoever registered it, and treating it as loopback would downgrade the
    transport to cleartext HTTP and hand the bearer token to that host.

    Args:
        host: A hostname (already lowercased).  May be a DNS name, an IPv4
            literal, or an IPv6 literal with or without brackets.

    Returns:
        True for ``localhost`` (also in its fully-qualified ``localhost.``
        form) and for IP literals in a loopback range — ``127.0.0.0/8``
        and ``::1``.
    """
    # The trailing dot is the absolute form of the same DNS name (RFC 6761
    # reserves it for the loopback), and brackets are stripped by
    # urlsplit, but not by every caller.
    candidate = host.strip().lower().removeprefix("[").removesuffix("]").rstrip(".")
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        # Not an IP literal → a DNS name.  Only "localhost" itself is loopback.
        # shortcut: legacy inet_aton spellings ("127.1", "2130706433") are not
        # valid IP literals, so they fall through here and are not loopback;
        # upgrade if a user ever needs them.
        return candidate == "localhost"


def allowed_hosts() -> set[str]:
    """Read the host allowlist from ``OPENZYN_MCP_ALLOWED_HOSTS``.

    Returns:
        Lowercased hostnames; empty when the variable is unset or blank.
    """
    raw = os.environ.get(ALLOWED_HOSTS_ENV, "")
    return {host.strip().lower() for host in raw.split(",") if host.strip()}


def validate_base_url(base_url: str) -> str:
    """Validate the OpenZync API base URL.

    Rules:

    - the URL must carry an ``http``/``https`` scheme and a host;
    - when ``OPENZYN_MCP_ALLOWED_HOSTS`` is set, only the listed hosts
      are accepted — any other host is rejected outright;
    - plain ``http://`` is accepted for loopback hosts — ``localhost``,
      ``127.0.0.0/8`` and ``::1`` (the local default).  For any other
      host it requires ``https://``, unless the host is explicitly
      allowlisted — then it is allowed, but only with a loud warning,
      because the bearer token and every response travel unencrypted.

    Args:
        base_url: The configured base URL.

    Returns:
        The base URL, unchanged.

    Raises:
        ValueError: When the URL is malformed, uses an unsupported scheme,
            points at a host outside the allowlist, or uses plain HTTP
            against a non-loopback host that is not allowlisted.
    """
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"base URL must use http or https, got {parsed.scheme or 'no scheme'!r}: {base_url!r}"
        )

    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"base URL must include a host: {base_url!r}")

    allowed = allowed_hosts()
    if allowed and host not in allowed:
        raise ValueError(
            f"base URL host {host!r} is not in {ALLOWED_HOSTS_ENV} ({', '.join(sorted(allowed))})"
        )

    if parsed.scheme == "http" and not _is_loopback(host):
        if host not in allowed:
            raise ValueError(
                f"base URL must use https for non-loopback host {host!r} — the "
                f"API key is sent as a bearer token on every request. Use "
                f"https://, point at a loopback address, or list the host in "
                f"{ALLOWED_HOSTS_ENV} to accept plain HTTP explicitly."
            )
        logger.warning(
            "Sending the OpenZync API key over plain HTTP to %s — the bearer "
            "token and every response travel unencrypted.",
            host,
        )
    return base_url
