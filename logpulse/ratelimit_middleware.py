"""Middleware that wraps an on_line callback with rate limiting."""
from __future__ import annotations

from typing import Callable, Optional

from logpulse.ratelimit import RateLimiter

OnLineFn = Callable[[str, str], None]

_SUPPRESSED_TEMPLATE = (
    "[logpulse] rate limit reached for '{source}': "
    "{dropped} line(s) suppressed"
)


class RateLimitMiddleware:
    """Wraps an *on_line* callback and drops lines that exceed the rate limit.

    When lines are suppressed a single summary message is emitted to *on_line*
    once the source falls back below the limit.

    Args:
        callback:    The downstream on_line(source, line) handler.
        max_lines:   Lines allowed per *window* seconds per source.
        window:      Sliding window length in seconds.
        warn_cb:     Optional callback for suppression warnings; defaults to
                     forwarding the warning through *callback* itself.
    """

    def __init__(
        self,
        callback: OnLineFn,
        max_lines: int,
        window: float = 1.0,
        warn_cb: Optional[OnLineFn] = None,
    ) -> None:
        self._cb = callback
        self._warn_cb: OnLineFn = warn_cb if warn_cb is not None else callback
        self._limiter = RateLimiter(max_lines=max_lines, window=window)
        self._dropped: dict[str, int] = {}

    # ------------------------------------------------------------------
    def __call__(self, source: str, line: str) -> None:
        self.on_line(source, line)

    def on_line(self, source: str, line: str) -> None:
        """Process a single log line from *source*."""
        if self._limiter.allow(source):
            # If we were suppressing, emit a summary first.
            if self._dropped.get(source, 0) > 0:
                msg = _SUPPRESSED_TEMPLATE.format(
                    source=source, dropped=self._dropped[source]
                )
                self._warn_cb(source, msg)
                self._dropped[source] = 0
            self._cb(source, line)
        else:
            self._dropped[source] = self._dropped.get(source, 0) + 1

    def dropped_count(self, source: str) -> int:
        """Return the number of currently-pending suppressed lines for *source*."""
        return self._dropped.get(source, 0)

    def flush_warnings(self) -> None:
        """Emit suppression warnings for all sources that have pending drops."""
        for source, count in list(self._dropped.items()):
            if count > 0:
                msg = _SUPPRESSED_TEMPLATE.format(source=source, dropped=count)
                self._warn_cb(source, msg)
                self._dropped[source] = 0
