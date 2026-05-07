"""Sampling middleware: passes only 1-in-N lines to reduce high-volume noise."""
from __future__ import annotations

from typing import Callable


class SamplingMiddleware:
    """Passes every *nth* line to the downstream callback and drops the rest.

    Parameters
    ----------
    callback:
        Downstream handler that receives sampled lines.
    rate:
        Keep 1 line out of every *rate* lines.  Must be >= 1.
        A rate of 1 means every line is forwarded (no sampling).
    """

    def __init__(self, callback: Callable[[str, str], None], rate: int = 10) -> None:
        if rate < 1:
            raise ValueError(f"rate must be >= 1, got {rate}")
        self._callback = callback
        self._rate = rate
        self._counters: dict[str, int] = {}
        self._dropped: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def on_line(self, source: str, line: str) -> None:
        """Receive a line; forward it only when the per-source counter hits *rate*."""
        count = self._counters.get(source, 0) + 1
        self._counters[source] = count

        if count % self._rate == 1:  # 1st, (rate+1)th, (2*rate+1)th …
            self._callback(source, line)
        else:
            self._dropped += 1

    def __call__(self, source: str, line: str) -> None:  # callable protocol
        self.on_line(source, line)

    @property
    def dropped_count(self) -> int:
        """Total number of lines dropped since creation."""
        return self._dropped

    @property
    def rate(self) -> int:
        """The configured sampling rate."""
        return self._rate

    def reset_counters(self) -> None:
        """Reset per-source counters (useful for testing or periodic resets)."""
        self._counters.clear()
        self._dropped = 0
