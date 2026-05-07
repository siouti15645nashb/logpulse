"""Tests for logpulse.throttle.ThrottleMiddleware."""

from __future__ import annotations

import time
from typing import List, Tuple
from unittest.mock import patch

import pytest

from logpulse.throttle import ThrottleMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collector() -> List[Tuple[str, str]]:
    return []


def cb(collected: List[Tuple[str, str]]):
    def _cb(source: str, line: str) -> None:
        collected.append((source, line))
    return _cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestThrottleMiddleware:
    def test_lines_within_limit_pass_through(self):
        out = _collector()
        mw = ThrottleMiddleware(cb(out), max_count=3, window_seconds=10.0)
        for _ in range(3):
            mw.on_line("app", "hello")
        assert len(out) == 3
        assert mw.throttled_count == 0

    def test_lines_over_limit_are_suppressed(self):
        out = _collector()
        mw = ThrottleMiddleware(cb(out), max_count=2, window_seconds=10.0)
        for _ in range(5):
            mw.on_line("app", "flood")
        assert len(out) == 2
        assert mw.throttled_count == 3

    def test_different_lines_tracked_independently(self):
        out = _collector()
        mw = ThrottleMiddleware(cb(out), max_count=2, window_seconds=10.0)
        for _ in range(3):
            mw.on_line("app", "line-a")
            mw.on_line("app", "line-b")
        # Each line gets 2 passes, 1 suppressed
        assert len(out) == 4
        assert mw.throttled_count == 2

    def test_different_sources_tracked_independently(self):
        out = _collector()
        mw = ThrottleMiddleware(cb(out), max_count=1, window_seconds=10.0)
        mw.on_line("src-a", "msg")
        mw.on_line("src-b", "msg")
        mw.on_line("src-a", "msg")  # throttled
        assert len(out) == 2
        assert mw.throttled_count == 1

    def test_window_expiry_resets_count(self):
        out = _collector()
        mw = ThrottleMiddleware(cb(out), max_count=1, window_seconds=1.0)

        fake_time = [0.0]

        def _monotonic():
            return fake_time[0]

        with patch("logpulse.throttle.time.monotonic", side_effect=_monotonic):
            mw.on_line("app", "tick")   # passes (count=1)
            mw.on_line("app", "tick")   # throttled (count=2)
            fake_time[0] = 2.0          # advance past window
            mw.on_line("app", "tick")   # passes again (window reset)

        assert len(out) == 2
        assert mw.throttled_count == 1

    def test_pattern_only_throttles_matching_lines(self):
        out = _collector()
        mw = ThrottleMiddleware(
            cb(out), max_count=1, window_seconds=10.0, pattern=r"ERROR"
        )
        for _ in range(3):
            mw.on_line("app", "ERROR boom")   # throttled after 1st
            mw.on_line("app", "INFO  ok")     # never throttled
        assert mw.throttled_count == 2
        # 1 ERROR + 3 INFO
        assert len(out) == 4

    def test_callable_interface(self):
        out = _collector()
        mw = ThrottleMiddleware(cb(out), max_count=2, window_seconds=10.0)
        for _ in range(4):
            mw("svc", "repeated")
        assert len(out) == 2
        assert mw.throttled_count == 2

    def test_initial_throttled_count_is_zero(self):
        mw = ThrottleMiddleware(cb(_collector()))
        assert mw.throttled_count == 0
