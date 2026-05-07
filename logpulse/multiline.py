"""Multiline log folding middleware.

Collapses continuation lines (e.g. Java stack traces, Python tracebacks)
into a single logical event before passing it downstream.
"""
from __future__ import annotations

import re
from typing import Callable, Optional


class MultilineMiddleware:
    """Buffer lines that match *continuation_pattern* and flush them as one.

    A line that does NOT match *continuation_pattern* is treated as the start
    of a new event.  The previous buffered event (if any) is flushed first.

    Parameters
    ----------
    callback:
        Downstream callable that receives ``(source, line)``.
    continuation_pattern:
        Regex; a line matching this is appended to the current buffer instead
        of starting a new event.  Defaults to lines that begin with whitespace
        (common for stack traces).
    max_lines:
        Hard cap on how many lines a single event may span.  When reached the
        buffer is flushed and the current line starts a fresh event.
    join_str:
        String used to join buffered lines when flushing.  Defaults to ``\\n``.
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        continuation_pattern: str = r"^\s+",
        max_lines: int = 50,
        join_str: str = "\n",
    ) -> None:
        self._callback = callback
        self._pattern: re.Pattern[str] = re.compile(continuation_pattern)
        self._max_lines = max_lines
        self._join_str = join_str
        self._buffer: list[str] = []
        self._source: Optional[str] = None
        self._folded_count = 0

    # ------------------------------------------------------------------
    def on_line(self, source: str, line: str) -> None:
        is_continuation = bool(self._pattern.match(line))
        buffer_full = len(self._buffer) >= self._max_lines
        source_changed = self._source is not None and source != self._source

        if self._buffer and (not is_continuation or buffer_full or source_changed):
            self._flush()

        if is_continuation and not source_changed:
            self._buffer.append(line)
            self._source = source
            self._folded_count += 1
        else:
            self._buffer = [line]
            self._source = source

    def __call__(self, source: str, line: str) -> None:
        self.on_line(source, line)

    def flush(self) -> None:
        """Force-flush any buffered lines (call at end of tailing session)."""
        if self._buffer:
            self._flush()

    @property
    def folded_count(self) -> int:
        """Total number of continuation lines that were folded."""
        return self._folded_count

    # ------------------------------------------------------------------
    def _flush(self) -> None:
        combined = self._join_str.join(self._buffer)
        assert self._source is not None
        self._callback(self._source, combined)
        self._buffer = []
        self._source = None
