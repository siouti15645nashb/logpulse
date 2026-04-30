"""Regex filter module for logpulse.

Provides the LineFilter class which applies include/exclude
regex patterns to log lines.
"""

import re
from typing import List, Optional


class LineFilter:
    """Filters log lines using include and exclude regex patterns."""

    def __init__(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        case_sensitive: bool = True,
    ) -> None:
        """
        Initialize the LineFilter.

        Args:
            include_patterns: Lines must match at least one of these patterns.
                              If empty or None, all lines are included by default.
            exclude_patterns: Lines matching any of these patterns are excluded.
            case_sensitive: Whether pattern matching is case-sensitive.
        """
        flags = 0 if case_sensitive else re.IGNORECASE

        self._include = [
            re.compile(p, flags) for p in (include_patterns or [])
        ]
        self._exclude = [
            re.compile(p, flags) for p in (exclude_patterns or [])
        ]

    def matches(self, line: str) -> bool:
        """Return True if the line passes the filter."""
        if self._exclude and any(p.search(line) for p in self._exclude):
            return False
        if self._include and not any(p.search(line) for p in self._include):
            return False
        return True

    def apply(self, lines: List[str]) -> List[str]:
        """Return only the lines that pass the filter."""
        return [line for line in lines if self.matches(line)]
