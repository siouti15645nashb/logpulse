"""CLI helpers for the deduplication middleware."""

from __future__ import annotations

import argparse
from typing import Callable

from logpulse.dedupe import DedupeMiddleware


def add_dedupe_args(parser: argparse.ArgumentParser) -> None:
    """Register deduplication flags on *parser*."""
    group = parser.add_argument_group("deduplication")
    group.add_argument(
        "--dedupe",
        action="store_true",
        default=False,
        help="Suppress repeated identical lines within the dedup window.",
    )
    group.add_argument(
        "--dedupe-window",
        metavar="SECONDS",
        type=float,
        default=5.0,
        help="Seconds to remember a line for deduplication (default: 5).",
    )
    group.add_argument(
        "--dedupe-cache",
        metavar="N",
        type=int,
        default=1024,
        help="Maximum distinct lines kept in the dedup cache (default: 1024).",
    )


def wrap_with_dedupe(
    callback: Callable[[str, str], None],
    args: argparse.Namespace,
) -> Callable[[str, str], None]:
    """Return *callback* wrapped in :class:`DedupeMiddleware` when enabled.

    If ``--dedupe`` was not requested the original *callback* is returned
    unchanged so there is zero overhead.
    """
    if not getattr(args, "dedupe", False):
        return callback

    middleware = DedupeMiddleware(
        callback=callback,
        window_seconds=args.dedupe_window,
        max_cache=args.dedupe_cache,
    )
    return middleware
