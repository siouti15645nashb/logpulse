"""High-level Pipeline builder.

Chains middleware in a consistent order and exposes a single callable
suitable for use as the ``on_line`` callback of :class:`~logpulse.aggregator.LogAggregator`.
"""
from __future__ import annotations

from typing import Callable, Optional

from logpulse.dedupe import DedupeMiddleware
from logpulse.formatter import LineFormatter
from logpulse.highlight import HighlightMiddleware
from logpulse.multiline import MultilineMiddleware
from logpulse.output_router import OutputRouter
from logpulse.ratelimit_middleware import RateLimitMiddleware
from logpulse.sampling import SamplingMiddleware
from logpulse.throttle import ThrottleMiddleware


LineCallback = Callable[[str, str], None]


def print_line(formatter: LineFormatter) -> LineCallback:
    """Return a callback that formats and prints each line."""

    def _print(source: str, line: str) -> None:
        print(formatter.format(source, line))

    return _print


class Pipeline:
    """Fluent builder for a logpulse middleware chain.

    Usage::

        cb = (
            Pipeline(print_line(fmt))
            .with_dedupe()
            .with_ratelimit(max_lines=100, window=1.0)
            .with_multiline()
            .build()
        )
    """

    def __init__(self, sink: LineCallback) -> None:
        self._sink = sink
        self._chain: LineCallback = sink
        self._multiline: Optional[MultilineMiddleware] = None

    # ------------------------------------------------------------------
    # middleware registration (outermost → innermost order)
    # ------------------------------------------------------------------

    def with_dedupe(
        self,
        window: float = 5.0,
        max_cache: int = 1024,
    ) -> "Pipeline":
        self._chain = DedupeMiddleware(self._chain, window=window, max_cache=max_cache)
        return self

    def with_ratelimit(
        self,
        max_lines: int = 100,
        window: float = 1.0,
    ) -> "Pipeline":
        self._chain = RateLimitMiddleware(self._chain, max_lines=max_lines, window=window)
        return self

    def with_throttle(
        self,
        max_lines: int = 50,
        window: float = 1.0,
    ) -> "Pipeline":
        self._chain = ThrottleMiddleware(self._chain, max_lines=max_lines, window=window)
        return self

    def with_sampling(self, rate: int = 1) -> "Pipeline":
        self._chain = SamplingMiddleware(self._chain, rate=rate)
        return self

    def with_highlight(self, rules: list) -> "Pipeline":
        self._chain = HighlightMiddleware(self._chain, rules=rules)
        return self

    def with_multiline(
        self,
        continuation_pattern: str = r"^\s+",
        max_lines: int = 50,
        join_str: str = "\n",
    ) -> "Pipeline":
        mw = MultilineMiddleware(
            self._chain,
            continuation_pattern=continuation_pattern,
            max_lines=max_lines,
            join_str=join_str,
        )
        self._multiline = mw
        self._chain = mw
        return self

    def with_router(self, router: OutputRouter) -> "Pipeline":
        """Replace the current chain with *router* as the outermost layer."""
        router.add_sink(self._chain)
        self._chain = router
        return self

    # ------------------------------------------------------------------

    def build(self) -> LineCallback:
        """Return the assembled callback."""
        return self._chain

    def flush(self) -> None:
        """Flush any stateful middleware (e.g. multiline buffer)."""
        if self._multiline is not None:
            self._multiline.flush()

    @property
    def multiline(self) -> Optional[MultilineMiddleware]:
        """Expose the multiline middleware instance if registered."""
        return self._multiline
