import time
from collections import defaultdict


class SlidingWindowRateLimiter:
    """In-process sliding window limiter with stale-key pruning."""

    def __init__(self, *, max_keys: int = 100_000) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._max_keys = max_keys

    def allow(self, key: str, *, limit: int, window_sec: float) -> bool:
        now = time.time()
        cutoff = now - window_sec
        bucket = [t for t in self._buckets.get(key, []) if t > cutoff]
        if len(bucket) >= limit:
            self._buckets[key] = bucket
            self._maybe_prune(now, window_sec)
            return False
        bucket.append(now)
        self._buckets[key] = bucket
        self._maybe_prune(now, window_sec)
        return True

    def _maybe_prune(self, now: float, window_sec: float) -> None:
        if len(self._buckets) <= self._max_keys:
            return
        cutoff = now - window_sec
        stale = [key for key, times in self._buckets.items() if not times or times[-1] <= cutoff]
        for key in stale:
            del self._buckets[key]

    def reset(self) -> None:
        self._buckets.clear()
