"""CLI helpers for the multiline-folding middleware."""
from __future__ import annotations

import argparse
from typing import Callable

from logpulse.multiline import MultilineMiddleware


def add_multiline_args(parser: argparse.ArgumentParser) -> None:
    """Register multiline-folding flags on *parser*."""
    grp = parser.add_argument_group("multiline folding")
    grp.add_argument(
        "--multiline",
        action="store_true",
        default=False,
        help="Enable multiline folding (collapse continuation lines).",
    )
    grp.add_argument(
        "--multiline-pattern",
        metavar="REGEX",
        default=r"^\s+",
        help=(
            "Regex that identifies a continuation line. "
            "Default: lines starting with whitespace."
        ),
    )
    grp.add_argument(
        "--multiline-max",
        metavar="N",
        type=int,
        default=50,
        help="Maximum lines per folded event (default: 50).",
    )
    grp.add_argument(
        "--multiline-join",
        metavar="STR",
        default="\n",
        help="String used to join folded lines (default: newline).",
    )


def wrap_with_multiline(
    args: argparse.Namespace,
    callback: Callable[[str, str], None],
) -> Callable[[str, str], None]:
    """Return *callback* wrapped in :class:`MultilineMiddleware` if enabled.

    The returned middleware must have :py:meth:`~MultilineMiddleware.flush`
    called by the caller when tailing finishes so any buffered lines are
    emitted.
    """
    if not args.multiline:
        return callback

    mw = MultilineMiddleware(
        callback,
        continuation_pattern=args.multiline_pattern,
        max_lines=args.multiline_max,
        join_str=args.multiline_join,
    )
    return mw
