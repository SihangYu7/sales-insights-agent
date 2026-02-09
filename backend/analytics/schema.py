"""
Dynamic Schema Discovery with Caching.

Queries actual database metadata instead of using hardcoded strings.
Falls back to hardcoded schema if discovery fails.
"""

import os
import time
from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass
from threading import Lock

if TYPE_CHECKING:
    from analytics.connector import DatabaseConnector


@dataclass
class SchemaCache:
    """Cached schema information with TTL."""
    schema_info: str
    tables: List[str]
    columns: Dict[str, List[str]]
    cached_at: float
    ttl: float = 300.0  # 5 minutes default

    def is_valid(self) -> bool:
        return (time.time() - self.cached_at) < self.ttl


class SchemaDiscovery:
    """
    Dynamic schema discovery with caching and fallback.

    Features:
    - Query actual metadata from database
    - Cache results with configurable TTL
    - Fall back to hardcoded schema on failure
    - Thread-safe caching
    """

    # Hardcoded fallback schemas
    SQLITE_FALLBACK = """
DATABASE SCHEMA (SQLite):

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

    DATABRICKS_FALLBACK_TEMPLATE = """
DATABASE SCHEMA (Databricks: {catalog}.{schema}):

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

NOTE: Tables are in catalog {catalog}, schema {schema}
"""

    def __init__(self, cache_ttl: float = 300.0):
        self._cache: Optional[SchemaCache] = None
        self._lock = Lock()
        self._cache_ttl = cache_ttl

    def get_schema_info(
        self,
        connector: 'DatabaseConnector',
        force_refresh: bool = False
    ) -> str:
        """
        Get schema information, using cache if available.

        Args:
            connector: Database connector to query
            force_refresh: Skip cache and query fresh

        Returns:
            Formatted schema string for LLM consumption
        """
        with self._lock:
            if not force_refresh and self._cache and self._cache.is_valid():
                return self._cache.schema_info

        try:
            schema_info = self._discover_schema(connector)

            with self._lock:
                self._cache = SchemaCache(
                    schema_info=schema_info,
                    tables=connector.get_table_names(),
                    columns={},
                    cached_at=time.time(),
                    ttl=self._cache_ttl
                )

            return schema_info

        except Exception as e:
            print(f"Warning: Schema discovery failed: {e}. Using fallback.")
            return self._get_fallback_schema(connector)

    def _discover_schema(self, connector: 'DatabaseConnector') -> str:
        """Query actual database metadata."""
        db_type = connector.get_db_type()

        if db_type == "sqlite":
            return self._discover_sqlite_schema(connector)
        elif db_type == "databricks":
            return self._discover_databricks_schema(connector)
        else:
            raise ValueError(f"Unknown database type: {db_type}")

    def _discover_sqlite_schema(self, connector: 'DatabaseConnector') -> str:
        """Discover SQLite schema from sqlite_master."""
        # Get all user tables (exclude sqlite internal tables)
        tables_result = connector.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' "
            "AND name NOT IN ('users', 'chat_sessions', 'query_history')"
        )

        schema_parts = ["DATABASE SCHEMA (SQLite - Dynamic Discovery):\n"]

        for table_row in tables_result:
            table_name = table_row.get('name')
            if not table_name:
                continue

            # Get column info using PRAGMA
            try:
                columns_result = connector.execute_query(
                    f"PRAGMA table_info({table_name})"
                )
            except Exception:
                continue

            schema_parts.append(f"\nTable: {table_name}")
            for col in columns_result:
                pk_marker = " (primary key)" if col.get('pk') else ""
                schema_parts.append(
                    f"- {col['name']} ({col['type']}{pk_marker})"
                )

        # Add relationship hints
        schema_parts.append("\nRELATIONSHIPS:")
        schema_parts.append("- sales.product_id links to products.id")

        # Add example queries
        schema_parts.append("\nEXAMPLE QUERIES:")
        schema_parts.append("- Total sales: SELECT SUM(total) FROM sales")
        schema_parts.append("- Sales by region: SELECT region, SUM(total) FROM sales GROUP BY region")

        return "\n".join(schema_parts)

    def _discover_databricks_schema(self, connector: 'DatabaseConnector') -> str:
        """Discover Databricks schema from information_schema."""
        catalog = connector.catalog
        schema = connector.schema

        # Query columns from information_schema
        # Note: This query is already qualified, no need to re-qualify
        columns_sql = f"""
        SELECT table_name, column_name, data_type, is_nullable
        FROM {catalog}.information_schema.columns
        WHERE table_schema = '{schema}'
        AND table_name IN ('products', 'sales')
        ORDER BY table_name, ordinal_position
        """

        result = connector.execute_query(columns_sql)

        # Group by table
        tables: Dict[str, List[Dict]] = {}
        for row in result:
            table = row['table_name']
            if table not in tables:
                tables[table] = []
            tables[table].append(row)

        schema_parts = [f"DATABASE SCHEMA (Databricks: {catalog}.{schema} - Dynamic Discovery):\n"]

        for table_name in ['products', 'sales']:  # Maintain order
            if table_name not in tables:
                continue

            columns = tables[table_name]
            schema_parts.append(f"\nTable: {table_name}")
            for col in columns:
                nullable = " (nullable)" if col['is_nullable'] == 'YES' else ""
                schema_parts.append(
                    f"- {col['column_name']} ({col['data_type']}{nullable})"
                )

        # Add relationship hints
        schema_parts.append("\nRELATIONSHIPS:")
        schema_parts.append("- sales.product_id links to products.id")

        # Add example queries
        schema_parts.append("\nEXAMPLE QUERIES:")
        schema_parts.append("- Total sales: SELECT SUM(total) FROM sales")
        schema_parts.append("- Sales by region: SELECT region, SUM(total) FROM sales GROUP BY region")

        return "\n".join(schema_parts)

    def _get_fallback_schema(self, connector: 'DatabaseConnector') -> str:
        """Return hardcoded fallback schema."""
        if connector.get_db_type() == "sqlite":
            return self.SQLITE_FALLBACK
        else:
            return self.DATABRICKS_FALLBACK_TEMPLATE.format(
                catalog=connector.catalog,
                schema=connector.schema
            )

    def invalidate_cache(self):
        """Force cache invalidation."""
        with self._lock:
            self._cache = None


# Singleton instance
_schema_discovery: Optional[SchemaDiscovery] = None


def get_schema_discovery() -> SchemaDiscovery:
    """Get or create schema discovery singleton."""
    global _schema_discovery
    if _schema_discovery is None:
        ttl = float(os.getenv("SCHEMA_CACHE_TTL", "300"))
        _schema_discovery = SchemaDiscovery(cache_ttl=ttl)
    return _schema_discovery
