"""Auth/session database setup."""

from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_auth_database_url

# Load environment variables from .env if present
load_dotenv()
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

AUTH_DATABASE_URL = get_auth_database_url()
_is_sqlite = AUTH_DATABASE_URL.startswith("sqlite")
engine_kwargs = {"echo": False}
if _is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(AUTH_DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def init_auth_db():
    """Create all auth/session tables in the database."""
    Base.metadata.create_all(engine)
    if _is_sqlite:
        _migrate_sqlite_schema()
    print("✅ Auth tables created!")


def _migrate_sqlite_schema():
    """Apply lightweight SQLite migrations for local auth/history tables."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(query_history)"))
            columns = {row[1] for row in result.fetchall()}
            if "session_id" not in columns:
                conn.execute(text("ALTER TABLE query_history ADD COLUMN session_id INTEGER"))
            conn.commit()
    except Exception as e:
        print(f"⚠️ SQLite migration skipped/failed: {e}")


def get_db():
    """Get a database session (connection)."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass
