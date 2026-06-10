import pytest
from app.fast_api import app
from app.database import get_db
from app.utils.oauth2 import get_current_user
from app import models

class MockUser:
    id = 1
    user_name = "Oliver"

@pytest.fixture
async def authenticated_client(client):
    app.dependency_overrides[get_current_user] = lambda: MockUser()
    yield client

@pytest.mark.anyio
async def test_find_recipes_success(authenticated_client, mocker):
    mock_spoonacular_response = [
        {
            "id": 716429,
            "title": "Pasta with Garlic and Tomato",
            "image": "https://spoonacular.com/recipeImages/716429-312x231.jpg",
            "raw_data": {}
        }
    ]
    
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_spoonacular_response
    mocker.patch("httpx.AsyncClient.get", return_value=mock_response)

    response = await authenticated_client.get("/recipes/find-by-ingredients", params={
        "ingredients": "tomato,pasta",
        "number": 3
    })
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["title"] == "Pasta with Garlic and Tomato"
    assert data[0]["id"] == 716429


@pytest.mark.anyio
async def test_find_recipes_missing_ingredients(authenticated_client):
    response = await authenticated_client.get("/recipes/find-by-ingredients")
    
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["detail"][0]["type"] == "missing"


@pytest.mark.anyio
async def test_find_recipes_invalid_number_type(authenticated_client):
    response = await authenticated_client.get("/recipes/find-by-ingredients", params={
        "ingredients": "apples",
        "number": "abc" 
    })
    
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["type"] == "int_parsing"


@pytest.mark.anyio
async def test_like_recipe(client, session):
    # Insert user
    db_user = models.User(id=1, user_name="Oliver", password="hashed_password")
    session.add(db_user)
    # Insert recipe with raw_data containing likes
    db_recipe = models.Recipe(id=101, spoonacular_id=101, title="Test Pizza", raw_data={"likes": 5})
    session.add(db_recipe)
    await session.commit()
    
    # Override current user dependency to return this specific user
    app.dependency_overrides[get_current_user] = lambda: db_user
    
    # Verify liking the recipe
    response = await client.post("/recipes/101/like")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "liked"
    
    # Fetch recipe from database to check incremented likes
    from sqlalchemy import select
    stmt = select(models.Recipe).filter(models.Recipe.id == 101)
    res = await session.execute(stmt)
    recipe = res.scalars().first()
    assert recipe.raw_data.get("likes") == 6
    
    # Verify unliking the recipe
    response = await client.post("/recipes/101/like")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unliked"
    
    # Refresh session and verify decremented likes
    res = await session.execute(stmt)
    recipe = res.scalars().first()
    assert recipe.raw_data.get("likes") == 5