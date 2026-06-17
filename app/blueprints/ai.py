from flask import Blueprint, request, redirect, url_for, session, flash, jsonify
from app.utils.flask_helpers import login_required
from app.database import SessionLocal
from app.services import ai_service

ai_bp = Blueprint('ai', __name__, url_prefix="/ai")


@ai_bp.route('/generate-ai', methods=['POST'])
@login_required
def generate_ai():
    """Route to generate a new recipe using AI from available ingredients."""
    ingredients = request.form.get('ingredients')
    redirect_to = request.form.get('redirect_to') or url_for('recipes.search')
    if not ingredients:
        flash("Please enter ingredients for the AI to use.", "warning")
        return redirect(redirect_to)
        
    try:
        with SessionLocal() as db:
            db_recipe = ai_service.generate_recipe_with_ai(ingredients, session['user_id'], db)
            flash("AI successfully created a custom recipe for you!", "success")
            return redirect(url_for('recipes.cooking_steps', recipe_id=db_recipe.id))
    except Exception as e:
        print(f"AI Generation error: {e}")
        flash("Failed to generate recipe using AI.", "error")
        
    return redirect(redirect_to)


@ai_bp.route('/recipe/<int:recipe_id>/substitute-ai', methods=['POST'])
@login_required
def substitute_ai(recipe_id):
    """Route to adapt an existing recipe using AI by replacing a specific ingredient."""
    ingredient_to_replace = request.form.get('ingredient_to_replace')
    if not ingredient_to_replace:
        flash("Please specify the ingredient to replace.", "warning")
        return redirect(url_for('recipes.cooking_steps', recipe_id=recipe_id))
        
    try:
        with SessionLocal() as db:
            db_recipe = ai_service.substitute_ingredient_with_ai(recipe_id, ingredient_to_replace, session['user_id'], db)
            flash("Recipe successfully adapted by AI with the substituted ingredient!", "success")
            return redirect(url_for('recipes.cooking_steps', recipe_id=db_recipe.id))
    except Exception as e:
        print(f"AI Substitution error: {e}")
        flash("Failed to adapt recipe using AI.", "error")
        
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
        with SessionLocal() as db:
            rec = ai_service.get_quick_substitute_from_ai(int(recipe_id), ingredient, db)
            return jsonify({"recommendation": rec}), 200
    except Exception as e:
        print(f"Quick substitute error: {e}")
        return jsonify({"error": "Failed to retrieve suggestion from AI backend"}), 500