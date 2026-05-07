"""Tests for MultilineMiddleware."""
from __future__ import annotations

import pytest

from logpulse.multiline import MultilineMiddleware


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _collector():
    received: list[tuple[str, str]] = []

    def cb(source: str, line: str) -> None:
        received.append((source, line))

    return received, cb


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class TestMultilineMiddleware:
    def test_single_line_event_passes_through(self):
        received, cb = _collector()
        mw = MultilineMiddleware(cb)
        mw.on_line("app", "INFO starting up")
        mw.flush()
        assert received == [("app", "INFO starting up")]

    def test_continuation_lines_are_folded(self):
        received, cb = _collector()
        mw = MultilineMiddleware(cb)
        mw.on_line("app", "ERROR boom")
        mw.on_line("app", "    at com.example.Foo(Foo.java:10)")
        mw.on_line("app", "    at com.example.Bar(Bar.java:20)")
        mw.flush()
        assert len(received) == 1
        src, text = received[0]
        assert src == "app"
        assert "ERROR boom" in text
        assert "Foo.java:10" in text
        assert "Bar.java:20" in text

    def test_new_event_flushes_previous(self):
        received, cb = _collector()
        mw = MultilineMiddleware(cb)
        mw.on_line("app", "INFO first")
        mw.on_line("app", "INFO second")  # not a continuation → flushes first
        mw.flush()
        assert len(received) == 2
        assert received[0] == ("app", "INFO first")
        assert received[1] == ("app", "INFO second")

    def test_folded_count_increments(self):
        received, cb = _collector()
        mw = MultilineMiddleware(cb)
        mw.on_line("app", "ERROR root")
        mw.on_line("app", "  line1")
        mw.on_line("app", "  line2")
        mw.flush()
        assert mw.folded_count == 2

    def test_max_lines_forces_flush(self):
        received, cb = _collector()
        mw = MultilineMiddleware(cb, max_lines=3)
        mw.on_line("app", "ERROR root")
        mw.on_line("app", "  c1")
        mw.on_line("app", "  c2")
        # buffer is now at max_lines=3; next continuation triggers flush
        mw.on_line("app", "  c3")
        mw.flush()
        assert len(received) == 1  # first batch flushed; second still pending
        # flush() above emits second batch
        assert received[0][1].startswith("ERROR root")

    def test_source_change_flushes_buffer(self):
        received, cb = _collector()
        mw = MultilineMiddleware(cb)
        mw.on_line("svc-a", "ERROR from a")
        mw.on_line("svc-a", "  continuation")
        mw.on_line("svc-b", "  still indented but different source")
        mw.flush()
        assert len(received) == 2
        assert received[0][0] == "svc-a"
        assert received[1][0] == "svc-b"

    def test_custom_join_str(self):
        received, cb = _collector()
        mw = MultilineMiddleware(cb, join_str=" | ")
        mw.on_line("app", "WARN header")
        mw.on_line("app", "  detail")
        mw.flush()
        assert received[0][1] == "WARN header | " + "  detail"

    def test_custom_continuation_pattern(self):
        received, cb = _collector()
        mw = MultilineMiddleware(cb, continuation_pattern=r"^\+")
        mw.on_line("app", "BEGIN")
        mw.on_line("app", "+more")
        mw.on_line("app", "+even more")
        mw.flush()
        assert len(received) == 1
        assert "BEGIN" in received[0][1]
        assert "+more" in received[0][1]
