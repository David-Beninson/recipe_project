from pydantic import BaseModel

class UserBase(BaseModel):
    user_name: str
    password: str

class UserCreate(UserBase):
    pass

class UserOut(BaseModel):
    id: int
    user_name: str

    class Config:
        orm_mode = True
