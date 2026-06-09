from pydantic import BaseModel, ConfigDict
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


class SubstituteResponse(BaseModel):
    """Response schema for ingredient substitute suggestions."""
    ingredient: str
    substitutes: List[str]
    message: str