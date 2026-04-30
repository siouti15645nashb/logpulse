"""File tailer module for logpulse.

Provides the FileTailer class which tails a single log file,
yielding new lines as they are appended.
"""

import os
import time
from typing import Generator


class FileTailer:
    """Tails a single file and yields new lines in real time."""

    def __init__(self, filepath: str, poll_interval: float = 0.1) -> None:
        """
        Initialize the FileTailer.

        Args:
            filepath: Path to the log file to tail.
            poll_interval: Seconds to wait between polls when no new data.
        """
        self.filepath = filepath
        self.poll_interval = poll_interval
        self._file = None
        self._inode = None

    def _open(self) -> None:
        """Open the file and seek to the end."""
        self._file = open(self.filepath, "r", encoding="utf-8", errors="replace")
        self._file.seek(0, os.SEEK_END)
        self._inode = os.fstat(self._file.fileno()).st_ino

    def _reopen_if_rotated(self) -> bool:
        """Check if the file has been rotated and reopen if necessary."""
        try:
            current_inode = os.stat(self.filepath).st_ino
        except FileNotFoundError:
            return False
        if current_inode != self._inode:
            self._file.close()
            self._file = open(self.filepath, "r", encoding="utf-8", errors="replace")
            self._inode = current_inode
            return True
        return False

    def tail(self) -> Generator[str, None, None]:
        """Yield new lines from the file as they are written."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Log file not found: {self.filepath}")

        self._open()
        try:
            while True:
                line = self._file.readline()
                if line:
                    yield line.rstrip("\n")
                else:
                    self._reopen_if_rotated()
                    time.sleep(self.poll_interval)
        finally:
            if self._file:
                self._file.close()
