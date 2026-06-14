import json
import httpx
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import SessionLocal
from app.models import User, UserSearch, Recipe
from app.utils.oauth2 import create_access_token
from app.utils.flask_helpers import login_required, filter_recipes_list, extract_filter_params
from app.config import settings

recipes_bp = Blueprint('recipes', __name__)

def _normalize_recipe(r, default_id_attr='id'):
    """Extract and normalize recipe ID, title, and raw data from DB model."""
    recipe_data = (r.raw_data or {}).copy()
    recipe_id = getattr(r, default_id_attr)
    recipe_data['id'] = recipe_id
    recipe_data['title'] = r.title
    recipe_data['user_id'] = r.user_id
    return recipe_id, recipe_data

def _filter_helper(recipes, filters):
    """Convenience wrapper for filter_recipes_list with filter dict."""
    return filter_recipes_list(
        recipes,
        dish_type=filters['dish_type'],
        prep_time=filters['prep_time'] if filters['prep_time'] != 9999 else None,
        vegetarian=filters['vegetarian'],
        vegan=filters['vegan'],
        gluten_free=filters['gluten_free'],
        kosher=filters['kosher']
    )

def _get_auth_headers():
    """Generate JWT authorization headers for backend requests."""
    token = create_access_token(data={"user_id": session['user_id']})
    return {"Authorization": f"Bearer {token}"}

@recipes_bp.route('/home')
@login_required
def home():
    """Home page after login showing previously searched recipes."""
    active_tab = request.args.get('tab', 'recipes')
    filters = extract_filter_params() 
    
    current_recipes = []
    tab_title = ""
    no_recipes_message = ""
    has_recipes_total = False

    try:
        with SessionLocal() as db:
            if active_tab == 'recipes':
                # Load search recipes
                stmt = select(UserSearch).filter(UserSearch.user_id == session['user_id']).options(selectinload(UserSearch.recipes))
                searches = db.execute(stmt).scalars().all()
                seen = set()
                raw_recipes = []
                for search_obj in searches:
                    for r in search_obj.recipes:
                        r_id, r_data = _normalize_recipe(r, 'spoonacular_id')
                        if r_id not in seen:
                            seen.add(r_id)
                            raw_recipes.append(r_data)

                current_recipes = _filter_helper(raw_recipes, filters)
                tab_title = "Searched Recipes"
                no_recipes_message = "No matching searched recipes found."
                has_recipes_total = len(raw_recipes) > 0
                
            elif active_tab == 'my_recipes':
                # Load custom recipes added by the user
                custom_stmt = select(Recipe).filter(Recipe.user_id == session['user_id'])
                custom_recipes = db.execute(custom_stmt).scalars().all()
                raw_recipes = []
                for r in custom_recipes:
                    _, r_data = _normalize_recipe(r, 'id')
                    raw_recipes.append(r_data)

                current_recipes = _filter_helper(raw_recipes, filters)
                tab_title = "My Recipes"
                no_recipes_message = "You haven't added any custom recipes yet."
                has_recipes_total = len(raw_recipes) > 0
                
            elif active_tab == 'liked':
                # Load user liked recipes
                user_stmt = select(User).filter(User.id == session['user_id']).options(selectinload(User.liked_recipes))
                user_obj = db.execute(user_stmt).scalars().first()
                raw_recipes = []
                if user_obj:
                    for r in user_obj.liked_recipes:
                        _, r_data = _normalize_recipe(r, 'spoonacular_id' if r.spoonacular_id else 'id')
                        raw_recipes.append(r_data)

                current_recipes = _filter_helper(raw_recipes, filters)
                tab_title = "Liked Recipes"
                no_recipes_message = "You do not have any liked recipes, you can add them in the 'Instructions' button."
                has_recipes_total = len(raw_recipes) > 0
                
            elif active_tab == 'all':
                # Load all recipes from database
                all_stmt = select(Recipe)
                db_recipes = db.execute(all_stmt).scalars().all()
                seen = set()
                raw_recipes = []
                for r in db_recipes:
                    r_id, r_data = _normalize_recipe(r, 'spoonacular_id' if r.spoonacular_id else 'id')
                    if r_id not in seen:
                        seen.add(r_id)
                        raw_recipes.append(r_data)

                current_recipes = _filter_helper(raw_recipes, filters)
                tab_title = "All Database Recipes"
                no_recipes_message = "No matching database recipes found."
                has_recipes_total = len(raw_recipes) > 0
                
            elif active_tab == 'edit':
                recipe_id = request.args.get('recipe_id')
                if recipe_id:
                    with httpx.Client() as client:
                        response = client.get(f"{settings.backend_url}/recipes/{recipe_id}/information", timeout=10.0)
                        if response.status_code == 200:
                            recipe_obj = response.json()
                            recipe_obj['id'] = recipe_id
                            
                            custom_stmt = select(Recipe).filter(Recipe.id == int(recipe_id))
                            db_recipe = db.execute(custom_stmt).scalars().first()
                            if db_recipe and db_recipe.user_id == session['user_id']:
                                return render_template(
                                    'home.html',
                                    username=session.get('username'),
                                    recipe=recipe_obj,
                                    active_tab='edit',
                                    current_recipes=[],
                                    tab_title="Edit Recipe",
                                    no_recipes_message="",
                                    has_recipes_total=False,
                                    **filters
                                )
                flash("You are not authorized to edit this recipe.", "error")
                return redirect(url_for('recipes.home'))
                
    except Exception as e:
        print(f"Error fetching recipes for tab {active_tab}: {e}")

    return render_template(
        'home.html',
        username=session.get('username'),
        current_recipes=current_recipes,
        tab_title=tab_title,
        no_recipes_message=no_recipes_message,
        has_recipes_total=has_recipes_total,
        active_tab=active_tab,
        **filters
    )

@recipes_bp.route('/add_recipe', methods=['POST'])
@login_required
def add_recipe():
    """Route to add a custom recipe."""
    title = request.form.get('title')
    ingredients_raw = request.form.get('ingredients')
    instructions = request.form.get('instructions')
    image = request.form.get('image') or ""

    try:
        ingredients = json.loads(ingredients_raw) if ingredients_raw else []
    except Exception as e:
        print(f"Error parsing ingredients JSON: {e}")
        ingredients = []

    payload = {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "image": image
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(f"{settings.backend_url}/recipes/custom", headers=_get_auth_headers(), json=payload, timeout=10.0)
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
    
    filters = extract_filter_params()
    
    if request.method == 'POST':
        ingredients = request.form.get('ingredients', '')
        number = request.form.get('number', 5)
        
        if not ingredients:
            flash('Please enter ingredients', 'warning')
            return redirect(url_for('recipes.search'))
        
        params = {"ingredients": ingredients, "number": number}
        
        try:
            # Call the FastAPI backend service
            with httpx.Client() as client:
                response = client.get(f"{settings.backend_url}/recipes/find-by-ingredients", headers=_get_auth_headers(), params=params, timeout=10.0)
                if response.status_code == 200:
                    raw_recipes = response.json()
                    recipes = _filter_helper(raw_recipes, filters)
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
        **filters
    )

@recipes_bp.route('/recipe/<int:recipe_id>')
@login_required
def cooking_steps(recipe_id):
    """Retrieve recipe details from FastAPI and display cooking steps."""
    try:
        # Fetch detailed recipe information (including instructions and ingredients)
        with httpx.Client() as client:
            response = client.get(f"{settings.backend_url}/recipes/{recipe_id}/information", timeout=10.0)
            if response.status_code == 200:
                recipe = response.json()
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
    try:
        with httpx.Client() as client:
            response = client.post(f"{settings.backend_url}/recipes/{recipe_id}/like", headers=_get_auth_headers(), timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                # Keep session cache of liked recipe IDs in sync
                if 'liked_recipe_ids' in session:
                    liked_ids = list(session['liked_recipe_ids'])
                    if data.get('status') == 'liked':
                        if recipe_id not in liked_ids:
                            liked_ids.append(recipe_id)
                    elif data.get('status') == 'unliked':
                        if recipe_id in liked_ids:
                            liked_ids.remove(recipe_id)
                    session['liked_recipe_ids'] = liked_ids
                return jsonify(data)
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
            response = client.get(f"{settings.backend_url}/recipes/substitutes", params={"ingredient": ingredient}, timeout=10.0)
            return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Substitutes backend error: {e}")
        return jsonify({"detail": "Failed to retrieve substitutes from backend"}), 500


@recipes_bp.route('/recipe/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    """Route to edit an existing custom recipe."""
    if request.method == 'POST':
        title = request.form.get('title')
        ingredients_raw = request.form.get('ingredients')
        instructions = request.form.get('instructions')
        image = request.form.get('image') or ""

        try:
            ingredients = json.loads(ingredients_raw) if ingredients_raw else []
        except Exception as e:
            print(f"Error parsing ingredients JSON: {e}")
            ingredients = []

        payload = {
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "image": image
        }

        try:
            with httpx.Client() as client:
                response = client.put(f"{settings.backend_url}/recipes/{recipe_id}", headers=_get_auth_headers(), json=payload, timeout=10.0)
                if response.status_code == 200:
                    flash("Recipe updated successfully!", "success")
                    return redirect(url_for('recipes.home', tab='my_recipes'))
                else:
                    flash(f"Backend API error: {response.text}", "error")
        except Exception as e:
            print(f"Connection error to backend: {e}")
            flash("Failed to connect to backend service.", "error")

        return redirect(url_for('recipes.edit_recipe', recipe_id=recipe_id))

    try:
        with httpx.Client() as client:
            response = client.get(f"{settings.backend_url}/recipes/{recipe_id}/information", timeout=10.0)
            if response.status_code == 200:
                recipe = response.json()
                recipe['id'] = recipe_id

                with SessionLocal() as db:
                    stmt = select(Recipe).filter(Recipe.id == recipe_id)
                    db_recipe = db.execute(stmt).scalars().first()
                    if not db_recipe or db_recipe.user_id != session['user_id']:
                        flash("You are not authorized to edit this recipe.", "error")
                        return redirect(url_for('recipes.home'))

                return render_template('edit_recipe.html', recipe=recipe)
            else:
                flash('Recipe not found on server', 'error')
                return redirect(url_for('recipes.home'))
    except Exception as e:
        print(f"Error loading recipe: {e}")
        flash('Error loading recipe from backend', 'error')
        return redirect(url_for('recipes.home'))


@recipes_bp.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    """Route to update user default preferences via FastAPI backend."""
    default_vegetarian = request.form.get('default_vegetarian') == 'on'
    default_vegan = request.form.get('default_vegan') == 'on'
    default_gluten_free = request.form.get('default_gluten_free') == 'on'
    default_kosher = request.form.get('default_kosher') == 'on'
    default_dish_type = request.form.get('default_dish_type', '')
    
    default_prep_time_str = request.form.get('default_prep_time', '9999')
    default_prep_time = int(default_prep_time_str) if default_prep_time_str.isdigit() else 9999
    
    payload = {
        "default_vegetarian": default_vegetarian,
        "default_vegan": default_vegan,
        "default_gluten_free": default_gluten_free,
        "default_kosher": default_kosher,
        "default_dish_type": default_dish_type,
        "default_prep_time": default_prep_time
    }
    
    try:
        with httpx.Client() as client:
            response = client.put(
                f"{settings.backend_url}/users/settings",
                headers=_get_auth_headers(),
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                flash("Default settings updated successfully!", "success")
            else:
                flash(f"Backend API error: {response.text}", "error")
    except Exception as e:
        print(f"Error updating settings: {e}")
        flash("Failed to connect to backend service.", "error")
        
    return redirect(url_for('recipes.settings_page'))


@recipes_bp.route('/settings', methods=['GET'])
@login_required
def settings_page():
    """Render the standalone settings page with user default preferences."""
    user_settings = {
        "default_vegetarian": False,
        "default_vegan": False,
        "default_gluten_free": False,
        "default_kosher": False,
        "default_dish_type": "",
        "default_prep_time": 9999
    }
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{settings.backend_url}/users/settings",
                headers=_get_auth_headers(),
                timeout=10.0
            )
            if response.status_code == 200:
                user_settings = response.json()
    except Exception as e:
        print(f"Error loading settings: {e}")
        
    return render_template(
        'settings.html',
        username=session.get('username'),
        user_settings=user_settings
    )



