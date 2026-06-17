import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.database as app_database
from app.database import Base, User, Recipe
from app.services import recipe_service, ai_service

sync_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=sync_test_engine, expire_on_commit=False)

@pytest.fixture(autouse=True)
def setup_sync_db():
    app_database.SessionLocal.configure(bind=sync_test_engine)
    Base.metadata.create_all(sync_test_engine)
    yield
    Base.metadata.drop_all(sync_test_engine)
    app_database.SessionLocal.configure(bind=app_database.engine)

# ================= RECIPE SERVICE TESTS =================

def test_save_custom_recipe():
    with TestingSessionLocal() as db:
        user = User(id=1, user_name="TestUser", password="...")
        db.add(user)
        db.commit()
        
        ingredients = [{"name": "salt", "qty": 1, "unitString": "tsp"}]
        recipe = recipe_service.save_custom_recipe(
            title="Custom Salad",
            ingredients_list=ingredients,
            instructions="Mix it.",
            image="http://example.com/salad.jpg",
            user_id=1,
            db=db
        )
        assert recipe.id is not None
        assert recipe.title == "Custom Salad"
        assert recipe.user_id == 1
        assert recipe.raw_data["instructions"] == "Mix it."

def test_toggle_like_recipe():
    with TestingSessionLocal() as db:
        user = User(id=1, user_name="TestUser", password="...")
        db.add(user)
        recipe = Recipe(id=50, title="Liked Pasta", raw_data={"id": 50, "likes": 5})
        db.add(recipe)
        db.commit()

        # Like
        res = recipe_service.toggle_like_recipe(recipe_id=50, user_id=1, db=db)
        assert res["status"] == "liked"
        assert res["likes"] == 6

        # Unlike
        res = recipe_service.toggle_like_recipe(recipe_id=50, user_id=1, db=db)
        assert res["status"] == "unliked"
        assert res["likes"] == 5

# ================= AI SERVICE TESTS =================

def test_ai_recipe_generation_success(mocker):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"title": "AI Feast", "ingredients": ["water", "salt"], "instructions": ["Boil water", "Add salt"], "servings": 2}'
                }
            }
        ]
    }
    mocker.patch("httpx.post", return_value=mock_response)

    with TestingSessionLocal() as db:
        user = User(id=1, user_name="AIUser", password="...")
        db.add(user)
        db.commit()

        recipe = ai_service.generate_recipe_with_ai("water, salt", user_id=1, db=db)
        assert recipe.title == "AI Feast"
        assert recipe.raw_data["readyInMinutes"] == 30
        assert len(recipe.raw_data["extendedIngredients"]) == 2

def test_ai_recipe_generation_unparseable_json(mocker):
    # What happens when AI returns invalid/malformed JSON?
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "This is not JSON text at all!"
                }
            }
        ]
    }
    mocker.patch("httpx.post", return_value=mock_response)

    with TestingSessionLocal() as db:
        user = User(id=1, user_name="AIUser", password="...")
        db.add(user)
        db.commit()

        with pytest.raises(Exception):
            ai_service.generate_recipe_with_ai("water", user_id=1, db=db)

def test_ai_recipe_generation_api_failure(mocker):
    # What happens when AI server returns 500 error?
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mocker.patch("httpx.post", return_value=mock_response)

    with TestingSessionLocal() as db:
        user = User(id=1, user_name="AIUser", password="...")
        db.add(user)
        db.commit()

        with pytest.raises(Exception) as exc_info:
            ai_service.generate_recipe_with_ai("water", user_id=1, db=db)
        assert "AI API error" in str(exc_info.value)

def test_quick_substitute_ai_success(mocker):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Use olive oil."
                }
            }
        ]
    }
    mocker.patch("httpx.post", return_value=mock_response)

    with TestingSessionLocal() as db:
        recipe = Recipe(id=60, title="Salad", raw_data={"id": 60})
        db.add(recipe)
        db.commit()

        rec = ai_service.get_quick_substitute_from_ai(recipe_id=60, ingredient_to_replace="butter", db=db)
        assert rec == "Use olive oil."

def test_quick_substitute_ai_failure(mocker):
    # If the AI call fails, it should gracefully fall back to a failure string instead of raising exception
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "AI Unavailable"
    mocker.patch("httpx.post", return_value=mock_response)

    with TestingSessionLocal() as db:
        recipe = Recipe(id=60, title="Salad", raw_data={"id": 60})
        db.add(recipe)
        db.commit()

        rec = ai_service.get_quick_substitute_from_ai(recipe_id=60, ingredient_to_replace="butter", db=db)
        assert "Failed to retrieve quick suggestion" in rec
