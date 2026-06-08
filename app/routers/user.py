from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy import select
from .. import schemas, models
from ..database import get_db
from ..utils import oauth2, password_hashing

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/sign_up", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def create_user(user: schemas.User, db: AsyncSession = Depends(get_db)):
    
    hashed_password = password_hashing.hash_password(user.password) 
    user.password = hashed_password
    
    new_user = models.User(
        user_name=user.user_name,
        password=hashed_password
    )   
    print(new_user)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user



@router.post('/login', response_model=schemas.Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    stmt = select(models.User).filter(models.User.user_name == user_credentials.username)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    if not password_hashing.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    access_token = oauth2.create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}