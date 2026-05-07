"""Pipeline builder that wires together middleware components in a consistent order.

The Pipeline class provides a fluent interface for composing the various
middleware layers (deduplication, rate-limiting, throttle, sampling) around
a core callback, so that callers don't have to remember the correct wrapping
order themselves.
"""

from __future__ import annotations

from typing import Callable, Optional

from logpulse.dedupe import DedupeMiddleware
from logpulse.ratelimit import RateLimiter
from logpulse.ratelimit_middleware import RateLimitMiddleware
from logpulse.sampling import SamplingMiddleware
from logpulse.throttle import ThrottleMiddleware

# Type alias for the line-callback signature used throughout logpulse.
LineCallback = Callable[[str, str], None]


class Pipeline:
    """Composable middleware pipeline for log line processing.

    Layers are applied in the following order (outermost → innermost):
        Sampling → RateLimit → Throttle → Dedupe → sink

    Only layers that have been explicitly configured are inserted; the rest
    are skipped so there is zero overhead from unused middleware.

    Example::

        def print_line(source: str, line: str) -> None:
            print(f"{source}: {line}")

        callback = (
            Pipeline(print_line)
            .with_dedupe(window=5.0, max_suppress=3)
            .with_throttle(limit=100, window=10.0)
            .build()
        )
    """

    def __init__(self, sink: LineCallback) -> None:
        """Initialise the pipeline with a terminal sink callback.

        Args:
            sink: The final callback that receives (source, line) tuples
                  after all middleware has been applied.
        """
        self._sink: LineCallback = sink

        # Optional middleware configuration (stored as kwargs dicts so that
        # build() can instantiate them in the correct order).
        self._dedupe_kwargs: Optional[dict] = None
        self._ratelimit_kwargs: Optional[dict] = None
        self._throttle_kwargs: Optional[dict] = None
        self._sampling_kwargs: Optional[dict] = None

    # ------------------------------------------------------------------
    # Fluent configuration methods
    # ------------------------------------------------------------------

    def with_dedupe(self, window: float = 5.0, max_suppress: int = 0) -> "Pipeline":
        """Enable duplicate-line suppression.

        Args:
            window:       Seconds during which an identical line is suppressed.
            max_suppress: Maximum consecutive suppression count before the
                          line is allowed through again (0 = unlimited).
        """
        self._dedupe_kwargs = {"window": window, "max_suppress": max_suppress}
        return self

    def with_ratelimit(self, limit: int, window: float = 1.0) -> "Pipeline":
        """Enable per-source rate limiting.

        Args:
            limit:  Maximum number of lines allowed per *window* seconds.
            window: Rolling time window in seconds.
        """
        self._ratelimit_kwargs = {"limit": limit, "window": window}
        return self

    def with_throttle(self, limit: int, window: float = 1.0) -> "Pipeline":
        """Enable global throughput throttling.

        Args:
            limit:  Maximum lines allowed across all sources per *window*.
            window: Rolling time window in seconds.
        """
        self._throttle_kwargs = {"limit": limit, "window": window}
        return self

    def with_sampling(self, rate: int) -> "Pipeline":
        """Enable deterministic line sampling.

        Args:
            rate: Keep every *rate*-th line (e.g. 2 → 50 %, 10 → 10 %).
        """
        if rate < 1:
            raise ValueError(f"Sampling rate must be >= 1, got {rate}")
        self._sampling_kwargs = {"rate": rate}
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> LineCallback:
        """Assemble and return the composed callback.

        Middleware is wrapped from innermost to outermost so that the
        execution order is: Sampling → RateLimit → Throttle → Dedupe → sink.

        Returns:
            A single ``(source, line) -> None`` callable that passes each
            line through every configured middleware layer before reaching
            the sink.
        """
        callback: LineCallback = self._sink

        # Innermost wrapper applied first (closest to the sink).
        if self._dedupe_kwargs is not None:
            callback = DedupeMiddleware(callback, **self._dedupe_kwargs)

        if self._throttle_kwargs is not None:
            callback = ThrottleMiddleware(callback, **self._throttle_kwargs)

        if self._ratelimit_kwargs is not None:
            limiter = RateLimiter(
                limit=self._ratelimit_kwargs["limit"],
                window=self._ratelimit_kwargs["window"],
            )
            callback = RateLimitMiddleware(callback, limiter)

        # Outermost wrapper applied last (first to see each line).
        if self._sampling_kwargs is not None:
            callback = SamplingMiddleware(callback, **self._sampling_kwargs)

        return callback
