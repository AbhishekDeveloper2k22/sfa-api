import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class ValidationUtils:
    """Common validation utilities"""
    
    @staticmethod
    def is_valid_mobile(mobile: str) -> bool:
        """Validate mobile number format"""
        if not mobile:
            return False
            
        # Remove any non-digit characters
        mobile = ''.join(filter(str.isdigit, mobile))
        
        # Check if it's 10 digits
        if len(mobile) == 10:
            return True
        
        # Check if it's 10 digits with country code
        if len(mobile) == 12 and mobile.startswith('91'):
            return True
            
        return False
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
            
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def is_valid_password(password: str) -> bool:
        """Validate password strength"""
        if not password:
            return False
            
        # At least 8 characters, 1 uppercase, 1 lowercase, 1 digit
        if len(password) < 8:
            return False
            
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        return has_upper and has_lower and has_digit
    
    @staticmethod
    def is_valid_otp(otp: str) -> bool:
        """Validate OTP format (6 digits)"""
        if not otp:
            return False
            
        return otp.isdigit() and len(otp) == 6
    
    @staticmethod
    def is_valid_object_id(object_id: str) -> bool:
        """Validate MongoDB ObjectId format"""
        if not object_id:
            return False
            
        # Check if it's a valid 24-character hex string
        import re
        return bool(re.match(r'^[0-9a-fA-F]{24}$', object_id))

class DateUtils:
    """Common date utilities"""
    
    @staticmethod
    def get_current_datetime() -> datetime:
        """Get current datetime"""
        return datetime.now()
    
    @staticmethod
    def get_current_date() -> str:
        """Get current date in YYYY-MM-DD format"""
        return datetime.now().strftime("%Y-%m-%d")
    
    @staticmethod
    def get_current_time() -> str:
        """Get current time in HH:MM:SS format"""
        return datetime.now().strftime("%H:%M:%S")
    
    @staticmethod
    def add_minutes_to_datetime(dt: datetime, minutes: int) -> datetime:
        """Add minutes to datetime"""
        return dt + timedelta(minutes=minutes)
    
    @staticmethod
    def add_hours_to_datetime(dt: datetime, hours: int) -> datetime:
        """Add hours to datetime"""
        return dt + timedelta(hours=hours)
    
    @staticmethod
    def is_datetime_expired(dt: datetime) -> bool:
        """Check if datetime is expired"""
        return datetime.now() > dt
    
    @staticmethod
    def get_days_difference(from_date: str, to_date: str) -> int:
        """Get days difference between two dates"""
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            return (to_dt - from_dt).days
        except ValueError:
            return 0

class StringUtils:
    """Common string utilities"""
    
    @staticmethod
    def generate_random_string(length: int = 8) -> str:
        """Generate random alphanumeric string"""
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_random_number(length: int = 6) -> str:
        """Generate random number string"""
        import random
        return ''.join(random.choices('0123456789', k=length))
    
    @staticmethod
    def sanitize_string(text: str) -> str:
        """Sanitize string by removing special characters"""
        if not text:
            return ""
        return re.sub(r'[^a-zA-Z0-9\s]', '', text)
    
    @staticmethod
    def format_mobile_number(mobile: str) -> str:
        """Format mobile number to standard format"""
        if not mobile:
            return ""
            
        # Remove any non-digit characters
        mobile = ''.join(filter(str.isdigit, mobile))
        
        # If 12 digits and starts with 91, remove country code
        if len(mobile) == 12 and mobile.startswith('91'):
            mobile = mobile[2:]
        
        # Return 10 digit mobile
        return mobile if len(mobile) == 10 else ""

class ResponseUtils:
    """Common response utilities"""
    
    @staticmethod
    def create_success_response(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create standardized success response"""
        response = {
            "success": True,
            "message": message
        }
        if data:
            response["data"] = data
        return response
    
    @staticmethod
    def create_error_response(message: str, error_code: str = "ERROR", details: Optional[str] = None) -> Dict[str, Any]:
        """Create standardized error response"""
        response = {
            "success": False,
            "message": message,
            "error": {
                "code": error_code
            }
        }
        if details:
            response["error"]["details"] = details
        return response

class SecurityUtils:
    """Common security utilities"""
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate OTP"""
        import random
        return ''.join(random.choices('0123456789', k=length))
    
    @staticmethod
    def is_strong_password(password: str) -> bool:
        """Check if password is strong"""
        if not password or len(password) < 8:
            return False
            
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return has_upper and has_lower and has_digit and has_special
    
    @staticmethod
    def mask_mobile_number(mobile: str) -> str:
        """Mask mobile number for display"""
        if not mobile or len(mobile) < 4:
            return mobile
            
        return mobile[:2] + "*" * (len(mobile) - 4) + mobile[-2:]
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email for display"""
        if not email or "@" not in email:
            return email
            
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            return email
            
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"


class AuditUtils:
    """Utilities for created/updated audit fields"""
    @staticmethod
    def build_create_meta(user_id: int) -> Dict[str, Any]:
        now = datetime.now()
        return {
            "created_at": now.strftime("%Y-%m-%d"),
            "created_time": now.strftime("%H:%M:%S"),
            "created_by": user_id,
        }

    @staticmethod
    def build_update_meta(user_id: int) -> Dict[str, Any]:
        now = datetime.now()
        return {
            "updated_at": now.strftime("%Y-%m-%d"),
            "updated_time": now.strftime("%H:%M:%S"),
            "updated_by": user_id,
        }
