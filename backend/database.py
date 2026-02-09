"""
Deprecated compatibility layer.

Use the new modules instead:
- auth.db / auth.models / auth.service
- analytics.query / analytics.sqlite_db
"""

from auth.db import SessionLocal, get_db, init_auth_db
from auth.models import User, ChatSession, QueryHistory
from auth.service import (
    save_query_history,
    get_user_query_history,
    create_chat_session,
    get_user_sessions,
    get_session_messages,
    get_session_by_id,
    update_session_title,
)
from analytics.query import run_query, get_schema_info
from analytics.sqlite_db import Product, Sale, init_analytics_db, seed_analytics_db


def init_db():
    """Compatibility: initialize auth tables and analytics SQLite tables."""
    init_auth_db()
    init_analytics_db()


def seed_database():
    """Compatibility: seed analytics SQLite data."""
    seed_analytics_db()
