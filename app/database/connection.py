from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# Build the PostgreSQL connection string for database access
SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"

# Create sync engine for Flask operations
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=True,
    pool_pre_ping=True,
    pool_recycle=300
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass
