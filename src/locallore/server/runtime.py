from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .. import __version__
from ..config import Settings
from ..embeddings import Embedder, FastEmbedder, embedding_model_id
from ..indexing.discovery import discover
from ..indexing.importer import ImportResult
from ..indexing.pipeline import update_index
from ..status import RuntimeStatus
from ..storage.db import connect, migrate

logger = logging.getLogger(__name__)

Snapshot = tuple[tuple[str, str, int, int], ...]


def source_snapshot(root: Path) -> Snapshot:
    """Return a stable, content-free snapshot of all JSONL sources."""
    return tuple(
        (
            source.relative_path,
            source.identity,
            source.size_bytes,
            source.mtime_ns,
        )
        for source in discover(root)
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class RefreshStats:
    files_added: int = 0
    files_removed: int = 0
    messages_added: int = 0
    messages_removed: int = 0
    messages_embedded: int = 0


class _LockedEmbedder:
    """Serialize each inference call while retaining one underlying model."""

    def __init__(self, runtime: LocalLoreRuntime) -> None:
        self._runtime = runtime

    @property
    def model_id(self) -> str:
        return self._runtime.model_id

    @property
    def dimension(self) -> int:
        return self._runtime.settings.embedding_dimension

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        with self._runtime.inference_lock:
            return self._runtime._get_embedder().encode(texts)

    def encode_query(self, query: str) -> np.ndarray:
        with self._runtime.inference_lock:
            return self._runtime._get_embedder().encode_query(query)


class LocalLoreRuntime:
    """Own daemon state, one lazy model, and one background refresh worker."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.inference_lock = threading.Lock()
        self._model_lock = threading.Lock()
        self._embedder: FastEmbedder | None = None
        self._locked_embedder = _LockedEmbedder(self)
        self._refresh_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        self._stopping = False
        self._snapshot: Snapshot | None = None
        self._model_id: str | None = None
        self._started_monotonic = time.monotonic()
        self.refresh_state = "starting"
        self.last_refresh_started_at: str | None = None
        self.last_refresh_completed_at: str | None = None
        self.last_successful_refresh_at: str | None = None
        self.last_refresh_duration_seconds: float | None = None
        self.last_background_error: str | None = None
        self.last_stats = RefreshStats()

    @property
    def model_id(self) -> str:
        if self._model_id is None:
            self._model_id = embedding_model_id(
                self.settings.embedding_model, self.settings.model_path
            )
        return self._model_id

    @property
    def search_embedder(self) -> Embedder:
        return self._locked_embedder

    def _get_embedder(self) -> FastEmbedder:
        if self._embedder is None:
            with self._model_lock:
                if self._embedder is None:
                    self._embedder = FastEmbedder(
                        self.settings.embedding_model,
                        self.settings.model_path,
                        self.settings.embedding_dimension,
                        model_id=self.model_id,
                    )
        return self._embedder

    async def start(self) -> None:
        if not self.settings.sessions_path.is_dir():
            raise FileNotFoundError(
                f"session directory does not exist: {self.settings.sessions_path}"
            )
        self._model_id = embedding_model_id(
            self.settings.embedding_model, self.settings.model_path
        )
        connection = connect(self.settings.database_path)
        try:
            migrate(connection)
        finally:
            connection.close()
        self._tasks = [
            asyncio.create_task(self._refresh_worker(), name="locallore-indexer"),
            asyncio.create_task(self._watch_sources(), name="locallore-watcher"),
        ]
        self.request_refresh()

    async def stop(self) -> None:
        self._stopping = True
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    def request_refresh(self) -> None:
        self._refresh_event.set()

    async def wait_until_ready(self, timeout: float = 300.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if (
                self.refresh_state == "idle"
                and self.last_successful_refresh_at is not None
            ):
                return True
            await asyncio.sleep(0.05)
        return False

    async def _watch_sources(self) -> None:
        while not self._stopping:
            await asyncio.sleep(self.settings.watcher_interval)
            try:
                current = await asyncio.to_thread(
                    source_snapshot, self.settings.sessions_path
                )
            except OSError as exc:
                self.last_background_error = f"watch scan failed: {exc}"
                logger.warning("LocalLore watcher scan failed: %s", exc)
                continue
            if current == self._snapshot:
                continue
            self._snapshot = current
            if self.refresh_state != "indexing":
                self.refresh_state = "debouncing"
            while True:
                await asyncio.sleep(self.settings.watcher_debounce)
                latest = await asyncio.to_thread(
                    source_snapshot, self.settings.sessions_path
                )
                if latest == self._snapshot:
                    break
                self._snapshot = latest
            self.request_refresh()

    async def _refresh_worker(self) -> None:
        backoff = 1.0
        while not self._stopping:
            await self._refresh_event.wait()
            self._refresh_event.clear()
            self.refresh_state = "indexing"
            self.last_refresh_started_at = _utc_now()
            started = time.monotonic()
            try:
                result, embedded = await asyncio.to_thread(self._refresh_once)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_refresh_completed_at = _utc_now()
                self.last_refresh_duration_seconds = round(
                    time.monotonic() - started, 6
                )
                self.last_background_error = str(exc)
                self.refresh_state = "error"
                logger.exception(
                    "background_refresh state=error duration=%.3f",
                    self.last_refresh_duration_seconds,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                self.request_refresh()
                continue
            backoff = 1.0
            completed = _utc_now()
            self.last_refresh_completed_at = completed
            self.last_successful_refresh_at = completed
            self.last_refresh_duration_seconds = round(time.monotonic() - started, 6)
            self.last_background_error = None
            self.last_stats = RefreshStats(
                files_added=result.files_added,
                files_removed=result.files_removed,
                messages_added=result.messages_added,
                messages_removed=result.messages_removed,
                messages_embedded=embedded,
            )
            self.refresh_state = "indexing" if self._refresh_event.is_set() else "idle"
            logger.info(
                "background_refresh state=success duration=%.3f "
                "files_changed=%d files_removed=%d messages_added=%d "
                "messages_removed=%d messages_embedded=%d",
                self.last_refresh_duration_seconds,
                result.files_changed,
                result.files_removed,
                result.messages_added,
                result.messages_removed,
                embedded,
            )

    def _refresh_once(self) -> tuple[ImportResult, int]:
        return update_index(self.settings, embedder=self.search_embedder)

    def status(self) -> RuntimeStatus:
        return {
            "daemon_version": __version__,
            "uptime_seconds": round(time.monotonic() - self._started_monotonic, 3),
            "refresh_state": self.refresh_state,
            "last_refresh_started_at": self.last_refresh_started_at,
            "last_refresh_completed_at": self.last_refresh_completed_at,
            "last_successful_refresh_at": self.last_successful_refresh_at,
            "last_refresh_duration_seconds": self.last_refresh_duration_seconds,
            "refresh_queued": self._refresh_event.is_set(),
            "last_refresh_files_added": self.last_stats.files_added,
            "last_refresh_files_removed": self.last_stats.files_removed,
            "last_refresh_messages_added": self.last_stats.messages_added,
            "last_refresh_messages_removed": self.last_stats.messages_removed,
            "last_background_error": self.last_background_error,
        }
