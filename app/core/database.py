from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, DeclarativeBase
from app.core.config import settings

# Engine configuration: handle SQLite vs PostgreSQL/Supabase
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # Automatically reconnect if connection was dropped
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# SQLAlchemy 2.0 Base Class
class Base(DeclarativeBase):
    pass


# Dependency to yield database sessions in FastAPI route handlers
def get_db() -> Generator:
    """Yield a database session and ensure it closes after request completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Quick connectivity probe for the /health endpoint."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        # In debug mode or logs, we can inspect e
        return False
