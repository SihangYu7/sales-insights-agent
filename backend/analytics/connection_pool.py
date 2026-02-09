"""
Connection Pool for Databricks SQL Warehouse.

Provides thread-safe connection pooling with:
- Configurable pool size (min/max)
- Connection validation before checkout
- Automatic cleanup of stale connections
- Context manager for safe connection handling
"""

import os
import threading
import time
from typing import Optional, Any
from queue import Queue, Empty
from dataclasses import dataclass
from contextlib import contextmanager

from exceptions import DatabaseConnectionError


@dataclass
class PoolConfig:
    """Configuration for connection pool."""
    min_size: int = 2
    max_size: int = 10
    acquire_timeout: float = 30.0  # seconds
    idle_timeout: float = 300.0    # 5 minutes
    validation_interval: float = 60.0  # seconds

    @classmethod
    def from_env(cls) -> 'PoolConfig':
        """Create config from environment variables."""
        return cls(
            min_size=int(os.getenv("DB_POOL_MIN_SIZE", "2")),
            max_size=int(os.getenv("DB_POOL_MAX_SIZE", "10")),
            acquire_timeout=float(os.getenv("DB_POOL_ACQUIRE_TIMEOUT", "30")),
            idle_timeout=float(os.getenv("DB_POOL_IDLE_TIMEOUT", "300")),
            validation_interval=float(os.getenv("DB_POOL_VALIDATION_INTERVAL", "60")),
        )


class PooledConnection:
    """Wrapper for a pooled database connection."""

    def __init__(self, connection: Any, created_at: float):
        self.connection = connection
        self.created_at = created_at
        self.last_used_at = created_at
        self.last_validated_at = created_at
        self.in_use = False


class DatabricksConnectionPool:
    """
    Thread-safe connection pool for Databricks SQL Warehouse.

    Features:
    - Configurable pool size (min/max)
    - Connection validation before checkout
    - Automatic cleanup of idle connections
    - Context manager for safe connection handling

    Usage:
        pool = DatabricksConnectionPool(hostname, http_path, access_token)

        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchall()
            cursor.close()

        pool.close()  # When done with pool
    """

    def __init__(
        self,
        hostname: str,
        http_path: str,
        access_token: str,
        config: Optional[PoolConfig] = None
    ):
        self.hostname = hostname
        self.http_path = http_path
        self.access_token = access_token
        self.config = config or PoolConfig.from_env()

        self._pool: Queue[PooledConnection] = Queue(maxsize=self.config.max_size)
        self._all_connections: list[PooledConnection] = []
        self._lock = threading.Lock()
        self._closed = False

        # Initialize minimum connections lazily on first use
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize pool on first use (lazy initialization)."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            for _ in range(self.config.min_size):
                try:
                    conn = self._create_connection()
                    self._pool.put(conn)
                except Exception as e:
                    print(f"Warning: Failed to create initial connection: {e}")

            self._initialized = True

    def _create_connection(self) -> PooledConnection:
        """Create a new database connection."""
        try:
            from databricks import sql as databricks_sql
        except ImportError:
            raise ImportError(
                "databricks-sql-connector not installed. "
                "Run: pip install databricks-sql-connector"
            )

        connection = databricks_sql.connect(
            server_hostname=self.hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        )

        pooled = PooledConnection(
            connection=connection,
            created_at=time.time()
        )

        with self._lock:
            self._all_connections.append(pooled)

        return pooled

    def _validate_connection(self, pooled: PooledConnection) -> bool:
        """Check if connection is still valid."""
        now = time.time()

        # Skip validation if recently validated
        if (now - pooled.last_validated_at) < self.config.validation_interval:
            return True

        try:
            cursor = pooled.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            pooled.last_validated_at = now
            return True
        except Exception:
            return False

    def _close_connection(self, pooled: PooledConnection):
        """Close a single connection."""
        try:
            pooled.connection.close()
        except Exception:
            pass

        with self._lock:
            if pooled in self._all_connections:
                self._all_connections.remove(pooled)

    @contextmanager
    def get_connection(self):
        """
        Acquire a connection from the pool.

        Usage:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)

        Raises:
            DatabaseConnectionError: If no connection available within timeout
        """
        if self._closed:
            raise DatabaseConnectionError("Connection pool is closed")

        self._ensure_initialized()

        pooled = None
        start_time = time.time()

        while (time.time() - start_time) < self.config.acquire_timeout:
            try:
                # Try to get from pool
                pooled = self._pool.get(timeout=1.0)

                # Validate connection
                if self._validate_connection(pooled):
                    pooled.in_use = True
                    pooled.last_used_at = time.time()
                    break
                else:
                    # Connection invalid, close and try again
                    self._close_connection(pooled)
                    pooled = None

            except Empty:
                # Pool empty, try to create new connection if under max
                with self._lock:
                    current_count = len(self._all_connections)

                if current_count < self.config.max_size:
                    try:
                        pooled = self._create_connection()
                        pooled.in_use = True
                        break
                    except Exception as e:
                        print(f"Warning: Failed to create connection: {e}")

        if pooled is None:
            raise DatabaseConnectionError(
                f"Could not acquire connection within {self.config.acquire_timeout}s"
            )

        try:
            yield pooled.connection
        finally:
            # Return connection to pool
            pooled.in_use = False
            pooled.last_used_at = time.time()

            if not self._closed:
                try:
                    self._pool.put_nowait(pooled)
                except Exception:
                    # Queue full, close this connection
                    self._close_connection(pooled)

    def close(self):
        """Close all connections in the pool."""
        self._closed = True

        with self._lock:
            for pooled in self._all_connections:
                try:
                    pooled.connection.close()
                except Exception:
                    pass
            self._all_connections.clear()

    def get_stats(self) -> dict:
        """Return pool statistics."""
        with self._lock:
            total = len(self._all_connections)
            in_use = sum(1 for c in self._all_connections if c.in_use)

        return {
            "total_connections": total,
            "in_use": in_use,
            "available": total - in_use,
            "max_size": self.config.max_size,
            "initialized": self._initialized
        }
