from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession  
from sqlalchemy import select
import httpx
from app.schemas import RecipeSearchParams
from ..config import settings
from ..database import get_db
from app import models 
from app.utils import oauth2  

router = APIRouter(prefix="/recipes", tags=["recipes"])

@router.get("/find-by-ingredients")
async def find_recipes(
    params: RecipeSearchParams = Depends(),
    db: AsyncSession = Depends(get_db), 
    current_user: models.User = Depends(oauth2.get_current_user)
):
    new_search = models.UserSearch(user_id=current_user.id, query_ingredients=params.ingredients)
    db.add(new_search)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.spoonacular_url, params={
            "apiKey": settings.spoonacular_api_key,
            "ingredients": params.ingredients,
            "number": params.number
        })
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Spoonacular API error")
        
        data = response.json()
        
        for r_data in data:
            stmt = select(models.Recipe).filter(models.Recipe.spoonacular_id == r_data['id'])
            result = await db.execute(stmt)
            recipe = result.scalars().first()
            
            if not recipe:
                recipe = models.Recipe(spoonacular_id=r_data['id'], title=r_data['title'], raw_data=r_data)
                db.add(recipe)
            new_search.recipes.append(recipe)
            
        await db.commit()
        return data

@router.get("/substitutes")
async def get_substitutes(ingredient: str, db: AsyncSession = Depends(get_db)):
    stmt = select(models.IngredientSubstitute).filter(models.IngredientSubstitute.ingredient_name == ingredient)
    result = await db.execute(stmt)
    cached = result.scalars().first()
    
    if cached:
        return {"ingredient": ingredient, "substitutes": cached.substitutes}

    url = f"https://api.spoonacular.com/food/ingredients/substitutes?ingredientName={ingredient}&apiKey={settings.spoonacular_api_key}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()
        
        new_sub = models.IngredientSubstitute(ingredient_name=ingredient, substitutes=data['substitutes'])
        db.add(new_sub)
        await db.commit() 
        return data