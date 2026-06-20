import hashlib
import os
from datetime import datetime, timedelta
from typing import Any


class APICache:
    """Simple in-memory cache to reduce API calls to Telegram.

    Supports TTL (time-to-live) for cache entries and persists data to disk.

    Attributes:
        cache_dir: Directory for cache files.
        ttl_seconds: Time-to-live for cache entries in seconds.
    """

    def __init__(self, cache_dir: str = "cache", ttl_seconds: int = 3600):
        """Initialize the cache.

        Args:
            cache_dir: Directory to store cache files.
            ttl_seconds: Time-to-live for cache entries (default: 3600 seconds).
        """
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self._memory_cache: dict[str, tuple] = {}
        os.makedirs(cache_dir, exist_ok=True)

    def _get_key(self, identifier: str) -> str:
        """Generate a cache key from an identifier using MD5 hash.

        Args:
            identifier: String identifier to hash.

        Returns:
            Hexadecimal MD5 hash string.
        """
        return hashlib.md5(identifier.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> str:
        """Get the file path for a cache key.

        Args:
            key: Cache key.

        Returns:
            Full path to the cache file.
        """
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, identifier: str) -> Any | None:
        """Retrieve a value from cache if it exists and is not expired.

        Args:
            identifier: Unique identifier for the cached value.

        Returns:
            The cached value if valid and not expired, otherwise None.
        """
        key = self._get_key(identifier)

        if key in self._memory_cache:
            try:
                data, timestamp = self._memory_cache[key]
                if not isinstance(timestamp, datetime):
                    del self._memory_cache[key]
                    return None
                if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                    return data
                else:
                    del self._memory_cache[key]
            except Exception:
                try:
                    del self._memory_cache[key]
                except Exception:
                    pass

        return None

    def set(self, identifier: str, data: Any) -> None:
        """Store a value in the cache.

        Args:
            identifier: Unique identifier for the value.
            data: The data to cache.
        """
        key = self._get_key(identifier)
        timestamp = datetime.now()
        self._memory_cache[key] = (data, timestamp)

    def clear(self) -> None:
        """Clear all cached data from memory and disk."""
        self._memory_cache.clear()
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.cache_dir, filename))
                except Exception:
                    pass


api_cache = APICache()
