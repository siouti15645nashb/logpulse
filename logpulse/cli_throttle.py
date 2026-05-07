"""CLI helpers for the throttle middleware."""

from __future__ import annotations

import argparse
from typing import Callable, Optional

from logpulse.throttle import ThrottleMiddleware


def add_throttle_args(parser: argparse.ArgumentParser) -> None:
    """Register throttle-related CLI arguments on *parser*."""
    grp = parser.add_argument_group("throttle")
    grp.add_argument(
        "--throttle-max",
        metavar="N",
        type=int,
        default=None,
        help="Max occurrences of the same line within --throttle-window (default: off).",
    )
    grp.add_argument(
        "--throttle-window",
        metavar="SECS",
        type=float,
        default=10.0,
        help="Rolling window in seconds for throttle counting (default: 10).",
    )
    grp.add_argument(
        "--throttle-pattern",
        metavar="REGEX",
        default=None,
        help="Only throttle lines matching this regex; others always pass through.",
    )


def wrap_with_throttle(
    callback: Callable[[str, str], None],
    args: argparse.Namespace,
) -> Callable[[str, str], None]:
    """Wrap *callback* with :class:`ThrottleMiddleware` if throttling is requested.

    Returns the original callback unchanged when ``--throttle-max`` is not set.
    """
    if args.throttle_max is None:
        return callback

    middleware = ThrottleMiddleware(
        callback=callback,
        max_count=args.throttle_max,
        window_seconds=args.throttle_window,
        pattern=args.throttle_pattern,
    )
    return middleware
