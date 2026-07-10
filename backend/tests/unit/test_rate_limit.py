from core.rate_limit import SlidingWindowRateLimiter


def test_rate_limiter_blocks_after_limit():
    limiter = SlidingWindowRateLimiter()
    key = "test-key"
    assert limiter.allow(key, limit=2, window_sec=60.0)
    assert limiter.allow(key, limit=2, window_sec=60.0)
    assert not limiter.allow(key, limit=2, window_sec=60.0)
