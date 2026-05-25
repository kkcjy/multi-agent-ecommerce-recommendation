from __future__ import annotations

import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """Simple fixed-window limiter for demo and classroom defense."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str) -> tuple[bool, int]:
        now = time.time()
        window_start = now - self.window_seconds
        queue = self._events[key]

        while queue and queue[0] < window_start:
            queue.popleft()

        if len(queue) >= self.limit:
            return False, max(0, int(queue[0] + self.window_seconds - now))

        queue.append(now)
        return True, 0
