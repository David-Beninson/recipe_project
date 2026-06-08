import pytest

@pytest.mark.anyio
async def test_create_user_success(client):
    payload = {
        "user_name": "david",
        "password": "securepassword123"
    }
    
    response = await client.post("/sign_up/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_success(client):
    user_payload = {
        "user_name": "Oliver",
        "password": "supersecretpassword"
    }
    await client.post("/sign_up/", json=user_payload)
    
    login_data = {
        "username": "Oliver",
        "password": "supersecretpassword"
    }
    
    response = await client.post("/login/", data=login_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_invalid_credentials(client):
    user_payload = {
        "user_name": "testuser",
        "password": "correctpassword"
    }
    await client.post("/sign_up/", json=user_payload)
    
    login_data = {
        "username": "testuser",
        "password": "wrongpassword"
    }
    
    response = await client.post("/login/", data=login_data)
    
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Invalid Credentials"