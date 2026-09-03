"""Async SQLAlchemy engine/session wiring, driven by the DATABASE_URL env var.

Postgres only — DATABASE_URL must point at one (e.g.
"postgresql+asyncpg://user:pass@host:5432/dbname"); docker-compose.yml sets
it to the postgres service for real deployments, and the test suite starts
its own ephemeral Postgres container (see tests/conftest.py) rather than
falling back to any other database. The rest of the app never touches the
URL or engine directly — everything goes through the session factory
stashed on app.state by main.py's lifespan.
"""

import os
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.storage.models import Base


def create_engine() -> AsyncEngine:
    """Build the async engine for DATABASE_URL.

    Raises:
        RuntimeError: DATABASE_URL isn't set.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set — this service requires Postgres (e.g. "
            "'postgresql+asyncpg://user:pass@host:5432/dbname'); see docker-compose.yml."
        )
    return create_async_engine(url)


async def init_models(engine: AsyncEngine) -> None:
    """Create every table that doesn't exist yet (no migration framework — see README)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session from app.state."""
    async with request.app.state.db_sessionmaker() as session:
        yield session
