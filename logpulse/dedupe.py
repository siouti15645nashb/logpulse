"""Deduplication middleware that suppresses repeated identical log lines."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Callable, Optional


class DedupeMiddleware:
    """Wraps a line callback and suppresses duplicate lines within a time window.

    A line is considered a duplicate if the same (source, text) pair was seen
    within *window_seconds*.  After the window expires the line is allowed
    through again.

    Parameters
    ----------
    callback:       downstream handler called with (source, line).
    window_seconds: how long (seconds) to remember a seen line.  Default 5 s.
    max_cache:      maximum number of distinct lines kept in memory.
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        window_seconds: float = 5.0,
        max_cache: int = 1024,
    ) -> None:
        self._callback = callback
        self._window = window_seconds
        self._max_cache = max_cache
        # OrderedDict keeps insertion order so we can evict oldest entries.
        self._seen: OrderedDict[tuple[str, str], float] = OrderedDict()
        self._suppressed: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def on_line(self, source: str, line: str) -> None:
        """Process a single log line, forwarding it only if it is not a duplicate."""
        key = (source, line)
        now = time.monotonic()

        last_seen: Optional[float] = self._seen.get(key)
        if last_seen is not None and (now - last_seen) < self._window:
            self._suppressed += 1
            return

        # Update / insert timestamp, move to end so eviction targets oldest.
        self._seen[key] = now
        self._seen.move_to_end(key)

        # Evict oldest entries when cache is full.
        while len(self._seen) > self._max_cache:
            self._seen.popitem(last=False)

        self._callback(source, line)

    # Alias so the middleware is a drop-in replacement for a plain callable.
    def __call__(self, source: str, line: str) -> None:
        self.on_line(source, line)

    @property
    def suppressed_count(self) -> int:
        """Total number of lines suppressed since creation."""
        return self._suppressed

    def _expire(self, now: Optional[float] = None) -> None:
        """Remove stale entries (exposed for testing)."""
        cutoff = (now if now is not None else time.monotonic()) - self._window
        stale = [k for k, ts in self._seen.items() if ts < cutoff]
        for k in stale:
            del self._seen[k]
