"""Tests for logpulse.ratelimit."""
import pytest

from logpulse.ratelimit import RateLimiter, _Bucket


class TestBucket:
    def test_allows_up_to_limit(self):
        b = _Bucket(window=1.0, max_lines=3)
        now = 100.0
        assert b.allow(now) is True
        assert b.allow(now) is True
        assert b.allow(now) is True

    def test_blocks_at_limit(self):
        b = _Bucket(window=1.0, max_lines=3)
        now = 100.0
        for _ in range(3):
            b.allow(now)
        assert b.allow(now) is False

    def test_allows_after_window_expires(self):
        b = _Bucket(window=1.0, max_lines=3)
        now = 100.0
        for _ in range(3):
            b.allow(now)
        # advance past the window
        assert b.allow(now + 1.1) is True

    def test_current_rate_empty(self):
        b = _Bucket(window=1.0, max_lines=10)
        assert b.current_rate(100.0) == pytest.approx(0.0)

    def test_current_rate_after_events(self):
        b = _Bucket(window=2.0, max_lines=100)
        now = 100.0
        for _ in range(4):
            b.allow(now)
        assert b.current_rate(now) == pytest.approx(2.0)  # 4 / 2s


class TestRateLimiter:
    def test_invalid_max_lines_raises(self):
        with pytest.raises(ValueError):
            RateLimiter(max_lines=0)

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            RateLimiter(max_lines=5, window=0)

    def test_allow_different_sources_independently(self):
        rl = RateLimiter(max_lines=2, window=1.0)
        now = 200.0
        assert rl.allow("a", now) is True
        assert rl.allow("a", now) is True
        assert rl.allow("a", now) is False
        # source b is independent
        assert rl.allow("b", now) is True
        assert rl.allow("b", now) is True
        assert rl.allow("b", now) is False

    def test_reset_clears_single_source(self):
        rl = RateLimiter(max_lines=1, window=1.0)
        now = 300.0
        rl.allow("x", now)
        assert rl.allow("x", now) is False
        rl.reset("x")
        assert rl.allow("x", now) is True

    def test_reset_all_clears_everything(self):
        rl = RateLimiter(max_lines=1, window=1.0)
        now = 300.0
        rl.allow("x", now)
        rl.allow("y", now)
        rl.reset_all()
        assert rl.allow("x", now) is True
        assert rl.allow("y", now) is True

    def test_current_rate_unknown_source_is_zero(self):
        rl = RateLimiter(max_lines=10, window=1.0)
        assert rl.current_rate("unknown") == pytest.approx(0.0)

    def test_current_rate_reflects_recent_activity(self):
        rl = RateLimiter(max_lines=100, window=2.0)
        now = 400.0
        for _ in range(6):
            rl.allow("src", now)
        assert rl.current_rate("src", now) == pytest.approx(3.0)  # 6 / 2s
