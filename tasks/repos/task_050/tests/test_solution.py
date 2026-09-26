from solution import SlidingWindowRateLimiter

def test_rate_limiter_basic():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10.0)
    allowed, rem = limiter.is_allowed("client_1")
    assert allowed is True
    assert rem == 2
