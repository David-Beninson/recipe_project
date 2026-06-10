from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession  
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import httpx
from app.schemas import RecipeSearchParams, Recipe as RecipeSchema, CustomRecipeCreate 
from ..config import settings
from ..database import get_db
from app import models 
from app.utils import oauth2  


# Recipe search endpoints router
router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/find-by-ingredients", response_model=List[RecipeSchema])
async def find_recipes(
    params: RecipeSearchParams = Depends(),
    db: AsyncSession = Depends(get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Search for recipes by ingredients.
    
    Query parameters:
        - ingredients: Comma-separated list of ingredients (e.g., "chicken,rice")
        - number: How many recipes to return (default: 5, max: usually 100)
        
    Returns:
        List of recipes from Spoonacular API that contain the specified ingredients
        
    Details:
        - Requires authentication (JWT token)
        - Saves the search history to user's account
        - Caches recipes in database to avoid duplicates
    """
    # Create search record for user
    new_search = models.UserSearch(user_id=current_user.id, query_ingredients=params.ingredients, recipes=[])
    db.add(new_search)
    
    # Call Spoonacular API to search for recipes
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.spoonacular_url, params={
            "apiKey": settings.spoonacular_api_key,
            "ingredients": params.ingredients,
            "number": params.number,
            "ranking": params.ranking,
            "ignorePantry": params.ignorePantry
        })
        
        # Handle API errors
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Spoonacular API error")
        
        data = response.json()
        
        # Pydantic Models
        recipes = [RecipeSchema.model_validate(item) for item in data]
        
        # Process each recipe returned from API
        for recipe_obj in recipes:
            # Check if recipe already exists in database
            stmt = select(models.Recipe).filter(models.Recipe.spoonacular_id == recipe_obj.id)
            result = await db.execute(stmt)
            recipe = result.scalars().first()
            
            # If recipe is new, save it to database
            if not recipe:
                recipe = models.Recipe(
                    spoonacular_id=recipe_obj.id, 
                    title=recipe_obj.title, 
                    raw_data=recipe_obj.model_dump()
                )
                db.add(recipe)
                await db.flush()
            
            # Link this recipe to the user's search
            new_search.recipes.append(recipe)
            
        # Save search record and all new recipes
        await db.commit()
        return data

@router.post("/custom", response_model=dict)
async def create_custom_recipe(
    recipe_in: CustomRecipeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Create a new custom recipe."""
    title = recipe_in.title
    ingredients = recipe_in.ingredients
    instructions = recipe_in.instructions
    image = recipe_in.image
    
    # Format raw_data to match Spoonacular response style for templates compatibility
    extended_ingredients = []
    used_ingredients = []
    for ing in ingredients:
        ing_item = {
            "id": hash(ing.name) % 1000000,
            "name": ing.name,
            "original": f"{ing.name} - {ing.originalAmount}",
            "amount": float(ing.qty),
            "unit": ing.unitString
        }
        extended_ingredients.append(ing_item)
        used_ingredients.append(ing_item)
        
    raw_data = {
        "title": title,
        "image": image,
        "extendedIngredients": extended_ingredients,
        "instructions": instructions,
        "likes": 0,
        "usedIngredientCount": len(used_ingredients),
        "usedIngredients": used_ingredients,
        "missedIngredientCount": 0,
        "missedIngredients": [],
        "unusedIngredients": []
    }
    
    db_recipe = models.Recipe(
        title=title,
        raw_data=raw_data,
        user_id=current_user.id
    )
    db.add(db_recipe)
    await db.commit()
    await db.refresh(db_recipe)
    
    # Update raw_data with DB recipe ID for the UI
    raw_data["id"] = db_recipe.id
    db_recipe.raw_data = raw_data
    await db.commit()
    
    return {"id": db_recipe.id, "title": title}

@router.get("/{recipe_id}/information")
async def get_recipe_info(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Check if recipe exists in DB first (checking both DB ID and spoonacular_id)
    stmt = select(models.Recipe).filter((models.Recipe.id == recipe_id) | (models.Recipe.spoonacular_id == recipe_id))
    result = await db.execute(stmt)
    recipe = result.scalars().first()
    
    # If found in DB and contains instructions or is custom, return stored data
    if recipe and recipe.raw_data and ("instructions" in recipe.raw_data or recipe.user_id is not None):
        return recipe.raw_data

    # If not in DB, fetch from Spoonacular
    info_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    async with httpx.AsyncClient() as client:
        response = await client.get(info_url, params={
            "apiKey": settings.spoonacular_api_key,
            "includeNutrition": True 
        })
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Spoonacular API error")
        
        data = response.json()
        
        # Save or update recipe in DB
        if not recipe:
            recipe = models.Recipe(
                spoonacular_id=recipe_id, 
                title=data['title'], 
                raw_data=data
            )
            db.add(recipe)
        else:
            recipe.raw_data = data
            
        await db.commit()
        return data  
    
@router.get("/substitutes")
async def get_substitutes(
    ingredient: str,
    amount: float = None, 
    unit: str = None,    
    db: AsyncSession = Depends(get_db)
):
    parts = [ingredient.strip().lower()]
    if amount is not None:
        parts.append(str(amount))
    if unit:
        parts.append(unit.strip().lower())
    cache_key = "_".join(parts)
    
    stmt = select(models.IngredientSubstitute).filter(
        models.IngredientSubstitute.ingredient_name == cache_key
    )
    result = await db.execute(stmt)
    cached = result.scalars().first()
    
    if cached:
        return {"ingredient": ingredient, "substitutes": cached.substitutes}

    # Fetch with optional parameters
    params = {"ingredientName": ingredient, "apiKey": settings.spoonacular_api_key}
    if amount: params["amount"] = amount
    if unit: params["unit"] = unit

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.spoonacular.com/food/ingredients/substitutes", params=params)
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="API error")
            
        data = response.json()
        
        # Save to DB with the unique cache key
        new_sub = models.IngredientSubstitute(
            ingredient_name=cache_key, 
            substitutes=data.get('substitutes', [])
        )
        db.add(new_sub)
        await db.commit() 
        
        return data


@router.post("/{recipe_id}/like", response_model=dict)
async def like_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Toggle liking a recipe for the authenticated user."""
    # Find recipe by id or spoonacular_id
    stmt = select(models.Recipe).filter((models.Recipe.id == recipe_id) | (models.Recipe.spoonacular_id == recipe_id))
    result = await db.execute(stmt)
    recipe = result.scalars().first()
    
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    # Load user with liked_recipes relationship
    user_stmt = select(models.User).filter(models.User.id == current_user.id).options(selectinload(models.User.liked_recipes))
    user_result = await db.execute(user_stmt)
    user = user_result.scalars().first()
    
    # Check if already liked
    liked_recipe_to_remove = None
    for r in user.liked_recipes:
        if r.id == recipe.id:
            liked_recipe_to_remove = r
            break
            
    if liked_recipe_to_remove:
        user.liked_recipes.remove(liked_recipe_to_remove)
        status_str = "unliked"
        if recipe.raw_data:
            raw_data = dict(recipe.raw_data)
            if "likes" in raw_data:
                raw_data["likes"] = max(0, (raw_data["likes"] or 0) - 1)
            elif "aggregateLikes" in raw_data:
                raw_data["aggregateLikes"] = max(0, (raw_data["aggregateLikes"] or 0) - 1)
            recipe.raw_data = raw_data
    else:
        user.liked_recipes.append(recipe)
        status_str = "liked"
        if recipe.raw_data:
            raw_data = dict(recipe.raw_data)
            if "likes" in raw_data:
                raw_data["likes"] = (raw_data.get("likes") or 0) + 1
            elif "aggregateLikes" in raw_data:
                raw_data["aggregateLikes"] = (raw_data.get("aggregateLikes") or 0) + 1
            else:
                raw_data["likes"] = 1
            recipe.raw_data = raw_data
            
    await db.commit()
    
    likes_count = 0
    if recipe.raw_data:
        likes_count = recipe.raw_data.get("likes") or recipe.raw_data.get("aggregateLikes") or 0
        
    return {"status": status_str, "likes": likes_count}