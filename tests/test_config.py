"""Tests for base-URL validation (openzync_mcp/_config.py).

The OpenZync API key travels in an ``Authorization: Bearer`` header on
every request, so the configured base URL decides *where a production
credential is sent*.  A plain ``http://`` URL to a non-loopback host is
therefore rejected at startup — an agent that writes a hostile base URL
into its MCP config gets an error instead of a leaked API key.
"""

from __future__ import annotations

import logging

import pytest

from openzync_mcp._config import ALLOWED_HOSTS_ENV, validate_base_url


@pytest.fixture(autouse=True)
def _no_allowlist(monkeypatch) -> None:
    """No host allowlist unless a test sets one."""
    monkeypatch.delenv(ALLOWED_HOSTS_ENV, raising=False)


def test_loopback_http_allowed() -> None:
    """Plain HTTP to the local machine is the supported default."""
    assert validate_base_url("http://localhost:8000") == "http://localhost:8000"
    assert validate_base_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert validate_base_url("http://[::1]:8000") == "http://[::1]:8000"


def test_plain_http_to_remote_host_rejected() -> None:
    """Plain HTTP to a non-loopback host is refused — the key would travel cleartext."""
    with pytest.raises(ValueError, match="must use https"):
        validate_base_url("http://api.openzync.test")


def test_https_allowed_for_any_host() -> None:
    """HTTPS to any host is accepted."""
    assert validate_base_url("https://api.openzync.test") == "https://api.openzync.test"
    assert validate_base_url("https://api.openzync.test:8443") == "https://api.openzync.test:8443"


def test_allowlisted_host_may_use_plain_http(monkeypatch, caplog) -> None:
    """A host in OPENZYN_MCP_ALLOWED_HOSTS may use plain HTTP — with a warning."""
    monkeypatch.setenv(ALLOWED_HOSTS_ENV, "api.openzync.test")

    with caplog.at_level(logging.WARNING, logger="openzync.mcp.config"):
        assert validate_base_url("http://api.openzync.test") == "http://api.openzync.test"

    assert "plain HTTP" in caplog.text


def test_allowlist_rejects_other_hosts(monkeypatch) -> None:
    """With an allowlist set, every other host is rejected — HTTPS included."""
    monkeypatch.setenv(ALLOWED_HOSTS_ENV, "api.openzync.test")

    with pytest.raises(ValueError, match="is not in"):
        validate_base_url("https://other.openzync.test")


def test_allowlist_is_case_insensitive(monkeypatch) -> None:
    """Host matching ignores case and surrounding whitespace."""
    monkeypatch.setenv(ALLOWED_HOSTS_ENV, " API.OpenZync.Test , other.test ")

    assert validate_base_url("http://api.openzync.test") == "http://api.openzync.test"


def test_unsupported_scheme_rejected() -> None:
    """Only http and https are accepted."""
    with pytest.raises(ValueError, match="must use http or https"):
        validate_base_url("ftp://api.openzync.test")

    with pytest.raises(ValueError, match="must use http or https"):
        validate_base_url("api.openzync.test")


def test_missing_host_rejected() -> None:
    """A URL without a host is refused."""
    with pytest.raises(ValueError, match="must include a host"):
        validate_base_url("http:///v1")


# ── Regression: loopback is an IP property, not a string prefix ──────────────
#
# The loopback check used to test ``host.startswith("127.")``, so any DNS name
# that merely *began* with ``127.`` counted as the local machine: plain
# ``http://`` was accepted and the OPENZYN_API_KEY bearer token travelled to
# that host in cleartext.  The contract that matters is which URLs
# ``validate_base_url`` accepts, so that is what the tests below pin.


def test_loopback_hosts_accept_plain_http() -> None:
    """Plain HTTP stays available for the local machine.

    ``127.0.0.0/8``, ``::1``, ``localhost`` and its absolute form
    ``localhost.`` are the local addresses.
    """
    for url in (
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://127.1.2.3:8000",
        "http://[::1]:8000",
        "http://localhost.:8000",
    ):
        assert validate_base_url(url) == url


def test_urls_that_must_not_be_accepted_are_rejected() -> None:
    """Every URL that could leak the key in cleartext is refused.

    ``127.attacker.test`` is the regression case — it starts with ``127.``
    but is a DNS name, so plain HTTP to it must be refused.
    """
    for url, message in (
        ("http://127.attacker.test:8000", "must use https"),
        ("http://10.0.0.1:8000", "must use https"),
        ("http://0.0.0.0:8000", "must use https"),
        ("http://example.com:8000", "must use https"),
        ("http://127x.attacker.test:8000", "must use https"),
        ("127.attacker.test", "must use http or https"),
        ("http:///v1", "must include a host"),
    ):
        with pytest.raises(ValueError, match=message):
            validate_base_url(url)


def test_https_accepted_for_any_host() -> None:
    """HTTPS is safe whatever the host — plain HTTP to the same host is not."""
    for url in ("https://app.openzync.tech", "https://127.attacker.test"):
        assert validate_base_url(url) == url

    with pytest.raises(ValueError, match="must use https"):
        validate_base_url("http://127.attacker.test")


def test_allowlist_gates_hosts_and_warns_for_listed_plain_http(monkeypatch, caplog) -> None:
    """The allowlist still gates hosts, and a listed host may use plain HTTP.

    Listing a host is the operator's explicit opt-in to cleartext HTTP, so a
    listed *non-loopback* host is accepted over ``http://`` — with a warning.
    The host below is one the old prefix matcher mistook for loopback: with
    the bug, the warning was skipped, because the host looked local.
    """
    monkeypatch.setenv(ALLOWED_HOSTS_ENV, "127.attacker.test")

    with pytest.raises(ValueError, match="is not in"):
        validate_base_url("https://other.openzync.test")

    with caplog.at_level(logging.WARNING, logger="openzync.mcp.config"):
        assert validate_base_url("http://127.attacker.test:8000") == "http://127.attacker.test:8000"

    assert "plain HTTP" in caplog.text
