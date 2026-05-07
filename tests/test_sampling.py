"""Tests for logpulse.sampling.SamplingMiddleware."""
from __future__ import annotations

import pytest

from logpulse.sampling import SamplingMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collector():
    received: list[tuple[str, str]] = []

    def cb(source: str, line: str) -> None:
        received.append((source, line))

    return received, cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSamplingMiddleware:
    def test_rate_one_passes_every_line(self):
        received, cb = _collector()
        mw = SamplingMiddleware(cb, rate=1)
        for i in range(5):
            mw.on_line("app", f"line {i}")
        assert len(received) == 5
        assert mw.dropped_count == 0

    def test_rate_two_passes_every_other_line(self):
        received, cb = _collector()
        mw = SamplingMiddleware(cb, rate=2)
        for i in range(6):
            mw.on_line("app", f"line {i}")
        # lines 0, 2, 4 should pass (counter 1, 3, 5 → odd → count%2==1)
        assert len(received) == 3
        assert mw.dropped_count == 3

    def test_rate_ten_passes_one_in_ten(self):
        received, cb = _collector()
        mw = SamplingMiddleware(cb, rate=10)
        for i in range(100):
            mw.on_line("svc", f"msg {i}")
        assert len(received) == 10
        assert mw.dropped_count == 90

    def test_counters_are_per_source(self):
        received, cb = _collector()
        mw = SamplingMiddleware(cb, rate=3)
        # Each source has its own counter; first line of each source passes.
        mw.on_line("a", "a-line-1")
        mw.on_line("b", "b-line-1")
        mw.on_line("a", "a-line-2")
        mw.on_line("b", "b-line-2")
        sources_passed = [src for src, _ in received]
        # Both sources should have their first line forwarded.
        assert sources_passed.count("a") == 1
        assert sources_passed.count("b") == 1

    def test_callable_protocol(self):
        received, cb = _collector()
        mw = SamplingMiddleware(cb, rate=1)
        mw("web", "hello")
        assert received == [("web", "hello")]

    def test_invalid_rate_raises(self):
        _, cb = _collector()
        with pytest.raises(ValueError, match="rate must be >= 1"):
            SamplingMiddleware(cb, rate=0)

    def test_reset_counters_clears_state(self):
        received, cb = _collector()
        mw = SamplingMiddleware(cb, rate=5)
        for i in range(5):
            mw.on_line("app", f"line {i}")
        assert mw.dropped_count == 4
        mw.reset_counters()
        assert mw.dropped_count == 0
        # After reset the next line should pass again (counter restarts).
        mw.on_line("app", "after-reset")
        assert received[-1] == ("app", "after-reset")

    def test_rate_property(self):
        _, cb = _collector()
        mw = SamplingMiddleware(cb, rate=7)
        assert mw.rate == 7
