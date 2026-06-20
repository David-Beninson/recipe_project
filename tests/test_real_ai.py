import pytest
import httpx
from app.config import settings
from app.services.ai_service import _call_ai_api

def test_real_ai_endpoint_connection():
    """Verify that we can reach the configured AI endpoint and it responds, without mocking."""
    payload = {
        "model": "{settings.model}",
        "messages": [
            {"role": "system", "content": "You are a test helper."},
            {"role": "user", "content": "Respond with 'OK'"}
        ],
        "temperature": 0.2
    }
    
    try:
        response = httpx.post(
            settings.ai_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )
        print(f"Real AI Endpoint response status: {response.status_code}")
        print(f"Real AI Endpoint response body: {response.text}")
        
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert "choices" in result
    except Exception as e:
        pytest.fail(f"Failed to connect to real AI URL ({settings.ai_url}): {e}")

def test_real_ai_service_integration():
    """Test the actual helper function calling the real AI endpoint."""
    try:
        result = _call_ai_api(
            system_prompt="Generate a recipe from scratch using the ingredients. Output JSON with title, ingredients (list), and instructions (list).",
            user_prompt="Ingredients: tomatoes, eggs"
        )
        print("Real AI Service Integration Result:", result)
        assert isinstance(result, dict)
        assert "title" in result
        assert "ingredients" in result
    except Exception as e:
        pytest.fail(f"Real AI service helper failed: {e}")
