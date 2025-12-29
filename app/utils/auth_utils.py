from typing import Any, Dict

import jwt
from fastapi import HTTPException, Request, status

from config import settings

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token, raising HTTP errors when invalid."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def extract_bearer_token(auth_header: str) -> str:
    """Extract the bearer token from an Authorization header."""
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    return token


def get_request_payload(request: Request) -> Dict[str, Any]:
    """Return decoded JWT payload from the incoming FastAPI request."""
    token = extract_bearer_token(request.headers.get("Authorization"))
    return decode_jwt_token(token)
