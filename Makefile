# ──────────────────────────────────────────────────────────────────────────────
# OpenZync MCP — Common development commands
# ──────────────────────────────────────────────────────────────────────────────
# Usage:  make <target> [ARGS=...]
#
# Examples:
#   make install          # Install package with dev dependencies
#   make lint             # Ruff check + format check
#   make test             # Run unit tests
#   make test-coverage    # Run tests with coverage (fails under 80%)
#   make docker-build     # Build the Docker image (context = repo root)
#   make changelog-check  # Verify a news fragment exists
#   make changelog-build VERSION=1.1.0  # Build CHANGELOG.md for release
#   make clean            # Remove build artifacts
# ──────────────────────────────────────────────────────────────────────────────

.PHONY: install lint lint-fix test test-coverage docker-build changelog-check changelog-build clean

# ── Variables ─────────────────────────────────────────────────────────────────

PORT ?= 8100
PYTHON ?= python3
PIP ?= pip3
VERSION ?= 0.0.0

# ── Installation ──────────────────────────────────────────────────────────────

install:
	$(PIP) install -e ".[dev]"

# ── Linting ───────────────────────────────────────────────────────────────────

lint:
	ruff check . --output-format=concise
	ruff format --check .

lint-fix:
	ruff check . --fix --output-format=concise
	ruff format .

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v $(ARGS)

test-coverage:
	pytest tests/ -v \
		--cov=openzync_mcp \
		--cov-report=term --cov-report=xml \
		--cov-fail-under=80 $(ARGS)

# ── Changelog (towncrier) ─────────────────────────────────────────────────────

changelog-check:
	@base=$$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p'); \
	if [ -z "$$base" ]; then base=main; fi; \
	if git rev-parse --verify origin/$$base >/dev/null 2>&1; then ref=origin/$$base; \
	elif git rev-parse --verify origin/main >/dev/null 2>&1; then ref=origin/main; \
	else ref=origin/master; fi; \
	echo "Checking fragments against $$ref..."; \
	towncrier check --compare-with $$ref

changelog-build:
	towncrier build --version $(VERSION) --yes

# ── Docker ────────────────────────────────────────────────────────────────────
# Build context is the repo root (`.`) — openzync-mcp is a standalone repo and
# the Dockerfile COPYs only paths within it; the openzync SDK comes from PyPI.

docker-build:
	docker build -t openzync-mcp:latest -f openzync_mcp/Dockerfile .

# ── Housekeeping ──────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache .coverage coverage.xml htmlcov .ruff_cache
