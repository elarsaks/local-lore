from __future__ import annotations

import fcntl
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def index_lock_path(database_path: Path) -> Path:
    return database_path.with_name(f"{database_path.name}.index.lock")


@contextmanager
def acquire_index_lock(database_path: Path) -> Iterator[None]:
    """Allow only one process to update an index at a time."""
    lock_path = index_lock_path(database_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "rb+", closefd=True) as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info(
                "Another LocalLore indexing operation is running; "
                "waiting for it to complete"
            )
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
