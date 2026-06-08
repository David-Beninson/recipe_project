from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession 
from .. import schemas, models
from ..database import get_db

router = APIRouter(
    prefix="/users",
    tags=['Users']
)

@router.get("/")
async def get_users():
    return {"message": "List of users"}

@router.post("/sing_in", status_code=status.HTTP_201_CREATED, response_model=schemas.SignInUser)
async def create_user(user: schemas.SignInUser, db: AsyncSession = Depends(get_db)):
    new_user = models.User(**user.model_dump())
    await db.commit()       
    await db.refresh(new_user) 

    return new_user