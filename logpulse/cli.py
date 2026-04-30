"""Command-line entry point for logpulse."""

import argparse
import sys
from datetime import datetime
from typing import List, Optional

from logpulse.aggregator import LogAggregator


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logpulse",
        description="Tail multiple log files with real-time regex filtering.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Log file(s) to tail.",
    )
    parser.add_argument(
        "-i",
        "--include",
        action="append",
        dest="include_patterns",
        metavar="PATTERN",
        default=None,
        help="Regex pattern to include (can be repeated).",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        action="append",
        dest="exclude_patterns",
        metavar="PATTERN",
        default=None,
        help="Regex pattern to exclude (can be repeated).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        metavar="SECONDS",
        help="Poll interval in seconds (default: 0.5).",
    )
    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Suppress timestamp prefix in output.",
    )
    return parser


def _make_printer(show_timestamp: bool, show_path: bool):
    def _print(path: str, line: str) -> None:
        parts = []
        if show_timestamp:
            parts.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if show_path:
            parts.append(f"[{path}]")
        parts.append(line)
        print(" ".join(parts), flush=True)

    return _print


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    show_path = len(args.files) > 1
    printer = _make_printer(
        show_timestamp=not args.no_timestamp,
        show_path=show_path,
    )

    agg = LogAggregator(
        paths=args.files,
        include_patterns=args.include_patterns,
        exclude_patterns=args.exclude_patterns,
        poll_interval=args.interval,
    )
    agg.on_line(printer)

    try:
        with agg:
            # Block until interrupted
            import time
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
