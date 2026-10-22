# Changelog

All notable changes to this project will be documented in this file.

<!-- towncrier release notes start -->

## [1.0.0] - 2026-10-22

### Breaking Changes

- **BREAKING:** the `--api-key` command-line flag is removed — the key is read from `OPENZYN_API_KEY` only, because argv is world-readable in `ps` output and lands in shell history. The server now validates `OPENZYN_BASE_URL`/`--base-url` at startup: plain `http://` is rejected for non-loopback hosts (the API key is a bearer token on every request), and the optional `OPENZYN_MCP_ALLOWED_HOSTS` allowlist restricts the accepted hosts — listing a host also opts it into plain HTTP with a loud warning. (+base-url-validation)
- **BREAKING:** `update_project_member` now requires the `role` argument — it used to default to `"member"`, so a call that omitted it silently demoted a project owner to member and reported success. The tool now fails with a validation error instead. (+projects-role-required)
### Added

- Pass `idempotency_key` through on `add_memory` so retries and replayed tool calls dedupe server-side instead of creating duplicate memories. (+add-memory-idempotency-key)
### Fixed

- Point the facts pagination hint at the `cursor` parameter so page 2 resolves instead of returning a 422. (+facts-cursor-hint)
- Emit fact timestamps as RFC-3339 (`2026-02-01T00:00:00Z`) instead of Python's `str(datetime)` form (`2026-02-01 00:00:00+00:00`), so `get_fact_history` and `retract_fact` speak the same timestamp format as every other OpenZync surface. (+facts-iso-timestamps)
- Parse the base-URL host as an IP address when deciding whether plain `http://` is allowed, instead of matching the string prefix `127.`. A host such as `http://127.attacker.test` was previously accepted as "loopback", so the `OPENZYN_API_KEY` bearer token was sent to it in cleartext. `localhost`, the `127.0.0.0/8` range and `::1` are still accepted. (+loopback-host-validation)
### Changed

- Bound the entity edge fan-out with a 10-second timeout that raises loudly instead of waiting out the slowest source on every call. (+graph-fanout-timeout)
## [Unreleased]
