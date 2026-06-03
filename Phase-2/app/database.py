"""
SQLAlchemy async engine + session factory.
Other modules get a session via `get_db` (FastAPI dependency).
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass


async def get_db():
    """FastAPI dependency: yields a database session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session
