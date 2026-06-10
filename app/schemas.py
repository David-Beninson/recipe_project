from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

# User-related request/response schemas
class UserBase(BaseModel):
    """Base schema for user login/signup with username and password."""
    user_name: str
    password: str


class User(UserBase):
    """User input schema - inherits from UserBase."""
    pass


class UserOut(BaseModel):
    """User output schema - only returns safe info (ID and username)."""
    id: int
    user_name: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT token response schema returned after successful login/signup."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token payload schema - stores the user ID encoded in the JWT."""
    id: Optional[int] = None


# Recipe-related request/response schemas
class RecipeSearchParams(BaseModel):
    """Parameters for searching recipes by ingredients."""
    ingredients: str  # Comma-separated list of ingredients
    number: int = 5   # Number of recipes to return (default: 5)
    ranking: int = 1
    ignorePantry: bool = True


class SubstituteResponse(BaseModel):
    """Response schema for ingredient substitute suggestions."""
    ingredient: str
    substitutes: List[str]
    message: str

# --- Recipe Schemas (Using Pydantic) ---

class Ingredient(BaseModel):
    id: int
    amount: float
    unit: str
    unit_long: str = Field(alias="unitLong")
    unit_short: str = Field(alias="unitShort")
    aisle: str
    name: str
    original: str
    original_name: str = Field(alias="originalName")
    meta: List[str]
    image: str
    extended_name: Optional[str] = Field(None, alias="extendedName")

    model_config = ConfigDict(populate_by_name=True)

class Recipe(BaseModel):
    id: int
    title: str
    image: str
    image_type: str = Field(alias="imageType")
    used_ingredient_count: int = Field(alias="usedIngredientCount")
    missed_ingredient_count: int = Field(alias="missedIngredientCount")
    likes: int
    missed_ingredients: List[Ingredient] = Field(alias="missedIngredients")
    used_ingredients: List[Ingredient] = Field(alias="usedIngredients")
    unused_ingredients: List[Ingredient] = Field(alias="unusedIngredients")
    
    # Optional fields for filtering
    ready_in_minutes: Optional[int] = Field(None, alias="readyInMinutes")
    dish_types: Optional[List[str]] = Field(None, alias="dishTypes")
    vegetarian: Optional[bool] = None
    vegan: Optional[bool] = None
    gluten_free: Optional[bool] = Field(None, alias="glutenFree")

    model_config = ConfigDict(populate_by_name=True)


# --- Custom Recipe Schemas ---

class CustomIngredient(BaseModel):
    name: str
    originalAmount: str
    qty: float
    unitString: str
    usedQty: float


class CustomRecipeCreate(BaseModel):
    title: str
    ingredients: List[CustomIngredient]
    instructions: str
    image: Optional[str] = None