import os
from datetime import datetime, timedelta
from trust_rewards.database import client1
from dotenv import load_dotenv
import jwt as pyjwt
from passlib.hash import bcrypt

load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET', 'your_jwt_secret')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_MINUTES = 10080  # 7 days

class BaseAuthService:
    def __init__(self):
        # Use trust_rewards users collection for web login as requested
        self.client_database = client1['trust_rewards']
        self.user_collection = self.client_database['users']

class UserAuthService(BaseAuthService):
    def __init__(self):
        super().__init__()

    def authenticate_user(self, email, password):
        # Find by email in trust_rewards.users (no role restriction)
        user = self.user_collection.find_one({"email": email})
        if not user or not user.get('hash_password'):
            return None
        if not bcrypt.verify(password, user['hash_password']):
            return None
        return user

    def create_jwt_token(self, user):
        payload = {
            '_id': str(user['_id']),
            'user_id': user['user_id'],
            'email': user['email'],
            'role': user.get('role', 'Admin'),
            'exp': datetime.utcnow() + timedelta(minutes=JWT_EXP_DELTA_MINUTES)
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    def login(self, email, password):
        user = self.authenticate_user(email, password)
        if not user:
            return None
        token = self.create_jwt_token(user)
        # Return full user info (sanitized): remove hash_password, stringify _id
        sanitized = dict(user)
        if 'hash_password' in sanitized:
            del sanitized['hash_password']
        if '_id' in sanitized:
            sanitized['_id'] = str(sanitized['_id'])
        return {"user": sanitized, "token": token}