"""Tests for logpulse.cli_redact."""
from __future__ import annotations

import argparse

import pytest

from logpulse.cli_redact import add_redact_args, wrap_with_redact
from logpulse.redact import RedactMiddleware


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"redact": [], "redact_replacement": "[REDACTED]"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _noop(source: str, line: str) -> None:
    pass


class TestAddRedactArgs:
    def test_registers_redact_argument(self):
        parser = argparse.ArgumentParser()
        add_redact_args(parser)
        ns = parser.parse_args(["--redact", r"\d+"])
        assert ns.redact == [r"\d+"]

    def test_registers_redact_replacement_argument(self):
        parser = argparse.ArgumentParser()
        add_redact_args(parser)
        ns = parser.parse_args(["--redact", "X", "--redact-replacement", "***"])
        assert ns.redact_replacement == "***"

    def test_default_replacement_is_redacted(self):
        parser = argparse.ArgumentParser()
        add_redact_args(parser)
        ns = parser.parse_args([])
        assert ns.redact_replacement == "[REDACTED]"

    def test_multiple_redact_patterns_collected(self):
        parser = argparse.ArgumentParser()
        add_redact_args(parser)
        ns = parser.parse_args(["--redact", "A", "--redact", "B"])
        assert ns.redact == ["A", "B"]


class TestWrapWithRedact:
    def test_no_patterns_returns_original_callback(self):
        args = _make_args(redact=[])
        result = wrap_with_redact(args, _noop)
        assert result is _noop

    def test_with_patterns_returns_middleware(self):
        args = _make_args(redact=[r"\d+"])
        result = wrap_with_redact(args, _noop)
        assert isinstance(result, RedactMiddleware)

    def test_middleware_uses_custom_replacement(self):
        received: list[tuple[str, str]] = []

        def cb(src, line):
            received.append((src, line))

        args = _make_args(redact=[r"\d+"], redact_replacement="NUM")
        mw = wrap_with_redact(args, cb)
        mw("s", "value 42")
        assert received[0][1] == "value NUM"

    def test_middleware_applies_all_patterns(self):
        received: list[tuple[str, str]] = []

        def cb(src, line):
            received.append((src, line))

        args = _make_args(redact=[r"user=\S+", r"pass=\S+"])
        mw = wrap_with_redact(args, cb)
        mw("db", "connect user=admin pass=secret")
        assert "[REDACTED]" in received[0][1]
        assert received[0][1].count("[REDACTED]") == 2
