import os
import secrets
import string
from datetime import datetime, timedelta
from sfa.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import jwt
import re

# Handle bcrypt import with compatibility
try:
    from passlib.hash import bcrypt
except ImportError:
    try:
        import bcrypt
        # Create a simple wrapper for passlib compatibility
        class BcryptWrapper:
            @staticmethod
            def hash(password):
                return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            @staticmethod
            def verify(password, hashed):
                return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        bcrypt = BcryptWrapper()
    except ImportError:
        raise ImportError("bcrypt is required for password hashing")

load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_MINUTES = 10080  # 7 days
REFRESH_TOKEN_EXP_DELTA_DAYS = 7

class BaseAuthService:
    def __init__(self):
        self.client_database = client1['field_squad']  # SFA database
        self.users_collection = self.client_database['users']  # Sales users (user_type == 5)

class AppUserAuthService(BaseAuthService):
    def __init__(self):
        super().__init__()

    def authenticate_user(self, employee_id, password):
        """Authenticate user with employee ID/email and password"""
        # Find user in users collection (sales users only)
        user = self.users_collection.find_one({
            "$or": [
                {"email": employee_id},
                {"employee_code": employee_id},
                {"mobile": employee_id}
            ]
        })

        print("debug user",user)
        
        if user and user.get('user_type') == 5:  # Sales user
            print(f"Found sales user: {user.get('name')} with user_type: {user.get('user_type')}")
            # For sales users, check if they have password field
            if user.get('password'):
                # Check if password is hashed with bcrypt
                if user['password'].startswith('$2b$'):
                    if not bcrypt.verify(password, user['password']):
                        print("Sales user password verification failed (bcrypt)")
                        return None
                else:
                    # Handle plain text passwords (for backward compatibility)
                    if user['password'] != password:
                        print("Sales user password verification failed (plain text)")
                        return None
                print("Sales user authentication successful")
                return user
            else:
                # If no password field, return None (sales users need password)
                print("Sales user has no password field")
                return None
        
        # Not a valid sales user
        return None

    def create_access_token(self, user_data, expires_delta=None):
        """Create JWT access token"""
        to_encode = user_data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWT_EXP_DELTA_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, user_data, expires_delta=None):
        """Create JWT refresh token"""
        to_encode = user_data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXP_DELTA_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    def verify_token(self, token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None

    def login(self, employee_id, password, device_info=None, remember_me=False):
        """SFA login with enhanced response for sales force automation"""
        user = self.authenticate_user(employee_id, password)
        if not user:
            return None
        
        # Only sales users are supported
        if user.get('user_type') != 5:
            return {
                "error": {
                    "code": "INVALID_USER_TYPE",
                    "details": "User is not authorized as sales user"
                }
            }
        
        # Create tokens with extended expiry for remember me
        user_data = {
            "sub": user.get('email') or user.get('mobile'),
            "user_id": str(user['_id']),
            "employee_id": user.get('employee_code', str(user['_id'])),
            "full_name": user.get('name', ''),
            "role": "Sales User",
            "user_type": user.get('user_type')
        }
        
        # Adjust token expiry based on remember me
        access_token_expires = timedelta(minutes=JWT_EXP_DELTA_MINUTES)
        refresh_token_expires = timedelta(days=30 if remember_me else REFRESH_TOKEN_EXP_DELTA_DAYS)
        
        access_token = self.create_access_token(user_data, access_token_expires)
        refresh_token = self.create_refresh_token(user_data, refresh_token_expires)
        
        # Update last login timestamp (sales users only)
        self.update_last_login(user.get('email') or user.get('mobile'))
        
        # Prepare user info according to SFA specification (sales users only)
        user_info = {
            "id": str(user['_id']),
            "employeeId": user.get('employee_code', str(user['_id'])),
            "name": user.get('name', ''),
            "email": user.get('email', ''),
            "role": "Sales User",
            "department": "Sales",
            "designation": user.get('designation', ''),
            "profileImage": "/images/profile_img.png",
            "phoneNumber": user.get('mobile', ''),
            "dateOfJoining": user.get('date_of_joining', ''),
            "isActive": True,
            "lastLoginAt": datetime.utcnow().isoformat(),
            "userType": user.get('user_type'),
            "location": user.get('location', {}),
            "weeklyOff": user.get('weekly_off', ''),
            "reportingManagerId": user.get('reporting_manager_id')
        }
        
        # Prepare tokens object
        tokens = {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresIn": JWT_EXP_DELTA_MINUTES * 60,
            "tokenType": "Bearer"
        }
        
        return {
            "user": user_info,
            "tokens": tokens,
        }


    def generate_reset_token(self, length=32):
        """Generate random reset token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def is_valid_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def is_valid_password(self, password):
        """Validate password strength"""
        if len(password) < 8:
            return False
        if not re.search(r'[a-zA-Z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        return True

    def blacklist_token(self, token):
        """Blacklist a token (for logout)"""
        try:
            # In a real implementation, you might want to store blacklisted tokens
            # For now, we'll just return success
            return True
        except Exception as e:
            return False

    

    def update_last_login(self, email):
        """Update user's last login timestamp"""
        try:
            # Update in users collection (sales users)
            result = self.users_collection.update_one(
                {"$or": [{"email": email}, {"mobile": email}]},
                {"$set": {
                    "last_login": datetime.utcnow().isoformat()
                }}
            )
            
            return True
        except Exception as e:
            return False

    def get_user_permissions(self, role):
        """Get user permissions based on role"""
        permissions_map = {
            "Employee": [
                "attendance.view",
                "attendance.mark",
                "leave.apply",
                "leave.view",
                "payslip.view",
                "profile.edit"
            ],
            "Manager": [
                "attendance.view",
                "attendance.mark",
                "attendance.manage",
                "leave.apply",
                "leave.view",
                "leave.approve",
                "payslip.view",
                "profile.edit",
                "team.view",
                "reports.view"
            ],
            "Admin": [
                "attendance.view",
                "attendance.mark",
                "attendance.manage",
                "leave.apply",
                "leave.view",
                "leave.approve",
                "leave.manage",
                "payslip.view",
                "payslip.manage",
                "profile.edit",
                "team.view",
                "team.manage",
                "reports.view",
                "reports.manage",
                "settings.manage",
                "users.manage"
            ]
        }
        return permissions_map.get(role, permissions_map["Employee"])
    
    def get_sales_user_permissions(self, permissions_dict):
        """Get sales user permissions based on permissions object"""
        if not permissions_dict:
            return []
        
        permissions = []
        if permissions_dict.get('view'):
            permissions.extend([
                "sales.view",
                "customers.view",
                "leads.view",
                "orders.view",
                "reports.view"
            ])
        
        if permissions_dict.get('edit'):
            permissions.extend([
                "sales.edit",
                "customers.edit",
                "leads.edit",
                "orders.edit",
                "profile.edit"
            ])
        
        if permissions_dict.get('add'):
            permissions.extend([
                "sales.add",
                "customers.add",
                "leads.add",
                "orders.add"
            ])
        
        if permissions_dict.get('delete'):
            permissions.extend([
                "sales.delete",
                "customers.delete",
                "leads.delete",
                "orders.delete"
            ])
        
        if permissions_dict.get('export'):
            permissions.extend([
                "sales.export",
                "customers.export",
                "leads.export",
                "orders.export",
                "reports.export"
            ])
        
        if permissions_dict.get('import'):
            permissions.extend([
                "customers.import",
                "leads.import"
            ])
        
        # Add default permissions for all sales users
        permissions.extend([
            "attendance.mark",
            "profile.view"
        ])
        
        return list(set(permissions))  # Remove duplicates 