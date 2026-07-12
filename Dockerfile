FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp/home \
    LOCALLORE_DB=/data/locallore.db \
    LOCALLORE_SESSIONS=/sessions

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev \
    && mkdir -p /data /tmp/home \
    && chown -R 65532:65532 /data /tmp/home

USER 65532:65532
ENTRYPOINT ["/app/.venv/bin/python", "-m", "locallore"]
CMD ["mcp"]
