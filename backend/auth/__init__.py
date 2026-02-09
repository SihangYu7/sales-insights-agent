from auth.db import SessionLocal, get_db, init_auth_db
from auth.models import User, ChatSession, QueryHistory
from auth.service import (
    create_user,
    authenticate_user,
    refresh_access_token,
    get_user_by_id,
    require_auth,
    optional_auth,
    save_query_history,
    get_user_query_history,
    create_chat_session,
    get_user_sessions,
    get_session_messages,
    get_session_by_id,
    update_session_title,
)

__all__ = [
    "SessionLocal",
    "get_db",
    "init_auth_db",
    "User",
    "ChatSession",
    "QueryHistory",
    "create_user",
    "authenticate_user",
    "refresh_access_token",
    "get_user_by_id",
    "require_auth",
    "optional_auth",
    "save_query_history",
    "get_user_query_history",
    "create_chat_session",
    "get_user_sessions",
    "get_session_messages",
    "get_session_by_id",
    "update_session_title",
]
