"""CLI helpers for the tag middleware."""
from __future__ import annotations

import argparse
from typing import Callable

from logpulse.tag import TagMiddleware


def add_tag_args(parser: argparse.ArgumentParser) -> None:
    """Register --tag arguments on *parser*.

    Each value must be in ``KEY=VALUE`` form.  The flag may be repeated.
    """
    parser.add_argument(
        "--tag",
        dest="tags",
        metavar="KEY=VALUE",
        action="append",
        default=[],
        help="Attach a static tag to every output line (repeatable).",
    )


def _parse_tag_spec(spec: str) -> tuple[str, str]:
    """Parse a ``KEY=VALUE`` string into a ``(key, value)`` tuple."""
    if "=" not in spec:
        raise argparse.ArgumentTypeError(
            f"Invalid tag spec {spec!r}: expected KEY=VALUE"
        )
    key, _, value = spec.partition("=")
    return key.strip(), value.strip()


def wrap_with_tag(args: argparse.Namespace, handler: Callable) -> Callable:
    """Wrap *handler* with :class:`TagMiddleware` when tags are requested.

    Returns *handler* unchanged when no ``--tag`` flags were supplied.
    """
    if not args.tags:
        return handler
    static: dict[str, str] = {}
    for spec in args.tags:
        key, value = _parse_tag_spec(spec)
        static[key] = value
    return TagMiddleware(next_handler=handler, static_tags=static)
