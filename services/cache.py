import threading
import time
from typing import Any, Optional


class CacheProvider:
    def get(self, key: str) -> Any:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError


class MemoryCache(CacheProvider):
    def __init__(self) -> None:
        self._store = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                self._misses += 1
                return None
            value, exp = item
            if exp is not None and exp < now:
                self._store.pop(key, None)
                self._misses += 1
                return None
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        exp = time.time() + ttl if ttl else None
        with self._lock:
            self._store[key] = (value, exp)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            ratio = (self._hits / total) if total else 0.0
            return {"hits": self._hits, "misses": self._misses, "hit_ratio": ratio}


# Global cache instance (simple for now)
memory_cache = MemoryCache()


