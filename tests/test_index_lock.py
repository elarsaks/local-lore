from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

from locallore.locking import acquire_index_lock, index_lock_path


def _hold_lock(
    database_path: str,
    entered: multiprocessing.synchronize.Event,
    release: multiprocessing.synchronize.Event,
) -> None:
    with acquire_index_lock(Path(database_path)):
        entered.set()
        release.wait(timeout=10)


def _exit_while_holding_lock(
    database_path: str,
    entered: multiprocessing.synchronize.Event,
) -> None:
    with acquire_index_lock(Path(database_path)):
        entered.set()
        os._exit(0)


def test_index_lock_serializes_processes(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    database_path = str(tmp_path / "locallore.db")
    first_entered = context.Event()
    second_entered = context.Event()
    release = context.Event()
    first = context.Process(
        target=_hold_lock,
        args=(database_path, first_entered, release),
    )
    second = context.Process(
        target=_hold_lock,
        args=(database_path, second_entered, release),
    )

    first.start()
    try:
        assert first_entered.wait(timeout=5)
        second.start()
        assert not second_entered.wait(timeout=0.5)
        release.set()
        assert second_entered.wait(timeout=5)
    finally:
        release.set()
        first.join(timeout=5)
        if second.pid is not None:
            second.join(timeout=5)
        if first.is_alive():
            first.terminate()
        if second.pid is not None and second.is_alive():
            second.terminate()

    assert first.exitcode == 0
    assert second.exitcode == 0
    assert index_lock_path(Path(database_path)).is_file()


def test_index_lock_is_released_when_owner_exits(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    database_path = str(tmp_path / "locallore.db")
    entered = context.Event()
    owner = context.Process(
        target=_exit_while_holding_lock,
        args=(database_path, entered),
    )

    owner.start()
    assert entered.wait(timeout=5)
    owner.join(timeout=5)
    assert owner.exitcode == 0

    with acquire_index_lock(Path(database_path)):
        pass
