FROM python:3.12.13-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp/home \
    LOCALLORE_DB=/data/locallore.db \
    LOCALLORE_SESSIONS=/sessions \
    LOCALLORE_MODEL_PATH=/models \
    LOCALLORE_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
    LOCALLORE_EMBEDDING_DIMENSION=384

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.6@sha256:b1e699368d24c57cda93c338a57a8c5a119009ba809305cc8e86986d4a006754 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

RUN mkdir -p /models \
    && .venv/bin/python -c "from fastembed import TextEmbedding; model=TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/models', revision='52398278842ec682c6f32300af41344b1c0b0bb2'); list(model.embed(['offline model smoke test']))"

COPY src ./src
RUN PYTHONPATH=/app/src .venv/bin/python -c "from pathlib import Path; from locallore.embeddings import MODEL_CHECKSUM_FILE, _directory_checksum; path=Path('/models'); (path / MODEL_CHECKSUM_FILE).write_text(_directory_checksum(path) + '\n')" \
    && uv sync --frozen --no-dev \
    && mkdir -p /data /tmp/home \
    && chown -R 65532:65532 /data /tmp/home /models

USER 65532:65532
ENTRYPOINT ["/app/.venv/bin/python", "-m", "locallore"]
EXPOSE 8000
CMD ["serve"]
