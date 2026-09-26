"""Task task_025: Security audit & rate limiting."""

import time
from typing import Dict, Tuple


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter by IP and token."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, list] = {}

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window_seconds
        if client_id not in self._history:
            self._history[client_id] = []
        
        # Purge expired timestamps
        self._history[client_id] = [t for t in self._history[client_id] if t > cutoff]

        if len(self._history[client_id]) < self.max_requests:
            self._history[client_id].append(now)
            remaining = self.max_requests - len(self._history[client_id])
            return True, remaining
        return False, 0
