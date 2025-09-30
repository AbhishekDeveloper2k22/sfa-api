import os
from datetime import datetime, timedelta
from sfa.database import client1
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
        # Use trust_rewards users collection for web login as requested
        self.client_database = client1['field_squad']
        self.user_collection = self.client_database['users']
        self.tenants_collection = self.client_database['tenants']
        self.module_master_collection = self.client_database['module_master']

    def fetch_modules_for_tenant(self, tenant_id):
        try:
            if not tenant_id:
                return []
            # First try matching tenants by _id, then by explicit tenantId field
            tenant = None
            try:
                tenant = self.tenants_collection.find_one({"tenantId": str(tenant_id)})
            except Exception:
                tenant = None
                return []

            module_ids = tenant.get("modules", []) or []
            object_ids = []
            for mid in module_ids:
                try:
                    object_ids.append(ObjectId(str(mid)))
                except Exception:
                    continue
            if not object_ids:
                return []
            modules = list(self.module_master_collection.find({"_id": {"$in": object_ids}}))
            for m in modules:
                if "_id" in m:
                    m["_id"] = str(m["_id"])
            return modules
        except Exception:
            return []

class UserAuthService(BaseAuthService):
    def __init__(self):
        super().__init__()

    def authenticate_user(self, email, password):
        # Find by email in trust_rewards.users (no role restriction)
        user = self.user_collection.find_one({"email": email})
        print("Debug: User found", user)
        if not user or not user.get('hash_password'):
            return None
        if not bcrypt.verify(password, user['hash_password']):
            return None
        return user

    def create_jwt_token(self, user):
        payload = {
            'user_id': str(user['_id']),
            'email': user['email'],
            'role': user.get('role', 'Admin'),
            'exp': datetime.utcnow() + timedelta(minutes=JWT_EXP_DELTA_MINUTES)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    def login(self, email, password):
        print("Debug: Login called with email", email)
        user = self.authenticate_user(email, password)
        if not user:
            return None
        token = self.create_jwt_token(user)
        # Return full user info (sanitized): remove hash_password, stringify _id
        sanitized = dict(user)
        for sensitive in ['hash_password', 'password', 'plain_password']:
            if sensitive in sanitized:
                del sanitized[sensitive]
        if '_id' in sanitized:
            sanitized['_id'] = str(sanitized['_id'])
        # Attach modules by tenantId only
        tenant_id = user.get('tenantId') or user.get('tenant_id')
        modules = self.fetch_modules_for_tenant(tenant_id)
        return {"user": sanitized, "modules": modules, "token": token}