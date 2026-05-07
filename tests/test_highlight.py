"""Tests for logpulse.highlight."""
from __future__ import annotations

from typing import List, Tuple

import pytest

from logpulse.highlight import HighlightMiddleware, HighlightRule, _COLOURS, _RESET


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
# HighlightRule unit tests
# ---------------------------------------------------------------------------

class TestHighlightRule:
    def test_wraps_match_in_colour(self):
        rule = HighlightRule(pattern="ERROR", colour_index=0)
        result = rule.apply("[ERROR] something broke")
        assert f"{_COLOURS[0]}ERROR{_RESET}" in result

    def test_non_matching_text_unchanged(self):
        rule = HighlightRule(pattern="ERROR")
        assert rule.apply("all good here") == "all good here"

    def test_multiple_occurrences_all_wrapped(self):
        rule = HighlightRule(pattern="x")
        result = rule.apply("x and x")
        assert result.count(_RESET) == 2

    def test_colour_index_wraps_around(self):
        rule = HighlightRule(pattern="a", colour_index=len(_COLOURS) + 1)
        # should not raise and colour_index is within bounds
        assert 0 <= rule.colour_index < len(_COLOURS)

    def test_regex_group_supported(self):
        rule = HighlightRule(pattern=r"\d+", colour_index=1)
        result = rule.apply("code 404 returned")
        assert f"{_COLOURS[1]}404{_RESET}" in result


# ---------------------------------------------------------------------------
# HighlightMiddleware tests
# ---------------------------------------------------------------------------

class TestHighlightMiddleware:
    def test_no_rules_passes_through_unchanged(self):
        out = _collector()
        mw = HighlightMiddleware(cb(out))
        mw("app", "hello world")
        assert out == [("app", "hello world")]

    def test_matching_rule_modifies_line(self):
        out = _collector()
        mw = HighlightMiddleware(cb(out))
        mw.add_rule("WARN", colour_index=0)
        mw("svc", "WARN: low disk")
        _, line = out[0]
        assert _COLOURS[0] in line
        assert "WARN" in line

    def test_non_matching_rule_leaves_line_intact(self):
        out = _collector()
        mw = HighlightMiddleware(cb(out))
        mw.add_rule("ERROR")
        mw("svc", "all systems nominal")
        assert out[0][1] == "all systems nominal"

    def test_highlighted_count_increments_only_on_match(self):
        out = _collector()
        mw = HighlightMiddleware(cb(out))
        mw.add_rule("ERROR")
        mw("a", "no match here")
        mw("a", "ERROR occurred")
        mw("a", "another ERROR")
        assert mw.highlighted_count == 2

    def test_multiple_rules_applied_in_order(self):
        out = _collector()
        mw = HighlightMiddleware(cb(out))
        mw.add_rule("ERROR", colour_index=0)
        mw.add_rule("404", colour_index=1)
        mw("svc", "ERROR 404 not found")
        _, line = out[0]
        assert _COLOURS[0] in line
        assert _COLOURS[1] in line

    def test_disabled_middleware_passes_raw_line(self):
        out = _collector()
        mw = HighlightMiddleware(cb(out), enabled=False)
        mw.add_rule("ERROR")
        mw("svc", "ERROR: boom")
        assert out[0][1] == "ERROR: boom"
        assert mw.highlighted_count == 0

    def test_source_forwarded_unchanged(self):
        out = _collector()
        mw = HighlightMiddleware(cb(out))
        mw("my-service", "line")
        assert out[0][0] == "my-service"
