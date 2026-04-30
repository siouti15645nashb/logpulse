"""Tests for LogAggregator."""

import os
import tempfile
import time
import threading
from typing import List, Tuple

import pytest

from logpulse.aggregator import LogAggregator


def _write_lines(path: str, lines: List[str]) -> None:
    with open(path, "a") as fh:
        for line in lines:
            fh.write(line + "\n")
        fh.flush()


@pytest.fixture()
def tmp_log(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("")  # create empty file
    return str(log)


def _collect(aggregator: LogAggregator, duration: float) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []
    aggregator.on_line(lambda path, line: results.append((path, line)))
    with aggregator:
        time.sleep(duration)
    return results


class TestLogAggregator:
    def test_collects_new_lines(self, tmp_log):
        agg = LogAggregator([tmp_log], poll_interval=0.05)
        collected: List[Tuple[str, str]] = []
        agg.on_line(lambda p, l: collected.append((p, l)))
        agg.start()
        time.sleep(0.1)
        _write_lines(tmp_log, ["hello world", "foo bar"])
        time.sleep(0.3)
        agg.stop()
        lines = [l for _, l in collected]
        assert "hello world" in lines
        assert "foo bar" in lines

    def test_include_filter_applied(self, tmp_log):
        agg = LogAggregator([tmp_log], include_patterns=[r"ERROR"], poll_interval=0.05)
        collected: List[Tuple[str, str]] = []
        agg.on_line(lambda p, l: collected.append((p, l)))
        agg.start()
        time.sleep(0.1)
        _write_lines(tmp_log, ["INFO startup", "ERROR disk full", "DEBUG ping"])
        time.sleep(0.3)
        agg.stop()
        lines = [l for _, l in collected]
        assert "ERROR disk full" in lines
        assert "INFO startup" not in lines
        assert "DEBUG ping" not in lines

    def test_exclude_filter_applied(self, tmp_log):
        agg = LogAggregator([tmp_log], exclude_patterns=[r"DEBUG"], poll_interval=0.05)
        collected: List[Tuple[str, str]] = []
        agg.on_line(lambda p, l: collected.append((p, l)))
        agg.start()
        time.sleep(0.1)
        _write_lines(tmp_log, ["INFO startup", "DEBUG verbose", "WARNING low mem"])
        time.sleep(0.3)
        agg.stop()
        lines = [l for _, l in collected]
        assert "INFO startup" in lines
        assert "WARNING low mem" in lines
        assert "DEBUG verbose" not in lines

    def test_context_manager_stops_threads(self, tmp_log):
        agg = LogAggregator([tmp_log], poll_interval=0.05)
        agg.on_line(lambda p, l: None)
        with agg:
            assert len(agg._threads) == 1
        assert all(not t.is_alive() for t in agg._threads)

    def test_multiple_files(self, tmp_path):
        logs = [str(tmp_path / f"app{i}.log") for i in range(3)]
        for p in logs:
            open(p, "w").close()
        agg = LogAggregator(logs, poll_interval=0.05)
        collected: List[Tuple[str, str]] = []
        agg.on_line(lambda p, l: collected.append((p, l)))
        agg.start()
        time.sleep(0.1)
        for p in logs:
            _write_lines(p, [f"line from {p}"])
        time.sleep(0.4)
        agg.stop()
        seen_paths = {p for p, _ in collected}
        assert seen_paths == set(logs)
