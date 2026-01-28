"""
Rate Limiting Middleware
========================
Per-user and per-endpoint rate limiting for API protection.

Features:
- In-memory rate limiting (development)
- Per-user request limits
- Configurable time windows
- Integration with Flask routes
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from functools import wraps
from flask import request, jsonify, g


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 10
    requests_per_hour: int = 100
    burst_limit: int = 5  # Max requests in 10 seconds


@dataclass
class UserRateData:
    """Tracks rate limit data for a single user."""
    minute_requests: list = field(default_factory=list)
    hour_requests: list = field(default_factory=list)
    burst_requests: list = field(default_factory=list)


class RateLimiter:
    """
    In-memory rate limiter with per-user tracking.

    Usage:
        limiter = RateLimiter()

        # Check if request is allowed
        allowed, info = limiter.check_limit(user_id=123)
        if not allowed:
            return jsonify({"error": info["message"]}), 429
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.user_data: Dict[int, UserRateData] = defaultdict(UserRateData)
        self._cleanup_interval = 60  # Cleanup old data every 60 seconds
        self._last_cleanup = time.time()

    def _cleanup_old_requests(self, user_data: UserRateData, current_time: float) -> None:
        """Remove expired timestamps from tracking lists."""
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        burst_window = current_time - 10

        user_data.minute_requests = [t for t in user_data.minute_requests if t > minute_ago]
        user_data.hour_requests = [t for t in user_data.hour_requests if t > hour_ago]
        user_data.burst_requests = [t for t in user_data.burst_requests if t > burst_window]

    def _maybe_global_cleanup(self) -> None:
        """Periodically clean up data for inactive users."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            inactive_users = []
            for user_id, data in self.user_data.items():
                if not data.hour_requests:
                    inactive_users.append(user_id)
            for user_id in inactive_users:
                del self.user_data[user_id]
            self._last_cleanup = current_time

    def check_limit(self, user_id: Optional[int] = None) -> Tuple[bool, Dict]:
        """
        Check if a request from a user is within rate limits.

        Args:
            user_id: The user ID to check. If None, uses a default key.

        Returns:
            Tuple of (allowed: bool, info: dict)
            - allowed: True if request is within limits
            - info: Contains remaining limits or error message
        """
        current_time = time.time()
        self._maybe_global_cleanup()

        # Use user_id or a default for unauthenticated requests
        key = user_id if user_id is not None else -1
        user_data = self.user_data[key]

        # Cleanup old timestamps
        self._cleanup_old_requests(user_data, current_time)

        # Check burst limit (10 second window)
        if len(user_data.burst_requests) >= self.config.burst_limit:
            retry_after = 10 - (current_time - user_data.burst_requests[0])
            return False, {
                "allowed": False,
                "message": f"Rate limit exceeded. Too many requests. Retry after {retry_after:.1f} seconds.",
                "retry_after": retry_after,
                "limit_type": "burst"
            }

        # Check minute limit
        if len(user_data.minute_requests) >= self.config.requests_per_minute:
            retry_after = 60 - (current_time - user_data.minute_requests[0])
            return False, {
                "allowed": False,
                "message": f"Rate limit exceeded. {self.config.requests_per_minute} requests per minute allowed.",
                "retry_after": retry_after,
                "limit_type": "minute"
            }

        # Check hourly limit
        if len(user_data.hour_requests) >= self.config.requests_per_hour:
            retry_after = 3600 - (current_time - user_data.hour_requests[0])
            return False, {
                "allowed": False,
                "message": f"Rate limit exceeded. {self.config.requests_per_hour} requests per hour allowed.",
                "retry_after": retry_after,
                "limit_type": "hour"
            }

        # Request is allowed - record it
        user_data.burst_requests.append(current_time)
        user_data.minute_requests.append(current_time)
        user_data.hour_requests.append(current_time)

        return True, {
            "allowed": True,
            "remaining_minute": self.config.requests_per_minute - len(user_data.minute_requests),
            "remaining_hour": self.config.requests_per_hour - len(user_data.hour_requests),
            "remaining_burst": self.config.burst_limit - len(user_data.burst_requests)
        }

    def get_user_status(self, user_id: Optional[int] = None) -> Dict:
        """Get current rate limit status for a user."""
        current_time = time.time()
        key = user_id if user_id is not None else -1
        user_data = self.user_data[key]

        self._cleanup_old_requests(user_data, current_time)

        return {
            "user_id": user_id,
            "requests_in_minute": len(user_data.minute_requests),
            "requests_in_hour": len(user_data.hour_requests),
            "remaining_minute": self.config.requests_per_minute - len(user_data.minute_requests),
            "remaining_hour": self.config.requests_per_hour - len(user_data.hour_requests),
            "limits": {
                "per_minute": self.config.requests_per_minute,
                "per_hour": self.config.requests_per_hour,
                "burst": self.config.burst_limit
            }
        }


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter


def check_rate_limit(user_id: Optional[int] = None) -> Tuple[bool, Dict]:
    """
    Convenience function to check rate limit using global instance.

    Args:
        user_id: User ID to check

    Returns:
        Tuple of (allowed, info)
    """
    return _rate_limiter.check_limit(user_id)


def rate_limit(f):
    """
    Decorator to apply rate limiting to Flask routes.

    Usage:
        @app.route('/api/agent', methods=['POST'])
        @require_auth
        @rate_limit
        def agent_endpoint():
            ...

    Note: Should be applied AFTER @require_auth so g.user_id is available.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = getattr(g, 'user_id', None)
        allowed, info = check_rate_limit(user_id)

        if not allowed:
            response = jsonify({
                "error": info["message"],
                "retry_after": info.get("retry_after"),
                "limit_type": info.get("limit_type")
            })
            response.headers["Retry-After"] = str(int(info.get("retry_after", 60)))
            return response, 429

        # Add rate limit info to response headers
        response = f(*args, **kwargs)

        # If response is a tuple (response, status_code), handle it
        if isinstance(response, tuple):
            resp_obj, status_code = response[0], response[1]
        else:
            resp_obj = response
            status_code = None

        # Try to add headers (only works with Response objects)
        try:
            resp_obj.headers["X-RateLimit-Remaining-Minute"] = str(info.get("remaining_minute", 0))
            resp_obj.headers["X-RateLimit-Remaining-Hour"] = str(info.get("remaining_hour", 0))
        except AttributeError:
            pass

        return response

    return decorated_function
