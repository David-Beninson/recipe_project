from .user import router as user_router
from .auth import router as auth_router
from .recipes import router as recipe_router

__all__ = ["user_router", "auth_router", "recipe_router"]
