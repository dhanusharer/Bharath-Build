"""SQLAlchemy database session lifecycle management and FastAPI dependencies."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.models import Base

logger = logging.getLogger("medication_accessibility.db")
settings = get_settings()

# Engine creation: In unit tests or dev, DATABASE_URL may be sqlite+aiosqlite or postgresql+asyncpg
# asyncpg does not take pool_size/max_overflow if using SQLite, so pass pool args only for postgresql
is_postgres = settings.DATABASE_URL.startswith("postgresql")

engine_kwargs = {
    "echo": False,
    "future": True,
}
if is_postgres:
    engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
        }
    )

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db(target_engine: AsyncEngine = engine) -> None:
    """Create all database tables asynchronously if they do not exist.
    
    Safe for local development and integration test initialization.
    Production uses schema migrations (Alembic).
    """
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an isolated AsyncSession per request."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
