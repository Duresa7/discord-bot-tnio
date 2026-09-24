"""Run status (``status.json``) and the one-sync-at-a-time lock (``sync.lock``)."""

import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class SyncBusy(RuntimeError):
    """Another sync (the scheduled task or the panel) is running now."""


def write_status(
    path: Path, *, server: str, ok: bool, results: list[str], error: str | None
) -> dict:
    status = {
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "server": server,
        "ok": ok,
        "results": results,
        "error": error,
    }
    path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


def read_status(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@contextmanager
def sync_lock(path: Path) -> Iterator[None]:
    """Hold an OS file lock while syncing. Raise ``SyncBusy`` if it is taken.

    The OS releases the lock when the process ends, so a crash never leaves a stale lock.
    """
    file = open(path, "a+")  # noqa: SIM115 - held open for the lock's lifetime
    try:
        try:
            _lock(file)
        except OSError as error:
            raise SyncBusy("Another sync is running. Try again in a minute.") from error
        try:
            yield
        finally:
            _unlock(file)
    finally:
        file.close()


if sys.platform == "win32":
    import msvcrt

    def _lock(file) -> None:
        file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(file) -> None:
        file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(file) -> None:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(file) -> None:
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
