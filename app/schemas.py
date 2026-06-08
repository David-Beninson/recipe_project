from pydantic import BaseModel, ConfigDict
from typing import Optional

class UserBase(BaseModel):
    user_name: str
    password: str

class User(UserBase):
    pass

class UserOut(BaseModel):
    id: int
    user_name: str
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int] = None