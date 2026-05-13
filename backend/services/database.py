"""
Database service for managing SQLite connections and initialization
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from backend.models import Base

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orcanos_performance.db")

# Create engine with SQLite-specific parameters
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables and apply lightweight migrations"""
    Base.metadata.create_all(bind=engine)
    # Add scenario_name column if it doesn't exist yet
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(test_runs)"))]
        if "scenario_name" not in cols:
            conn.execute(text("ALTER TABLE test_runs ADD COLUMN scenario_name VARCHAR(255)"))
            conn.commit()


def get_db():
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db():
    """Close database connection"""
    engine.dispose()
