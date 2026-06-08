from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models
from ..database import get_db
from app.utils import hash_password, create_access_token


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
