"""Thread-safe in-memory time-to-live (TTL) cache implementation."""

import threading
import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Thread-safe in-memory key-value cache with per-entry expiration."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._store: dict[str, tuple[T, float]] = {}

    def get(self, key: str) -> T | None:
        """Return cached value or None if missing or expired."""
        with self._lock:
            if key not in self._store:
                return None
            value, expires_at = self._store[key]
            if time.time() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: T) -> None:
        """Store value under key. Entry expires after ttl_seconds."""
        expires_at = time.time() + self._ttl_seconds
        with self._lock:
            self._store[key] = (value, expires_at)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries from cache."""
        with self._lock:
            self._store.clear()
