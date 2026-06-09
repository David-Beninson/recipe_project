from jose import JWTError, jwt
from app import schemas, database, models, config
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


# OAuth2 scheme - defines where to look for JWT token (in Authorization header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

# JWT configuration from environment settings
SECRET_KEY = config.settings.secret_key
ALGORITHM = config.settings.algorithm


def create_access_token(data: dict) -> str:
    """Create a JWT access token.
    
    Args:
        data: Dictionary with user info (e.g., {"user_id": 123})
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    # Sign the token with secret key using specified algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str, credentials_exception):
    """Verify and decode a JWT token.
    
    Args:
        token: The JWT token string to verify
        credentials_exception: The exception to raise if token is invalid
        
    Returns:
        TokenData object containing the user_id from the token
        
    Raises:
        credentials_exception if token is invalid or expired
    """
    try:
        # Decode and verify the JWT signature
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = str(payload.get("user_id"))
        
        if user_id is None:
            raise credentials_exception
        token_data = schemas.TokenData(id=user_id)
    except JWTError:
        raise credentials_exception

    return token_data


async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(database.get_db)
) -> models.User:
    """Get the currently authenticated user from JWT token.
    
    This dependency validates the JWT token and retrieves the user from database.
    Use in endpoint parameters: current_user: models.User = Depends(get_current_user)
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        The User object from database
        
    Raises:
        HTTPException 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials", 
        headers={"WWW-Authenticate": "Bearer"}
    )

    # Verify token and extract user_id
    token_data = verify_access_token(token, credentials_exception)

    # Fetch user from database
    stmt = select(models.User).filter(models.User.id == int(token_data.id))
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None:
        raise credentials_exception
    
    # Return the user object so endpoints can access current_user
    return user