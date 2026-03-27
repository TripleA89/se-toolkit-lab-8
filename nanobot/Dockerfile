# Nanobot gateway Dockerfile
# Multi-stage build with uv

ARG REGISTRY_PREFIX_DOCKER_HUB

# ---
# Stage 1: Build the application
# ---

FROM ${REGISTRY_PREFIX_DOCKER_HUB}astral/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy workspace files (root pyproject.toml and uv.lock for workspace resolution)
COPY --from=workspace pyproject.toml uv.lock /app/

# Copy nanobot project files (build context is ./nanobot, so files are at root)
# Copy them to /app/nanobot/
RUN mkdir -p /app/nanobot
COPY . /app/nanobot/

# Copy mcp for editable install (from workspace context)
COPY --from=workspace mcp /app/mcp/

# Copy nanobot-websocket-channel for webchat support
COPY --from=workspace nanobot-websocket-channel /app/nanobot-websocket-channel/

# Sync nanobot dependencies (includes workspace mcp and webchat)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package nanobot

# ---
# Stage 2: Final image
# ---

FROM ${REGISTRY_PREFIX_DOCKER_HUB}python:3.14.2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

# Non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy application from builder
COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/nanobot"

USER nonroot
WORKDIR /app/nanobot

# Run the entrypoint which resolves config and starts nanobot gateway
CMD ["python", "/app/nanobot/entrypoint.py"]
