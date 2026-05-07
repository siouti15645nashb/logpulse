"""Highlight middleware — wraps matched regex spans in ANSI colour codes."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

_RESET = "\033[0m"
_COLOURS = [
    "\033[93m",  # bright yellow
    "\033[96m",  # bright cyan
    "\033[92m",  # bright green
    "\033[95m",  # bright magenta
    "\033[91m",  # bright red
]


@dataclass
class HighlightRule:
    pattern: str
    colour_index: int = 0
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern)
        self.colour_index = self.colour_index % len(_COLOURS)

    def apply(self, text: str) -> str:
        """Return *text* with every match wrapped in the assigned ANSI colour."""
        colour = _COLOURS[self.colour_index]

        def _wrap(m: re.Match) -> str:  # type: ignore[type-arg]
            return f"{colour}{m.group(0)}{_RESET}"

        return self._compiled.sub(_wrap, text)


class HighlightMiddleware:
    """Middleware that applies one or more :class:`HighlightRule` objects to
    each log line before forwarding it to the next callback.

    Parameters
    ----------
    callback:
        Downstream callable that receives ``(source, line)`` pairs.
    rules:
        Ordered list of :class:`HighlightRule` instances.  Rules are applied
        sequentially so earlier rules take precedence for overlapping spans.
    enabled:
        When *False* the middleware is a transparent pass-through (useful when
        stdout is not a TTY).
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        rules: Optional[List[HighlightRule]] = None,
        *,
        enabled: bool = True,
    ) -> None:
        self._callback = callback
        self._rules: List[HighlightRule] = rules or []
        self._enabled = enabled
        self._highlighted = 0

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def add_rule(self, pattern: str, colour_index: int = 0) -> HighlightRule:
        """Create and register a new rule; return it for inspection."""
        rule = HighlightRule(pattern=pattern, colour_index=colour_index)
        self._rules.append(rule)
        return rule

    @property
    def highlighted_count(self) -> int:
        """Total number of lines that had at least one match highlighted."""
        return self._highlighted

    # ------------------------------------------------------------------
    # Middleware protocol
    # ------------------------------------------------------------------

    def on_line(self, source: str, line: str) -> None:
        if not self._enabled or not self._rules:
            self._callback(source, line)
            return

        modified = line
        changed = False
        for rule in self._rules:
            new = rule.apply(modified)
            if new != modified:
                changed = True
            modified = new

        if changed:
            self._highlighted += 1
        self._callback(source, modified)

    def __call__(self, source: str, line: str) -> None:
        self.on_line(source, line)
