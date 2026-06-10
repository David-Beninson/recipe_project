from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession  
from sqlalchemy import select
import httpx
from app.schemas import RecipeSearchParams, Recipe as RecipeSchema 
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
    new_search = models.UserSearch(user_id=current_user.id, query_ingredients=params.ingredients)
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

@router.get("/{recipe_id}/information")
async def get_recipe_info(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Check if recipe exists in DB first to save API calls
    stmt = select(models.Recipe).filter(models.Recipe.spoonacular_id == recipe_id)
    result = await db.execute(stmt)
    recipe = result.scalars().first()
    
    # If found in DB, return stored data
    if recipe and recipe.raw_data and "instructions" in recipe.raw_data:
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
    cache_key = f"{ingredient}_{amount}_{unit}"
    
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