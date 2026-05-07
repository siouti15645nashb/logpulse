"""Pipeline integration for the redaction middleware."""
from __future__ import annotations

from typing import List, Optional

from logpulse.pipeline import Pipeline
from logpulse.redact import RedactMiddleware, RedactRule


def _attach_redact(pipeline: "Pipeline") -> None:  # noqa: F821
    """Monkey-patch helper — not called directly; used by :meth:`Pipeline.with_redact`."""


class PipelineRedactMixin:
    """Mixin that adds :meth:`with_redact` to :class:`Pipeline`.

    Import this module to enable the method::

        import logpulse.pipeline_redact  # noqa: F401
    """

    def with_redact(
        self,
        patterns: List[str],
        replacement: str = "[REDACTED]",
    ) -> "Pipeline":
        """Wrap the current sink with :class:`RedactMiddleware`.

        Parameters
        ----------
        patterns:
            List of regex strings to redact.
        replacement:
            String that replaces each match (default ``[REDACTED]``).
        """
        rules = [RedactRule(pattern=p, replacement=replacement) for p in patterns]
        mw = RedactMiddleware(callback=self._sink, rules=rules)  # type: ignore[attr-defined]
        self._sink = mw  # type: ignore[attr-defined]
        self.redact_middleware: Optional[RedactMiddleware] = mw
        return self  # type: ignore[return-value]


# Dynamically extend Pipeline so callers only need to import this module.
Pipeline.with_redact = PipelineRedactMixin.with_redact  # type: ignore[attr-defined]
Pipeline.redact_middleware = None  # type: ignore[attr-defined]
