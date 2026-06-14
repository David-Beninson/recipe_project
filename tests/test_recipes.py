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
    mock_search_response = [
        {
            "id": 716429,
            "title": "Pasta with Garlic and Tomato",
            "image": "https://spoonacular.com/recipeImages/716429-312x231.jpg",
            "imageType": "jpg",
            "usedIngredientCount": 2,
            "missedIngredientCount": 1,
            "likes": 10,
            "usedIngredients": [],
            "missedIngredients": [],
            "unusedIngredients": []
        }
    ]
    
    mock_bulk_response = [
        {
            "id": 716429,
            "title": "Pasta with Garlic and Tomato",
            "image": "https://spoonacular.com/recipeImages/716429-312x231.jpg",
            "readyInMinutes": 25,
            "dishTypes": ["lunch", "main course", "dinner"],
            "vegetarian": True,
            "vegan": False,
            "glutenFree": True,
            "instructions": "Boil pasta.",
            "extendedIngredients": []
        }
    ]
    
    async def mock_get(url, params=None, **kwargs):
        mock_resp = mocker.MagicMock()
        mock_resp.status_code = 200
        if "informationBulk" in url:
            mock_resp.json.return_value = mock_bulk_response
        else:
            mock_resp.json.return_value = mock_search_response
        return mock_resp

    mocker.patch("httpx.AsyncClient.get", side_effect=mock_get)

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


@pytest.mark.anyio
async def test_update_custom_recipe_success(client, session):
    db_user = models.User(id=1, user_name="Oliver", password="hashed_password")
    session.add(db_user)
    db_recipe = models.Recipe(id=102, title="Original Title", user_id=1, raw_data={"title": "Original Title", "ingredients": []})
    session.add(db_recipe)
    await session.commit()

    app.dependency_overrides[get_current_user] = lambda: db_user

    update_payload = {
        "title": "Updated Title",
        "ingredients": [
            {
                "name": "Sugar",
                "originalAmount": "1 cup",
                "qty": 1.0,
                "unitString": "cup",
                "usedQty": 1.0
            }
        ],
        "instructions": "Mix it.",
        "image": "http://image.url"
    }

    response = await client.put("/recipes/102", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"

    from sqlalchemy import select
    stmt = select(models.Recipe).filter(models.Recipe.id == 102)
    res = await session.execute(stmt)
    recipe = res.scalars().first()
    assert recipe.title == "Updated Title"
    assert recipe.raw_data.get("instructions") == "Mix it."


@pytest.mark.anyio
async def test_update_custom_recipe_unauthorized(client, session):
    db_user = models.User(id=1, user_name="Oliver", password="hashed_password")
    session.add(db_user)
    db_recipe = models.Recipe(id=103, title="Secret Title", user_id=2, raw_data={"title": "Secret Title"})
    session.add(db_recipe)
    await session.commit()

    app.dependency_overrides[get_current_user] = lambda: db_user

    update_payload = {
        "title": "Hack Title",
        "ingredients": [],
        "instructions": "Hack.",
        "image": None
    }

    response = await client.put("/recipes/103", json=update_payload)
    assert response.status_code == 403