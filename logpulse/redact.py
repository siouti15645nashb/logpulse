"""Redaction middleware — masks sensitive patterns in log lines before output."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class RedactRule:
    """A single pattern/replacement pair used for redaction."""

    pattern: str
    replacement: str = "[REDACTED]"
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern)

    def apply(self, line: str) -> str:
        """Return *line* with all matches replaced by *replacement*."""
        return self._compiled.sub(self.replacement, line)


class RedactMiddleware:
    """Apply one or more :class:`RedactRule` objects to every line.

    Lines are passed to *callback* after all rules have been applied.
    The original line is never forwarded; only the redacted version is.
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        rules: Optional[List[RedactRule]] = None,
    ) -> None:
        self._callback = callback
        self._rules: List[RedactRule] = rules or []
        self._redacted_count = 0

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def add_rule(self, rule: RedactRule) -> None:
        """Append *rule* to the active rule list."""
        self._rules.append(rule)

    @property
    def redacted_count(self) -> int:
        """Total number of lines that had at least one substitution."""
        return self._redacted_count

    # ------------------------------------------------------------------
    # Middleware protocol
    # ------------------------------------------------------------------

    def on_line(self, source: str, line: str) -> None:
        """Process *line* from *source* and forward to the next callback."""
        redacted = line
        for rule in self._rules:
            redacted = rule.apply(redacted)
        if redacted != line:
            self._redacted_count += 1
        self._callback(source, redacted)

    def __call__(self, source: str, line: str) -> None:  # noqa: D401
        self.on_line(source, line)
