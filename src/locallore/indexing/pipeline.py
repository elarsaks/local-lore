from __future__ import annotations

from ..config import Settings
from ..embeddings import (
    Embedder,
    FastEmbedder,
    embed_pending_messages,
    embedding_model_id,
    has_pending_messages,
)
from ..storage.db import connect, migrate
from .importer import ImportResult, import_sessions
from .locking import acquire_index_lock


def update_index(
    settings: Settings,
    *,
    embedder: Embedder | None = None,
) -> tuple[ImportResult, int]:
    """Import changed sessions and embed any messages that are out of date."""
    with acquire_index_lock(settings.database_path):
        connection = connect(settings.database_path)
        try:
            migrate(connection)
            result = import_sessions(connection, settings.sessions_path)
            model_id = (
                embedder.model_id
                if embedder is not None
                else embedding_model_id(
                    settings.embedding_model,
                    settings.model_path,
                )
            )
            if not has_pending_messages(
                connection,
                model_id,
                settings.embedding_dimension,
            ):
                return result, 0
            if embedder is None:
                embedder = FastEmbedder(
                    settings.embedding_model,
                    settings.model_path,
                    settings.embedding_dimension,
                    model_id=model_id,
                )
            embedded = embed_pending_messages(
                connection,
                embedder,
                batch_size=settings.embedding_batch_size,
            )
            return result, embedded
        finally:
            connection.close()
