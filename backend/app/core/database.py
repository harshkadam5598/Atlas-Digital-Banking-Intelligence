"""
Atlas – Digital Banking Intelligence Platform
Database Connection & Session Management

Provides SQLAlchemy engine, session factory, and dependency injection
for FastAPI route handlers. Supports both sync and async patterns.
"""

from contextlib import contextmanager
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import settings


# ─── SQLAlchemy Engine ────────────────────────────────────────────────────────

engine = create_engine(
    settings.db.url,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
    echo=settings.db.echo,
    pool_pre_ping=True,          # Verify connections before checkout
    pool_recycle=3600,           # Recycle connections after 1 hour
)

# Log slow queries in development
if settings.is_development:
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = __import__("time").time()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = __import__("time").time() - context._query_start_time
        if total > 0.5:  # Log queries slower than 500ms
            logger.warning(f"Slow query detected ({total:.3f}s): {statement[:100]}...")


# ─── Session Factory ──────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ─── Base Model ───────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Base class for all Atlas SQLAlchemy ORM models."""
    pass


# ─── Dependency Injection ─────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    Automatically commits on success, rolls back on exception.

    Usage:
        @router.get("/example")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager version for use outside FastAPI request lifecycle.
    Useful in ETL pipelines, analytics engines, and scripts.

    Usage:
        with get_db_context() as db:
            results = db.execute(text("SELECT 1")).fetchall()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def verify_connection() -> bool:
    """
    Verify that the database is reachable.
    Called during application startup to fail fast if DB is unavailable.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Database connection verified: {settings.db.host}:{settings.db.port}/{settings.db.db}")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
