import pytest
from app import models
from app.fast_api import app
from app.utils.oauth2 import get_current_user

@pytest.mark.anyio
async def test_update_user_settings_success(client, session):
    db_user = models.User(id=1, user_name="Oliver", password="hashed_password")
    session.add(db_user)
    await session.commit()

    app.dependency_overrides[get_current_user] = lambda: db_user

    # Update settings
    settings_payload = {
        "default_vegetarian": True,
        "default_vegan": False,
        "default_gluten_free": True,
        "default_kosher": True,
        "default_dish_type": "salad",
        "default_prep_time": 30
    }

    response = await client.put("/users/settings", json=settings_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["default_vegetarian"] is True
    assert data["default_kosher"] is True
    assert data["default_dish_type"] == "salad"
    assert data["default_prep_time"] == 30

    # Retrieve settings to verify persistence
    response = await client.get("/users/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["default_vegetarian"] is True
    assert data["default_kosher"] is True
    assert data["default_dish_type"] == "salad"
    assert data["default_prep_time"] == 30


@pytest.mark.anyio
async def test_extract_filter_params_defaults(monkeypatch):
    from app.main import app as flask_app
    from app.utils.flask_helpers import extract_filter_params
    import app.utils.flask_helpers
    
    # Mock settings returned by get_user_settings
    mock_settings = {
        'dish_type': 'soup',
        'prep_time': 15,
        'vegetarian': True,
        'vegan': False,
        'gluten_free': False,
        'kosher': True
    }
    
    monkeypatch.setattr(app.utils.flask_helpers, "get_user_settings", lambda user_id: mock_settings)

    # 1. Test when NO query parameters are sent (fresh page load) -> should return user defaults
    with flask_app.test_request_context("/home?tab=recipes"):
        from flask import session as flask_session
        flask_session['user_id'] = 2
        
        filters = extract_filter_params()
        assert filters['vegetarian'] is True
        assert filters['kosher'] is True
        assert filters['vegan'] is False
        assert filters['dish_type'] == "soup"
        assert filters['prep_time'] == 15

    # 2. Test when filters ARE explicitly submitted -> should override user defaults
    with flask_app.test_request_context("/home?tab=recipes&filter_submitted=true&vegetarian=on&dish_type=salad&prep_time=45"):
        from flask import session as flask_session
        flask_session['user_id'] = 2
        
        filters = extract_filter_params()
        # Even though user default kosher is True, since they explicitly submitted filters and didn't check kosher, it should be False
        assert filters['vegetarian'] is True
        assert filters['kosher'] is False
        assert filters['dish_type'] == "salad"
        assert filters['prep_time'] == 45


