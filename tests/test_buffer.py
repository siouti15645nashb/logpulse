"""Tests for logpulse.buffer.BufferMiddleware."""
from __future__ import annotations

import time
from typing import List, Tuple

import pytest

from logpulse.buffer import BufferMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collector() -> Tuple[List[Tuple[str, str]], callable]:
    received: List[Tuple[str, str]] = []

    def cb(source: str, line: str) -> None:
        received.append((source, line))

    return received, cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBufferMiddleware:
    def test_lines_held_until_max_size(self):
        received, cb = _collector()
        mw = BufferMiddleware(cb, max_size=3, flush_interval=60.0)
        mw.on_line("src", "a")
        mw.on_line("src", "b")
        assert received == [], "should not flush before max_size"
        mw.on_line("src", "c")  # triggers flush
        assert len(received) == 3
        mw.close()

    def test_manual_flush_drains_buffer(self):
        received, cb = _collector()
        mw = BufferMiddleware(cb, max_size=100, flush_interval=60.0)
        mw.on_line("src", "hello")
        assert received == []
        mw.flush()
        assert received == [("src", "hello")]
        mw.close()

    def test_close_flushes_remaining_lines(self):
        received, cb = _collector()
        mw = BufferMiddleware(cb, max_size=100, flush_interval=60.0)
        mw.on_line("src", "x")
        mw.on_line("src", "y")
        mw.close()
        assert received == [("src", "x"), ("src", "y")]

    def test_flushed_count_accumulates(self):
        received, cb = _collector()
        mw = BufferMiddleware(cb, max_size=2, flush_interval=60.0)
        for i in range(6):
            mw.on_line("src", str(i))
        assert mw.flushed_count == 6
        mw.close()

    def test_pending_reflects_buffer_size(self):
        received, cb = _collector()
        mw = BufferMiddleware(cb, max_size=10, flush_interval=60.0)
        mw.on_line("s", "1")
        mw.on_line("s", "2")
        assert mw.pending == 2
        mw.flush()
        assert mw.pending == 0
        mw.close()

    def test_timer_flushes_after_interval(self):
        received, cb = _collector()
        mw = BufferMiddleware(cb, max_size=100, flush_interval=0.1)
        mw.on_line("src", "timed")
        time.sleep(0.35)
        assert ("src", "timed") in received
        mw.close()

    def test_callable_interface(self):
        received, cb = _collector()
        mw = BufferMiddleware(cb, max_size=1, flush_interval=60.0)
        mw("s", "line")  # should flush immediately (max_size=1)
        assert received == [("s", "line")]
        mw.close()

    def test_invalid_max_size_raises(self):
        _, cb = _collector()
        with pytest.raises(ValueError, match="max_size"):
            BufferMiddleware(cb, max_size=0)

    def test_invalid_flush_interval_raises(self):
        _, cb = _collector()
        with pytest.raises(ValueError, match="flush_interval"):
            BufferMiddleware(cb, flush_interval=-1.0)
