import pytest
from app.fast_api import app
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
async def test_generate_recipe_ai_success(client, session, mocker):
    db_user = models.User(id=2, user_name="Alice", password="hashed_password")
    session.add(db_user)
    await session.commit()
    
    app.dependency_overrides[get_current_user] = lambda: db_user
    
    # Mock AI response
    mock_ai_response = {
        "choices": [
            {
                "message": {
                    "content": '{"title": "AI Tomato Pasta", "ingredients": ["pasta", "tomato", "basil"], "instructions": ["Boil pasta", "Make tomato sauce", "Combine everything", "Garnish with basil"], "prep_time": "20 mins", "servings": 2}'
                }
            }
        ]
    }
    
    import httpx
    original_post = httpx.AsyncClient.post
    async def mock_post(self, url, *args, **kwargs):
        if "chat/completions" in str(url):
            mock_resp = mocker.MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_ai_response
            return mock_resp
        return await original_post(self, url, *args, **kwargs)

    mocker.patch("httpx.AsyncClient.post", side_effect=mock_post, autospec=True)
    
    response = await client.post("/ai/generate", json={"ingredients": "pasta,tomato"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["title"] == "AI Tomato Pasta"


@pytest.mark.anyio
async def test_substitute_recipe_ai_success(client, session, mocker):
    db_user = models.User(id=3, user_name="Bob", password="hashed_password")
    session.add(db_user)
    
    # Original recipe
    db_recipe = models.Recipe(
        id=202,
        spoonacular_id=202,
        title="Chicken Alfredo",
        raw_data={
            "title": "Chicken Alfredo",
            "extendedIngredients": [{"original": "chicken", "name": "chicken"}, {"original": "heavy cream", "name": "heavy cream"}],
            "instructions": "Cook chicken. Add cream."
        }
    )
    session.add(db_recipe)
    await session.commit()
    
    app.dependency_overrides[get_current_user] = lambda: db_user
    
    # Mock AI response for substitution
    mock_ai_response = {
        "choices": [
            {
                "message": {
                    "content": '{"title": "Adapted Chicken Alfredo (substituted chicken)", "ingredients": ["tofu", "heavy cream"], "instructions": ["Cook tofu", "Add cream", "Simmer until done", "Serve hot"], "prep_time": "25 mins", "servings": 4}'
                }
            }
        ]
    }
    
    import httpx
    original_post = httpx.AsyncClient.post
    async def mock_post(self, url, *args, **kwargs):
        if "chat/completions" in str(url):
            mock_resp = mocker.MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_ai_response
            return mock_resp
        return await original_post(self, url, *args, **kwargs)

    mocker.patch("httpx.AsyncClient.post", side_effect=mock_post, autospec=True)
    
    response = await client.post("/ai/substitute/202", json={"ingredient_to_replace": "chicken"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "Adapted Chicken Alfredo" in data["title"]


@pytest.mark.anyio
async def test_quick_substitute_ai_success(client, session, mocker):
    # Insert recipe
    db_recipe = models.Recipe(
        id=303,
        spoonacular_id=303,
        title="Beef Stew",
        raw_data={
            "title": "Beef Stew",
            "extendedIngredients": [{"original": "beef", "name": "beef"}]
        }
    )
    session.add(db_recipe)
    await session.commit()
    
    # Mock AI response for quick substitute suggestion
    mock_ai_response = {
        "choices": [
            {
                "message": {
                    "content": "You can use button mushrooms or portobello mushrooms instead of beef for a vegetarian option."
                }
            }
        ]
    }
    
    import httpx
    original_post = httpx.AsyncClient.post
    async def mock_post(self, url, *args, **kwargs):
        if "chat/completions" in str(url):
            mock_resp = mocker.MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_ai_response
            return mock_resp
        return await original_post(self, url, *args, **kwargs)

    mocker.patch("httpx.AsyncClient.post", side_effect=mock_post, autospec=True)
    
    response = await client.get("/ai/quick-substitute?recipe_id=303&ingredient=beef")
    assert response.status_code == 200
    data = response.json()
    assert "recommendation" in data
    assert "button mushrooms" in data["recommendation"]


