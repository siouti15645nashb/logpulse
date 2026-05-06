"""Tests for logpulse.output_router.OutputRouter."""
from __future__ import annotations

import pytest

from logpulse.output_router import OutputRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collector():
    """Return (list, callback) where list accumulates (source, line) tuples."""
    received: list[tuple[str, str]] = []

    def cb(source: str, line: str) -> None:
        received.append((source, line))

    return received, cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOutputRouter:
    def test_no_sinks_route_returns_zero(self):
        router = OutputRouter()
        assert router.route("app.log", "hello") == 0

    def test_single_sink_receives_line(self):
        router = OutputRouter()
        received, cb = _collector()
        router.add_sink(cb)
        router.route("app.log", "hello world")
        assert received == [("app.log", "hello world")]

    def test_multiple_sinks_all_receive_line(self):
        router = OutputRouter()
        r1, cb1 = _collector()
        r2, cb2 = _collector()
        router.add_sink(cb1, name="a")
        router.add_sink(cb2, name="b")
        count = router.route("svc.log", "line")
        assert count == 2
        assert r1 == [("svc.log", "line")]
        assert r2 == [("svc.log", "line")]

    def test_remove_sink_by_name(self):
        router = OutputRouter()
        r1, cb1 = _collector()
        r2, cb2 = _collector()
        router.add_sink(cb1, name="stdout")
        router.add_sink(cb2, name="file")
        removed = router.remove_sink("stdout")
        assert removed == 1
        router.route("x.log", "msg")
        assert r1 == []
        assert r2 == [("x.log", "msg")]

    def test_remove_nonexistent_name_returns_zero(self):
        router = OutputRouter()
        assert router.remove_sink("ghost") == 0

    def test_remove_removes_all_with_same_name(self):
        router = OutputRouter()
        _, cb = _collector()
        router.add_sink(cb, name="dup")
        router.add_sink(cb, name="dup")
        removed = router.remove_sink("dup")
        assert removed == 2
        assert router.sink_count() == 0

    def test_sink_count_and_names(self):
        router = OutputRouter()
        _, cb = _collector()
        router.add_sink(cb, name="a")
        router.add_sink(cb)
        assert router.sink_count() == 2
        assert router.sink_names() == ["a", None]

    def test_broken_sink_does_not_prevent_others(self):
        router = OutputRouter()
        received, cb_good = _collector()

        def bad_cb(source, line):
            raise RuntimeError("boom")

        router.add_sink(bad_cb, name="bad")
        router.add_sink(cb_good, name="good")
        count = router.route("x.log", "test")
        # Only the good sink succeeded
        assert count == 1
        assert received == [("x.log", "test")]

    def test_callable_interface(self):
        router = OutputRouter()
        received, cb = _collector()
        router.add_sink(cb)
        result = router("a.log", "via call")
        assert result == 1
        assert received == [("a.log", "via call")]
