"""
Database Connector Abstraction Layer
=====================================
Factory pattern for supporting multiple database backends:
- SQLite (development, default)
- Databricks (production, optional)

Environment Variables:
- USE_DATABRICKS: Set to "true" to enable Databricks
- DATABRICKS_SERVER_HOSTNAME: Databricks SQL Warehouse hostname
- DATABRICKS_HTTP_PATH: SQL Warehouse HTTP path
- DATABRICKS_ACCESS_TOKEN: Personal access token
- DATABRICKS_CATALOG: Unity Catalog name (default: "main")
- DATABRICKS_SCHEMA: Schema name (default: "default")
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


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
        """Execute a SQL query and return results."""
        session = self.SessionLocal()
        try:
            result = session.execute(text(sql))
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return rows
        except Exception as e:
            return {"error": str(e)}
        finally:
            session.close()

    def get_schema_info(self) -> str:
        """Return SQLite schema information."""
        return """
    DATABASE SCHEMA:

    Table: products
    - id (INTEGER, primary key)
    - name (TEXT) - product name like 'Laptop', 'Smartphone'
    - category (TEXT) - category like 'Electronics', 'Furniture', 'Books'
    - price (REAL) - price in dollars

    Table: sales
    - id (INTEGER, primary key)
    - product_id (INTEGER) - references products.id
    - quantity (INTEGER) - number of items sold
    - total (REAL) - total sale amount in dollars
    - sale_date (DATE) - when the sale happened
    - region (TEXT) - 'North', 'South', 'East', or 'West'

    RELATIONSHIPS:
    - sales.product_id links to products.id
    - To get product names with sales, JOIN the tables

    EXAMPLE QUERIES:
    - Total sales: SELECT SUM(total) FROM sales
    - Sales by region: SELECT region, SUM(total) FROM sales GROUP BY region
    - Top products: SELECT p.name, SUM(s.total) FROM sales s JOIN products p ON s.product_id = p.id GROUP BY p.name ORDER BY SUM(s.total) DESC
    """

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
        except Exception:
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

        # Connection caching
        self._connection = None

        # Health check caching
        self._healthy: Optional[bool] = None
        self._last_health_check: float = 0
        self._health_check_interval: float = 60  # seconds

    def _get_connection(self):
        """Get or create Databricks connection."""
        if self._connection is None:
            try:
                from databricks import sql as databricks_sql

                self._connection = databricks_sql.connect(
                    server_hostname=self.hostname,
                    http_path=self.http_path,
                    access_token=self.access_token,
                )
            except ImportError:
                raise ImportError(
                    "databricks-sql-connector not installed. "
                    "Run: pip install databricks-sql-connector"
                )
        return self._connection

    def _qualify_table_name(self, table: str) -> str:
        """Add catalog.schema prefix to table name."""
        return f"{self.catalog}.{self.schema}.{table}"

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute query on Databricks SQL Warehouse."""
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Qualify table names in the query
            # Simple approach: prefix common table names
            qualified_sql = sql
            for table in ["products", "sales"]:
                # Replace standalone table names (not already qualified)
                qualified_sql = qualified_sql.replace(
                    f" {table} ", f" {self._qualify_table_name(table)} "
                )
                qualified_sql = qualified_sql.replace(
                    f" {table}\n", f" {self._qualify_table_name(table)}\n"
                )
                qualified_sql = qualified_sql.replace(
                    f"from {table}", f"from {self._qualify_table_name(table)}"
                )
                qualified_sql = qualified_sql.replace(
                    f"FROM {table}", f"FROM {self._qualify_table_name(table)}"
                )
                qualified_sql = qualified_sql.replace(
                    f"join {table}", f"join {self._qualify_table_name(table)}"
                )
                qualified_sql = qualified_sql.replace(
                    f"JOIN {table}", f"JOIN {self._qualify_table_name(table)}"
                )

            cursor.execute(qualified_sql)

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return rows
            return []
        except Exception as e:
            return {"error": str(e)}
        finally:
            if cursor:
                cursor.close()

    def get_schema_info(self) -> str:
        """Return Databricks schema information."""
        schema_text = f"""
    DATABASE SCHEMA (Databricks: {self.catalog}.{self.schema}):

    Table: products
    - id (BIGINT, primary key)
    - name (STRING) - product name like 'Laptop', 'Smartphone'
    - category (STRING) - category like 'Electronics', 'Furniture', 'Books'
    - price (DOUBLE) - price in dollars

    Table: sales
    - id (BIGINT, primary key)
    - product_id (BIGINT) - references products.id
    - quantity (INT) - number of items sold
    - total (DOUBLE) - total sale amount in dollars
    - sale_date (DATE) - when the sale happened
    - region (STRING) - 'North', 'South', 'East', or 'West'

    RELATIONSHIPS:
    - sales.product_id links to products.id
    - To get product names with sales, JOIN the tables

    EXAMPLE QUERIES:
    - Total sales: SELECT SUM(total) FROM sales
    - Sales by region: SELECT region, SUM(total) FROM sales GROUP BY region
    - Top products: SELECT p.name, SUM(s.total) FROM sales s JOIN products p ON s.product_id = p.id GROUP BY p.name ORDER BY SUM(s.total) DESC

    NOTE: Tables are in catalog {self.catalog}, schema {self.schema}
    """
        return schema_text

    def get_langchain_uri(self) -> str:
        """
        Return Databricks connection URI for LangChain.

        Note: LangChain's SQLDatabase doesn't natively support Databricks well.
        This returns a format that may require custom handling.
        """
        # Databricks SQLAlchemy format (requires sqlalchemy-databricks)
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
        except Exception as e:
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
    Uses USE_DATABRICKS environment variable to determine backend.

    Returns cached singleton instance for performance.
    """
    global _connector_instance

    if _connector_instance is not None:
        return _connector_instance

    use_databricks = os.getenv("USE_DATABRICKS", "false").lower() == "true"

    if use_databricks:
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
