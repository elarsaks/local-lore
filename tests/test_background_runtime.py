from __future__ import annotations

import asyncio
import logging
import os
import threading
from pathlib import Path

from starlette.testclient import TestClient

from locallore.config import Settings
from locallore.embeddings import MODEL_CHECKSUM_FILE
from locallore.indexing.importer import ImportResult
from locallore.server.mcp import mcp
from locallore.server.runtime import LocalLoreRuntime, source_snapshot


def runtime_settings(tmp_path: Path) -> Settings:
    sessions = tmp_path / "sessions"
    models = tmp_path / "models"
    sessions.mkdir()
    models.mkdir()
    (models / MODEL_CHECKSUM_FILE).write_text(f"{'a' * 64}\n")
    return Settings(
        tmp_path / "locallore.db",
        sessions,
        models,
        "fixture",
        3,
        8,
        watcher_interval=0.01,
        watcher_idle_interval=0.02,
        watcher_debounce=0.01,
    )


def test_snapshot_detects_all_portable_source_changes(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    source = root / "history.jsonl"
    source.write_text("{}\n")
    created = source_snapshot(root)

    with source.open("a") as handle:
        handle.write("{}\n")
    appended = source_snapshot(root)
    assert appended != created

    source.write_text("")
    truncated = source_snapshot(root)
    assert truncated != appended

    replacement = root / "replacement.jsonl"
    replacement.write_text("{}\n")
    os.replace(replacement, source)
    replaced = source_snapshot(root)
    assert replaced != truncated

    renamed = root / "renamed.jsonl"
    source.rename(renamed)
    assert source_snapshot(root) != replaced
    renamed.unlink()
    assert source_snapshot(root) == ()


def test_refresh_event_during_work_runs_one_follow_up(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = runtime_settings(tmp_path)
    runtime = LocalLoreRuntime(settings)
    calls = 0
    first_started = threading.Event()
    release_first = threading.Event()
    second_finished = threading.Event()

    def refresh_once() -> tuple[ImportResult, int]:
        nonlocal calls
        calls += 1
        if calls == 1:
            first_started.set()
            release_first.wait(timeout=2)
        else:
            second_finished.set()
        return ImportResult(), 0

    monkeypatch.setattr(runtime, "_refresh_once", refresh_once)

    async def exercise() -> None:
        worker = asyncio.create_task(runtime._refresh_worker())
        runtime.request_refresh()
        await asyncio.to_thread(first_started.wait, 2)
        runtime.request_refresh()
        runtime.request_refresh()
        release_first.set()
        await asyncio.to_thread(second_finished.wait, 2)
        runtime._stopping = True
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)

    asyncio.run(exercise())
    assert calls == 2


def test_failed_refresh_records_error_and_retries(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    settings = runtime_settings(tmp_path)
    runtime = LocalLoreRuntime(settings)
    calls = 0
    retry_finished = threading.Event()
    original_sleep = asyncio.sleep

    def refresh_once() -> tuple[ImportResult, int]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary indexing failure")
        retry_finished.set()
        return ImportResult(messages_added=1), 0

    async def skip_backoff(delay: float) -> None:
        if delay != 1.0:
            await original_sleep(delay)

    monkeypatch.setattr(runtime, "_refresh_once", refresh_once)
    monkeypatch.setattr("locallore.server.runtime.asyncio.sleep", skip_backoff)

    async def exercise() -> None:
        worker = asyncio.create_task(runtime._refresh_worker())
        runtime.request_refresh()
        assert await asyncio.to_thread(retry_finished.wait, 2)
        assert await runtime.wait_until_ready(timeout=2)
        runtime._stopping = True
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)

    with caplog.at_level(logging.ERROR):
        asyncio.run(exercise())

    assert calls == 2
    assert "temporary indexing failure" in caplog.text
    assert runtime.last_background_error is None
    assert runtime.last_stats.messages_added == 1


def test_runtime_starts_ready_and_initializes_one_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = runtime_settings(tmp_path)
    runtime = LocalLoreRuntime(settings)
    initializations = 0

    class FakeEmbedder:
        def __init__(self, *_args, **_kwargs) -> None:
            nonlocal initializations
            initializations += 1

    monkeypatch.setattr("locallore.server.runtime.FastEmbedder", FakeEmbedder)

    async def exercise() -> None:
        await runtime.start()
        assert await runtime.wait_until_ready(timeout=2)
        assert runtime.status()["transport"] == "streamable-http"
        await runtime.stop()

    asyncio.run(exercise())
    assert runtime._get_embedder() is runtime._get_embedder()
    assert initializations == 1


def test_local_unauthenticated_transport_security() -> None:
    with TestClient(
        mcp.streamable_http_app(),
        base_url="http://127.0.0.1:8765",
    ) as client:
        initialize = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        }
        assert (
            client.post(
                "/mcp",
                json=initialize,
                headers={"Accept": "application/json"},
            ).status_code
            == 200
        )
        assert (
            client.post("/mcp", json={}, headers={"Host": "evil.example"}).status_code
            == 421
        )
        assert (
            client.post(
                "/mcp",
                json={},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )
