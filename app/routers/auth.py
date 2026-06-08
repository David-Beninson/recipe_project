from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy import select
from .. import schemas, models
from ..database import get_db
from app.utils import verify_password, create_access_token


# Login endpoint router
router = APIRouter(
    prefix="/login",
    tags=["Users"]
)


@router.post('/', response_model=schemas.Token)
async def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    """Login endpoint - authenticate user with username and password.
    
    Request body (form-data):
        - username: User's username
        - password: User's password
        
    Returns:
        JWT access token for authenticated user
        
    Raises:
        403 Forbidden if credentials are invalid
    """
    # Look up user by username
    stmt = select(models.User).filter(models.User.user_name == user_credentials.username)
    result = await db.execute(stmt)
    user = result.scalars().first()

    # User not found
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    # Password doesn't match
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    # Create JWT token with user ID
    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}