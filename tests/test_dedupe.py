"""Tests for logpulse.dedupe.DedupeMiddleware."""

from __future__ import annotations

import time
from typing import List, Tuple

import pytest

from logpulse.dedupe import DedupeMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collector() -> Tuple[List[Tuple[str, str]], callable]:
    collected: List[Tuple[str, str]] = []

    def cb(source: str, line: str) -> None:
        collected.append((source, line))

    return collected, cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDedupeMiddleware:
    def test_first_occurrence_passes_through(self):
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=5.0)
        mw.on_line("app", "hello world")
        assert collected == [("app", "hello world")]

    def test_immediate_duplicate_is_suppressed(self):
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=5.0)
        mw.on_line("app", "hello")
        mw.on_line("app", "hello")
        assert len(collected) == 1
        assert mw.suppressed_count == 1

    def test_different_sources_are_independent(self):
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=5.0)
        mw.on_line("src-a", "same line")
        mw.on_line("src-b", "same line")
        assert len(collected) == 2
        assert mw.suppressed_count == 0

    def test_different_lines_both_pass(self):
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=5.0)
        mw.on_line("app", "line one")
        mw.on_line("app", "line two")
        assert len(collected) == 2

    def test_line_allowed_after_window_expires(self):
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=1.0)
        mw.on_line("app", "repeat")
        # Manually expire the cache entry.
        mw._expire(now=time.monotonic() + 2.0)
        mw.on_line("app", "repeat")
        assert len(collected) == 2
        assert mw.suppressed_count == 0

    def test_suppressed_count_accumulates(self):
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=60.0)
        for _ in range(5):
            mw.on_line("app", "flood")
        assert mw.suppressed_count == 4

    def test_max_cache_evicts_oldest_entry(self):
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=60.0, max_cache=3)
        for i in range(4):
            mw.on_line("app", f"unique-{i}")
        assert len(mw._seen) == 3

    def test_callable_interface(self):
        """Middleware should be usable as a plain callable."""
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=5.0)
        mw("app", "via call")
        mw("app", "via call")
        assert len(collected) == 1

    def test_expire_removes_stale_entries(self):
        collected, cb = _collector()
        mw = DedupeMiddleware(cb, window_seconds=2.0)
        mw.on_line("app", "old line")
        mw._expire(now=time.monotonic() + 10.0)
        assert len(mw._seen) == 0
