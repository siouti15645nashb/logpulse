"""Per-source line statistics tracker for logpulse."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SourceStats:
    """Statistics for a single log source."""

    total_lines: int = 0
    matched_lines: int = 0
    last_seen: Optional[float] = None

    def record(self, matched: bool) -> None:
        self.total_lines += 1
        if matched:
            self.matched_lines += 1
        self.last_seen = time.time()

    @property
    def drop_rate(self) -> float:
        """Fraction of lines that did NOT match (were filtered out)."""
        if self.total_lines == 0:
            return 0.0
        return (self.total_lines - self.matched_lines) / self.total_lines


class StatsTracker:
    """Thread-safe aggregator of per-source line statistics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: Dict[str, SourceStats] = {}

    def record(self, source: str, matched: bool) -> None:
        """Record a line event for *source*."""
        with self._lock:
            if source not in self._sources:
                self._sources[source] = SourceStats()
            self._sources[source].record(matched)

    def snapshot(self) -> Dict[str, SourceStats]:
        """Return a shallow copy of current stats keyed by source path."""
        with self._lock:
            return {
                src: SourceStats(
                    total_lines=s.total_lines,
                    matched_lines=s.matched_lines,
                    last_seen=s.last_seen,
                )
                for src, s in self._sources.items()
            }

    def reset(self, source: Optional[str] = None) -> None:
        """Reset stats for *source*, or all sources if *source* is None."""
        with self._lock:
            if source is not None:
                self._sources.pop(source, None)
            else:
                self._sources.clear()

    def summary_lines(self) -> list[str]:
        """Return human-readable summary lines for all sources."""
        lines = []
        for src, s in self.snapshot().items():
            lines.append(
                f"{src}: total={s.total_lines} matched={s.matched_lines} "
                f"drop_rate={s.drop_rate:.1%}"
            )
        return lines
