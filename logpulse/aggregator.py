"""Aggregator that coordinates multiple FileTailers with a LineFilter."""

import threading
import time
from typing import Callable, List, Optional

from logpulse.tailer import FileTailer
from logpulse.filter import LineFilter


class LogAggregator:
    """Tails multiple log files concurrently and emits filtered lines."""

    def __init__(
        self,
        paths: List[str],
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        poll_interval: float = 0.5,
    ) -> None:
        self.paths = paths
        self.poll_interval = poll_interval
        self._filter = LineFilter(
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
        self._tailers: List[FileTailer] = [
            FileTailer(path) for path in paths
        ]
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._callback: Optional[Callable[[str, str], None]] = None

    def on_line(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback invoked with (path, line) for each matched line."""
        self._callback = callback

    def _tail_file(self, tailer: FileTailer) -> None:
        """Background worker that polls a single tailer."""
        while not self._stop_event.is_set():
            for line in tailer.tail():
                if self._filter.matches(line) and self._callback:
                    self._callback(tailer.path, line)
            time.sleep(self.poll_interval)

    def start(self) -> None:
        """Start background tailing threads for all files."""
        self._stop_event.clear()
        for tailer in self._tailers:
            t = threading.Thread(
                target=self._tail_file,
                args=(tailer,),
                daemon=True,
                name=f"tailer-{tailer.path}",
            )
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        """Signal all tailing threads to stop and wait for them."""
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads.clear()

    def __enter__(self) -> "LogAggregator":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()
