import json
import httpx
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import SessionLocal
from app.models import User, UserSearch, Recipe
from app.utils.oauth2 import create_access_token
from app.utils.flask_helpers import login_required, filter_recipes_list, check_kosher

recipes_bp = Blueprint('recipes', __name__)

@recipes_bp.route('/home')
@login_required
def home():
    """Home page after login showing previously searched recipes."""
    user_recipes = []
    liked_recipes = []
    
    # Get tab and filter parameters
    active_tab = request.args.get('tab', 'recipes')
    dish_type = request.args.get('dish_type', '')
    prep_time_str = request.args.get('prep_time', '')
    prep_time = int(prep_time_str) if prep_time_str and prep_time_str.isdigit() else 9999
    vegetarian = request.args.get('vegetarian') == 'on' or request.args.get('vegetarian') == 'true'
    vegan = request.args.get('vegan') == 'on' or request.args.get('vegan') == 'true'
    gluten_free = request.args.get('gluten_free') == 'on' or request.args.get('gluten_free') == 'true'
    isKosher = vegetarian or vegan or request.args.get('extendedIngredients') 

    try:
        with SessionLocal() as db:
            # Load user searches with their cached recipes
            stmt = select(UserSearch).filter(UserSearch.user_id == session['user_id']).options(selectinload(UserSearch.recipes))
            searches = db.execute(stmt).scalars().all()
            
            seen_recipe_ids = set()
            for search_obj in searches:
                for r in search_obj.recipes:
                    if r.spoonacular_id not in seen_recipe_ids:
                        seen_recipe_ids.add(r.spoonacular_id)
                        recipe_data = r.raw_data if r.raw_data else {}
                        # Make sure necessary keys are set
                        recipe_data['id'] = r.spoonacular_id
                        recipe_data['title'] = r.title
                        user_recipes.append(recipe_data)
            
            # Load custom recipes added by the user
            custom_stmt = select(Recipe).filter(Recipe.user_id == session['user_id'])
            custom_recipes = db.execute(custom_stmt).scalars().all()
            for r in custom_recipes:
                recipe_data = r.raw_data if r.raw_data else {}
                recipe_data['id'] = r.id
                recipe_data['title'] = r.title
                user_recipes.append(recipe_data)
                
            # Load user liked recipes
            user_stmt = select(User).filter(User.id == session['user_id']).options(selectinload(User.liked_recipes))
            user_obj = db.execute(user_stmt).scalars().first()
            if user_obj:
                for r in user_obj.liked_recipes:
                    recipe_data = r.raw_data if r.raw_data else {}
                    recipe_data['id'] = r.spoonacular_id if r.spoonacular_id else r.id
                    recipe_data['title'] = r.title
                    liked_recipes.append(recipe_data)
                
    except Exception as e:
        print(f"Error fetching user recipes: {e}")
        user_recipes = []
        liked_recipes = []
        
    # Apply filtering in Python
    filtered_user_recipes = filter_recipes_list(
        user_recipes,
        dish_type=dish_type,
        prep_time=prep_time if prep_time != 9999 else None,
        vegetarian=vegetarian,
        vegan=vegan,
        gluten_free=gluten_free,
        kosher=isKosher
    )
    
    filtered_liked_recipes = filter_recipes_list(
        liked_recipes,
        dish_type=dish_type,
        prep_time=prep_time if prep_time != 9999 else None,
        vegetarian=vegetarian,
        vegan=vegan,
        gluten_free=gluten_free,
        kosher=isKosher
    )

    return render_template(
        'home.html',
        username=session.get('username'),
        user_recipes=filtered_user_recipes,
        liked_recipes=filtered_liked_recipes,
        has_recipes_total=len(user_recipes) > 0 or len(liked_recipes) > 0,
        active_tab=active_tab,
        dish_type=dish_type,
        prep_time=prep_time,
        vegetarian=vegetarian,
        vegan=vegan,
        gluten_free=gluten_free,
        kosher=isKosher
    )

@recipes_bp.route('/add_recipe', methods=['POST'])
@login_required
def add_recipe():
    """Route to add a custom recipe."""
    title = request.form.get('title')
    ingredients_raw = request.form.get('ingredients')
    instructions = request.form.get('instructions')
    
    try:
        ingredients = json.loads(ingredients_raw) if ingredients_raw else []
    except Exception as e:
        print(f"Error parsing ingredients JSON: {e}")
        ingredients = []
        
    # Generate JWT token for authenticate with FastAPI
    token = create_access_token(data={"user_id": session['user_id']})
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "image": ""
    }
    
    try:
        with httpx.Client() as client:
            response = client.post("http://127.0.0.1:8000/recipes/custom", headers=headers, json=payload, timeout=10.0)
            if response.status_code == 200:
                flash("Recipe added successfully!", "success")
            else:
                flash(f"Backend API error: {response.text}", "error")
    except Exception as e:
        print(f"Connection error to backend: {e}")
        flash("Failed to connect to backend service.", "error")
        
    return redirect(url_for('recipes.home'))

@recipes_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Search for recipes page and handler - calls FastAPI backend."""
    recipes = []
    ingredients = ""
    number = 5
    dish_type = ""
    prep_time = 9999
    vegetarian = False
    vegan = False
    gluten_free = False
    
    if request.method == 'POST':
        ingredients = request.form.get('ingredients', '')
        number = request.form.get('number', 5)
        dish_type = request.form.get('dish_type', '')
        prep_time_str = request.form.get('prep_time', '9999')
        prep_time = int(prep_time_str) if prep_time_str.isdigit() else 9999
        vegetarian = request.form.get('vegetarian') == 'on'
        vegan = request.form.get('vegan') == 'on'
        gluten_free = request.form.get('gluten_free') == 'on'
        
        if not ingredients:
            flash('Please enter ingredients', 'warning')
            return redirect(url_for('recipes.search'))
        
        # Generate JWT token for authenticate with FastAPI
        token = create_access_token(data={"user_id": session['user_id']})
        headers = {"Authorization": f"Bearer {token}"}
        params = {"ingredients": ingredients, "number": number}
        
        try:
            # Call the FastAPI backend service
            with httpx.Client() as client:
                response = client.get("http://127.0.0.1:8000/recipes/find-by-ingredients", headers=headers, params=params, timeout=10.0)
                if response.status_code == 200:
                    raw_recipes = response.json()
                    # Filter in Python
                    recipes = filter_recipes_list(
                        raw_recipes,
                        dish_type=dish_type,
                        prep_time=prep_time if prep_time != 9999 else None,
                        vegetarian=vegetarian,
                        vegan=vegan,
                        gluten_free=gluten_free
                    )
                    flash(f'Found {len(recipes)} recipes matching filters.', 'success')
                else:
                    flash(f"Backend API error: {response.text}", "error")
        except Exception as e:
            print(f"Connection error to backend: {e}")
            flash("Failed to connect to backend service.", "error")
    
    return render_template(
        'search.html',
        recipes=recipes,
        ingredients=ingredients,
        number=number,
        dish_type=dish_type,
        prep_time=prep_time,
        vegetarian=vegetarian,
        vegan=vegan,
        gluten_free=gluten_free
    )

@recipes_bp.route('/recipe/<int:recipe_id>')
@login_required
def cooking_steps(recipe_id):
    """Retrieve recipe details from FastAPI and display cooking steps."""
    try:
        # Fetch detailed recipe information (including instructions and ingredients)
        with httpx.Client() as client:
            response = client.get(f"http://127.0.0.1:8000/recipes/{recipe_id}/information", timeout=10.0)
            if response.status_code == 200:
                recipe = response.json()
                # Ensure the ID matches what templates expect
                recipe['id'] = recipe_id
                
                # Check if this recipe is liked by the current user
                is_liked = False
                with SessionLocal() as db:
                    user_stmt = select(User).filter(User.id == session['user_id']).options(selectinload(User.liked_recipes))
                    user_obj = db.execute(user_stmt).scalars().first()
                    if user_obj:
                        is_liked = any(r.spoonacular_id == recipe_id or r.id == recipe_id for r in user_obj.liked_recipes)
                        
                return render_template('cooking_steps.html', recipe=recipe, is_liked=is_liked)
            else:
                flash('Recipe detail not found on server', 'error')
                return redirect(url_for('recipes.home'))
    except Exception as e:
        print(f"Error fetching recipe: {e}")
        flash('Error loading recipe details from backend', 'error')
        return redirect(url_for('recipes.home'))

@recipes_bp.route('/recipe/<int:recipe_id>/like', methods=['POST'])
@login_required
def like_recipe_route(recipe_id):
    """Toggle like for a recipe by calling the backend."""
    token = create_access_token(data={"user_id": session['user_id']})
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client() as client:
            response = client.post(f"http://127.0.0.1:8000/recipes/{recipe_id}/like", headers=headers, timeout=10.0)
            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return jsonify({"error": "Failed to toggle like on backend"}), response.status_code
    except Exception as e:
        print(f"Error calling like backend: {e}")
        return jsonify({"error": "Connection error to backend"}), 500

@recipes_bp.route('/substitutes')
@login_required
def substitutes():
    """Proxy route to call FastAPI substitutes endpoint."""
    ingredient = request.args.get('ingredient')
    if not ingredient:
        return jsonify({"detail": "Missing ingredient parameter"}), 400
        
    try:
        with httpx.Client() as client:
            response = client.get("http://127.0.0.1:8000/recipes/substitutes", params={"ingredient": ingredient}, timeout=10.0)
            return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Substitutes backend error: {e}")
        return jsonify({"detail": "Failed to retrieve substitutes from backend"}), 500
