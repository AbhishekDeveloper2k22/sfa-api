import os
from dotenv import load_dotenv
from fastapi import Request, HTTPException
import jwt

load_dotenv()

SECRET_KEY = os.getenv('JWT_SECRET')
ALGORITHM = 'HS256'


def verify_token(token: str):
    """Verify JWT token and return payload or None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(request: Request):
    """Extract and verify Bearer token from Authorization header; raise 401 on failure."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload


