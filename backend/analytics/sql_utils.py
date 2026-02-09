"""
SQL Utilities for query transformation.

Provides robust table name qualification using regex patterns
instead of fragile string replacement.
"""

import re
from typing import List


def qualify_table_names(
    sql: str,
    tables: List[str],
    catalog: str,
    schema: str
) -> str:
    """
    Qualify unqualified table names with catalog.schema prefix.

    Uses regex with word boundaries for reliable matching.
    Handles: FROM, JOIN, INTO, UPDATE contexts.
    Skips already-qualified names (containing dots).

    Args:
        sql: Original SQL query
        tables: List of known table names to qualify
        catalog: Databricks catalog name
        schema: Databricks schema name

    Returns:
        SQL with qualified table names

    Example:
        >>> qualify_table_names(
        ...     "SELECT * FROM products JOIN sales ON ...",
        ...     ["products", "sales"],
        ...     "workspace",
        ...     "default"
        ... )
        "SELECT * FROM workspace.default.products JOIN workspace.default.sales ON ..."
    """
    qualified_sql = sql

    for table in tables:
        qualified_name = f"{catalog}.{schema}.{table}"

        # Pattern matches table name that is:
        # - NOT preceded by a dot (would mean already qualified)
        # - A whole word (word boundaries)
        # - NOT followed by a dot (would mean it's a schema/catalog prefix)
        #
        # Uses negative lookbehind (?<!\.) and negative lookahead (?!\.)
        pattern = rf'(?<![.\w])\b{re.escape(table)}\b(?!\s*\.)'

        qualified_sql = re.sub(
            pattern,
            qualified_name,
            qualified_sql,
            flags=re.IGNORECASE
        )

    return qualified_sql


def is_select_query(sql: str) -> bool:
    """
    Check if a SQL query is a SELECT statement.

    Args:
        sql: SQL query string

    Returns:
        True if it's a SELECT query, False otherwise
    """
    # Remove leading whitespace and comments
    cleaned = sql.strip()

    # Remove single-line comments
    cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)

    # Remove multi-line comments
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)

    # Check if starts with SELECT (case-insensitive)
    cleaned = cleaned.strip()
    return cleaned.upper().startswith('SELECT')


def extract_table_names(sql: str) -> List[str]:
    """
    Extract table names from a SQL query.

    This is a simple extraction that finds table names after
    FROM and JOIN keywords. Not a full SQL parser.

    Args:
        sql: SQL query string

    Returns:
        List of table names found
    """
    tables = []

    # Pattern for FROM/JOIN followed by table name
    # Captures: FROM table, JOIN table, FROM schema.table
    pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'

    matches = re.findall(pattern, sql, flags=re.IGNORECASE)

    for match in matches:
        # Get just the table name (last part if qualified)
        table_name = match.split('.')[-1]
        if table_name not in tables:
            tables.append(table_name)

    return tables
