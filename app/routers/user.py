from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models
from ..database import get_db
from app.utils import hash_password, create_access_token, oauth2


# Sign up endpoint router
router = APIRouter(
    prefix="/sign_up",
    tags=["Users"]
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Token)
async def create_user(
    user: schemas.User, 
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account.
    
    Request body (JSON):
        - user_name: Unique username
        - password: User's password
        
    Returns:
        JWT access token for newly created user
        
    Raises:
        400 Bad Request if username already exists
    """
    # Hash the password before storing in database
    hashed_password = hash_password(user.password) 
    
    # Create new user object with hashed password
    new_user = models.User(
        user_name=user.user_name,
        password=hashed_password
    )   
    
    # Save to database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate JWT token for automatic login after signup
    access_token = create_access_token(data={"user_id": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}


# User settings router
settings_router = APIRouter(
    prefix="/users",
    tags=["UserSettings"]
)


@settings_router.get("/settings", response_model=schemas.UserSettings)
async def get_settings(
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Retrieve default recipe filters/settings for the authenticated user."""
    return current_user


@settings_router.put("/settings", response_model=schemas.UserSettings)
async def update_settings(
    settings_in: schemas.UserSettings,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Update default recipe filters/settings for the authenticated user."""
    current_user.default_vegetarian = settings_in.default_vegetarian
    current_user.default_vegan = settings_in.default_vegan
    current_user.default_gluten_free = settings_in.default_gluten_free
    current_user.default_kosher = settings_in.default_kosher
    current_user.default_dish_type = settings_in.default_dish_type
    current_user.default_prep_time = settings_in.default_prep_time
    
    await db.commit()
    await db.refresh(current_user)
    return current_user
