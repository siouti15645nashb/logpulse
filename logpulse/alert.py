"""Alert module: triggers callbacks when a log line matches a threshold rule."""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Optional


@dataclass
class AlertRule:
    """A single alert rule: fire when *pattern* matches >= *threshold* times
    within *window_seconds*."""

    name: str
    pattern: str
    threshold: int
    window_seconds: float
    _regex: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._regex = re.compile(self.pattern)

    def matches(self, line: str) -> bool:
        return bool(self._regex.search(line))


class AlertManager:
    """Tracks match counts per rule and fires a callback when a rule fires."""

    def __init__(
        self,
        rules: list[AlertRule],
        callback: Callable[[AlertRule, str, int], None],
    ) -> None:
        self._rules = rules
        self._callback = callback
        # rule name -> deque of match timestamps
        self._windows: dict[str, Deque[float]] = {
            r.name: deque() for r in rules
        }

    def feed(self, source: str, line: str) -> None:
        """Evaluate *line* from *source* against every rule."""
        now = time.monotonic()
        for rule in self._rules:
            if not rule.matches(line):
                continue
            window = self._windows[rule.name]
            window.append(now)
            # evict timestamps outside the sliding window
            cutoff = now - rule.window_seconds
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= rule.threshold:
                self._callback(rule, source, len(window))
                window.clear()  # reset after firing to avoid repeated alerts

    def reset(self, rule_name: Optional[str] = None) -> None:
        """Clear counters for *rule_name* or all rules when None."""
        targets = [rule_name] if rule_name else list(self._windows)
        for name in targets:
            if name in self._windows:
                self._windows[name].clear()
