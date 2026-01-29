"""
AI Agent Backend - Module 2: Database Setup
============================================
This file sets up a SQLite database with sample sales data.
Your AI agent will learn to query this data!

KEY CONCEPTS:
- SQLite: A simple file-based database (no server needed!)
- SQLAlchemy: Python library to work with databases
- ORM: Maps Python classes to database tables
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, Text, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import date, datetime, timedelta, timezone
import random

# Database setup
# Load environment variables from .env if present
load_dotenv()
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
# Defaults to local SQLite; override with DATABASE_URL (e.g., Supabase Postgres)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sales.db")
_is_sqlite = DATABASE_URL.startswith("sqlite")
engine_kwargs = {"echo": False}
if _is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# =============================================================================
# DATABASE MODELS (Tables)
# =============================================================================
# Each class below becomes a table in your database

class Product(Base):
    """
    Products table - stores information about items for sale

    Example row:
    | id | name      | category    | price |
    | 1  | Laptop    | Electronics | 999.99|
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": self.price
        }


class Sale(Base):
    """
    Sales table - stores each transaction

    Example row:
    | id | product_id | quantity | total  | sale_date  | region |
    | 1  | 1          | 2        | 1999.98| 2024-01-15 | West   |
    """
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)
    sale_date = Column(Date, nullable=False)
    region = Column(String, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "total": self.total,
            "sale_date": str(self.sale_date),
            "region": self.region
        }


class User(Base):
    """
    Users table - stores user authentication information

    Example row:
    | id | email              | password_hash | name     | created_at          | is_active |
    | 1  | user@example.com   | $2b$12$...    | John Doe | 2024-01-15 10:30:00 | True      |
    """
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
            "is_active": self.is_active
        }


class ChatSession(Base):
    """
    Chat sessions table - groups messages into conversations

    Example row:
    | id | user_id | title              | created_at          | updated_at          |
    | 1  | 1       | Sales Analysis     | 2024-01-15 10:30:00 | 2024-01-15 11:00:00 |
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None
        }


class QueryHistory(Base):
    """
    Query history table - stores user queries for history and analytics

    Example row:
    | id | user_id | session_id | question          | answer        | sql_query       | agent_type | created_at |
    | 1  | 1       | 1          | Total sales?      | $204,593.89   | SELECT SUM(...) | text_to_sql| 2024-01-15 |
    """
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    sql_query = Column(Text)
    agent_type = Column(String(50))  # 'text_to_sql' or 'tool_agent'
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
            "created_at": str(self.created_at) if self.created_at else None
        }


def save_query_history(user_id: int, question: str, answer: str, sql_query: str = None,
                       agent_type: str = None, cache_hit: bool = False, duration_seconds: float = None,
                       session_id: int = None):
    """Save a query to history."""
    db = SessionLocal()
    try:
        history = QueryHistory(
            user_id=user_id,
            session_id=session_id,
            question=question,
            answer=answer,
            sql_query=sql_query,
            agent_type=agent_type,
            cache_hit=cache_hit,
            duration_seconds=duration_seconds
        )
        db.add(history)
        db.commit()

        # Update session's updated_at timestamp and title if it's the first message
        if session_id:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                session.updated_at = datetime.now(timezone.utc)
                # Auto-generate title from first question if still default
                if session.title == "New Chat":
                    session.title = question[:50] + ("..." if len(question) > 50 else "")
                db.commit()

        return history.to_dict()
    except Exception as e:
        db.rollback()
        print(f"Error saving query history: {e}")
        return None
    finally:
        db.close()


def get_user_query_history(user_id: int, limit: int = 50):
    """Get query history for a user."""
    db = SessionLocal()
    try:
        history = db.query(QueryHistory).filter(
            QueryHistory.user_id == user_id
        ).order_by(QueryHistory.created_at.desc()).limit(limit).all()
        return [h.to_dict() for h in history]
    finally:
        db.close()


# =============================================================================
# CHAT SESSION FUNCTIONS
# =============================================================================

def create_chat_session(user_id: int, title: str = "New Chat") -> dict:
    """Create a new chat session for a user."""
    db = SessionLocal()
    try:
        session = ChatSession(user_id=user_id, title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.to_dict()
    except Exception as e:
        db.rollback()
        print(f"Error creating chat session: {e}")
        return None
    finally:
        db.close()


def get_user_sessions(user_id: int, limit: int = 50) -> list:
    """Get all chat sessions for a user, ordered by most recent."""
    db = SessionLocal()
    try:
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.updated_at.desc()).limit(limit).all()
        return [s.to_dict() for s in sessions]
    finally:
        db.close()


def get_session_messages(session_id: int, user_id: int) -> list:
    """Get all messages in a specific session."""
    db = SessionLocal()
    try:
        messages = db.query(QueryHistory).filter(
            QueryHistory.session_id == session_id,
            QueryHistory.user_id == user_id
        ).order_by(QueryHistory.created_at.asc()).all()
        return [m.to_dict() for m in messages]
    finally:
        db.close()


def get_session_by_id(session_id: int, user_id: int) -> dict:
    """Get a specific session by ID."""
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()
        return session.to_dict() if session else None
    finally:
        db.close()


def update_session_title(session_id: int, user_id: int, title: str) -> dict:
    """Update a session's title."""
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()
        if session:
            session.title = title
            db.commit()
            db.refresh(session)
            return session.to_dict()
        return None
    except Exception as e:
        db.rollback()
        print(f"Error updating session title: {e}")
        return None
    finally:
        db.close()


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def init_db():
    """Create all tables in the database"""
    Base.metadata.create_all(engine)
    if _is_sqlite:
        _migrate_sqlite_schema()
    print("✅ Database tables created!")


def _migrate_sqlite_schema():
    """Apply lightweight SQLite migrations for local auth/history tables."""
    try:
        # Add session_id to query_history if missing
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(query_history)"))
            columns = {row[1] for row in result.fetchall()}
            if "session_id" not in columns:
                conn.execute(text("ALTER TABLE query_history ADD COLUMN session_id INTEGER"))
            conn.commit()
    except Exception as e:
        print(f"⚠️ SQLite migration skipped/failed: {e}")


def get_db():
    """Get a database session (connection)"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # We'll close it manually when done


def seed_database():
    """
    Fill the database with sample data for testing.
    This creates realistic sales data you can query!
    """
    if not _is_sqlite:
        print("📊 Skipping seed: non-SQLite database configured.")
        return
    db = SessionLocal()

    # Check if data already exists
    if db.query(Product).count() > 0:
        print("📊 Database already has data, skipping seed.")
        db.close()
        return

    # Sample products
    products = [
        Product(name="Laptop", category="Electronics", price=999.99),
        Product(name="Smartphone", category="Electronics", price=699.99),
        Product(name="Headphones", category="Electronics", price=149.99),
        Product(name="Keyboard", category="Electronics", price=79.99),
        Product(name="Mouse", category="Electronics", price=49.99),
        Product(name="Desk Chair", category="Furniture", price=299.99),
        Product(name="Standing Desk", category="Furniture", price=449.99),
        Product(name="Monitor Stand", category="Furniture", price=59.99),
        Product(name="Python Book", category="Books", price=39.99),
        Product(name="AI Textbook", category="Books", price=89.99),
    ]

    db.add_all(products)
    db.commit()
    print(f"✅ Added {len(products)} products")

    # Generate random sales for the past 90 days
    regions = ["North", "South", "East", "West"]
    sales = []

    for i in range(200):  # 200 sales records
        product = random.choice(products)
        quantity = random.randint(1, 5)
        days_ago = random.randint(0, 90)

        sale = Sale(
            product_id=product.id,
            quantity=quantity,
            total=round(product.price * quantity, 2),
            sale_date=date.today() - timedelta(days=days_ago),
            region=random.choice(regions)
        )
        sales.append(sale)

    db.add_all(sales)
    db.commit()
    print(f"✅ Added {len(sales)} sales records")

    db.close()
    print("🎉 Database seeded successfully!")


def run_query(sql_query: str):
    """
    Execute a raw SQL query and return results.
    This is what the AI agent will use!

    Uses the database connector abstraction to support both SQLite and Databricks.

    Example:
        results = run_query("SELECT * FROM products WHERE category = 'Electronics'")
    """
    from db_connector import get_database_connector
    connector = get_database_connector()
    return connector.execute_query(sql_query)


def get_schema_info():
    """
    Returns information about the database schema.
    The AI agent needs this to know what tables/columns exist!

    Uses the database connector abstraction to support both SQLite and Databricks.
    """
    from db_connector import get_database_connector
    connector = get_database_connector()
    return connector.get_schema_info()


# =============================================================================
# Run this file directly to set up the database
# =============================================================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🗄️  Setting up the database...")
    print("="*50 + "\n")

    init_db()
    seed_database()

    # Test a query
    print("\n📊 Testing query - Products in database:")
    results = run_query("SELECT * FROM products")
    for product in results:
        print(f"  - {product['name']} (${product['price']}) - {product['category']}")

    print("\n📈 Testing query - Total sales by region:")
    results = run_query("SELECT region, SUM(total) as total_sales FROM sales GROUP BY region")
    for row in results:
        print(f"  - {row['region']}: ${row['total_sales']:,.2f}")
