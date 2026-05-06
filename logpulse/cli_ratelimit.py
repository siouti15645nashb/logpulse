"""CLI helpers for wiring rate limiting into the logpulse pipeline."""
from __future__ import annotations

import argparse
from typing import Callable, Optional

from logpulse.ratelimit_middleware import RateLimitMiddleware

OnLineFn = Callable[[str, str], None]

_DEFAULT_WINDOW = 1.0


def add_ratelimit_args(parser: argparse.ArgumentParser) -> None:
    """Register --rate-limit and --rate-window arguments on *parser*."""
    group = parser.add_argument_group("rate limiting")
    group.add_argument(
        "--rate-limit",
        metavar="N",
        type=int,
        default=None,
        help=(
            "Maximum number of lines per source per RATE_WINDOW seconds. "
            "Lines beyond this limit are suppressed and a summary is printed."
        ),
    )
    group.add_argument(
        "--rate-window",
        metavar="SECS",
        type=float,
        default=_DEFAULT_WINDOW,
        help=(
            f"Sliding window length in seconds for --rate-limit "
            f"(default: {_DEFAULT_WINDOW})."
        ),
    )


def wrap_with_ratelimit(
    callback: OnLineFn,
    args: argparse.Namespace,
    warn_cb: Optional[OnLineFn] = None,
) -> OnLineFn:
    """Return *callback* wrapped in :class:`RateLimitMiddleware` if requested.

    If ``args.rate_limit`` is ``None`` the original *callback* is returned
    unchanged so there is zero overhead when rate limiting is disabled.

    Args:
        callback: The downstream on_line handler to wrap.
        args:     Parsed CLI namespace (must contain *rate_limit* and
                  *rate_window* attributes added by :func:`add_ratelimit_args`).
        warn_cb:  Optional separate warning callback; forwarded to the
                  middleware unchanged.
    """
    limit: Optional[int] = getattr(args, "rate_limit", None)
    if limit is None:
        return callback

    window: float = getattr(args, "rate_window", _DEFAULT_WINDOW)
    mw = RateLimitMiddleware(
        callback=callback,
        max_lines=limit,
        window=window,
        warn_cb=warn_cb,
    )
    return mw.on_line
