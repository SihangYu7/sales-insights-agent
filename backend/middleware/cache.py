"""
Response Caching Middleware
===========================
In-memory response caching with TTL for reducing API costs.

Features:
- In-memory cache with configurable TTL
- Cache key generation from query + user context
- Automatic cache invalidation
- Cache statistics tracking
- Redis-ready interface for production
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
from functools import wraps


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""
    value: Any
    created_at: float
    ttl: float
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() > (self.created_at + self.ttl)

    def get_age(self) -> float:
        """Get age of this entry in seconds."""
        return time.time() - self.created_at


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_entries: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


class ResponseCache:
    """
    In-memory response cache with TTL support.

    Usage:
        cache = ResponseCache(default_ttl=300)  # 5 minute default TTL

        # Check cache
        cached = cache.get(question="What are total sales?", user_id=123)
        if cached:
            return cached

        # Compute response...
        response = compute_expensive_response()

        # Store in cache
        cache.set(
            question="What are total sales?",
            user_id=123,
            value=response
        )
    """

    def __init__(
        self,
        default_ttl: float = 300,  # 5 minutes
        max_entries: int = 1000,
        cleanup_interval: float = 60
    ):
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._last_cleanup = time.time()

    def _generate_key(
        self,
        question: str,
        user_id: Optional[int] = None,
        agent_type: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a unique cache key from query parameters.

        Keys are hashed to ensure consistent length and avoid special characters.
        """
        key_parts = {
            "question": question.lower().strip(),
            "user_id": user_id,
            "agent_type": agent_type,
            **kwargs
        }
        key_string = json.dumps(key_parts, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        if current_time - self._last_cleanup < self.cleanup_interval:
            return

        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]
            self._stats.evictions += 1

        self._stats.total_entries = len(self._cache)
        self._last_cleanup = current_time

    def _evict_lru(self) -> None:
        """Evict least recently used entry when cache is full."""
        if len(self._cache) < self.max_entries:
            return

        # Find oldest entry
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        del self._cache[oldest_key]
        self._stats.evictions += 1

    def get(
        self,
        question: str,
        user_id: Optional[int] = None,
        agent_type: Optional[str] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Get a cached response if available and not expired.

        Args:
            question: The query question
            user_id: User ID for context-specific caching
            agent_type: Type of agent (e.g., "text_to_sql", "tool_agent")
            **kwargs: Additional key parameters

        Returns:
            Cached value if found and valid, None otherwise
        """
        self._cleanup_expired()

        key = self._generate_key(question, user_id, agent_type, **kwargs)
        entry = self._cache.get(key)

        if entry is None:
            self._stats.misses += 1
            return None

        if entry.is_expired():
            del self._cache[key]
            self._stats.misses += 1
            self._stats.evictions += 1
            return None

        entry.hits += 1
        self._stats.hits += 1
        return entry.value

    def set(
        self,
        question: str,
        value: Any,
        user_id: Optional[int] = None,
        agent_type: Optional[str] = None,
        ttl: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Store a response in the cache.

        Args:
            question: The query question
            value: The response to cache
            user_id: User ID for context-specific caching
            agent_type: Type of agent
            ttl: Time-to-live in seconds (uses default if not specified)
            **kwargs: Additional key parameters

        Returns:
            The cache key
        """
        self._cleanup_expired()
        self._evict_lru()

        key = self._generate_key(question, user_id, agent_type, **kwargs)
        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl if ttl is not None else self.default_ttl
        )
        self._stats.total_entries = len(self._cache)

        return key

    def invalidate(
        self,
        question: Optional[str] = None,
        user_id: Optional[int] = None,
        agent_type: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        Invalidate cache entries matching the given parameters.

        If no parameters are given, clears entire cache.

        Returns:
            Number of entries invalidated
        """
        if question is None and user_id is None and agent_type is None and not kwargs:
            # Clear all
            count = len(self._cache)
            self._cache.clear()
            self._stats.evictions += count
            self._stats.total_entries = 0
            return count

        # Invalidate specific key
        key = self._generate_key(
            question or "",
            user_id,
            agent_type,
            **kwargs
        )

        if key in self._cache:
            del self._cache[key]
            self._stats.evictions += 1
            self._stats.total_entries = len(self._cache)
            return 1

        return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "hit_rate": f"{self._stats.hit_rate:.1f}%",
            "evictions": self._stats.evictions,
            "total_entries": self._stats.total_entries,
            "max_entries": self.max_entries,
            "default_ttl": self.default_ttl
        }


# Global cache instance
_response_cache = ResponseCache()


def get_response_cache() -> ResponseCache:
    """Get the global response cache instance."""
    return _response_cache


def get_cached_response(
    question: str,
    user_id: Optional[int] = None,
    agent_type: Optional[str] = None,
    **kwargs
) -> Optional[Any]:
    """
    Convenience function to get cached response.

    Args:
        question: The query question
        user_id: User ID
        agent_type: Agent type

    Returns:
        Cached response or None
    """
    return _response_cache.get(question, user_id, agent_type, **kwargs)


def cache_response(
    question: str,
    value: Any,
    user_id: Optional[int] = None,
    agent_type: Optional[str] = None,
    ttl: Optional[float] = None,
    **kwargs
) -> str:
    """
    Convenience function to cache a response.

    Args:
        question: The query question
        value: Response to cache
        user_id: User ID
        agent_type: Agent type
        ttl: Time-to-live in seconds

    Returns:
        Cache key
    """
    return _response_cache.set(question, value, user_id, agent_type, ttl, **kwargs)


def with_cache(agent_type: str = "default", ttl: Optional[float] = None):
    """
    Decorator to add caching to agent functions.

    Usage:
        @with_cache(agent_type="text_to_sql", ttl=300)
        def text_to_sql_agent(question, user_id=None):
            ...

    The decorated function must accept 'question' as first arg
    and optionally 'user_id' as keyword arg.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(question: str, *args, user_id: Optional[int] = None, **kwargs):
            # Check cache first
            cached = get_cached_response(
                question=question,
                user_id=user_id,
                agent_type=agent_type
            )

            if cached is not None:
                # Add cache hit indicator
                if isinstance(cached, dict):
                    cached["cache_hit"] = True
                return cached

            # Execute function
            result = f(question, *args, user_id=user_id, **kwargs)

            # Cache successful results
            if isinstance(result, dict) and result.get("success", True):
                cache_response(
                    question=question,
                    value=result,
                    user_id=user_id,
                    agent_type=agent_type,
                    ttl=ttl
                )
                result["cache_hit"] = False

            return result

        return wrapper
    return decorator
