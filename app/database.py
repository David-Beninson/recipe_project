from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings


# Build the PostgreSQL connection string for async database access
SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"


# Create async engine for database operations
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# Session factory for creating database sessions
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db():
    """Dependency function to get database session.
    Used in FastAPI endpoints via Depends(get_db).
    """
    async with sessionmaker() as session:
        try:
            yield session
        finally:
            await session.close()