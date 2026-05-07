"""Buffered output middleware: accumulates lines and flushes on a time or size trigger."""
from __future__ import annotations

import threading
import time
from typing import Callable, List, Optional


class BufferMiddleware:
    """Collects lines into a buffer and flushes them to *callback* either when
    the buffer reaches *max_size* or when *flush_interval* seconds have elapsed
    since the last flush, whichever comes first.
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        *,
        max_size: int = 50,
        flush_interval: float = 2.0,
    ) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if flush_interval <= 0:
            raise ValueError("flush_interval must be > 0")

        self._callback = callback
        self._max_size = max_size
        self._flush_interval = flush_interval

        self._lock = threading.Lock()
        self._buffer: List[tuple[str, str]] = []  # (source, line)
        self._last_flush: float = time.monotonic()
        self._flushed_count: int = 0

        self._timer: Optional[threading.Timer] = None
        self._schedule_timer()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def on_line(self, source: str, line: str) -> None:
        """Receive a line; flush immediately if the buffer is full."""
        with self._lock:
            self._buffer.append((source, line))
            if len(self._buffer) >= self._max_size:
                self._flush_locked()

    def __call__(self, source: str, line: str) -> None:
        self.on_line(source, line)

    def flush(self) -> None:
        """Force an immediate flush of any buffered lines."""
        with self._lock:
            self._flush_locked()

    @property
    def flushed_count(self) -> int:
        """Total number of lines that have been forwarded to *callback*."""
        return self._flushed_count

    @property
    def pending(self) -> int:
        """Number of lines currently sitting in the buffer."""
        with self._lock:
            return len(self._buffer)

    def close(self) -> None:
        """Cancel the background timer and flush remaining lines."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self.flush()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flush_locked(self) -> None:
        """Must be called with *_lock* held."""
        for source, line in self._buffer:
            self._callback(source, line)
        self._flushed_count += len(self._buffer)
        self._buffer.clear()
        self._last_flush = time.monotonic()

    def _schedule_timer(self) -> None:
        self._timer = threading.Timer(self._flush_interval, self._timer_flush)
        self._timer.daemon = True
        self._timer.start()

    def _timer_flush(self) -> None:
        with self._lock:
            self._flush_locked()
        self._schedule_timer()
