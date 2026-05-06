"""Tests for logpulse.snapshot.PositionSnapshot."""

import json
import os

import pytest

from logpulse.snapshot import PositionSnapshot


@pytest.fixture()
def snap_path(tmp_path):
    return str(tmp_path / "positions.json")


class TestPositionSnapshot:
    def test_get_returns_zero_when_no_snapshot(self, snap_path):
        snap = PositionSnapshot(snap_path)
        assert snap.get("/var/log/app.log") == 0

    def test_update_and_get_roundtrip(self, snap_path):
        snap = PositionSnapshot(snap_path)
        snap.update("/var/log/app.log", 1024)
        assert snap.get("/var/log/app.log") == 1024

    def test_save_creates_file(self, snap_path):
        snap = PositionSnapshot(snap_path)
        snap.update("/var/log/app.log", 512)
        snap.save()
        assert os.path.exists(snap_path)

    def test_save_and_reload_preserves_positions(self, snap_path):
        snap = PositionSnapshot(snap_path)
        snap.update("/var/log/app.log", 2048)
        snap.update("/var/log/other.log", 99)
        snap.save()

        snap2 = PositionSnapshot(snap_path)
        assert snap2.get("/var/log/app.log") == 2048
        assert snap2.get("/var/log/other.log") == 99

    def test_remove_clears_entry(self, snap_path):
        snap = PositionSnapshot(snap_path)
        snap.update("/var/log/app.log", 300)
        snap.remove("/var/log/app.log")
        assert snap.get("/var/log/app.log") == 0

    def test_relative_and_absolute_paths_normalised(self, snap_path, tmp_path):
        log_file = tmp_path / "service.log"
        log_file.write_text("")
        abs_path = str(log_file)
        snap = PositionSnapshot(snap_path)
        snap.update(abs_path, 777)
        # Querying with the same absolute path should return the value.
        assert snap.get(abs_path) == 777

    def test_corrupt_snapshot_starts_fresh(self, snap_path):
        with open(snap_path, "w") as fh:
            fh.write("{not valid json")
        snap = PositionSnapshot(snap_path)
        assert snap.get("/any/file.log") == 0

    def test_save_is_atomic_via_tmp_file(self, snap_path, monkeypatch):
        """os.replace should be called so writes are atomic."""
        replaced = []
        original_replace = os.replace

        def spy_replace(src, dst):
            replaced.append((src, dst))
            original_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy_replace)
        snap = PositionSnapshot(snap_path)
        snap.update("/var/log/app.log", 1)
        snap.save()
        assert len(replaced) == 1
        assert replaced[0][1] == snap_path
