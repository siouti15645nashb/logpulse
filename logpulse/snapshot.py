"""Snapshot persistence for FileTailer seek positions.

Allows logpulse to resume tailing from where it left off after a restart.
"""

import json
import os
from typing import Dict


class PositionSnapshot:
    """Persists and restores file seek positions across runs."""

    def __init__(self, snapshot_path: str) -> None:
        self._path = snapshot_path
        self._positions: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        """Load positions from disk if the snapshot file exists."""
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self._positions = {k: int(v) for k, v in data.items()}
        except (json.JSONDecodeError, ValueError, OSError):
            # Corrupt or unreadable snapshot — start fresh.
            self._positions = {}

    def save(self) -> None:
        """Persist current positions to disk atomically."""
        tmp_path = self._path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(self._positions, fh, indent=2)
            os.replace(tmp_path, self._path)
        except OSError:
            # Best-effort — don't crash the aggregator on save failure.
            pass

    def get(self, file_path: str) -> int:
        """Return the last known byte offset for *file_path*, or 0."""
        return self._positions.get(os.path.abspath(file_path), 0)

    def update(self, file_path: str, position: int) -> None:
        """Record a new byte offset for *file_path*."""
        self._positions[os.path.abspath(file_path)] = position

    def remove(self, file_path: str) -> None:
        """Remove the stored position for *file_path* (e.g. after rotation)."""
        self._positions.pop(os.path.abspath(file_path), None)

    @property
    def path(self) -> str:
        return self._path
