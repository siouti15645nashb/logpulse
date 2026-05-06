"""Rate limiting for log line output to prevent flooding."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class _Bucket:
    """Sliding-window counter for a single source."""
    window: float
    max_lines: int
    timestamps: Deque[float] = field(default_factory=deque)

    def allow(self, now: float | None = None) -> bool:
        """Return True if the line should be passed through."""
        now = now if now is not None else time.monotonic()
        cutoff = now - self.window
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.max_lines:
            return False
        self.timestamps.append(now)
        return True

    def current_rate(self, now: float | None = None) -> float:
        """Return lines-per-second over the current window."""
        now = now if now is not None else time.monotonic()
        cutoff = now - self.window
        active = sum(1 for t in self.timestamps if t >= cutoff)
        return active / self.window if self.window > 0 else 0.0


class RateLimiter:
    """Per-source sliding-window rate limiter.

    Args:
        max_lines: Maximum number of lines allowed per *window* seconds.
        window:    Length of the sliding window in seconds (default 1.0).
    """

    def __init__(self, max_lines: int, window: float = 1.0) -> None:
        if max_lines <= 0:
            raise ValueError("max_lines must be positive")
        if window <= 0:
            raise ValueError("window must be positive")
        self._max_lines = max_lines
        self._window = window
        self._buckets: Dict[str, _Bucket] = {}

    def allow(self, source: str, now: float | None = None) -> bool:
        """Return True if *source* has not exceeded its rate limit."""
        if source not in self._buckets:
            self._buckets[source] = _Bucket(
                window=self._window, max_lines=self._max_lines
            )
        return self._buckets[source].allow(now)

    def current_rate(self, source: str, now: float | None = None) -> float:
        """Return the current line rate (lines/sec) for *source*."""
        if source not in self._buckets:
            return 0.0
        return self._buckets[source].current_rate(now)

    def reset(self, source: str) -> None:
        """Clear the bucket for *source*."""
        self._buckets.pop(source, None)

    def reset_all(self) -> None:
        """Clear all buckets."""
        self._buckets.clear()
