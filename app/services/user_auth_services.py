import os
from datetime import datetime, timedelta
from app.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import jwt
from passlib.hash import bcrypt

load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET', 'your_jwt_secret')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_MINUTES = 10080  # 7 days

class BaseAuthService:
    def __init__(self):
        self.client_database = client1['hrms_master']
        self.user_collection = self.client_database['users']  # Changed to 'users' collection

class UserAuthService(BaseAuthService):
    def __init__(self):
        super().__init__()

    def authenticate_user(self, email, password):
        user = self.user_collection.find_one({"email": email, "role": "Admin"})
        if not user or not user.get('password'):
            return None
        if not bcrypt.verify(password, user['password']):
            return None
        return user

    def create_jwt_token(self, user):
        payload = {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("full_name", ""),
            "tenant_id": user.get("tenant_id"),
            "role": user.get("role", "Admin"),
            "status": user.get("status", "active"),
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXP_DELTA_MINUTES),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    def login(self, email, password):
        user = self.authenticate_user(email, password)
        if not user:
            return None
        token = self.create_jwt_token(user)
        user_info = self._serialize_user(user)
        return {"user": user_info, "token": token}

    def _serialize_user(self, user):
        """Return sanitized user profile for API responses."""
        return {
            "id": str(user["_id"]),
            "full_name": user.get("full_name", ""),
            "email": user.get("email"),
            "contact_number": user.get("contact_number"),
            "role": user.get("role", "Admin"),
            "tenant_id": user.get("tenant_id"),
            "status": user.get("status", "active"),
            "created_at": user.get("created_at"),
            "created_time": user.get("created_time"),
            "created_by": user.get("created_by"),
        }