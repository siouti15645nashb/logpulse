"""Tests for logpulse.truncate.TruncateMiddleware."""

from __future__ import annotations

from typing import List, Tuple

import pytest

from logpulse.truncate import TruncateMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collector() -> List[Tuple[str, str]]:
    return []


def cb(collected: List[Tuple[str, str]]) -> object:
    def _cb(source: str, line: str) -> None:
        collected.append((source, line))
    return _cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTruncateMiddleware:
    def test_short_line_passes_unchanged(self):
        out: List[Tuple[str, str]] = _collector()
        mw = TruncateMiddleware(cb(out), max_length=50)
        mw("app", "hello world")
        assert out == [("app", "hello world")]

    def test_line_exactly_at_limit_passes_unchanged(self):
        out: List[Tuple[str, str]] = _collector()
        mw = TruncateMiddleware(cb(out), max_length=10)
        mw("app", "1234567890")
        assert out == [("app", "1234567890")]

    def test_long_line_is_truncated(self):
        out: List[Tuple[str, str]] = _collector()
        suffix = " […]"
        mw = TruncateMiddleware(cb(out), max_length=20, suffix=suffix)
        long_line = "A" * 30
        mw("svc", long_line)
        assert len(out) == 1
        source, line = out[0]
        assert source == "svc"
        assert len(line) == 20
        assert line.endswith(suffix)

    def test_truncated_count_increments(self):
        out: List[Tuple[str, str]] = _collector()
        mw = TruncateMiddleware(cb(out), max_length=10)
        mw("x", "short")
        mw("x", "this is definitely longer than ten characters")
        mw("x", "also very long indeed yes")
        assert mw.truncated_count == 2

    def test_truncated_count_zero_when_no_truncation(self):
        out: List[Tuple[str, str]] = _collector()
        mw = TruncateMiddleware(cb(out), max_length=100)
        mw("x", "tiny")
        assert mw.truncated_count == 0

    def test_custom_suffix_used(self):
        out: List[Tuple[str, str]] = _collector()
        mw = TruncateMiddleware(cb(out), max_length=15, suffix="...")
        mw("svc", "123456789012345678")
        _, line = out[0]
        assert line.endswith("...")
        assert len(line) == 15

    def test_invalid_max_length_raises(self):
        with pytest.raises(ValueError, match="max_length"):
            TruncateMiddleware(lambda s, l: None, max_length=3, suffix=" […]")

    def test_callable_interface(self):
        """Instance should be directly callable (duck-type compatible)."""
        out: List[Tuple[str, str]] = _collector()
        mw = TruncateMiddleware(cb(out), max_length=50)
        mw("src", "line")
        assert len(out) == 1

    def test_multiple_sources_tracked_independently(self):
        out: List[Tuple[str, str]] = _collector()
        mw = TruncateMiddleware(cb(out), max_length=10)
        mw("a", "short")
        mw("b", "this is way too long for the limit")
        assert out[0] == ("a", "short")
        assert out[1][0] == "b"
        assert len(out[1][1]) == 10
