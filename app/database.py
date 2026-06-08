from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from .config import settings


# Build the PostgreSQL connection string for async database access
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.database_username}:{settings.database_password}"
    f"@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
)

# Create async engine for database operations
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# Session factory for creating database sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False  # Keep data accessible after commit
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db():
    """Dependency function to get database session.
    Used in FastAPI endpoints via Depends(get_db).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()