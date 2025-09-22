import bcrypt
from typing import str

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    if not password:
        raise ValueError("Password cannot be empty")
    
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    if not password or not hashed_password:
        return False
    
    try:
        # Check if password matches hash
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def generate_salt() -> str:
    """Generate a new salt for password hashing"""
    salt = bcrypt.gensalt()
    return salt.decode('utf-8')
