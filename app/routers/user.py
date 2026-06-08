from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models
from ..database import get_db
from ..utils.hash_password import hash_password

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/")
async def get_users():
    return {"message": "List of users"}

@router.post("/sign_up", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    
    hashed_password = hash_password(user.password) 
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