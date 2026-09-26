from solution import SlidingWindowRateLimiter

def test_gt_burst_limit_enforced():
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=1.0)
    for _ in range(5):
        ok, _ = limiter.is_allowed("victim_ip")
        assert ok is True
    
    # 6th request must be rejected
    ok, rem = limiter.is_allowed("victim_ip")
    assert ok is False
    assert rem == 0

def test_gt_ip_isolation():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=1.0)
    limiter.is_allowed("ip_a")
    limiter.is_allowed("ip_a")
    # ip_b must still be allowed
    ok, rem = limiter.is_allowed("ip_b")
    assert ok is True
