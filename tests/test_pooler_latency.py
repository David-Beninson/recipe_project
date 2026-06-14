import time
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User

@pytest.mark.skip(reason="Manual latency check, requires real database/network connection")
def test_pooler_latency():
    print("Testing Pooler DB Latency...")
    # Change host to pooler
    pooler_host = "ep-dawn-cloud-abergnqy-pooler.eu-west-2.aws.neon.tech"
    start_connect = time.time()
    engine = create_engine(f"postgresql://{settings.database_username}:{settings.database_password}@{pooler_host}:{settings.database_port}/{settings.database_name}")
    SessionLocal = sessionmaker(bind=engine)
    print(f"Engine creation took {time.time() - start_connect:.4f} seconds")

    # Time a single query
    start_query = time.time()
    with SessionLocal() as db:
        stmt = select(User).limit(1)
        res = db.execute(stmt).scalars().first()
        print(f"First query with pooler took {time.time() - start_query:.4f} seconds")
        
        start_query2 = time.time()
        res2 = db.execute(stmt).scalars().first()
        print(f"Second query with pooler took {time.time() - start_query2:.4f} seconds")

if __name__ == "__main__":
    test_pooler_latency()
