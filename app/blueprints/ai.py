import httpx
from flask import Blueprint, request, redirect, url_for, session, flash, jsonify
from app.utils.oauth2 import create_access_token
from app.utils.flask_helpers import login_required
from app.config import settings

ai_bp = Blueprint('ai', __name__, url_prefix="/ai")


@ai_bp.route('/generate-ai', methods=['POST'])
@login_required
def generate_ai():
    """Route to generate a new recipe using AI from available ingredients."""
    ingredients = request.form.get('ingredients')
    if not ingredients:
        flash("Please enter ingredients for the AI to use.", "warning")
        return redirect(url_for('recipes.search'))
        
    token = create_access_token(data={"user_id": session['user_id']})
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with httpx.Client() as client:
            # Call FastAPI AI generation endpoint
            response = client.post(
                f"{settings.backend_url}/ai/generate",
                headers=headers,
                json={"ingredients": ingredients},
                timeout=35.0
            )
            if response.status_code == 200:
                result = response.json()
                flash("AI successfully created a custom recipe for you!", "success")
                return redirect(url_for('recipes.cooking_steps', recipe_id=result["id"]))
            else:
                flash(f"AI Generation Error: {response.text}", "error")
    except Exception as e:
        print(f"AI Generation connection error: {e}")
        flash("Failed to connect to AI backend service.", "error")
        
    return redirect(url_for('recipes.search'))


@ai_bp.route('/recipe/<int:recipe_id>/substitute-ai', methods=['POST'])
@login_required
def substitute_ai(recipe_id):
    """Route to adapt an existing recipe using AI by replacing a specific ingredient."""
    ingredient_to_replace = request.form.get('ingredient_to_replace')
    if not ingredient_to_replace:
        flash("Please specify the ingredient to replace.", "warning")
        return redirect(url_for('recipes.cooking_steps', recipe_id=recipe_id))
        
    token = create_access_token(data={"user_id": session['user_id']})
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with httpx.Client() as client:
            # Call FastAPI AI substitution endpoint
            response = client.post(
                f"{settings.backend_url}/ai/substitute/{recipe_id}",
                headers=headers,
                json={"ingredient_to_replace": ingredient_to_replace},
                timeout=35.0
            )
            if response.status_code == 200:
                result = response.json()
                flash("Recipe successfully adapted by AI with the substituted ingredient!", "success")
                return redirect(url_for('recipes.cooking_steps', recipe_id=result["id"]))
            else:
                flash(f"AI Substitution Error: {response.text}", "error")
    except Exception as e:
        print(f"AI Substitution connection error: {e}")
        flash("Failed to connect to AI backend service.", "error")
        
    return redirect(url_for('recipes.cooking_steps', recipe_id=recipe_id))


@ai_bp.route('/quick-substitute', methods=['GET'])
@login_required
def quick_substitute():
    """Route to fetch a quick AI substitute suggestion dynamically (AJAX)."""
    recipe_id = request.args.get('recipe_id')
    ingredient = request.args.get('ingredient')
    if not recipe_id or not ingredient:
        return jsonify({"error": "Missing parameters"}), 400
        
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{settings.backend_url}/ai/quick-substitute",
                params={"recipe_id": recipe_id, "ingredient": ingredient},
                timeout=25.0
            )
            return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Quick substitute backend connection error: {e}")
        return jsonify({"error": "Failed to retrieve suggestion from AI backend"}), 500