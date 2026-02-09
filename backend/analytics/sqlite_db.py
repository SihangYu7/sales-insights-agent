"""
SQLite models and seed data for analytics (development only).
"""

import random
from datetime import date, timedelta

from sqlalchemy import Column, Date, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLITE_DB_URL = "sqlite:///sales.db"
engine = create_engine(SQLITE_DB_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Product(Base):
    """Products table - stores information about items for sale."""

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
            "price": self.price,
        }


class Sale(Base):
    """Sales table - stores each transaction."""

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
            "region": self.region,
        }


def init_analytics_db():
    """Create all analytics tables in SQLite."""
    Base.metadata.create_all(engine)
    print("✅ Analytics tables created!")


def seed_analytics_db():
    """Fill the SQLite analytics database with sample data."""
    db = SessionLocal()

    if db.query(Product).count() > 0:
        print("📊 Analytics DB already has data, skipping seed.")
        db.close()
        return

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

    regions = ["North", "South", "East", "West"]
    sales = []

    for _ in range(200):
        product = random.choice(products)
        quantity = random.randint(1, 5)
        days_ago = random.randint(0, 90)

        sale = Sale(
            product_id=product.id,
            quantity=quantity,
            total=round(product.price * quantity, 2),
            sale_date=date.today() - timedelta(days=days_ago),
            region=random.choice(regions),
        )
        sales.append(sale)

    db.add_all(sales)
    db.commit()
    print(f"✅ Added {len(sales)} sales records")

    db.close()
    print("🎉 Analytics DB seeded successfully!")


def get_db():
    """Get a database session for SQLite analytics."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass
