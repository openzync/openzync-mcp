# ──────────────────────────────────────────────────────────────────────────────
# OpenZync MCP Server — Production Docker image
# ──────────────────────────────────────────────────────────────────────────────
# Multi-stage build:
#   1. builder — installs runtime dependencies into ~/.local
#   2. runtime — minimal image that copies only the built artifacts + source
#
# Build from the openzync-mcp REPO ROOT (standalone repo, not a monorepo):
#   docker build -t openzync-mcp:latest -f openzync_mcp/Dockerfile .
#   docker run -p 8100:8100 --env-file .env openzync-mcp:latest
#
# The builder installs openzync-mcp editable, which pulls the `openzync` SDK
# from PyPI as a regular dependency — no sibling-package copying needed.
# The runtime stage copies the source, and `python -m openzync_mcp` resolves
# the editable install via the working directory.
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS builder
WORKDIR /app

# Install the package and its dependencies into ~/.local.
# NOTE: unlike openzync-core (hatchling), setuptools editable builds need the
# package source present to register the import — COPY the package dir too.
# README.md is copied too — setuptools validates it exists at build time.
COPY pyproject.toml README.md openzync_mcp/ ./
RUN pip install --no-cache-dir --user -e .

# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS runtime
WORKDIR /app

# Copy installed packages from builder.
COPY --from=builder /root/.local /root/.local

# Copy application source.
# ⚠️ SECRET RISK: this also copies .env (real API keys), .venv and .git — all
# excluded by the repo-root .dockerignore (same pattern as openzync-core).
COPY . .

# Ensure ~/.local/bin (where pip --user installs scripts) is on PATH.
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8100

# TCP probe, not HTTP: a bare GET /mcp returns 406 (Streamable HTTP requires
# Accept: application/json, text/event-stream), so an HTTP probe would mark a
# healthy container unhealthy. A socket connect only checks the port is up.
# # note: a real /health route would be the fuller fix — TCP is the lazy correct one.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python3 -c "import socket; socket.create_connection(('127.0.0.1', 8100), 5).close()" || exit 1

# The MCP server requires OPENZYN_API_KEY to be set at runtime.
# Default transport is stdio; override with --transport http --port 8100
# for HTTP transport, or --transport sse for SSE transport.
CMD ["python", "-m", "openzync_mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8100"]
