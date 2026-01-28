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

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, Text, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import date, datetime, timedelta, timezone
import random

# Database setup
# SQLite stores everything in a single file called 'sales.db'
DATABASE_URL = "sqlite:///sales.db"
engine = create_engine(DATABASE_URL, echo=False)
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


class QueryHistory(Base):
    """
    Query history table - stores user queries for history and analytics

    Example row:
    | id | user_id | question          | answer        | sql_query       | agent_type | created_at |
    | 1  | 1       | Total sales?      | $204,593.89   | SELECT SUM(...) | text_to_sql| 2024-01-15 |
    """
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
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
            "question": self.question,
            "answer": self.answer,
            "sql_query": self.sql_query,
            "agent_type": self.agent_type,
            "cache_hit": self.cache_hit,
            "duration_seconds": self.duration_seconds,
            "created_at": str(self.created_at) if self.created_at else None
        }


def save_query_history(user_id: int, question: str, answer: str, sql_query: str = None,
                       agent_type: str = None, cache_hit: bool = False, duration_seconds: float = None):
    """Save a query to history."""
    db = SessionLocal()
    try:
        history = QueryHistory(
            user_id=user_id,
            question=question,
            answer=answer,
            sql_query=sql_query,
            agent_type=agent_type,
            cache_hit=cache_hit,
            duration_seconds=duration_seconds
        )
        db.add(history)
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
# DATABASE FUNCTIONS
# =============================================================================

def init_db():
    """Create all tables in the database"""
    Base.metadata.create_all(engine)
    print("✅ Database tables created!")


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
