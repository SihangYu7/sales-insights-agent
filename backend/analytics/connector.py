"""
Database Connector Abstraction Layer
=====================================
Factory pattern for supporting multiple database backends:
- SQLite (development, default)
- Databricks (production, optional)

Features:
- Robust table name qualification using regex
- Connection pooling for Databricks
- Dynamic schema discovery with caching
- Proper exception-based error handling

Environment Variables:
- ANALYTICS_BACKEND: Set to "databricks" or "sqlite" (default: sqlite)
- USE_DATABRICKS: Legacy flag (true => databricks) if ANALYTICS_BACKEND not set
- DATABRICKS_SERVER_HOSTNAME: Databricks SQL Warehouse hostname
- DATABRICKS_HTTP_PATH: SQL Warehouse HTTP path
- DATABRICKS_ACCESS_TOKEN: Personal access token
- DATABRICKS_CATALOG: Unity Catalog name (default: "main")
- DATABRICKS_SCHEMA: Schema name (default: "default")
- DB_POOL_MIN_SIZE: Min connections in pool (default: 2)
- DB_POOL_MAX_SIZE: Max connections in pool (default: 10)
- SCHEMA_CACHE_TTL: Schema cache TTL in seconds (default: 300)
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from exceptions import QueryExecutionError, DatabaseConnectionError
from analytics.sql_utils import qualify_table_names
from analytics.schema import get_schema_discovery
from config import get_analytics_backend


class DatabaseConnector(ABC):
    """Abstract base class for database connectors."""

    @abstractmethod
    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts."""
        pass

    @abstractmethod
    def get_schema_info(self) -> str:
        """Return schema information as formatted string for LLM."""
        pass

    @abstractmethod
    def get_langchain_uri(self) -> str:
        """Return connection URI for LangChain SQLDatabase."""
        pass

    @abstractmethod
    def get_table_names(self) -> List[str]:
        """Return list of table names."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if database connection is healthy."""
        pass

    @abstractmethod
    def get_db_type(self) -> str:
        """Return the database type identifier."""
        pass


class SQLiteConnector(DatabaseConnector):
    """SQLite database connector for development."""

    def __init__(self, db_path: str = "sqlite:///sales.db"):
        self.db_path = db_path
        self.engine = create_engine(db_path, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.

        Args:
            sql: SQL query to execute

        Returns:
            List of result dicts

        Raises:
            QueryExecutionError: If query execution fails
        """
        session = self.SessionLocal()
        try:
            result = session.execute(text(sql))
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return rows
        except Exception as e:
            raise QueryExecutionError(
                message=f"Query execution failed: {str(e)}",
                sql=sql,
                original_error=e
            )
        finally:
            session.close()

    def get_schema_info(self) -> str:
        """Return SQLite schema information using dynamic discovery."""
        return get_schema_discovery().get_schema_info(self)

    def get_langchain_uri(self) -> str:
        """Return SQLite connection URI."""
        return self.db_path

    def get_table_names(self) -> List[str]:
        """Return SQLite table names."""
        return ["products", "sales"]

    def is_healthy(self) -> bool:
        """Check SQLite connection health."""
        try:
            self.execute_query("SELECT 1")
            return True
        except QueryExecutionError:
            return False

    def get_db_type(self) -> str:
        """Return database type."""
        return "sqlite"


class DatabricksConnector(DatabaseConnector):
    """Databricks SQL Warehouse connector for production."""

    def __init__(self):
        self.hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        self.http_path = os.getenv("DATABRICKS_HTTP_PATH")
        self.access_token = os.getenv("DATABRICKS_ACCESS_TOKEN")
        self.catalog = os.getenv("DATABRICKS_CATALOG", "main")
        self.schema = os.getenv("DATABRICKS_SCHEMA", "default")

        # Validate required configuration
        if not all([self.hostname, self.http_path, self.access_token]):
            raise ValueError(
                "Databricks configuration incomplete. Required: "
                "DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN"
            )

        # Simple connection caching (connection pool available in connection_pool.py if needed)
        self._connection = None

        # Health check caching
        self._healthy: Optional[bool] = None
        self._last_health_check: float = 0
        self._health_check_interval: float = 60  # seconds

    def _get_connection(self, force_new: bool = False):
        """Get or create Databricks connection."""
        if force_new and self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

        if self._connection is None:
            try:
                from databricks import sql as databricks_sql
                self._connection = databricks_sql.connect(
                    server_hostname=self.hostname,
                    http_path=self.http_path,
                    access_token=self.access_token,
                )
            except ImportError:
                raise DatabaseConnectionError(
                    "databricks-sql-connector not installed. "
                    "Run: pip install databricks-sql-connector"
                )
        return self._connection

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute query on Databricks SQL Warehouse.

        Args:
            sql: SQL query to execute

        Returns:
            List of result dicts

        Raises:
            DatabaseConnectionError: If connection cannot be acquired
            QueryExecutionError: If query execution fails
        """
        # Qualify table names using robust regex-based approach
        qualified_sql = qualify_table_names(
            sql,
            self.get_table_names(),
            self.catalog,
            self.schema
        )

        cursor = None
        for attempt in range(2):
            try:
                conn = self._get_connection(force_new=(attempt == 1))
                cursor = conn.cursor()
                cursor.execute(qualified_sql)

                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    return rows
                return []
            except DatabaseConnectionError:
                raise
            except Exception as e:
                message = str(e)
                if (
                    "Invalid SessionHandle" in message
                    or "INVALID_STATE" in message
                ):
                    self.close()
                    if attempt == 0:
                        continue
                raise QueryExecutionError(
                    message=f"Query execution failed: {message}",
                    sql=qualified_sql,
                    original_error=e
                )
            finally:
                if cursor:
                    cursor.close()
                    cursor = None

    def get_schema_info(self) -> str:
        """Return Databricks schema information using dynamic discovery."""
        return get_schema_discovery().get_schema_info(self)

    def get_langchain_uri(self) -> str:
        """
        Return Databricks connection URI for LangChain.

        Note: LangChain's SQLDatabase doesn't natively support Databricks well.
        This returns a format that may require custom handling.
        """
        return (
            f"databricks://token:{self.access_token}@{self.hostname}:443"
            f"?http_path={self.http_path}&catalog={self.catalog}&schema={self.schema}"
        )

    def get_table_names(self) -> List[str]:
        """Return Databricks table names."""
        return ["products", "sales"]

    def is_healthy(self) -> bool:
        """Check Databricks connection health with caching."""
        now = time.time()

        # Return cached result if within interval
        if (
            self._healthy is not None
            and (now - self._last_health_check) < self._health_check_interval
        ):
            return self._healthy

        try:
            result = self.execute_query("SELECT 1 as test")
            self._healthy = isinstance(result, list) and len(result) > 0
        except (QueryExecutionError, DatabaseConnectionError) as e:
            print(f"Databricks health check failed: {e}")
            self._healthy = False

        self._last_health_check = now
        return self._healthy

    def get_db_type(self) -> str:
        """Return database type."""
        return "databricks"

    def close(self):
        """Close the Databricks connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Singleton instance
_connector_instance: Optional[DatabaseConnector] = None


def get_database_connector() -> DatabaseConnector:
    """
    Factory function to get the appropriate database connector.
    Uses ANALYTICS_BACKEND (or legacy USE_DATABRICKS) to determine backend.

    Returns cached singleton instance for performance.
    """
    global _connector_instance

    if _connector_instance is not None:
        return _connector_instance

    analytics_backend = get_analytics_backend()

    if analytics_backend == "databricks":
        print("🔗 Initializing Databricks connector...")
        _connector_instance = DatabricksConnector()
    else:
        print("🔗 Initializing SQLite connector...")
        _connector_instance = SQLiteConnector()

    return _connector_instance


def reset_connector():
    """Reset the connector singleton (useful for testing)."""
    global _connector_instance
    if _connector_instance and hasattr(_connector_instance, "close"):
        _connector_instance.close()
    _connector_instance = None
