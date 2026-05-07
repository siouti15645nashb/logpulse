"""Middleware that truncates log lines exceeding a configured byte length."""

from __future__ import annotations

from typing import Callable


class TruncateMiddleware:
    """Pass lines through, truncating any that exceed *max_length* bytes.

    Truncated lines receive a configurable suffix (default ``" […]"``) so
    readers can tell the line was cut.  The suffix is always included in the
    final length, so the output never exceeds *max_length* characters.

    Parameters
    ----------
    callback:
        Downstream callable that receives ``(source, line)``.
    max_length:
        Maximum number of characters allowed per line.  Must be greater than
        the length of *suffix*.
    suffix:
        String appended to truncated lines.  Defaults to ``" […]"``.
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        max_length: int = 200,
        suffix: str = " […]",
    ) -> None:
        if max_length <= len(suffix):
            raise ValueError(
                f"max_length ({max_length}) must be greater than "
                f"suffix length ({len(suffix)})"
            )
        self._callback = callback
        self._max_length = max_length
        self._suffix = suffix
        self._truncated_count = 0

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def truncated_count(self) -> int:
        """Total number of lines that have been truncated so far."""
        return self._truncated_count

    def on_line(self, source: str, line: str) -> None:
        """Process a single *line* from *source*."""
        if len(line) > self._max_length:
            cut = self._max_length - len(self._suffix)
            line = line[:cut] + self._suffix
            self._truncated_count += 1
        self._callback(source, line)

    def __call__(self, source: str, line: str) -> None:  # noqa: D401
        """Alias for :meth:`on_line` so the instance is directly callable."""
        self.on_line(source, line)
