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

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import date, timedelta
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

    Example:
        results = run_query("SELECT * FROM products WHERE category = 'Electronics'")
    """
    db = SessionLocal()
    try:
        result = db.execute(text(sql_query))
        # Get column names
        columns = result.keys()
        # Fetch all rows and convert to list of dicts
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return rows
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


def get_schema_info():
    """
    Returns information about the database schema.
    The AI agent needs this to know what tables/columns exist!
    """
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
