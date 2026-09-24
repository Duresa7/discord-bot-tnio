import pytest

from tnio_bot.status import SyncBusy, read_status, sync_lock, write_status


def test_write_and_read_status(tmp_path) -> None:
    path = tmp_path / "status.json"
    write_status(path, server="test", ok=True, results=["Week of Sep 21: posted"], error=None)
    status = read_status(path)
    assert status["server"] == "test"
    assert status["ok"] is True
    assert status["results"] == ["Week of Sep 21: posted"]
    assert "time" in status


def test_missing_or_broken_status(tmp_path) -> None:
    assert read_status(tmp_path / "missing.json") is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert read_status(broken) is None


def test_second_lock_is_busy_and_lock_is_released(tmp_path) -> None:
    path = tmp_path / "sync.lock"
    with sync_lock(path), pytest.raises(SyncBusy), sync_lock(path):
        pass
    with sync_lock(path):  # free again after the first one ends
        pass
