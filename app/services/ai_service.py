import httpx
import json
import re
from typing import Optional
from sqlalchemy import select
from app.database import models
from app.config import settings

def _get_recipe_by_id(recipe_id: int, db) -> Optional[models.Recipe]:
    """Helper to query a recipe by either its database ID or Spoonacular ID."""
    try:
        stmt = select(models.Recipe).filter((models.Recipe.id == recipe_id) | (models.Recipe.spoonacular_id == recipe_id))
        return db.execute(stmt).scalars().first()
    except Exception as e:
        print(f"Error querying recipe by ID {recipe_id}: {e}")
        return None

def _call_ai_api(system_prompt: str, user_prompt: str) -> dict:
    """Helper to call the configured OpenAI-compatible completions API."""
    payload = {
        "model": "qwen2.5:3b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    try:
        response = httpx.post(
            settings.ai_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=35.0
        )
        if response.status_code != 200:
            raise RuntimeError(f"AI API error: {response.text}")
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Strip markdown json code block wraps if present
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                content = "\n".join(lines[1:-1])
            else:
                content = "\n".join(lines[1:])
        
        return json.loads(content)
    except Exception as e:
        print(f"Error communicating with AI completions API: {e}")
        raise e

def _map_ai_recipe_to_raw_data(ai_data: dict) -> dict:
    """Converts JSON output from the AI into Spoonacular-compatible structure for the database."""
    ingredients_list = ai_data.get("ingredients", [])
    extended_ingredients = []
    
    for ing in ingredients_list:
        # If the AI returns parsed dicts instead of string lists
        if isinstance(ing, dict):
            name = ing.get("name", "Unknown Ingredient")
            amount = float(ing.get("amount") or 1.0)
            unit = ing.get("unit", "")
            original = ing.get("original", f"{amount} {unit} {name}".strip())
        else:
            name = str(ing)
            amount = 1.0
            unit = ""
            original = str(ing)

        extended_ingredients.append({
            "id": hash(name) % 1000000,
            "name": name,
            "nameClean": name,
            "original": original,
            "amount": amount,
            "unit": unit,
            "aisle": "Produce"  # Default fallback aisle
        })
        
    instructions_raw = ai_data.get("instructions", [])
    if isinstance(instructions_raw, list):
        instructions_html = "<ol>" + "".join([f"<li>{step}</li>" for step in instructions_raw]) + "</ol>"
    else:
        instructions_html = str(instructions_raw)
        
    prep_time_str = str(ai_data.get("prep_time", "30"))
    digits = re.findall(r'\d+', prep_time_str)
    ready_in_minutes = int(digits[0]) if digits else 30

    return {
        "title": ai_data.get("title", "AI Recipe"),
        "image": "", 
        "extendedIngredients": extended_ingredients,
        "instructions": instructions_html,
        "readyInMinutes": ready_in_minutes,
        "servings": ai_data.get("servings", 4),
        "likes": 0,
        "usedIngredientCount": len(extended_ingredients),
        "usedIngredients": extended_ingredients,
        "missedIngredientCount": 0,
        "missedIngredients": [],
        "unusedIngredients": []
    }

def generate_recipe_with_ai(ingredients_str: str, user_id: int, db) -> models.Recipe:
    """Generates a custom recipe from ingredients using AI and saves it to the database."""
    try:
        system_prompt = (
            "You are a helpful culinary assistant. Perform TASK 1: Generate a recipe from scratch.\n"
            "Input: A list of ingredients.\n"
            "Output: MUST be a valid JSON object matching the SCHEMA below. NO markdown, NO conversational text.\n"
            "SCHEMA FOR TASK 1:\n"
            "{\n"
            '  "title": "string",\n'
            '  "ingredients": ["string"],\n'
            '  "instructions": ["string"],\n'
            '  "prep_time": "string",\n'
            '  "servings": 4\n'
            "}"
        )
        user_prompt = f"Ingredients available: {ingredients_str}"
        
        ai_data = _call_ai_api(system_prompt, user_prompt)
        raw_data = _map_ai_recipe_to_raw_data(ai_data)
        
        db_recipe = models.Recipe(
            title=raw_data["title"],
            raw_data=raw_data,
            user_id=user_id
        )
        db.add(db_recipe)
        db.commit()
        db.refresh(db_recipe)
        
        raw_data["id"] = db_recipe.id
        db_recipe.raw_data = raw_data
        db.commit()
        
        return db_recipe
    except Exception as e:
        db.rollback()
        print(f"Error generating recipe with AI: {e}")
        raise e

def substitute_ingredient_with_ai(recipe_id: int, ingredient_to_replace: str, user_id: int, db) -> models.Recipe:
    """Adapts an existing recipe by substituting a specific ingredient using AI."""
    try:
        orig_recipe = _get_recipe_by_id(recipe_id, db)
        if not orig_recipe:
            raise ValueError(f"Original recipe {recipe_id} not found")
            
        orig_title = orig_recipe.title
        orig_ingredients = []
        if orig_recipe.raw_data and "extendedIngredients" in orig_recipe.raw_data:
            orig_ingredients = [ing.get("original", ing.get("name", "")) for ing in orig_recipe.raw_data["extendedIngredients"]]
        
        orig_instructions = orig_recipe.raw_data.get("instructions", "") if orig_recipe.raw_data else ""

        system_prompt = (
            "You are a helpful culinary assistant. Perform TASK 2: Adapt an existing recipe.\n"
            "Input: An existing recipe and ingredients to substitute.\n"
            "Output: MUST be a valid JSON object matching the SCHEMA below. NO markdown, NO conversational text.\n"
            "SCHEMA FOR TASK 2:\n"
            "{\n"
            '  "title": "string",\n'
            '  "ingredients": ["string"],\n'
            '  "instructions": ["string"],\n'
            '  "prep_time": "string",\n'
            '  "servings": 4\n'
            "}"
        )
        user_prompt = f"Original Recipe Title: {orig_title}\nOriginal Ingredients: {json.dumps(orig_ingredients)}\nOriginal Instructions: {orig_instructions}\nIngredient to Replace: {ingredient_to_replace}"

        ai_data = _call_ai_api(system_prompt, user_prompt)
        raw_data = _map_ai_recipe_to_raw_data(ai_data)
        
        db_recipe = models.Recipe(
            title=raw_data["title"],
            raw_data=raw_data,
            user_id=user_id
        )
        db.add(db_recipe)
        db.commit()
        db.refresh(db_recipe)
        
        raw_data["id"] = db_recipe.id
        db_recipe.raw_data = raw_data
        db.commit()
        
        return db_recipe
    except Exception as e:
        db.rollback()
        print(f"Error adapting recipe with AI: {e}")
        raise e

def get_quick_substitute_from_ai(recipe_id: int, ingredient_to_replace: str, db) -> str:
    """Gets a quick 1-2 sentence substitute recommendation for an ingredient in a recipe."""
    try:
        orig_recipe = _get_recipe_by_id(recipe_id, db)
        recipe_title = orig_recipe.title if orig_recipe else "Recipe"
        
        system_prompt = (
            "You are a helpful culinary assistant. Perform TASK 3: Quick ingredient substitute recommendation.\n"
            "Input: A recipe title and an ingredient to replace.\n"
            "Output: A quick, professional 1-2 sentence suggestion directly as plain text. Do NOT output JSON or markdown."
        )
        user_prompt = f"Recipe: {recipe_title}\nIngredient to replace: {ingredient_to_replace}"
        
        payload = {
            "model": "qwen2.5:3b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.5
        }
        
        response = httpx.post(
            settings.ai_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=25.0
        )
        if response.status_code != 200:
            raise RuntimeError(f"AI API error: {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error fetching quick substitute from AI: {e}")
        return f"Failed to retrieve quick suggestion for {ingredient_to_replace}."
