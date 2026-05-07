"""Tests for logpulse.redact."""
from __future__ import annotations

import pytest

from logpulse.redact import RedactMiddleware, RedactRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collector():
    received: list[tuple[str, str]] = []

    def cb(source: str, line: str) -> None:
        received.append((source, line))

    return received, cb


# ---------------------------------------------------------------------------
# RedactRule
# ---------------------------------------------------------------------------

class TestRedactRule:
    def test_replaces_match_with_default_placeholder(self):
        rule = RedactRule(pattern=r"\d{4}-\d{4}-\d{4}-\d{4}")
        result = rule.apply("card: 1234-5678-9012-3456 charged")
        assert result == "card: [REDACTED] charged"

    def test_custom_replacement(self):
        rule = RedactRule(pattern=r"password=\S+", replacement="password=***")
        result = rule.apply("login password=secret123 ok")
        assert result == "login password=*** ok"

    def test_no_match_returns_line_unchanged(self):
        rule = RedactRule(pattern=r"SECRET")
        original = "nothing sensitive here"
        assert rule.apply(original) == original

    def test_multiple_matches_in_one_line(self):
        rule = RedactRule(pattern=r"\b\d{3}-\d{2}-\d{4}\b", replacement="[SSN]")
        result = rule.apply("ssn 123-45-6789 and 987-65-4321")
        assert result == "ssn [SSN] and [SSN]"


# ---------------------------------------------------------------------------
# RedactMiddleware
# ---------------------------------------------------------------------------

class TestRedactMiddleware:
    def test_line_without_match_passes_unchanged(self):
        received, cb = _collector()
        mw = RedactMiddleware(callback=cb, rules=[RedactRule(pattern=r"SECRET")])
        mw("app", "hello world")
        assert received == [("app", "hello world")]

    def test_matching_line_is_redacted_before_forwarding(self):
        received, cb = _collector()
        rule = RedactRule(pattern=r"token=\S+", replacement="token=[REDACTED]")
        mw = RedactMiddleware(callback=cb, rules=[rule])
        mw("svc", "auth token=abc123 accepted")
        assert received == [("svc", "auth token=[REDACTED] accepted")]

    def test_redacted_count_increments_only_when_changed(self):
        received, cb = _collector()
        rule = RedactRule(pattern=r"\d+")
        mw = RedactMiddleware(callback=cb, rules=[rule])
        mw("src", "no digits here")
        mw("src", "port 8080 open")
        assert mw.redacted_count == 1

    def test_multiple_rules_applied_in_order(self):
        received, cb = _collector()
        rules = [
            RedactRule(pattern=r"user=\S+", replacement="user=[U]"),
            RedactRule(pattern=r"pass=\S+", replacement="pass=[P]"),
        ]
        mw = RedactMiddleware(callback=cb, rules=rules)
        mw("db", "connect user=admin pass=s3cr3t")
        assert received == [("db", "connect user=[U] pass=[P]")]

    def test_add_rule_extends_active_rules(self):
        received, cb = _collector()
        mw = RedactMiddleware(callback=cb)
        mw.add_rule(RedactRule(pattern=r"key=\S+"))
        mw("cfg", "loaded key=mysecret")
        assert "[REDACTED]" in received[0][1]

    def test_no_rules_passes_all_lines(self):
        received, cb = _collector()
        mw = RedactMiddleware(callback=cb)
        mw("x", "some line")
        assert received == [("x", "some line")]
        assert mw.redacted_count == 0

    def test_source_label_preserved(self):
        received, cb = _collector()
        mw = RedactMiddleware(callback=cb, rules=[RedactRule(pattern=r"\d+")])
        mw("myapp", "error code 42")
        assert received[0][0] == "myapp"
