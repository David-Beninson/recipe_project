import httpx
import zlib
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import models
from app.config import settings

def _get_deterministic_id(name: str) -> int:
    """Generates a stable numeric ID for an ingredient based on its name."""
    return zlib.adler32(name.lower().encode()) % 1000000

def _map_ingredient(ing: dict) -> dict:
    """Helper to map individual ingredient keys and normalize default values."""
    return {
        "id": ing.get("id") or 0,
        "amount": float(ing.get("amount") or 0.0),
        "unit": ing.get("unit") or "",
        "unitLong": ing.get("unitLong") or ing.get("unit_long") or "",
        "unitShort": ing.get("unitShort") or ing.get("unit_short") or "",
        "aisle": ing.get("aisle") or "",
        "name": ing.get("name") or "",
        "original": ing.get("original") or "",
        "originalName": ing.get("originalName") or ing.get("original_name") or "",
        "meta": ing.get("meta") or [],
        "image": ing.get("image") or ""
    }

def _get_recipe_by_id(recipe_id: int, db) -> Optional[models.Recipe]:
    """Helper to query a recipe by either its database ID or Spoonacular ID."""
    try:
        stmt = select(models.Recipe).filter((models.Recipe.id == recipe_id) | (models.Recipe.spoonacular_id == recipe_id))
        return db.execute(stmt).scalars().first()
    except Exception as e:
        print(f"Error querying recipe by ID {recipe_id}: {e}")
        return None

def _enrich_recipes_bulk(data: list) -> list:
    """Fetches detailed instructions, ready time, and ingredients in bulk from Spoonacular."""
    if not data:
        return data
        
    recipe_ids = ",".join([str(item["id"]) for item in data])
    bulk_url = "https://api.spoonacular.com/recipes/informationBulk"
    
    try:
        response = httpx.get(bulk_url, params={
            "apiKey": settings.spoonacular_api_key,
            "ids": recipe_ids,
            "includeNutrition": False
        }, timeout=15.0)
        if response.status_code == 200:
            details_map = {recipe["id"]: recipe for recipe in response.json()}
            for item in data:
                if item["id"] in details_map:
                    detail = details_map[item["id"]]
                    fields = ["readyInMinutes", "dishTypes", "vegetarian", "vegan", "glutenFree", "instructions", "extendedIngredients"]
                    item.update({field: detail.get(field) for field in fields})
    except Exception as e:
        print(f"Error in bulk enrichment from Spoonacular: {e}")
    return data

def _fallback_local_search(ingredients: str, number: int, db) -> Optional[list]:
    """Fallback search in cached local DB recipes when API is offline."""
    try:
        stmt = select(models.Recipe)
        all_recipes = db.execute(stmt).scalars().all()
        
        search_ingredients = [i.strip().lower() for i in ingredients.split(",") if i.strip()]
        matched = []
        
        for recipe in all_recipes:
            if not recipe.raw_data:
                continue
            ext_ingredients = recipe.raw_data.get("extendedIngredients", []) or recipe.raw_data.get("usedIngredients", [])
            used_ingredients, missed_ingredients = [], []
            for ing in ext_ingredients:
                if isinstance(ing, dict) and "name" in ing:
                    mapped = _map_ingredient(ing)
                    if any(si in ing["name"].lower() for si in search_ingredients):
                        used_ingredients.append(mapped)
                    else:
                        missed_ingredients.append(mapped)
            if used_ingredients:
                matched.append({
                    **(recipe.raw_data or {}),
                    "id": recipe.spoonacular_id or recipe.id,
                    "title": recipe.title,
                    "usedIngredientCount": len(used_ingredients),
                    "missedIngredientCount": len(missed_ingredients),
                    "usedIngredients": used_ingredients,
                    "missedIngredients": missed_ingredients,
                    "unusedIngredients": []
                })
        return matched[:number] if matched else None
    except Exception as e:
        print(f"Error in local fallback search: {e}")
        return None

def fetch_recipes_with_fallback(ingredients: str, number: int, db) -> Optional[list]:
    """Searches Spoonacular API with automatic local database fallback."""
    try:
        response = httpx.get(settings.spoonacular_url, params={
            "apiKey": settings.spoonacular_api_key,
            "ingredients": ingredients,
            "number": number,
            "ranking": 1,
            "ignorePantry": True
        }, timeout=10.0)
        if response.status_code == 200:
            return _enrich_recipes_bulk(response.json())
    except Exception as e:
        print(f"Spoonacular API call failed: {e}")
        
    return _fallback_local_search(ingredients, number, db)

def cache_and_link_recipes(data: list, new_search: models.UserSearch, db):
    """Caches newly searched recipes locally and associates them with search history."""
    try:
        recipe_ids = [item["id"] for item in data]
        stmt = select(models.Recipe).filter(models.Recipe.spoonacular_id.in_(recipe_ids))
        existing_recipes = {r.spoonacular_id: r for r in db.execute(stmt).scalars().all()}
        
        for item in data:
            recipe_id = item["id"]
            recipe = existing_recipes.get(recipe_id)
            if not recipe:
                recipe = models.Recipe(
                    spoonacular_id=recipe_id, 
                    title=item.get("title", "Spoonacular Recipe"), 
                    raw_data=item
                )
                db.add(recipe)
                db.flush()
                existing_recipes[recipe_id] = recipe
            new_search.recipes.append(recipe)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error caching and linking recipes: {e}")

def save_custom_recipe(title: str, ingredients_list: list, instructions: str, image: str, user_id: int, db):
    """Saves a custom user-created recipe."""
    try:
        extended_ingredients = []
        for ing in ingredients_list:
            ing_name = ing.get("name", "")
            ing_id = ing.get("id")
            if not ing_id:
                ing_id = str(_get_deterministic_id(ing_name))
            elif str(ing_id).isdigit():
                ing_id = int(ing_id)

            extended_ingredients.append({
                "id": ing_id,
                "name": ing_name,
                "original": f"{ing_name} - {ing.get('originalAmount', '')}",
                "amount": float(ing.get("qty") or 0.0),
                "unit": ing.get("unitString") or ""
            })
        
        raw_data = {
            "title": title,
            "image": image,
            "extendedIngredients": extended_ingredients,
            "instructions": instructions,
            "likes": 0,
            "usedIngredientCount": len(extended_ingredients),
            "usedIngredients": extended_ingredients,
            "missedIngredientCount": 0,
            "missedIngredients": [],
            "unusedIngredients": []
        }
        
        db_recipe = models.Recipe(title=title, raw_data=raw_data, user_id=user_id)
        db.add(db_recipe)
        db.commit()
        db.refresh(db_recipe)
        
        raw_data["id"] = db_recipe.id
        db_recipe.raw_data = raw_data
        db.commit()
        return db_recipe
    except Exception as e:
        db.rollback()
        print(f"Error saving custom recipe: {e}")
        raise e

def update_custom_recipe(recipe_id: int, title: str, ingredients_list: list, instructions: str, image: str, user_id: int, db):
    """Updates an existing custom user-created recipe."""
    try:
        recipe = _get_recipe_by_id(recipe_id, db)
        if not recipe:
            return None
        if recipe.user_id != user_id:
            raise PermissionError("Not authorized to edit this recipe")

        extended_ingredients = []
        for ing in ingredients_list:
            ing_name = ing.get("name", "")
            ing_id = ing.get("id")
            if not ing_id:
                ing_id = str(_get_deterministic_id(ing_name))
            elif str(ing_id).isdigit():
                ing_id = int(ing_id)

            extended_ingredients.append({
                "id": ing_id,
                "name": ing_name,
                "original": f"{ing_name} - {ing.get('originalAmount', '')}",
                "amount": float(ing.get("qty") or 0.0),
                "unit": ing.get("unitString") or ""
            })

        raw_data = {
            "id": recipe.id,
            "title": title,
            "image": image,
            "extendedIngredients": extended_ingredients,
            "instructions": instructions,
            "likes": recipe.raw_data.get("likes", 0) if recipe.raw_data else 0,
            "usedIngredientCount": len(extended_ingredients),
            "usedIngredients": extended_ingredients,
            "missedIngredientCount": 0,
            "missedIngredients": [],
            "unusedIngredients": []
        }

        recipe.title = title
        recipe.raw_data = raw_data
        db.commit()
        db.refresh(recipe)
        return recipe
    except Exception as e:
        db.rollback()
        print(f"Error updating custom recipe {recipe_id}: {e}")
        raise e

def get_recipe_details(recipe_id: int, db) -> Optional[dict]:
    """Retrieves full details of a recipe (via DB cache or Spoonacular API)."""
    try:
        recipe = _get_recipe_by_id(recipe_id, db)
        if recipe and recipe.raw_data and ("instructions" in recipe.raw_data or recipe.user_id is not None):
            return recipe.raw_data

        info_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
        response = httpx.get(info_url, params={
            "apiKey": settings.spoonacular_api_key,
            "includeNutrition": True 
        }, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            if not recipe:
                recipe = models.Recipe(spoonacular_id=recipe_id, title=data['title'], raw_data=data)
                db.add(recipe)
            else:
                recipe.raw_data = data
            db.commit()
            return data
    except Exception as e:
        print(f"Error retrieving recipe details for {recipe_id}: {e}")
    return recipe.raw_data if recipe else None

def get_ingredient_substitutes(ingredient: str, db) -> dict:
    """Gets ingredient substitute recommendations."""
    parts = [ingredient.strip().lower()]
    cache_key = "_".join(parts)
    
    try:
        stmt = select(models.IngredientSubstitute).filter(models.IngredientSubstitute.ingredient_name == cache_key)
        cached = db.execute(stmt).scalars().first()
        if cached:
            return {"ingredient": ingredient, "substitutes": cached.substitutes}

        response = httpx.get("https://api.spoonacular.com/food/ingredients/substitutes", params={
            "ingredientName": ingredient, "apiKey": settings.spoonacular_api_key
        }, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            new_sub = models.IngredientSubstitute(ingredient_name=cache_key, substitutes=data.get('substitutes', []))
            db.add(new_sub)
            db.commit() 
            return data
    except Exception as e:
        print(f"Error loading substitutes for {ingredient}: {e}")
        
    return {"ingredient": ingredient, "substitutes": []}

def toggle_like_recipe(recipe_id: int, user_id: int, db) -> Optional[dict]:
    """Toggles the like/unlike status of a recipe for a user."""
    try:
        recipe = _get_recipe_by_id(recipe_id, db)
        if not recipe:
            return None
            
        user_stmt = select(models.User).filter(models.User.id == user_id).options(selectinload(models.User.liked_recipes))
        user = db.execute(user_stmt).scalars().first()
        if not user:
            return None
            
        liked_recipe = next((r for r in user.liked_recipes if r.id == recipe.id), None)
        if liked_recipe:
            user.liked_recipes.remove(liked_recipe)
            status_str = "unliked"
            modifier = -1
        else:
            user.liked_recipes.append(recipe)
            status_str = "liked"
            modifier = 1
            
        if recipe.raw_data:
            raw_data = dict(recipe.raw_data)
            like_key = "likes" if "likes" in raw_data or "aggregateLikes" not in raw_data else "aggregateLikes"
            raw_data[like_key] = max(0, (raw_data.get(like_key) or 0) + modifier)
            recipe.raw_data = raw_data
                
        db.commit()
        likes_count = recipe.raw_data.get("likes") or recipe.raw_data.get("aggregateLikes") or 0 if recipe.raw_data else 0
        return {"status": status_str, "likes": likes_count}
    except Exception as e:
        db.rollback()
        print(f"Error toggling like for recipe {recipe_id}: {e}")
        return None
