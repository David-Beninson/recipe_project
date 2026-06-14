import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

@pytest.mark.skip(reason="Manual connectivity test, requires real Neon database connection")
@pytest.mark.anyio
async def test_db_ssl_connection():
    db_url = f"postgresql+asyncpg://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
    
    # Test connection with pool_pre_ping and pool_recycle configured as in database.py
    engine = create_async_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300
    )
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            assert res.scalar() == 1
    finally:
        await engine.dispose()
