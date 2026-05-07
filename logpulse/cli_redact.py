"""CLI helpers for the redaction middleware."""
from __future__ import annotations

import argparse
from typing import Callable

from logpulse.redact import RedactMiddleware, RedactRule


def add_redact_args(parser: argparse.ArgumentParser) -> None:
    """Register ``--redact`` and ``--redact-replacement`` arguments on *parser*."""
    parser.add_argument(
        "--redact",
        metavar="PATTERN",
        action="append",
        default=[],
        help="Regex pattern whose matches will be replaced in every line. "
             "May be specified multiple times.",
    )
    parser.add_argument(
        "--redact-replacement",
        metavar="TEXT",
        default="[REDACTED]",
        help="Replacement string used for all --redact patterns (default: [REDACTED]).",
    )


def wrap_with_redact(
    args: argparse.Namespace,
    callback: Callable[[str, str], None],
) -> Callable[[str, str], None]:
    """Return *callback* wrapped in :class:`RedactMiddleware` when patterns are given.

    If no ``--redact`` patterns were supplied the original *callback* is
    returned unchanged so there is no runtime overhead.
    """
    patterns: list[str] = args.redact  # type: ignore[attr-defined]
    if not patterns:
        return callback

    replacement: str = args.redact_replacement  # type: ignore[attr-defined]
    rules = [RedactRule(pattern=p, replacement=replacement) for p in patterns]
    middleware = RedactMiddleware(callback=callback, rules=rules)
    return middleware
