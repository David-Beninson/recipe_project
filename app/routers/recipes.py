from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession  

from app import models, schemas
from ..config import settings
from ..database import get_db
from app.utils import oauth2  
from . import services

# Recipe search endpoints router
router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/find-by-ingredients", response_model=List[schemas.Recipe])
async def find_recipes(
    params: schemas.RecipeSearchParams = Depends(),
    db: AsyncSession = Depends(get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Search for recipes by ingredients with local fallback and caching."""
    # Create search record for user
    new_search = models.UserSearch(user_id=current_user.id, query_ingredients=params.ingredients, recipes=[])
    db.add(new_search)
    
    # Try fetching recipes from Spoonacular, with automatic fallback to DB search
    data = await services.fetch_recipes_with_fallback(params, db)
    if not data:
        raise HTTPException(status_code=502, detail="Spoonacular API error and no matching local recipes found")
    
    # Cache recipes to DB and link them to the search history
    await services.cache_and_link_recipes(data, new_search, db)
    return data


@router.post("/custom", response_model=dict)
async def create_custom_recipe(
    recipe_in: schemas.CustomRecipeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Create a new custom recipe."""
    db_recipe = await services.save_custom_recipe(recipe_in, current_user.id, db)
    return {"id": db_recipe.id, "title": db_recipe.title}


@router.get("/{recipe_id}/information")
async def get_recipe_info(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get full recipe details from DB cache or Spoonacular API."""
    data = await services.get_recipe_details(recipe_id, db)
    if not data:
        raise HTTPException(status_code=502, detail="Spoonacular API error")
    return data  
    

@router.get("/substitutes")
async def get_substitutes(
    ingredient: str,
    amount: float = None, 
    unit: str = None,    
    db: AsyncSession = Depends(get_db)
):
    """Fetch ingredient substitutes with caching."""
    return await services.get_ingredient_substitutes(ingredient, amount, unit, db)


@router.post("/{recipe_id}/like", response_model=dict)
async def like_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Toggle liking a recipe for the authenticated user."""
    return await services.toggle_like_recipe(recipe_id, current_user.id, db)