"""
Async database connection and session management using SQLAlchemy 2.0.

Provides:
- Async engine creation
- Async session factory
- FastAPI dependency for database sessions
- Base model class for all SQLAlchemy models
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Naming convention for constraints
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Metadata with naming convention
metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides:
    - Metadata with naming conventions
    - Auto-generated table names from class names
    - Common helper methods
    """

    metadata = metadata

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case)."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return "".join(
            ["_" + c.lower() if c.isupper() else c for c in name]
        ).lstrip("_")

    def dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        """String representation of model instance."""
        attrs = ", ".join(
            f"{k}={v!r}" for k, v in self.dict().items() if not k.startswith("_")
        )
        return f"{self.__class__.__name__}({attrs})"


# ============================================================================
# Engine Creation
# ============================================================================


def create_engine(
    url: str | None = None,
    echo: bool | None = None,
    pool_size: int | None = None,
    max_overflow: int | None = None,
) -> AsyncEngine:
    """
    Create async SQLAlchemy engine.

    Args:
        url: Database URL (defaults to settings.database_url)
        echo: Echo SQL queries (defaults to settings.database_echo)
        pool_size: Connection pool size (defaults to settings.database_pool_size)
        max_overflow: Max overflow connections (defaults to settings.database_max_overflow)

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    url = url or settings.database_url
    echo = echo if echo is not None else settings.database_echo
    pool_size = pool_size if pool_size is not None else settings.database_pool_size
    max_overflow = (
        max_overflow if max_overflow is not None else settings.database_max_overflow
    )

    logger.info(
        "creating_database_engine",
        url=url.split("@")[0] + "@***",  # Hide credentials in logs
        pool_size=pool_size,
        max_overflow=max_overflow,
    )

    return create_async_engine(
        url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )


# ============================================================================
# Global Engine and Session Factory
# ============================================================================

# Create global engine
engine: AsyncEngine = create_engine()

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autoflush=False,  # Don't auto-flush
    autocommit=False,  # Don't auto-commit
)


# ============================================================================
# Test Engine (for testing with separate database)
# ============================================================================


def create_test_engine() -> AsyncEngine:
    """
    Create async engine for testing.

    Uses settings.test_database_url if available, otherwise uses NullPool.

    Returns:
        AsyncEngine: Test database engine
    """
    test_url = settings.test_database_url or settings.database_url

    logger.info("creating_test_database_engine", url=test_url.split("@")[0] + "@***")

    return create_async_engine(
        test_url,
        echo=False,
        poolclass=NullPool,  # No connection pooling for tests
    )


# ============================================================================
# FastAPI Dependency
# ============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        AsyncSession: Database session

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_session():
    """
    Context manager for database sessions (non-FastAPI usage).

    Returns:
        AsyncSession: Database session context manager

    Usage:
        async with get_session() as db:
            result = await db.execute(select(Item))
            items = result.scalars().all()
    """
    return AsyncSessionLocal()


# ============================================================================
# Database Lifecycle Management
# ============================================================================


async def init_db() -> None:
    """
    Initialize database (create all tables).

    Note: This is for development only.
    Use Alembic migrations for production.
    """
    logger.info("initializing_database")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("database_initialized")


async def close_db() -> None:
    """
    Close database connections.

    Should be called on application shutdown.
    """
    logger.info("closing_database_connections")
    await engine.dispose()
    logger.info("database_connections_closed")


# ============================================================================
# Health Check
# ============================================================================


async def check_db_health() -> bool:
    """
    Check database connection health.

    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        async with engine.connect() as conn:
            await conn.scalar("SELECT 1")
        logger.info("database_health_check", status="healthy")
        return True
    except Exception as e:
        logger.error("database_health_check", status="unhealthy", error=str(e))
        return False
