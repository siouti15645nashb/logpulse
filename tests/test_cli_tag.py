"""Tests for :mod:`logpulse.cli_tag`."""
from __future__ import annotations

import argparse
from typing import List, Tuple, Optional

import pytest

from logpulse.cli_tag import add_tag_args, wrap_with_tag, _parse_tag_spec
from logpulse.tag import TagMiddleware


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"tags": []}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _noop(source: str, line: str, meta: Optional[dict] = None) -> None:
    pass


class TestAddTagArgs:
    def test_registers_tag_argument(self):
        parser = argparse.ArgumentParser()
        add_tag_args(parser)
        ns = parser.parse_args(["--tag", "env=prod"])
        assert ns.tags == ["env=prod"]

    def test_tag_argument_repeatable(self):
        parser = argparse.ArgumentParser()
        add_tag_args(parser)
        ns = parser.parse_args(["--tag", "env=prod", "--tag", "app=api"])
        assert ns.tags == ["env=prod", "app=api"]

    def test_default_is_empty_list(self):
        parser = argparse.ArgumentParser()
        add_tag_args(parser)
        ns = parser.parse_args([])
        assert ns.tags == []


class TestParseTagSpec:
    def test_simple_key_value(self):
        assert _parse_tag_spec("env=prod") == ("env", "prod")

    def test_value_with_equals_sign(self):
        key, value = _parse_tag_spec("url=http://x.com/a=b")
        assert key == "url"
        assert value == "http://x.com/a=b"

    def test_missing_equals_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_tag_spec("noequals")


class TestWrapWithTag:
    def test_no_tags_returns_handler_unchanged(self):
        args = _make_args(tags=[])
        result = wrap_with_tag(args, _noop)
        assert result is _noop

    def test_with_tags_returns_tag_middleware(self):
        args = _make_args(tags=["env=prod"])
        result = wrap_with_tag(args, _noop)
        assert isinstance(result, TagMiddleware)

    def test_static_tags_populated(self):
        args = _make_args(tags=["env=prod", "app=api"])
        mw = wrap_with_tag(args, _noop)
        assert isinstance(mw, TagMiddleware)
        assert mw.static_tags == {"env": "prod", "app": "api"}

    def test_next_handler_set_correctly(self):
        args = _make_args(tags=["k=v"])
        mw = wrap_with_tag(args, _noop)
        assert isinstance(mw, TagMiddleware)
        assert mw.next_handler is _noop
