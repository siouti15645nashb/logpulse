"""Output formatting for log lines with optional colorization and timestamps."""

import sys
from datetime import datetime, timezone
from typing import Optional


ANSI_COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "reset": "\033[0m",
}

FILE_COLORS = [
    "cyan",
    "green",
    "yellow",
    "magenta",
]


class LineFormatter:
    """Formats a log line with optional source label, timestamp, and color."""

    def __init__(
        self,
        show_timestamp: bool = False,
        colorize: bool = False,
        label_width: int = 20,
    ) -> None:
        self.show_timestamp = show_timestamp
        self.colorize = colorize and self._supports_color()
        self.label_width = label_width
        self._color_map: dict[str, str] = {}
        self._color_cycle_index = 0

    @staticmethod
    def _supports_color() -> bool:
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def _color_for(self, source: str) -> str:
        if source not in self._color_map:
            color_name = FILE_COLORS[self._color_cycle_index % len(FILE_COLORS)]
            self._color_map[source] = ANSI_COLORS[color_name]
            self._color_cycle_index += 1
        return self._color_map[source]

    def format(self, line: str, source: Optional[str] = None) -> str:
        """Return a formatted string for the given log line."""
        parts = []

        if self.show_timestamp:
            ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            parts.append(f"[{ts}]")

        if source is not None:
            label = source[-self.label_width :].ljust(self.label_width)
            if self.colorize:
                color = self._color_for(source)
                label = f"{color}{label}{ANSI_COLORS['reset']}"
            parts.append(f"{label} |")

        parts.append(line)
        return " ".join(parts)
