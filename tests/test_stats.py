"""Tests for logpulse.stats.StatsTracker and SourceStats."""

from __future__ import annotations

import threading
import time

import pytest

from logpulse.stats import SourceStats, StatsTracker


class TestSourceStats:
    def test_initial_state(self):
        s = SourceStats()
        assert s.total_lines == 0
        assert s.matched_lines == 0
        assert s.last_seen is None
        assert s.drop_rate == 0.0

    def test_record_matched(self):
        s = SourceStats()
        s.record(matched=True)
        assert s.total_lines == 1
        assert s.matched_lines == 1
        assert s.drop_rate == 0.0

    def test_record_unmatched(self):
        s = SourceStats()
        s.record(matched=False)
        assert s.total_lines == 1
        assert s.matched_lines == 0
        assert s.drop_rate == 1.0

    def test_drop_rate_mixed(self):
        s = SourceStats()
        for _ in range(3):
            s.record(matched=True)
        for _ in range(1):
            s.record(matched=False)
        assert s.drop_rate == pytest.approx(0.25)

    def test_last_seen_updated(self):
        s = SourceStats()
        before = time.time()
        s.record(matched=True)
        after = time.time()
        assert before <= s.last_seen <= after


class TestStatsTracker:
    def test_record_and_snapshot(self):
        tracker = StatsTracker()
        tracker.record("app.log", matched=True)
        tracker.record("app.log", matched=False)
        snap = tracker.snapshot()
        assert "app.log" in snap
        assert snap["app.log"].total_lines == 2
        assert snap["app.log"].matched_lines == 1

    def test_multiple_sources(self):
        tracker = StatsTracker()
        tracker.record("a.log", matched=True)
        tracker.record("b.log", matched=False)
        snap = tracker.snapshot()
        assert set(snap.keys()) == {"a.log", "b.log"}

    def test_reset_single_source(self):
        tracker = StatsTracker()
        tracker.record("a.log", matched=True)
        tracker.record("b.log", matched=True)
        tracker.reset("a.log")
        snap = tracker.snapshot()
        assert "a.log" not in snap
        assert "b.log" in snap

    def test_reset_all(self):
        tracker = StatsTracker()
        tracker.record("a.log", matched=True)
        tracker.record("b.log", matched=True)
        tracker.reset()
        assert tracker.snapshot() == {}

    def test_summary_lines(self):
        tracker = StatsTracker()
        tracker.record("app.log", matched=True)
        tracker.record("app.log", matched=False)
        lines = tracker.summary_lines()
        assert len(lines) == 1
        assert "app.log" in lines[0]
        assert "total=2" in lines[0]
        assert "matched=1" in lines[0]
        assert "50.0%" in lines[0]

    def test_thread_safety(self):
        tracker = StatsTracker()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    tracker.record("shared.log", matched=True)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert tracker.snapshot()["shared.log"].total_lines == 800
