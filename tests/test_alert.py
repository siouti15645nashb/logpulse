"""Tests for logpulse.alert."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from logpulse.alert import AlertManager, AlertRule


# ---------------------------------------------------------------------------
# AlertRule
# ---------------------------------------------------------------------------

class TestAlertRule:
    def test_matches_returns_true_for_matching_line(self):
        rule = AlertRule("err", r"ERROR", threshold=1, window_seconds=5)
        assert rule.matches("2024-01-01 ERROR something went wrong")

    def test_matches_returns_false_for_non_matching_line(self):
        rule = AlertRule("err", r"ERROR", threshold=1, window_seconds=5)
        assert not rule.matches("INFO all good")

    def test_pattern_is_compiled_as_regex(self):
        rule = AlertRule("warn", r"WARN(ING)?", threshold=1, window_seconds=5)
        assert rule.matches("WARNING: disk low")
        assert rule.matches("WARN: disk low")


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------

@pytest.fixture()
def callback():
    return MagicMock()


@pytest.fixture()
def simple_rule():
    return AlertRule("err", r"ERROR", threshold=3, window_seconds=10)


class TestAlertManager:
    def test_no_alert_below_threshold(self, simple_rule, callback):
        mgr = AlertManager([simple_rule], callback)
        mgr.feed("app.log", "ERROR one")
        mgr.feed("app.log", "ERROR two")
        callback.assert_not_called()

    def test_alert_fires_at_threshold(self, simple_rule, callback):
        mgr = AlertManager([simple_rule], callback)
        for i in range(3):
            mgr.feed("app.log", f"ERROR {i}")
        callback.assert_called_once()
        rule_arg, source_arg, count_arg = callback.call_args.args
        assert rule_arg.name == "err"
        assert source_arg == "app.log"
        assert count_arg == 3

    def test_window_resets_after_alert(self, simple_rule, callback):
        mgr = AlertManager([simple_rule], callback)
        for i in range(3):
            mgr.feed("app.log", f"ERROR {i}")
        assert callback.call_count == 1
        # Feed two more — should NOT fire again (window was cleared)
        mgr.feed("app.log", "ERROR again")
        mgr.feed("app.log", "ERROR again")
        assert callback.call_count == 1

    def test_non_matching_lines_do_not_count(self, simple_rule, callback):
        mgr = AlertManager([simple_rule], callback)
        for _ in range(5):
            mgr.feed("app.log", "INFO everything fine")
        callback.assert_not_called()

    def test_reset_clears_specific_rule(self, simple_rule, callback):
        mgr = AlertManager([simple_rule], callback)
        mgr.feed("app.log", "ERROR one")
        mgr.feed("app.log", "ERROR two")
        mgr.reset("err")
        mgr.feed("app.log", "ERROR three")
        # Only one match after reset — should not fire
        callback.assert_not_called()

    def test_multiple_rules_independent(self, callback):
        r1 = AlertRule("err", r"ERROR", threshold=2, window_seconds=10)
        r2 = AlertRule("warn", r"WARN", threshold=2, window_seconds=10)
        mgr = AlertManager([r1, r2], callback)
        mgr.feed("app.log", "ERROR x")
        mgr.feed("app.log", "WARN x")
        mgr.feed("app.log", "ERROR y")  # fires r1
        assert callback.call_count == 1
        assert callback.call_args.args[0].name == "err"
