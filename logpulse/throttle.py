"""Throttle middleware: suppress repeated identical lines within a time window.

Unlike DedupeMiddleware (which suppresses consecutive duplicates), ThrottleMiddleware
silences any line matching a given pattern if it has been seen more than `max_count`
times within a rolling `window_seconds` interval.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, Optional


@dataclass
class _LineWindow:
    """Sliding window of timestamps for a single line key."""
    timestamps: Deque[float] = field(default_factory=deque)

    def record(self, now: float, window: float) -> None:
        self._evict(now, window)
        self.timestamps.append(now)

    def count(self, now: float, window: float) -> int:
        self._evict(now, window)
        return len(self.timestamps)

    def _evict(self, now: float, window: float) -> None:
        cutoff = now - window
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()


class ThrottleMiddleware:
    """Pass lines through unless they exceed max_count within window_seconds.

    Parameters
    ----------
    callback:       downstream handler receiving (source, line) pairs.
    max_count:      maximum occurrences allowed within the window (default 5).
    window_seconds: rolling window length in seconds (default 10.0).
    pattern:        optional regex; only lines matching it are throttled.
                    Lines that do *not* match are always forwarded.
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        max_count: int = 5,
        window_seconds: float = 10.0,
        pattern: Optional[str] = None,
    ) -> None:
        self._callback = callback
        self._max_count = max_count
        self._window = window_seconds
        self._pattern: Optional[re.Pattern[str]] = (
            re.compile(pattern) if pattern else None
        )
        self._windows: Dict[str, _LineWindow] = defaultdict(_LineWindow)
        self._throttled_count = 0

    # Support being passed directly as a callback
    def __call__(self, source: str, line: str) -> None:
        self.on_line(source, line)

    def on_line(self, source: str, line: str) -> None:
        if self._pattern and not self._pattern.search(line):
            self._callback(source, line)
            return

        key = f"{source}\x00{line}"
        now = time.monotonic()
        win = self._windows[key]
        win.record(now, self._window)

        if win.count(now, self._window) <= self._max_count:
            self._callback(source, line)
        else:
            self._throttled_count += 1

    @property
    def throttled_count(self) -> int:
        """Total number of lines suppressed by throttling."""
        return self._throttled_count
