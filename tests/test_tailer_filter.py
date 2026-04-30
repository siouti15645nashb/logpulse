"""Tests for logpulse tailer and filter modules."""

import os
import tempfile
import threading
import time

import pytest

from logpulse.filter import LineFilter
from logpulse.tailer import FileTailer


# ---------------------------------------------------------------------------
# LineFilter tests
# ---------------------------------------------------------------------------

class TestLineFilter:
    def test_no_patterns_accepts_all(self):
        f = LineFilter()
        assert f.matches("any line here")

    def test_include_pattern_matches(self):
        f = LineFilter(include_patterns=[r"ERROR"])
        assert f.matches("ERROR: something went wrong")
        assert not f.matches("INFO: all good")

    def test_exclude_pattern_filters_out(self):
        f = LineFilter(exclude_patterns=[r"DEBUG"])
        assert f.matches("INFO: startup complete")
        assert not f.matches("DEBUG: verbose output")

    def test_include_and_exclude_combined(self):
        f = LineFilter(include_patterns=[r"ERROR"], exclude_patterns=[r"ignored"])
        assert f.matches("ERROR: critical failure")
        assert not f.matches("ERROR: ignored error")
        assert not f.matches("INFO: normal")

    def test_case_insensitive(self):
        f = LineFilter(include_patterns=[r"error"], case_sensitive=False)
        assert f.matches("ERROR: uppercase")
        assert f.matches("error: lowercase")

    def test_apply_returns_filtered_list(self):
        f = LineFilter(include_patterns=[r"WARN|ERROR"])
        lines = ["INFO: ok", "WARN: watch out", "ERROR: fail", "DEBUG: noise"]
        result = f.apply(lines)
        assert result == ["WARN: watch out", "ERROR: fail"]


# ---------------------------------------------------------------------------
# FileTailer tests
# ---------------------------------------------------------------------------

class TestFileTailer:
    def test_raises_on_missing_file(self):
        tailer = FileTailer("/nonexistent/path/to/file.log")
        with pytest.raises(FileNotFoundError):
            next(tailer.tail())

    def test_yields_appended_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            filepath = f.name

        collected = []
        stop_event = threading.Event()

        def run_tailer():
            tailer = FileTailer(filepath, poll_interval=0.05)
            for line in tailer.tail():
                collected.append(line)
                if stop_event.is_set():
                    break

        t = threading.Thread(target=run_tailer, daemon=True)
        t.start()
        time.sleep(0.1)

        with open(filepath, "a") as f:
            f.write("hello world\n")
            f.write("second line\n")

        time.sleep(0.3)
        stop_event.set()
        t.join(timeout=1.0)
        os.unlink(filepath)

        assert "hello world" in collected
        assert "second line" in collected
