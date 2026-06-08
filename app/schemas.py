from pydantic_settings import BaseSettings

#log in or log out schema
class User(BaseSettings):
    user_name: str
    password: str

#sign in new user schema
class SignInUser(BaseSettings):
    id: int
    user:User
