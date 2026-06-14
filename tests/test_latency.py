import time
import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User, Recipe

@pytest.mark.skip(reason="Manual latency check, requires real database/network connection")
def test_db_latency():
    print("Testing Sync DB Latency...")
    start_connect = time.time()
    engine = create_engine(f"postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}")
    SessionLocal = sessionmaker(bind=engine)
    print(f"Engine creation took {time.time() - start_connect:.4f} seconds")

    # Time a single query
    start_query = time.time()
    with SessionLocal() as db:
        stmt = select(User).limit(1)
        res = db.execute(stmt).scalars().first()
        print(f"First query took {time.time() - start_query:.4f} seconds")
        
        start_query2 = time.time()
        stmt2 = select(Recipe).limit(1)
        res2 = db.execute(stmt2).scalars().first()
        print(f"Second query (same session) took {time.time() - start_query2:.4f} seconds")

@pytest.mark.skip(reason="Manual latency check, requires real Spoonacular API key")
def test_spoonacular_latency():
    print("\nTesting Spoonacular API Latency...")
    start = time.time()
    try:
        response = httpx.get("https://api.spoonacular.com/recipes/findByIngredients", params={
            "apiKey": settings.spoonacular_api_key,
            "ingredients": "tomato",
            "number": 1
        }, timeout=5.0)
        print(f"Spoonacular call took {time.time() - start:.4f} seconds (Status: {response.status_code})")
    except Exception as e:
        print(f"Spoonacular call failed: {e}")

if __name__ == "__main__":
    test_db_latency()
    test_spoonacular_latency()
