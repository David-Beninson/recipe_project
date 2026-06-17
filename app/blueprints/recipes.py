import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import SessionLocal, User, UserSearch, Recipe
from app.utils.flask_helpers import login_required, filter_recipes_list, extract_filter_params
from app.services import recipe_service

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
    recipe_obj = None

    try:
        with SessionLocal() as db:
            # Query active user with preloaded search history and custom recipes
            user_stmt = select(User).filter(User.id == session['user_id']).options(
                selectinload(User.searches).selectinload(UserSearch.recipes),
                selectinload(User.custom_recipes),
                selectinload(User.liked_recipes)
            )
            user_obj = db.execute(user_stmt).scalars().first()
            
            if user_obj:
                # Count total recipes available across all custom/searched items
                searched_recipes_exist = any(len(s.recipes) > 0 for s in user_obj.searches)
                custom_recipes_exist = len(user_obj.custom_recipes) > 0
                has_recipes_total = searched_recipes_exist or custom_recipes_exist

                if active_tab == 'recipes':
                    tab_title = "Searched Recipes"
                    no_recipes_message = "No recently searched recipes found. Go to 'Find Recipes' to discover new meals!"
                    
                    seen_ids = set()
                    for search_history in reversed(user_obj.searches):
                        for r in search_history.recipes:
                            recipe_id, recipe_data = _normalize_recipe(r, 'spoonacular_id')
                            if recipe_id not in seen_ids:
                                seen_ids.add(recipe_id)
                                current_recipes.append(recipe_data)

                elif active_tab == 'my_recipes':
                    tab_title = "My Recipes"
                    no_recipes_message = "You haven't created any custom recipes yet. Use the 'Create Custom Recipe' tool on this page to build your own!"
                    
                    for r in reversed(user_obj.custom_recipes):
                        recipe_id, recipe_data = _normalize_recipe(r)
                        current_recipes.append(recipe_data)

                elif active_tab == 'liked':
                    tab_title = "Liked Recipes"
                    no_recipes_message = "You haven't liked any recipes yet. Click the heart icon on any recipe steps page to save it here!"
                    
                    for r in reversed(user_obj.liked_recipes):
                        recipe_id, recipe_data = _normalize_recipe(r, 'spoonacular_id' if r.spoonacular_id else 'id')
                        current_recipes.append(recipe_data)

                elif active_tab == 'all':
                    tab_title = "All Recipes"
                    no_recipes_message = "No recipes found in your dashboard yet."
                    
                    seen_ids = set()
                    # Add custom user recipes first
                    for r in reversed(user_obj.custom_recipes):
                        recipe_id, recipe_data = _normalize_recipe(r)
                        if recipe_id not in seen_ids:
                            seen_ids.add(recipe_id)
                            current_recipes.append(recipe_data)
                    # Add searched recipes second
                    for search_history in reversed(user_obj.searches):
                        for r in search_history.recipes:
                            recipe_id, recipe_data = _normalize_recipe(r, 'spoonacular_id')
                            if recipe_id not in seen_ids:
                                seen_ids.add(recipe_id)
                                current_recipes.append(recipe_data)

                elif active_tab == 'edit':
                    # Fetch recipe details to populate the edit form
                    recipe_id_val = request.args.get('recipe_id', type=int)
                    if recipe_id_val:
                        recipe_obj = recipe_service.get_recipe_details(recipe_id_val, db)
                        if recipe_obj:
                            recipe_obj['id'] = recipe_id_val
            
            # Apply user dietary/filtering choices to dashboard list
            current_recipes = _filter_helper(current_recipes, filters)

    except Exception as e:
        print(f"Error loading home dashboard: {e}")
        flash("Failed to load recipe dashboard.", "error")

    is_htmx = request.headers.get('HX-Request') == 'true'
    template = 'partials/home_content.html' if is_htmx else 'home.html'
    return render_template(
        template,
        username=session.get('username'),
        current_recipes=current_recipes,
        active_tab=active_tab,
        tab_title=tab_title,
        no_recipes_message=no_recipes_message,
        has_recipes_total=has_recipes_total,
        recipe=recipe_obj,
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
    
    try:
        with SessionLocal() as db:
            recipe_service.save_custom_recipe(title, ingredients, instructions, image, session['user_id'], db)
            flash("Recipe added successfully!", "success")
    except Exception as e:
        print(f"Error saving custom recipe: {e}")
        flash("Failed to save custom recipe.", "error")
        
    return redirect(url_for('recipes.home'))

@recipes_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Search for recipes page and handler."""
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
        
        try:
            with SessionLocal() as db:
                new_search = UserSearch(user_id=session['user_id'], query_ingredients=ingredients, recipes=[])
                db.add(new_search)
                
                raw_recipes = recipe_service.fetch_recipes_with_fallback(ingredients, int(number), db)
                if raw_recipes:
                    recipe_service.cache_and_link_recipes(raw_recipes, new_search, db)
                    recipes = _filter_helper(raw_recipes, filters)
                    flash(f'Found {len(recipes)} recipes matching filters.', 'success')
                else:
                    flash("No matching recipes found.", "warning")
        except Exception as e:
            print(f"Error searching recipes: {e}")
            flash("Failed to search recipes.", "error")
    
    is_htmx = request.headers.get('HX-Request') == 'true'
    template = 'partials/search_content.html' if is_htmx else 'search.html'
    return render_template(
        template,
        recipes=recipes,
        ingredients=ingredients,
        number=number,
        **filters
    )

@recipes_bp.route('/recipe/<int:recipe_id>')
@login_required
def cooking_steps(recipe_id):
    """Retrieve recipe details and display cooking steps."""
    try:
        with SessionLocal() as db:
            recipe = recipe_service.get_recipe_details(recipe_id, db)
            if recipe:
                recipe['id'] = recipe_id
                
                is_liked = False
                user_stmt = select(User).filter(User.id == session['user_id']).options(selectinload(User.liked_recipes))
                user_obj = db.execute(user_stmt).scalars().first()
                if user_obj:
                    is_liked = any(r.spoonacular_id == recipe_id or r.id == recipe_id for r in user_obj.liked_recipes)
                        
                return render_template('cooking_steps.html', recipe=recipe, is_liked=is_liked)
            else:
                flash('Recipe detail not found', 'error')
                return redirect(url_for('recipes.home'))
    except Exception as e:
        print(f"Error fetching recipe: {e}")
        flash('Error loading recipe details', 'error')
        return redirect(url_for('recipes.home'))

@recipes_bp.route('/recipe/<int:recipe_id>/like', methods=['POST'])
@login_required
def like_recipe_route(recipe_id):
    """Toggle like/unlike status for a recipe."""
    try:
        with SessionLocal() as db:
            data = recipe_service.toggle_like_recipe(recipe_id, session['user_id'], db)
            if data:
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
                return jsonify({"error": "Recipe not found"}), 404
    except Exception as e:
        print(f"Error toggling like: {e}")
        return jsonify({"error": "Failed to toggle like"}), 500

@recipes_bp.route('/substitutes')
@login_required
def substitutes():
    """Get ingredient substitute suggestions."""
    ingredient = request.args.get('ingredient')
    if not ingredient:
        return jsonify({"detail": "Missing ingredient parameter"}), 400
        
    try:
        with SessionLocal() as db:
            data = recipe_service.get_ingredient_substitutes(ingredient, db)
            return jsonify(data)
    except Exception as e:
        print(f"Substitutes error: {e}")
        return jsonify({"detail": "Failed to retrieve substitutes"}), 500


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

        try:
            with SessionLocal() as db:
                recipe_service.update_custom_recipe(recipe_id, title, ingredients, instructions, image, session['user_id'], db)
                flash("Recipe updated successfully!", "success")
                return redirect(url_for('recipes.home', tab='my_recipes'))
        except PermissionError:
            flash("You are not authorized to edit this recipe.", "error")
            return redirect(url_for('recipes.home'))
        except Exception as e:
            print(f"Error updating recipe: {e}")
            flash("Failed to update recipe.", "error")

        return redirect(url_for('recipes.edit_recipe', recipe_id=recipe_id))

    try:
        with SessionLocal() as db:
            recipe = recipe_service.get_recipe_details(recipe_id, db)
            if recipe:
                recipe['id'] = recipe_id

                stmt = select(Recipe).filter(Recipe.id == recipe_id)
                db_recipe = db.execute(stmt).scalars().first()
                if not db_recipe or db_recipe.user_id != session['user_id']:
                    flash("You are not authorized to edit this recipe.", "error")
                    return redirect(url_for('recipes.home'))

                return render_template('edit_recipe.html', recipe=recipe)
            else:
                flash('Recipe not found', 'error')
                return redirect(url_for('recipes.home'))
    except Exception as e:
        print(f"Error loading recipe: {e}")
        flash('Error loading recipe', 'error')
        return redirect(url_for('recipes.home'))


@recipes_bp.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    """Route to update user default dietary preferences."""
    default_vegetarian = request.form.get('default_vegetarian') == 'on'
    default_vegan = request.form.get('default_vegan') == 'on'
    default_gluten_free = request.form.get('default_gluten_free') == 'on'
    default_kosher = request.form.get('default_kosher') == 'on'
    default_dish_type = request.form.get('default_dish_type', '')
    
    default_prep_time_str = request.form.get('default_prep_time', '9999')
    default_prep_time = int(default_prep_time_str) if default_prep_time_str.isdigit() else 9999
    
    try:
        with SessionLocal() as db:
            user = db.execute(select(User).filter(User.id == session['user_id'])).scalars().first()
            if user:
                user.default_vegetarian = default_vegetarian
                user.default_vegan = default_vegan
                user.default_gluten_free = default_gluten_free
                user.default_kosher = default_kosher
                user.default_dish_type = default_dish_type
                user.default_prep_time = default_prep_time
                db.commit()
                flash("Default settings updated successfully!", "success")
            else:
                flash("User not found.", "error")
    except Exception as e:
        print(f"Error updating settings: {e}")
        flash("Failed to update settings.", "error")
        
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
        with SessionLocal() as db:
            user = db.execute(select(User).filter(User.id == session['user_id'])).scalars().first()
            if user:
                user_settings = {
                    "default_vegetarian": user.default_vegetarian,
                    "default_vegan": user.default_vegan,
                    "default_gluten_free": user.default_gluten_free,
                    "default_kosher": user.default_kosher,
                    "default_dish_type": user.default_dish_type,
                    "default_prep_time": user.default_prep_time
                }
    except Exception as e:
        print(f"Error loading settings: {e}")
        
    is_htmx = request.headers.get('HX-Request') == 'true'
    template = 'partials/settings_content.html' if is_htmx else 'settings.html'
    return render_template(
        template,
        username=session.get('username'),
        user_settings=user_settings
    )
