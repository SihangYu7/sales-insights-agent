"""
Analytics query helpers.
"""

from analytics.connector import get_database_connector
from exceptions import DatabaseException


def run_query(sql_query: str):
    """
    Execute a raw SQL query and return results.

    For backward compatibility, this function catches exceptions and returns
    error dicts in the format {"error": str} instead of raising.
    """
    connector = get_database_connector()
    try:
        return connector.execute_query(sql_query)
    except DatabaseException as e:
        return {"error": e.message}
    except Exception as e:
        return {"error": str(e)}


def get_schema_info():
    """Return schema information for the analytics database."""
    connector = get_database_connector()
    return connector.get_schema_info()
