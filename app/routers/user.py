from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models
from ..database import get_db
from app.utils import hash_password, create_access_token

router = APIRouter(
    prefix="/sign_up",
    tags=["Users"]
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Token)
async def create_user(user: schemas.User, db: AsyncSession = Depends(get_db)):
    
    hashed_password = hash_password(user.password) 
    
    new_user = models.User(
        user_name=user.user_name,
        password=hashed_password
    )   
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(data={"user_id": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}
