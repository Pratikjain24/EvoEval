"""Thread-safe In-Memory Sliding Window Rate Limiter for Public Leaderboard API.

Protects against denial-of-service (DoS), automated scraping, and brute-force attacks.
Emits standard HTTP 429 Too Many Requests with Retry-After and X-RateLimit-* headers.
"""

from __future__ import annotations
import os
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Optional, Tuple
from fastapi import HTTPException, Request, Response, status


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter per client IP."""

    def __init__(
        self,
        default_limit: int = 120,
        window_seconds: int = 60,
        cleanup_interval_seconds: int = 300,
    ):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._lock = threading.Lock()
        # Mapping from client_ip -> deque of timestamps
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._last_cleanup = time.time()

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP handling forward proxies securely."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # First IP in X-Forwarded-For list is client IP
            client_ip = forwarded.split(",")[0].strip()
            if client_ip:
                return client_ip
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def is_rate_limited(
        self, client_ip: str, limit: Optional[int] = None
    ) -> Tuple[bool, int, int, int]:
        """Check if client IP has exceeded the allowed rate.

        Returns:
            (is_limited, remaining, reset_seconds, effective_limit)
        """
        now = time.time()
        effective_limit = limit if limit is not None else self.default_limit
        cutoff = now - self.window_seconds

        with self._lock:
            # Periodic cleanup of idle IPs to prevent memory leaks
            if now - self._last_cleanup > self.cleanup_interval_seconds:
                self._cleanup_stale_ips(cutoff)
                self._last_cleanup = now

            timestamps = self._hits[client_ip]

            # Remove timestamps outside current sliding window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            current_count = len(timestamps)

            if current_count >= effective_limit:
                # Exceeded rate limit
                oldest = timestamps[0]
                reset_seconds = max(1, int(oldest + self.window_seconds - now))
                return True, 0, reset_seconds, effective_limit

            # Record this valid request
            timestamps.append(now)
            remaining = max(0, effective_limit - len(timestamps))
            reset_seconds = self.window_seconds
            return False, remaining, reset_seconds, effective_limit

    def _cleanup_stale_ips(self, cutoff: float) -> None:
        """Evict IPs with no active timestamps in the window."""
        stale_keys = [
            ip for ip, d in self._hits.items()
            if not d or d[-1] < cutoff
        ]
        for ip in stale_keys:
            del self._hits[ip]

    def reset(self) -> None:
        """Clear all recorded hits (useful for testing)."""
        with self._lock:
            self._hits.clear()


# Global rate limiter instance
_global_limiter = SlidingWindowRateLimiter(
    default_limit=int(os.environ.get("RATE_LIMIT_READ_PER_MINUTE", "120")),
    window_seconds=60,
)


def get_global_rate_limiter() -> SlidingWindowRateLimiter:
    return _global_limiter


def rate_limit(
    limit: Optional[int] = None,
    window_seconds: int = 60,
) -> Callable:
    """FastAPI dependency factory enforcing rate limits on endpoints."""
    async def dependency(request: Request, response: Response) -> None:
        # Check if rate limiting is globally disabled for testing/benchmarks
        if os.environ.get("EVOEVAL_DISABLE_RATE_LIMIT", "false").lower() in ("true", "1"):
            return

        limiter = get_global_rate_limiter()
        env_override = os.environ.get("RATE_LIMIT_OVERRIDE")
        effective_limit = int(env_override) if env_override is not None else limit

        client_ip = limiter.get_client_ip(request)
        is_limited, remaining, reset_secs, max_limit = limiter.is_rate_limited(
            client_ip, limit=effective_limit
        )

        # Attach standard rate limit headers
        response.headers["X-RateLimit-Limit"] = str(max_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_secs)

        if is_limited:
            response.headers["Retry-After"] = str(reset_secs)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_limit} requests per minute. Retry in {reset_secs} seconds.",
                headers={
                    "Retry-After": str(reset_secs),
                    "X-RateLimit-Reset": str(reset_secs),
                },
            )

    return dependency
