import httpx
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app import models, schemas
from ..config import settings


async def fetch_recipes_with_fallback(params: schemas.RecipeSearchParams, db: AsyncSession):
    """
    Tries to retrieve recipes by ingredients from the Spoonacular API.
    If the API call fails or is unavailable, falls back to searching local cached recipes.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.spoonacular_url, params={
                "apiKey": settings.spoonacular_api_key,
                "ingredients": params.ingredients,
                "number": params.number,
                "ranking": params.ranking,
                "ignorePantry": params.ignorePantry
            })
            if response.status_code == 200:
                return await _enrich_recipes_bulk(response.json(), client)
    except Exception:
        pass  # API error: fall back to local database search below
        
    return await _fallback_local_search(params, db)


async def _enrich_recipes_bulk(data: list, client: httpx.AsyncClient):
    """
    Fetches detailed instructions, ready time, and ingredient details 
    for all search result recipes in bulk to minimize API calls.
    """
    if not data:
        return data
        
    recipe_ids = ",".join([str(item["id"]) for item in data])
    bulk_url = "https://api.spoonacular.com/recipes/informationBulk"
    
    response = await client.get(bulk_url, params={
        "apiKey": settings.spoonacular_api_key,
        "ids": recipe_ids,
        "includeNutrition": False
    })
    
    if response.status_code == 200:
        details_map = {recipe["id"]: recipe for recipe in response.json()}
        for item in data:
            if item["id"] in details_map:
                detail = details_map[item["id"]]
                # Inject necessary detailed fields back into the search result items
                fields = ["readyInMinutes", "dishTypes", "vegetarian", "vegan", "glutenFree", "instructions", "extendedIngredients"]
                item.update({field: detail.get(field) for field in fields})
                
    return data


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


async def _get_recipe_by_id(recipe_id: int, db: AsyncSession) -> Optional[models.Recipe]:
    """Helper to query a recipe by either its database ID or Spoonacular ID (DRY)."""
    stmt = select(models.Recipe).filter((models.Recipe.id == recipe_id) | (models.Recipe.spoonacular_id == recipe_id))
    result = await db.execute(stmt)
    return result.scalars().first()


async def _fallback_local_search(params: schemas.RecipeSearchParams, db: AsyncSession):
    """
    Searches cached recipes locally by matching search ingredients against ingredients in the raw_data.
    Returns matched recipes up to the requested limit.
    """
    stmt = select(models.Recipe)
    result = await db.execute(stmt)
    all_recipes = result.scalars().all()
    
    search_ingredients = [i.strip().lower() for i in params.ingredients.split(",") if i.strip()]
    matched_recipes = []
    
    for recipe in all_recipes:
        if not recipe.raw_data:
            continue
        
        # Extract recipe ingredients from local DB cache
        ext_ingredients = recipe.raw_data.get("extendedIngredients", []) or recipe.raw_data.get("usedIngredients", [])
        recipe_ing_names = [ing["name"].lower() for ing in ext_ingredients if isinstance(ing, dict) and "name" in ing]
        
        # Check if the search ingredients list overlaps with this recipe's ingredients list
        matching_indices = [
            idx for idx, name in enumerate(recipe_ing_names)
            if any(search_ing in name for search_ing in search_ingredients)
        ]
        
        if matching_indices:
            # Categorize ingredients into used vs missed
            used_ings, missed_ings = [], []
            for idx, ing in enumerate(ext_ingredients):
                if not isinstance(ing, dict):
                    continue
                mapped = _map_ingredient(ing)
                if idx in matching_indices:
                    used_ings.append(mapped)
                else:
                    missed_ings.append(mapped)
            
            # Construct standard recipe dictionary representation
            matched_recipes.append({
                "id": recipe.spoonacular_id or recipe.id,
                "title": recipe.title,
                "image": recipe.raw_data.get("image") or "",
                "imageType": recipe.raw_data.get("imageType") or "jpg",
                "usedIngredientCount": len(used_ings),
                "missedIngredientCount": len(missed_ings),
                "likes": recipe.raw_data.get("likes") or recipe.raw_data.get("aggregateLikes") or 0,
                "usedIngredients": used_ings,
                "missedIngredients": missed_ings,
                "unusedIngredients": [],
                "readyInMinutes": recipe.raw_data.get("readyInMinutes"),
                "dishTypes": recipe.raw_data.get("dishTypes"),
                "vegetarian": recipe.raw_data.get("vegetarian"),
                "vegan": recipe.raw_data.get("vegan"),
                "glutenFree": recipe.raw_data.get("glutenFree")
            })
            
    return matched_recipes[:params.number] if matched_recipes else None


async def cache_and_link_recipes(data: list, new_search: models.UserSearch, db: AsyncSession):
    """
    Validates newly fetched recipes against Pydantic models, ensures they exist
    in the local database (caching), and associates them with the user's search history.
    """
    recipes = [schemas.Recipe.model_validate(item) for item in data]
    if not recipes:
        await db.commit()
        return

    recipe_ids = [recipe_obj.id for recipe_obj in recipes]
    
    # Batch query all existing recipes by spoonacular_id in a single database roundtrip
    stmt = select(models.Recipe).filter(models.Recipe.spoonacular_id.in_(recipe_ids))
    result = await db.execute(stmt)
    existing_recipes = {r.spoonacular_id: r for r in result.scalars().all()}
    
    for recipe_obj in recipes:
        recipe = existing_recipes.get(recipe_obj.id)
        
        # Cache to local DB if not present
        if not recipe:
            recipe = models.Recipe(
                spoonacular_id=recipe_obj.id, 
                title=recipe_obj.title, 
                raw_data=recipe_obj.model_dump(by_alias=True)
            )
            db.add(recipe)
            await db.flush()
            existing_recipes[recipe_obj.id] = recipe
        
        new_search.recipes.append(recipe)
        
    await db.commit()


async def save_custom_recipe(recipe_in: schemas.CustomRecipeCreate, user_id: int, db: AsyncSession):
    """
    Creates and saves a user-defined custom recipe to the database.
    Normalizes the structure to mimic Spoonacular's response style for compatibility.
    """
    # Create normalized ingredient entries
    extended_ingredients = [
        {
            "id": hash(ing.name) % 1000000,
            "name": ing.name,
            "original": f"{ing.name} - {ing.originalAmount}",
            "amount": float(ing.qty),
            "unit": ing.unitString
        } for ing in recipe_in.ingredients
    ]
    
    raw_data = {
        "title": recipe_in.title,
        "image": recipe_in.image,
        "extendedIngredients": extended_ingredients,
        "instructions": recipe_in.instructions,
        "likes": 0,
        "usedIngredientCount": len(extended_ingredients),
        "usedIngredients": extended_ingredients,
        "missedIngredientCount": 0,
        "missedIngredients": [],
        "unusedIngredients": []
    }
    
    db_recipe = models.Recipe(
        title=recipe_in.title,
        raw_data=raw_data,
        user_id=user_id
    )
    db.add(db_recipe)
    await db.commit()
    await db.refresh(db_recipe)
    
    # Store auto-generated database primary key inside raw_data as well
    raw_data["id"] = db_recipe.id
    db_recipe.raw_data = raw_data
    await db.commit()
    return db_recipe


async def get_recipe_details(recipe_id: int, db: AsyncSession):
    """
    Retrieves full details of a recipe. Searches the local DB first.
    If details are missing, fetches from Spoonacular API and caches it.
    """
    recipe = await _get_recipe_by_id(recipe_id, db)
    
    # Return local cache if available and has content
    if recipe and recipe.raw_data and ("instructions" in recipe.raw_data or recipe.user_id is not None):
        return recipe.raw_data

    # Fetch from API and save to DB
    info_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    async with httpx.AsyncClient() as client:
        response = await client.get(info_url, params={
            "apiKey": settings.spoonacular_api_key,
            "includeNutrition": True 
        })
        if response.status_code != 200:
            return None
        
        data = response.json()
        if not recipe:
            recipe = models.Recipe(spoonacular_id=recipe_id, title=data['title'], raw_data=data)
            db.add(recipe)
        else:
            recipe.raw_data = data
            
        await db.commit()
        return data


async def get_ingredient_substitutes(ingredient: str, amount: Optional[float], unit: Optional[str], db: AsyncSession):
    """
    Fetches ingredient substitutes using a cached lookup or querying Spoonacular if needed.
    """
    parts = [ingredient.strip().lower()]
    if amount is not None:
        parts.append(str(amount))
    if unit:
        parts.append(unit.strip().lower())
    cache_key = "_".join(parts)
    
    stmt = select(models.IngredientSubstitute).filter(models.IngredientSubstitute.ingredient_name == cache_key)
    result = await db.execute(stmt)
    cached = result.scalars().first()
    
    if cached:
        return {"ingredient": ingredient, "substitutes": cached.substitutes}

    # API call for new ingredient substitutes
    params = {"ingredientName": ingredient, "apiKey": settings.spoonacular_api_key}
    if amount: params["amount"] = amount
    if unit: params["unit"] = unit

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.spoonacular.com/food/ingredients/substitutes", params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="API error")
            
        data = response.json()
        new_sub = models.IngredientSubstitute(ingredient_name=cache_key, substitutes=data.get('substitutes', []))
        db.add(new_sub)
        await db.commit() 
        return data


async def toggle_like_recipe(recipe_id: int, user_id: int, db: AsyncSession):
    """
    Toggles like/unlike status for a recipe by a specific user.
    Updates the likes counter on the recipe's raw_data as well.
    """
    recipe = await _get_recipe_by_id(recipe_id, db)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    user_stmt = select(models.User).filter(models.User.id == user_id).options(selectinload(models.User.liked_recipes))
    user_result = await db.execute(user_stmt)
    user = user_result.scalars().first()
    
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
            
    await db.commit()
    likes_count = recipe.raw_data.get("likes") or recipe.raw_data.get("aggregateLikes") or 0 if recipe.raw_data else 0
    return {"status": status_str, "likes": likes_count}
