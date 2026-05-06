"""Tests for logpulse.ratelimit_middleware."""
from logpulse.ratelimit_middleware import RateLimitMiddleware


def _collector():
    """Return a list and a callback that appends (source, line) tuples."""
    received = []

    def cb(source, line):
        received.append((source, line))

    return received, cb


class TestRateLimitMiddleware:
    def test_lines_within_limit_pass_through(self):
        received, cb = _collector()
        mw = RateLimitMiddleware(cb, max_lines=5, window=1.0)
        now = 10.0
        for i in range(5):
            mw._limiter.allow = lambda s, t=None, _orig=mw._limiter.allow: _orig(s, now)
        # Use the limiter directly with a fixed timestamp
        limiter = mw._limiter
        for i in range(5):
            assert limiter.allow("src", now) is True

    def test_lines_over_limit_are_dropped(self):
        received, cb = _collector()
        mw = RateLimitMiddleware(cb, max_lines=2, window=1.0)
        now = 20.0
        # Manually seed the limiter so allow() uses our timestamp
        for _ in range(2):
            mw._limiter.allow("app", now)
        # Now the bucket is full; simulate on_line with patched allow
        original_allow = mw._limiter.allow

        def patched(source, t=None):
            return original_allow(source, now)

        mw._limiter.allow = patched
        mw.on_line("app", "should be dropped")
        assert ("app", "should be dropped") not in received
        assert mw.dropped_count("app") == 1

    def test_suppression_warning_emitted_on_recovery(self):
        warnings, warn_cb = _collector()
        received, cb = _collector()
        mw = RateLimitMiddleware(cb, max_lines=2, window=1.0, warn_cb=warn_cb)
        t0 = 30.0
        # Fill the bucket
        for _ in range(2):
            mw._limiter.allow("svc", t0)
        # Drop 3 lines
        for _ in range(3):
            mw._limiter.allow = lambda s, t=None: False  # force deny
            mw.on_line("svc", "dropped")
        assert mw.dropped_count("svc") == 3
        # Restore allow to always permit
        mw._limiter.allow = lambda s, t=None: True
        mw.on_line("svc", "recovered line")
        # Warning should have been emitted
        assert any("3 line(s) suppressed" in line for _, line in warnings)
        assert mw.dropped_count("svc") == 0

    def test_flush_warnings_emits_pending(self):
        warnings, warn_cb = _collector()
        received, cb = _collector()
        mw = RateLimitMiddleware(cb, max_lines=1, window=1.0, warn_cb=warn_cb)
        # Force two drops
        mw._limiter.allow = lambda s, t=None: False
        mw.on_line("x", "a")
        mw.on_line("x", "b")
        assert mw.dropped_count("x") == 2
        mw.flush_warnings()
        assert any("2 line(s) suppressed" in line for _, line in warnings)
        assert mw.dropped_count("x") == 0

    def test_callable_interface(self):
        received, cb = _collector()
        mw = RateLimitMiddleware(cb, max_lines=10, window=1.0)
        mw._limiter.allow = lambda s, t=None: True
        mw("src", "hello")
        assert ("src", "hello") in received
