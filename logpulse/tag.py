"""Tag middleware — attaches static or dynamic key/value tags to each log line."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class TagMiddleware:
    """Append a dict of tags to every line payload forwarded downstream.

    Tags are injected into the *meta* dict that accompanies each line so that
    downstream sinks (formatters, routers, etc.) can use them without altering
    the raw log text.

    Args:
        next_handler: Callable that receives (source, line, meta).
        static_tags: Fixed str→str pairs attached to every line.
        dynamic_tags: Callables that receive (source, line) and return a str
            value; evaluated per line.
    """

    next_handler: Callable
    static_tags: Dict[str, str] = field(default_factory=dict)
    dynamic_tags: Dict[str, Callable[[str, str], str]] = field(default_factory=dict)
    _tagged_count: int = field(default=0, init=False, repr=False)

    def on_line(self, source: str, line: str, meta: Optional[dict] = None) -> None:
        meta = dict(meta) if meta else {}
        tags = dict(self.static_tags)
        for key, fn in self.dynamic_tags.items():
            tags[key] = fn(source, line)
        meta.setdefault("tags", {})
        meta["tags"].update(tags)
        self._tagged_count += 1
        self.next_handler(source, line, meta)

    def __call__(self, source: str, line: str, meta: Optional[dict] = None) -> None:
        self.on_line(source, line, meta)

    @property
    def tagged_count(self) -> int:
        """Total number of lines that have been tagged."""
        return self._tagged_count
