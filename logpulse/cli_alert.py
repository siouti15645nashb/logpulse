"""CLI helpers for wiring alert rules from command-line arguments."""

from __future__ import annotations

import sys
from typing import Sequence

from logpulse.alert import AlertManager, AlertRule


def parse_alert_specs(specs: Sequence[str]) -> list[AlertRule]:
    """Parse alert spec strings of the form ``name:pattern:threshold:window``.

    Example::

        "errors:ERROR:5:60"  # fire when ERROR appears 5 times in 60 s
    """
    rules: list[AlertRule] = []
    for spec in specs:
        parts = spec.split(":", maxsplit=3)
        if len(parts) != 4:
            print(
                f"[logpulse] Invalid alert spec (expected name:pattern:threshold:window): {spec!r}",
                file=sys.stderr,
            )
            continue
        name, pattern, raw_threshold, raw_window = parts
        try:
            threshold = int(raw_threshold)
            window = float(raw_window)
        except ValueError:
            print(
                f"[logpulse] Alert spec has non-numeric threshold/window: {spec!r}",
                file=sys.stderr,
            )
            continue
        if threshold < 1 or window <= 0:
            print(
                f"[logpulse] Alert spec threshold must be >= 1 and window > 0: {spec!r}",
                file=sys.stderr,
            )
            continue
        rules.append(AlertRule(name=name, pattern=pattern, threshold=threshold, window_seconds=window))
    return rules


def make_alert_manager(
    specs: Sequence[str],
    color: bool = True,
) -> AlertManager | None:
    """Build an :class:`AlertManager` from CLI spec strings, or return *None*
    if no valid specs are provided."""
    rules = parse_alert_specs(specs)
    if not rules:
        return None

    def _alert_callback(rule: AlertRule, source: str, count: int) -> None:
        prefix = "\033[1;31m[ALERT]\033[0m" if color else "[ALERT]"
        print(
            f"{prefix} rule={rule.name!r} source={source!r} "
            f"matched {count}x in {rule.window_seconds}s (pattern={rule.pattern!r})",
            file=sys.stderr,
        )

    return AlertManager(rules, _alert_callback)
