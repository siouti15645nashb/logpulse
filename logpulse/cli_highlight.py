"""CLI helpers for wiring highlight rules into the processing pipeline.

Expected argument format (repeatable)::

    --highlight 'ERROR:#ff0000'
    --highlight 'WARN:#ffaa00:bold'

Each spec is ``<pattern>:<colour>[:<bold>]`` where *colour* is an ANSI hex
colour or one of the named shortcuts (red, green, yellow, blue, magenta, cyan)
and the optional third field is the literal string ``bold``.
"""

from __future__ import annotations

import argparse
from typing import List, Optional

from logpulse.highlight import HighlightMiddleware, HighlightRule

# ---------------------------------------------------------------------------
# Named colour shortcuts → ANSI 256-colour / true-colour escape sequences
# ---------------------------------------------------------------------------

_NAMED_COLOURS: dict[str, str] = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}


def _resolve_colour(colour_spec: str) -> str:
    """Return an ANSI escape sequence for *colour_spec*.

    Accepts named shortcuts (case-insensitive) or raw ``#RRGGBB`` hex strings.
    Falls back to the plain bold escape when the spec cannot be parsed.
    """
    lower = colour_spec.lower()
    if lower in _NAMED_COLOURS:
        return _NAMED_COLOURS[lower]
    if colour_spec.startswith("#") and len(colour_spec) == 7:
        try:
            r = int(colour_spec[1:3], 16)
            g = int(colour_spec[3:5], 16)
            b = int(colour_spec[5:7], 16)
            return f"\033[38;2;{r};{g};{b}m"
        except ValueError:
            pass
    # Unknown spec — fall back to bold so the match is still visible.
    return "\033[1m"


# ---------------------------------------------------------------------------
# Argument registration
# ---------------------------------------------------------------------------


def add_highlight_args(parser: argparse.ArgumentParser) -> None:
    """Register ``--highlight`` and ``--highlight-reset`` on *parser*."""
    parser.add_argument(
        "--highlight",
        metavar="PATTERN[:COLOUR[:bold]]",
        action="append",
        default=[],
        dest="highlight_specs",
        help=(
            "Highlight lines matching PATTERN.  Colour can be a named colour "
            "(red, green, yellow, blue, magenta, cyan) or a #RRGGBB hex value. "
            "Append ':bold' to also embolden the match.  Repeatable."
        ),
    )
    parser.add_argument(
        "--highlight-reset",
        action="store_true",
        default=False,
        help="Reset colour after each highlighted match (default: True internally).",
    )


# ---------------------------------------------------------------------------
# Spec parsing
# ---------------------------------------------------------------------------


def parse_highlight_specs(specs: List[str]) -> List[HighlightRule]:
    """Convert a list of raw spec strings into :class:`HighlightRule` objects.

    Each spec must be ``<pattern>`` or ``<pattern>:<colour>`` or
    ``<pattern>:<colour>:bold``.  Invalid specs are skipped with a warning
    printed to *stderr*.
    """
    import sys

    rules: List[HighlightRule] = []
    for spec in specs:
        parts = spec.split(":", 2)
        pattern = parts[0].strip()
        if not pattern:
            print(f"[logpulse] highlight: empty pattern in spec {spec!r}, skipping", file=sys.stderr)
            continue

        colour_escape: Optional[str] = None
        bold = False

        if len(parts) >= 2 and parts[1].strip():
            colour_escape = _resolve_colour(parts[1].strip())
        if len(parts) == 3 and parts[2].strip().lower() == "bold":
            bold = True

        try:
            rules.append(HighlightRule(pattern=pattern, colour=colour_escape, bold=bold))
        except Exception as exc:  # noqa: BLE001
            print(
                f"[logpulse] highlight: could not compile pattern {pattern!r}: {exc}, skipping",
                file=sys.stderr,
            )
    return rules


# ---------------------------------------------------------------------------
# Middleware factory
# ---------------------------------------------------------------------------


def wrap_with_highlight(callback, args: argparse.Namespace):
    """Wrap *callback* with :class:`HighlightMiddleware` when specs are present.

    Returns *callback* unchanged when no ``--highlight`` specs were provided so
    the rest of the pipeline is unaffected.
    """
    specs: List[str] = getattr(args, "highlight_specs", []) or []
    if not specs:
        return callback

    rules = parse_highlight_specs(specs)
    if not rules:
        return callback

    return HighlightMiddleware(rules=rules, callback=callback)
