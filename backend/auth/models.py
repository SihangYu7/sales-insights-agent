"""Auth and session models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Float

from auth.db import Base


class User(Base):
    """Users table - stores user authentication information."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": str(self.created_at) if self.created_at else None,
            "is_active": self.is_active,
        }


class ChatSession(Base):
    """Chat sessions table - groups messages into conversations."""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }


class QueryHistory(Base):
    """Query history table - stores user queries for history and analytics."""

    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    sql_query = Column(Text)
    agent_type = Column(String(50))
    cache_hit = Column(Boolean, default=False)
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "question": self.question,
            "answer": self.answer,
            "sql_query": self.sql_query,
            "agent_type": self.agent_type,
            "cache_hit": self.cache_hit,
            "duration_seconds": self.duration_seconds,
            "created_at": str(self.created_at) if self.created_at else None,
        }
