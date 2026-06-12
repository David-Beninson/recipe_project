import bcrypt


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        The bcrypt hashed password string
    """
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    try:
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode('utf-8')
    except TypeError:
        # Fallback if bcrypt expects string arguments
        hashed_str = bcrypt.hashpw(password, salt.decode('utf-8') if isinstance(salt, bytes) else salt)
        return hashed_str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a bcrypt hash.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except AttributeError:
        # Fallback if checkpw is not present
        return bcrypt.hashpw(plain_password, hashed_password) == hashed_password
    except TypeError:
        # Fallback if bcrypt expects string arguments
        try:
            return bcrypt.checkpw(plain_password, hashed_password)
        except AttributeError:
            return bcrypt.hashpw(plain_password, hashed_password) == hashed_password