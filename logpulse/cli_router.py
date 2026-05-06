"""CLI helpers: build an OutputRouter wired to stdout and optional file sinks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from logpulse.output_router import OutputRouter


def add_router_args(parser: argparse.ArgumentParser) -> None:
    """Attach output-routing arguments to *parser*."""
    parser.add_argument(
        "--output",
        metavar="FILE",
        action="append",
        default=[],
        help="Write matched lines to FILE in addition to stdout (repeatable).",
    )
    parser.add_argument(
        "--no-stdout",
        action="store_true",
        default=False,
        help="Suppress stdout output (useful when --output is set).",
    )


def build_router(
    output_files: List[str],
    no_stdout: bool = False,
    stdout_callback=None,
) -> OutputRouter:
    """Create an :class:`OutputRouter` from parsed CLI values.

    Parameters
    ----------
    output_files:
        Paths supplied via ``--output``.
    no_stdout:
        When *True* the stdout sink is omitted.
    stdout_callback:
        Override the default ``print``-based stdout sink (useful in tests).
    """
    router = OutputRouter()

    if not no_stdout:
        if stdout_callback is None:
            def stdout_callback(source: str, line: str) -> None:  # type: ignore[misc]
                sys.stdout.write(f"{line}\n")

        router.add_sink(stdout_callback, name="stdout")

    for path_str in output_files:
        path = Path(path_str)
        # Open in append mode so multiple runs accumulate.
        fh = path.open("a", encoding="utf-8")

        def _file_sink(source: str, line: str, _fh=fh) -> None:
            _fh.write(f"{line}\n")
            _fh.flush()

        router.add_sink(_file_sink, name=f"file:{path_str}")

    return router
