"""
Custom exceptions for the database layer.

Exception Hierarchy:
    DatabaseException (base)
    ├── DatabaseConnectionError - Failed to connect/acquire connection
    ├── QueryError - Error executing query
    │   ├── QueryValidationError - SQL validation failed
    │   └── QueryExecutionError - Database rejected query
    └── SchemaError - Schema discovery/parsing error
"""


class DatabaseException(Exception):
    """Base exception for all database errors."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error

    def to_dict(self) -> dict:
        """Convert to dict for API responses (backward compatibility)."""
        return {"error": self.message}


class DatabaseConnectionError(DatabaseException):
    """Failed to establish or acquire database connection."""
    pass


class QueryError(DatabaseException):
    """Base class for query-related errors."""

    def __init__(self, message: str, sql: str = None, original_error: Exception = None):
        super().__init__(message, original_error)
        self.sql = sql


class QueryValidationError(QueryError):
    """SQL query failed validation (e.g., dangerous operation)."""
    pass


class QueryExecutionError(QueryError):
    """Database rejected the query."""
    pass


class SchemaError(DatabaseException):
    """Error discovering or parsing schema."""
    pass
