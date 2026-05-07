"""Pipeline mixin that adds :meth:`with_tag` support."""
from __future__ import annotations

from typing import Callable, Dict

from logpulse.tag import TagMiddleware


def _attach_tag(
    handler: Callable,
    static_tags: Dict[str, str],
    dynamic_tags: Dict[str, Callable[[str, str], str]] | None = None,
) -> TagMiddleware:
    return TagMiddleware(
        next_handler=handler,
        static_tags=static_tags,
        dynamic_tags=dynamic_tags or {},
    )


class PipelineTagMixin:
    """Mixin for :class:`~logpulse.pipeline.Pipeline` adding ``with_tag``."""

    def with_tag(
        self,
        static_tags: Dict[str, str] | None = None,
        dynamic_tags: Dict[str, Callable[[str, str], str]] | None = None,
    ) -> "PipelineTagMixin":
        """Prepend a :class:`~logpulse.tag.TagMiddleware` to the pipeline.

        Args:
            static_tags: Fixed ``{key: value}`` pairs added to every line.
            dynamic_tags: ``{key: callable(source, line) -> str}`` pairs
                evaluated per line.

        Returns:
            *self* for chaining.
        """
        mw = _attach_tag(
            handler=self._handler,  # type: ignore[attr-defined]
            static_tags=static_tags or {},
            dynamic_tags=dynamic_tags or {},
        )
        self._handler = mw  # type: ignore[attr-defined]
        self.tag: TagMiddleware | None = mw
        return self
