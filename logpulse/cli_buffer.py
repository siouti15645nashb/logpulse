"""CLI helpers for the buffer middleware."""
from __future__ import annotations

import argparse
from typing import Callable, Optional

from logpulse.buffer import BufferMiddleware

_DEFAULT_MAX_SIZE = 50
_DEFAULT_INTERVAL = 2.0


def add_buffer_args(parser: argparse.ArgumentParser) -> None:
    """Register ``--buffer-size`` and ``--buffer-interval`` on *parser*."""
    grp = parser.add_argument_group("output buffering")
    grp.add_argument(
        "--buffer-size",
        metavar="N",
        type=int,
        default=None,
        help=(
            "Accumulate up to N lines before forwarding them to output "
            f"(default: {_DEFAULT_MAX_SIZE}).  Use 0 to disable buffering."
        ),
    )
    grp.add_argument(
        "--buffer-interval",
        metavar="SECS",
        type=float,
        default=_DEFAULT_INTERVAL,
        help=(
            "Flush the buffer after SECS seconds even if it is not full "
            f"(default: {_DEFAULT_INTERVAL})."
        ),
    )


def wrap_with_buffer(
    callback: Callable[[str, str], None],
    args: argparse.Namespace,
) -> tuple[Callable[[str, str], None], Optional[BufferMiddleware]]:
    """Return *(wrapped_callback, middleware)* or *(callback, None)* if disabled.

    The second element is returned so callers can call ``middleware.close()``
    on shutdown to flush any remaining lines.
    """
    size: Optional[int] = getattr(args, "buffer_size", None)
    interval: float = getattr(args, "buffer_interval", _DEFAULT_INTERVAL)

    if size == 0:
        # Explicitly disabled.
        return callback, None

    effective_size = size if size is not None else _DEFAULT_MAX_SIZE

    mw = BufferMiddleware(
        callback,
        max_size=effective_size,
        flush_interval=interval,
    )
    return mw, mw
