"""Tests for :mod:`logpulse.tag`."""
from __future__ import annotations

from typing import List, Tuple, Optional

import pytest

from logpulse.tag import TagMiddleware


def _collector() -> Tuple[List, callable]:
    received: List[Tuple[str, str, dict]] = []

    def cb(source: str, line: str, meta: Optional[dict] = None) -> None:
        received.append((source, line, meta or {}))

    return received, cb


class TestTagMiddleware:
    def test_static_tags_added_to_meta(self):
        received, cb = _collector()
        mw = TagMiddleware(next_handler=cb, static_tags={"env": "prod", "app": "api"})
        mw("svc", "hello", {})
        assert received[0][2]["tags"] == {"env": "prod", "app": "api"}

    def test_dynamic_tag_evaluated_per_line(self):
        received, cb = _collector()
        mw = TagMiddleware(
            next_handler=cb,
            dynamic_tags={"length": lambda src, ln: str(len(ln))},
        )
        mw("svc", "hello", {})
        assert received[0][2]["tags"]["length"] == "5"

    def test_existing_meta_preserved(self):
        received, cb = _collector()
        mw = TagMiddleware(next_handler=cb, static_tags={"x": "1"})
        mw("svc", "line", {"other": "value"})
        assert received[0][2]["other"] == "value"
        assert received[0][2]["tags"]["x"] == "1"

    def test_none_meta_initialised_to_empty_dict(self):
        received, cb = _collector()
        mw = TagMiddleware(next_handler=cb, static_tags={"k": "v"})
        mw("svc", "line", None)
        assert "tags" in received[0][2]

    def test_tagged_count_increments(self):
        _, cb = _collector()
        mw = TagMiddleware(next_handler=cb, static_tags={"k": "v"})
        mw("s", "a", {})
        mw("s", "b", {})
        assert mw.tagged_count == 2

    def test_static_and_dynamic_merged(self):
        received, cb = _collector()
        mw = TagMiddleware(
            next_handler=cb,
            static_tags={"env": "test"},
            dynamic_tags={"src": lambda s, _l: s.upper()},
        )
        mw("web", "msg", {})
        tags = received[0][2]["tags"]
        assert tags["env"] == "test"
        assert tags["src"] == "WEB"

    def test_dynamic_tag_receives_correct_source_and_line(self):
        calls: list = []
        received, cb = _collector()
        mw = TagMiddleware(
            next_handler=cb,
            dynamic_tags={"info": lambda s, l: (calls.append((s, l)) or "ok")},
        )
        mw("myfile", "test line", {})
        assert calls == [("myfile", "test line")]

    def test_meta_not_mutated_in_place(self):
        """Original meta dict passed by caller must not be mutated."""
        received, cb = _collector()
        mw = TagMiddleware(next_handler=cb, static_tags={"k": "v"})
        original = {"keep": True}
        mw("s", "l", original)
        assert "tags" not in original
