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
        sr_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(step_results)"))]
        if "requests" not in sr_cols:
            conn.execute(text("ALTER TABLE step_results ADD COLUMN requests JSON"))
            conn.commit()
        user_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
        if "email" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
            conn.commit()

        # Make hashed_password nullable for Google OAuth users
        # SQLite doesn't support ALTER COLUMN, so we check if it's already nullable
        user_col_info = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        for col in user_col_info:
            if col[1] == "hashed_password" and col[3] == 1:  # col[3] is notnull flag
                # Rebuild table without NOT NULL on hashed_password
                conn.execute(text("""
                    CREATE TABLE users_new (
                        id INTEGER PRIMARY KEY,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        email VARCHAR(255) UNIQUE,
                        hashed_password VARCHAR(256),
                        role VARCHAR(20) NOT NULL DEFAULT 'user',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(text("INSERT INTO users_new SELECT * FROM users"))
                conn.execute(text("DROP TABLE users"))
                conn.execute(text("ALTER TABLE users_new RENAME TO users"))
                conn.commit()
                break

        tables = [row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))]
        if "summary_cache" not in tables:
            conn.execute(text("CREATE TABLE summary_cache (id INTEGER PRIMARY KEY, computed_at DATETIME, data JSON)"))
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
