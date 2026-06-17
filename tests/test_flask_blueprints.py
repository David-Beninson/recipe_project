import pytest
import json
from unittest.mock import MagicMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as app_database
from app.main import app as flask_app
from app.database import Base, User, Recipe, UserSearch

# Setup sync in-memory SQLite database for testing
sync_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@pytest.fixture(autouse=True)
def setup_sync_db():
    app_database.SessionLocal.configure(bind=sync_test_engine)
    Base.metadata.create_all(sync_test_engine)
    yield
    Base.metadata.drop_all(sync_test_engine)
    app_database.SessionLocal.configure(bind=app_database.engine)

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    with flask_app.test_client() as client:
        yield client

@pytest.fixture
def logged_in_session(client):
    with app_database.SessionLocal() as db:
        user = User(id=999, user_name="TestUser", password="pbkdf2:sha256:...")
        db.add(user)
        db.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = 999
        sess['username'] = "TestUser"
    return 999

def test_home_page_requires_login(client):
    response = client.get('/home')
    assert response.status_code == 302

def test_home_page_loads_recipes(client, logged_in_session):
    with app_database.SessionLocal() as db:
        recipe = Recipe(id=1, title="Test Recipe", user_id=logged_in_session, raw_data={
            "id": 1, "title": "Test Recipe", "readyInMinutes": 10, "extendedIngredients": []
        })
        db.add(recipe)
        db.commit()

    response = client.get('/home?tab=my_recipes')
    print("RESPONSE STATUS:", response.status_code)
    print("RESPONSE HEADERS:", response.headers)
    print("RESPONSE DATA:", response.data[:500])
    assert response.status_code == 200
    assert b"Test Recipe" in response.data

def test_add_custom_recipe(client, logged_in_session):
    ingredients = [{"id": 1, "name": "salt", "originalAmount": "1 tsp", "qty": 1, "unitString": "tsp"}]
    payload = {
        "title": "New Custom Recipe",
        "ingredients": json.dumps(ingredients),
        "instructions": "Step 1: Sprinkle salt.",
        "image": "http://example.com/salt.jpg"
    }
    response = client.post('/add_recipe', data=payload, follow_redirects=True)
    assert response.status_code == 200
    
    with app_database.SessionLocal() as db:
        recipe = db.execute(select(Recipe).filter(Recipe.title == "New Custom Recipe")).scalars().first()
        assert recipe is not None
        assert recipe.user_id == logged_in_session

def test_search_recipes(client, logged_in_session, mocker):
    mock_spoonacular_response = [
        {
            "id": 101,
            "title": "Mock Soup",
            "image": "http://mock.jpg",
            "readyInMinutes": 15,
            "dishTypes": ["soup"],
            "vegetarian": True,
            "vegan": True,
            "glutenFree": True,
            "instructions": "Eat it cold.",
            "extendedIngredients": []
        }
    ]
    
    mock_get = mocker.patch("httpx.get")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_spoonacular_response
    mock_get.return_value = mock_response

    response = client.post('/search', data={"ingredients": "water", "number": 3}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Mock Soup" in response.data

def test_get_recipe_details(client, logged_in_session):
    with app_database.SessionLocal() as db:
        recipe = Recipe(id=200, title="Database Pasta", user_id=logged_in_session, raw_data={
            "id": 200, "title": "Database Pasta", "instructions": "Boil pasta.", "extendedIngredients": []
        })
        db.add(recipe)
        db.commit()

    response = client.get('/recipe/200')
    assert response.status_code == 200
    assert b"Database Pasta" in response.data

def test_like_recipe(client, logged_in_session):
    with app_database.SessionLocal() as db:
        recipe = Recipe(id=300, title="Likable Pizza", raw_data={
            "id": 300, "title": "Likable Pizza", "likes": 0
        })
        db.add(recipe)
        db.commit()

    response = client.post('/recipe/300/like')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "liked"

def test_edit_custom_recipe(client, logged_in_session):
    with app_database.SessionLocal() as db:
        recipe = Recipe(id=400, title="Old Pizza", user_id=logged_in_session, raw_data={
            "id": 400, "title": "Old Pizza", "instructions": "Bake it."
        })
        db.add(recipe)
        db.commit()

    payload = {
        "title": "New Pizza",
        "ingredients": "[]",
        "instructions": "Bake it longer.",
        "image": ""
    }
    response = client.post('/recipe/400/edit', data=payload, follow_redirects=True)
    assert response.status_code == 200
    
    with app_database.SessionLocal() as db:
        db_recipe = db.execute(select(Recipe).filter(Recipe.id == 400)).scalars().first()
        assert db_recipe.title == "New Pizza"

def test_update_settings(client, logged_in_session):
    payload = {
        "default_vegetarian": "on",
        "default_vegan": "on",
        "default_gluten_free": "on",
        "default_kosher": "on",
        "default_dish_type": "dessert",
        "default_prep_time": "45"
    }
    response = client.post('/update_settings', data=payload, follow_redirects=True)
    assert response.status_code == 200

    with app_database.SessionLocal() as db:
        user = db.execute(select(User).filter(User.id == logged_in_session)).scalars().first()
        assert user.default_vegetarian is True
        assert user.default_dish_type == "dessert"

def test_ai_generate_recipe(client, logged_in_session, mocker):
    mock_ai_response = {
        "choices": [
            {
                "message": {
                    "content": '{"title": "AI Salad", "ingredients": ["lettuce"], "instructions": ["Chop lettuce"], "servings": 1}'
                }
            }
        ]
    }
    mock_post = mocker.patch("httpx.post")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ai_response
    mock_post.return_value = mock_response

    response = client.post('/ai/generate-ai', data={"ingredients": "lettuce"}, follow_redirects=True)
    assert response.status_code == 200
    
    with app_database.SessionLocal() as db:
        recipe = db.execute(select(Recipe).filter(Recipe.title == "AI Salad")).scalars().first()
        assert recipe is not None

def test_ai_substitute_recipe(client, logged_in_session, mocker):
    with app_database.SessionLocal() as db:
        recipe = Recipe(id=500, title="Carrot Cake", user_id=logged_in_session, raw_data={
            "title": "Carrot Cake",
            "extendedIngredients": [{"name": "sugar", "original": "sugar"}],
            "instructions": "Bake it."
        })
        db.add(recipe)
        db.commit()

    mock_ai_response = {
        "choices": [
            {
                "message": {
                    "content": '{"title": "Adapted Carrot Cake", "ingredients": ["honey"], "instructions": ["Use honey", "Bake it"]}'
                }
            }
        ]
    }
    mock_post = mocker.patch("httpx.post")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ai_response
    mock_post.return_value = mock_response

    response = client.post('/ai/recipe/500/substitute-ai', data={"ingredient_to_replace": "sugar"}, follow_redirects=True)
    assert response.status_code == 200

    with app_database.SessionLocal() as db:
        new_recipe = db.execute(select(Recipe).filter(Recipe.title == "Adapted Carrot Cake")).scalars().first()
        assert new_recipe is not None

def test_ai_quick_substitute(client, logged_in_session, mocker):
    with app_database.SessionLocal() as db:
        recipe = Recipe(id=600, title="Milkshake", user_id=logged_in_session, raw_data={
            "title": "Milkshake",
            "extendedIngredients": [{"name": "milk"}]
        })
        db.add(recipe)
        db.commit()

    mock_ai_response = {
        "choices": [
            {
                "message": {
                    "content": "Use almond milk instead."
                }
            }
        ]
    }
    mock_post = mocker.patch("httpx.post")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ai_response
    mock_post.return_value = mock_response

    response = client.get('/ai/quick-substitute?recipe_id=600&ingredient=milk')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "almond milk" in data["recommendation"]
