from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession  
from sqlalchemy import select
import httpx
from app.schemas import RecipeSearchParams
from ..config import settings
from ..database import get_db
from app import models 
from app.utils import oauth2  


# Recipe search endpoints router
router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/find-by-ingredients")
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
            "number": params.number
        })
        
        # Handle API errors
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Spoonacular API error")
        
        data = response.json()
        
        # Process each recipe returned from API
        for r_data in data:
            # Check if recipe already exists in database (avoid duplicates)
            stmt = select(models.Recipe).filter(models.Recipe.spoonacular_id == r_data['id'])
            result = await db.execute(stmt)
            recipe = result.scalars().first()
            
            # If recipe is new, save it to database
            if not recipe:
                recipe = models.Recipe(
                    spoonacular_id=r_data['id'], 
                    title=r_data['title'], 
                    raw_data=r_data
                )
                db.add(recipe)
            
            # Link this recipe to the user's search
            new_search.recipes.append(recipe)
            
        # Save search record and all new recipes
        await db.commit()
        return data


@router.get("/substitutes")
async def get_substitutes(
    ingredient: str, 
    db: AsyncSession = Depends(get_db)
):
    """Get substitute ingredients for a given ingredient.
    
    Query parameters:
        - ingredient: The ingredient to find substitutes for (e.g., "milk")
        
    Returns:
        Dictionary with list of substitute ingredients
        
    Details:
        - First checks if we have cached substitutes in database
        - If not cached, fetches from Spoonacular API and caches for future use
        - No authentication required for this endpoint
    """
    # Check if we already have substitutes cached for this ingredient
    stmt = select(models.IngredientSubstitute).filter(
        models.IngredientSubstitute.ingredient_name == ingredient
    )
    result = await db.execute(stmt)
    cached = result.scalars().first()
    
    # Return cached data if available
    if cached:
        return {"ingredient": ingredient, "substitutes": cached.substitutes}

    # If not cached, fetch from Spoonacular API
    url = f"https://api.spoonacular.com/food/ingredients/substitutes?ingredientName={ingredient}&apiKey={settings.spoonacular_api_key}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()
        
        # Cache the result for future requests
        new_sub = models.IngredientSubstitute(
            ingredient_name=ingredient, 
            substitutes=data['substitutes']
        )
        db.add(new_sub)
        await db.commit() 
        return data