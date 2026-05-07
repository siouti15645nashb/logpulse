"""Integration tests: Pipeline with multiline middleware."""
from __future__ import annotations

import pytest

from logpulse.pipeline import Pipeline


def _sink():
    received: list[tuple[str, str]] = []

    def cb(source: str, line: str) -> None:
        received.append((source, line))

    return received, cb


class TestPipelineMultiline:
    def test_build_returns_callable(self):
        received, cb = _sink()
        pipeline = Pipeline(cb).with_multiline()
        assert callable(pipeline.build())

    def test_multiline_property_set_after_with_multiline(self):
        received, cb = _sink()
        p = Pipeline(cb).with_multiline()
        assert p.multiline is not None

    def test_multiline_property_none_without_registration(self):
        received, cb = _sink()
        p = Pipeline(cb)
        assert p.multiline is None

    def test_flush_emits_buffered_lines(self):
        received, cb = _sink()
        pipeline = Pipeline(cb).with_multiline()
        fn = pipeline.build()
        fn("app", "ERROR root cause")
        fn("app", "  at frame1")
        assert received == []  # not yet flushed
        pipeline.flush()
        assert len(received) == 1
        assert "ERROR root cause" in received[0][1]
        assert "at frame1" in received[0][1]

    def test_flush_noop_when_no_multiline(self):
        received, cb = _sink()
        pipeline = Pipeline(cb)
        pipeline.flush()  # must not raise

    def test_multiline_with_dedupe_chain(self):
        """Multiline folding then deduplication: identical folded events suppressed."""
        received, cb = _sink()
        pipeline = Pipeline(cb).with_dedupe(window=60).with_multiline()
        fn = pipeline.build()

        fn("app", "ERROR repeated")
        fn("app", "  detail")
        pipeline.flush()

        # send identical event again
        fn("app", "ERROR repeated")
        fn("app", "  detail")
        pipeline.flush()

        # dedupe should suppress the second identical folded event
        assert len(received) == 1

    def test_continuation_pattern_respected(self):
        received, cb = _sink()
        pipeline = Pipeline(cb).with_multiline(continuation_pattern=r"^\+")
        fn = pipeline.build()
        fn("svc", "START")
        fn("svc", "+extra")
        fn("svc", "NEXT")
        pipeline.flush()
        assert len(received) == 2
        assert "+extra" in received[0][1]
        assert received[1][1] == "NEXT"

    def test_max_lines_respected(self):
        received, cb = _sink()
        pipeline = Pipeline(cb).with_multiline(max_lines=2)
        fn = pipeline.build()
        fn("app", "HEAD")
        fn("app", "  c1")  # buffer: HEAD, c1  (size == max_lines)
        fn("app", "  c2")  # triggers flush of [HEAD, c1]; c2 starts new buffer
        pipeline.flush()   # flushes [c2]
        assert len(received) == 2
