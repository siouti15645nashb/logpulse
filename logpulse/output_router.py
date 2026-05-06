"""Output router: fan-out matched lines to multiple sinks (callbacks)."""
from __future__ import annotations

from typing import Callable, List, Optional

LineCallback = Callable[[str, str], None]  # (source, line)


class OutputRouter:
    """Fan-out a matched line to one or more registered sink callbacks.

    Sinks can be added dynamically and optionally given a name for
    identification / removal.
    """

    def __init__(self) -> None:
        self._sinks: List[tuple[Optional[str], LineCallback]] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_sink(self, callback: LineCallback, name: Optional[str] = None) -> None:
        """Register *callback* as a sink.  Duplicate names are allowed."""
        self._sinks.append((name, callback))

    def remove_sink(self, name: str) -> int:
        """Remove all sinks registered under *name*.  Returns removal count."""
        before = len(self._sinks)
        self._sinks = [(n, cb) for n, cb in self._sinks if n != name]
        return before - len(self._sinks)

    def sink_count(self) -> int:
        """Return the number of currently registered sinks."""
        return len(self._sinks)

    def sink_names(self) -> List[Optional[str]]:
        """Return ordered list of sink names (may contain None)."""
        return [n for n, _ in self._sinks]

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(self, source: str, line: str) -> int:
        """Deliver *(source, line)* to every registered sink.

        Exceptions raised by individual sinks are caught and printed so
        that one broken sink cannot silence the others.

        Returns the number of sinks that received the line successfully.
        """
        ok = 0
        for _name, cb in list(self._sinks):
            try:
                cb(source, line)
                ok += 1
            except Exception as exc:  # noqa: BLE001
                print(f"[logpulse] OutputRouter sink error: {exc}")
        return ok

    # Make instances directly callable as a line callback.
    def __call__(self, source: str, line: str) -> int:
        return self.route(source, line)
