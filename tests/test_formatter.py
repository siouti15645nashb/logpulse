"""Tests for logpulse.formatter.LineFormatter."""

import pytest
from unittest.mock import patch

from logpulse.formatter import LineFormatter, ANSI_COLORS


class TestLineFormatter:
    def test_plain_line_no_options(self):
        fmt = LineFormatter()
        result = fmt.format("hello world")
        assert result == "hello world"

    def test_source_label_padded(self):
        fmt = LineFormatter(label_width=10)
        result = fmt.format("msg", source="app.log")
        assert "app.log" in result
        assert "|" in result
        # label should be padded to width
        assert result.index("|") >= 10

    def test_source_label_truncated_when_long(self):
        fmt = LineFormatter(label_width=5)
        result = fmt.format("msg", source="very_long_filename.log")
        # only last 5 chars of source should appear
        assert "e.log" in result
        assert "very_long" not in result

    def test_timestamp_included_when_enabled(self):
        fmt = LineFormatter(show_timestamp=True)
        result = fmt.format("entry")
        # ISO-like timestamp bracket
        assert result.startswith("[")
        assert "Z]" in result

    def test_timestamp_not_included_by_default(self):
        fmt = LineFormatter()
        result = fmt.format("entry")
        assert "[" not in result

    def test_colorize_false_no_ansi(self):
        fmt = LineFormatter(colorize=False)
        result = fmt.format("line", source="srv.log")
        assert "\033[" not in result

    def test_colorize_true_with_tty_adds_ansi(self):
        with patch("logpulse.formatter.LineFormatter._supports_color", return_value=True):
            fmt = LineFormatter(colorize=True)
            result = fmt.format("line", source="srv.log")
        assert "\033[" in result
        assert ANSI_COLORS["reset"] in result

    def test_different_sources_get_different_colors(self):
        with patch("logpulse.formatter.LineFormatter._supports_color", return_value=True):
            fmt = LineFormatter(colorize=True)
            r1 = fmt.format("a", source="file1.log")
            r2 = fmt.format("b", source="file2.log")
        # extract color codes used
        color1 = fmt._color_map["file1.log"]
        color2 = fmt._color_map["file2.log"]
        assert color1 != color2

    def test_same_source_consistent_color(self):
        with patch("logpulse.formatter.LineFormatter._supports_color", return_value=True):
            fmt = LineFormatter(colorize=True)
            fmt.format("x", source="app.log")
            color_first = fmt._color_map["app.log"]
            fmt.format("y", source="app.log")
            color_second = fmt._color_map["app.log"]
        assert color_first == color_second

    def test_format_combines_timestamp_source_and_line(self):
        fmt = LineFormatter(show_timestamp=True, label_width=8)
        result = fmt.format("the log line", source="web.log")
        assert "the log line" in result
        assert "web.log" in result
        assert "[" in result

    def test_format_empty_line(self):
        """Empty lines should be formatted without raising and preserve structure."""
        fmt = LineFormatter(label_width=8)
        result = fmt.format("", source="app.log")
        # The separator and source label should still appear
        assert "app.log" in result
        assert "|" in result
        # The line content after the separator should be empty
        content_after_pipe = result.split("|", 1)[-1]
        assert content_after_pipe == ""

    def test_format_line_without_source(self):
        """Lines formatted without a source should not include a separator."""
        fmt = LineFormatter(label_width=8)
        result = fmt.format("standalone line")
        assert "standalone line" in result
        assert "|" not in result
