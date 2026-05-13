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

    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(test_runs)"))]
        if "scenario_name" not in cols:
            conn.execute(text("ALTER TABLE test_runs ADD COLUMN scenario_name VARCHAR(255)"))
            conn.commit()
        acct_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(accounts)"))]
        if "version" not in acct_cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN version VARCHAR(50) DEFAULT ''"))
            conn.commit()

    # Seed default users (idempotent)
    import os
    from backend.models import User
    from backend.services.auth import hash_password

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin_pass = os.getenv("ADMIN_PASSWORD", "admin")
            db.add(User(username="admin", hashed_password=hash_password(admin_pass), role="admin"))
        if not db.query(User).filter(User.username == "user").first():
            user_pass = os.getenv("USER_PASSWORD", "user")
            db.add(User(username="user", hashed_password=hash_password(user_pass), role="user"))
        db.commit()
    finally:
        db.close()


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
