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
        self.client_database = client1['hrms_master']
        self.user_collection = self.client_database['employee_master']
        self.password_reset_collection = self.client_database['password_reset_tokens']

class AppUserAuthService(BaseAuthService):
    def __init__(self):
        super().__init__()

    def authenticate_user(self, employee_id, password):
        """Authenticate user with employee ID/email and password"""
        # Try to find user by email or employee ID
        user = self.user_collection.find_one({
            "$or": [
                {"email": employee_id},
                {"official_email_username": employee_id}
            ]
        })
        
        if not user or not user.get('password'):
            return None
        
        # Check if password is hashed with bcrypt
        if user['password'].startswith('$2b$'):
            if not bcrypt.verify(password, user['password']):
                return None
        else:
            # Handle plain text passwords (for backward compatibility)
            if user['password'] != password:
                return None
        
        return user

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
        """HRMS Pro login with enhanced response"""
        user = self.authenticate_user(employee_id, password)
        if not user:
            return None
        
        # Check if account is active
        if user.get('employment_status') != 'Active':
            return {
                "success": False,
                "error": {
                    "code": "ACCOUNT_INACTIVE",
                    "details": "Account has been deactivated by administrator"
                }
            }
        
        # Create tokens with extended expiry for remember me
        user_data = {
            "sub": user.get('email') or user.get('official_email_username'),
            "user_id": str(user['_id']),
            "employee_id": str(user['_id']),  # Using _id as employee_id
            "full_name": user.get('full_name', ''),
            "role": user.get('role_access_level', 'Employee')
        }
        
        # Adjust token expiry based on remember me
        access_token_expires = timedelta(minutes=JWT_EXP_DELTA_MINUTES)
        refresh_token_expires = timedelta(days=30 if remember_me else REFRESH_TOKEN_EXP_DELTA_DAYS)
        
        access_token = self.create_access_token(user_data, access_token_expires)
        refresh_token = self.create_refresh_token(user_data, refresh_token_expires)
        
        # Update last login timestamp
        self.update_last_login(user.get('email') or user.get('official_email_username'))
        
        # Prepare user info according to HRMS Pro specification
        user_info = {
            "id": str(user['_id']),
            "employeeId": str(user['_id']),  # Using _id as employeeId
            "name": user.get('full_name', ''),
            "email": user.get('email') or user.get('official_email_username', ''),
            "role": user.get('role_access_level', 'Employee'),
            "department": user.get('department', ''),
            "designation": user.get('designation', ''),
            "profileImage": user.get('profile_image', '/images/profile_img.png'),
            "phoneNumber": user.get('mobile_no', ''),
            "dateOfJoining": user.get('joining_date', ''),
            "isActive": user.get('employment_status') == 'Active',
            "permissions": self.get_user_permissions(user.get('role_access_level', 'Employee')),
            "lastLoginAt": datetime.utcnow().isoformat()
        }
        
        # Prepare tokens object
        tokens = {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresIn": JWT_EXP_DELTA_MINUTES * 60,
            "tokenType": "Bearer"
        }
        
        # Prepare company info (default values)
        company = {
            "id": "comp_001",
            "name": "HRMS Pro Company",
            "logo": "/images/company_logo.png",
            "timezone": "Asia/Kolkata",
            "workingDays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "workingHours": {
                "start": "09:00",
                "end": "18:00"
            }
        }
        
        return {
            "success": True,
            "user": user_info,
            "tokens": tokens,
            "company": company
        }

    def register(self, email, password, full_name):
        """User registration"""
        try:
            # Check if user already exists
            existing_user = self.user_collection.find_one({"email": email})
            if existing_user:
                return {
                    "success": False,
                    "message": "User with this email already exists"
                }
            
            # Validate email format
            if not self.is_valid_email(email):
                return {
                    "success": False,
                    "message": "Invalid email format"
                }
            
            # Validate password strength
            if not self.is_valid_password(password):
                return {
                    "success": False,
                    "message": "Password must be at least 8 characters long and contain letters and numbers"
                }
            
            # Hash password
            hashed_password = bcrypt.hash(password)
            
            # Create user document
            user_data = {
                "email": email,
                "password": hashed_password,
                "full_name": full_name,
                "role_access_level": "Employee",
                "employment_status": "Active",
                "date_created": datetime.utcnow().isoformat(),
                "created_by": "system"
            }
            
            # Insert user
            result = self.user_collection.insert_one(user_data)
            
            if result.inserted_id:
                return {
                    "success": True,
                    "message": "User registered successfully",
                    "user_id": str(result.inserted_id)
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to create user"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Registration failed: {str(e)}"
            }

    def get_user_profile(self, email):
        """Get user profile by email organized in categories"""
        try:
            user = self.user_collection.find_one({"email": email})
            if not user:
                return None
            
            # Convert ObjectId to string
            user['_id'] = str(user['_id'])
            
            # Organize user data into categories
            profile_data = {
                "id": str(user['_id']),
                "basicInfo": {
                    "fullName": user.get("full_name", ""),
                    "email": user.get("email", ""),
                    "personalEmail": user.get("personal_email", ""),
                    "mobileNo": user.get("mobile_no", ""),
                    "whatsappNumber": user.get("whatsapp_number", ""),
                    "gender": user.get("gender", ""),
                    "dateOfBirth": user.get("date_of_birth", ""),
                    "bloodGroup": user.get("blood_group", ""),
                    "maritalStatus": user.get("marital_status", ""),
                    "profileImage": user.get("profile_image", "/images/profile_img.png")
                },
                "employmentInfo": {
                    "employeeId": str(user['_id']),
                    "department": user.get("department", ""),
                    "designation": user.get("designation", ""),
                    "employeeType": user.get("employee_type", ""),
                    "employmentStatus": user.get("employment_status", ""),
                    "joiningDate": user.get("joining_date", ""),
                    "workLocation": user.get("work_location", ""),
                    "reportingManager": user.get("reporting_manager", ""),
                    "officialEmailUsername": user.get("official_email_username", ""),
                    "roleAccessLevel": user.get("role_access_level", ""),
                    "lastLogin": user.get("last_login", ""),
                    "dateCreated": user.get("date_created", ""),
                    "dateUpdated": user.get("date_updated", ""),
                    "createdBy": user.get("created_by", ""),
                    "updatedBy": user.get("updated_by", "")
                },
                "salaryInfo": {
                    "annualCtc": user.get("annual_ctc", 0),
                    "annualGrossSalary": user.get("annual_gross_salary", 0),
                    "monthlyGrossSalary": user.get("monthly_gross_salary", 0),
                    "netSalaryMonthly": user.get("net_salary_monthly", 0),
                    "netSalaryYearly": user.get("net_salary_yearly", 0),
                    "basicSalaryPercent": user.get("basic_salary_percent", ""),
                    "hraPercent": user.get("hra_percent", 0),
                    "specialAllowance": user.get("special_allowance", 0),
                    "conveyanceAllowance": user.get("conveyance_allowance", 0),
                    "medicalAllowance": user.get("medical_allowance", 0),
                    "performanceBonus": user.get("performance_bonus", 0),
                    "joiningBonus": user.get("joining_bonus", 0),
                    "otherBenefits": user.get("other_benefits", 0)
                },
                "deductions": {
                    "pfApplicable": user.get("pf_applicable", ""),
                    "employeePfDeductionMonthly": user.get("employee_pf_deduction_monthly", 0),
                    "employeePfDeductionYearly": user.get("employee_pf_deduction_yearly", 0),
                    "employerEpfMonthly": user.get("employer_epf_monthly", 0),
                    "employerEpfYearly": user.get("employer_epf_yearly", 0),
                    "employerEpsMonthly": user.get("employer_eps_monthly", 0),
                    "employerEpsYearly": user.get("employer_eps_yearly", 0),
                    "employerPfDeductionMonthly": user.get("employer_pf_deduction_monthly", 0),
                    "employerPfDeductionYearly": user.get("employer_pf_deduction_yearly", 0),
                    "employeeEsiDeductionMonthly": user.get("employee_esi_deduction_monthly", 0),
                    "employeeEsiDeductionYearly": user.get("employee_esi_deduction_yearly", 0),
                    "professionalTaxMonthly": user.get("professional_tax_monthly", 0),
                    "professionalTaxYearly": user.get("professional_tax_yearly", 0),
                    "tdsMonthly": user.get("tds_monthly", 0),
                    "tdsYearly": user.get("tds_yearly", 0)
                },
                "bankDetails": {
                    "accountNo": user.get("bank_account_no", ""),
                    "bankName": user.get("bank_name", ""),
                    "ifscCode": user.get("ifsc_code", ""),
                    "accountType": user.get("account_type", "")
                },
                "addressInfo": {
                    "presentAddress": {
                        "line1": user.get("present_address_line1", ""),
                        "line2": user.get("present_address_line2", ""),
                        "city": user.get("present_city", ""),
                        "state": user.get("present_state", ""),
                        "pinCode": user.get("present_pin_code", ""),
                        "country": user.get("present_country", "")
                    },
                    "permanentAddress": {
                        "line1": user.get("permanent_address_line1", ""),
                        "line2": user.get("permanent_address_line2", ""),
                        "city": user.get("permanent_city", ""),
                        "state": user.get("permanent_state", ""),
                        "pinCode": user.get("permanent_pin_code", ""),
                        "country": user.get("permanent_country", "")
                    }
                },
                "emergencyContact": {
                    "name": user.get("contact_name", ""),
                    "relationship": user.get("relationship", ""),
                    "mobile": user.get("emergency_mobile", ""),
                    "address": user.get("emergency_address", "")
                },
                "documents": {
                    "aadhaarCard": user.get("aadhaar_card", ""),
                    "panCard": user.get("pan_card", ""),
                    "bankPassbook": user.get("bank_passbook", ""),
                    "offerLetter": user.get("offer_letter", ""),
                    "resumeCv": user.get("resume_cv", ""),
                    "educationalCertificates": user.get("educational_certificates", []),
                    "experienceLetter": user.get("experience_letter", "")
                },
                "governmentIds": {
                    "aadhaarNo": user.get("aadhaar_no", ""),
                    "panNo": user.get("pan_no", "")
                }
            }
            
            return profile_data
        except Exception as e:
            return None

    def update_user_profile(self, email, update_data):
        """Update user profile"""
        try:
            # Remove sensitive fields that shouldn't be updated directly
            update_data.pop('password', None)
            update_data.pop('plain_password', None)
            update_data.pop('_id', None)
            update_data.pop('email', None)  # Email should be updated separately
            
            # Add update timestamp
            update_data['date_updated'] = datetime.utcnow().isoformat()
            update_data['updated_by'] = email
            
            # Update user
            result = self.user_collection.update_one(
                {"email": email},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Profile updated successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "No changes made or user not found"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Profile update failed: {str(e)}"
            }

    def change_password(self, email, current_password, new_password):
        """Change user password"""
        try:
            # Authenticate user
            user = self.authenticate_user(email, current_password)
            if not user:
                return {
                    "success": False,
                    "message": "Current password is incorrect"
                }
            
            # Validate new password
            if not self.is_valid_password(new_password):
                return {
                    "success": False,
                    "message": "New password must be at least 8 characters long and contain letters and numbers"
                }
            
            # Hash new password
            hashed_password = bcrypt.hash(new_password)
            
            # Update password
            result = self.user_collection.update_one(
                {"email": email},
                {"$set": {
                    "password": hashed_password,
                    "date_updated": datetime.utcnow().isoformat(),
                    "updated_by": email
                }}
            )
            
            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Password changed successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update password"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Password change failed: {str(e)}"
            }

    def forgot_password(self, email):
        """Generate password reset token"""
        try:
            # Check if user exists
            user = self.user_collection.find_one({"email": email})
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            # Generate reset token
            reset_token = self.generate_reset_token()
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Store reset token
            reset_data = {
                "email": email,
                "token": reset_token,
                "expires_at": expires_at,
                "used": False,
                "created_at": datetime.utcnow()
            }
            
            # Remove old tokens for this user
            self.password_reset_collection.delete_many({"email": email})
            
            # Insert new token
            self.password_reset_collection.insert_one(reset_data)
            
            # In a real implementation, send email here
            # For now, we'll return the token (in production, send via email)
            return {
                "success": True,
                "message": "Password reset token generated",
                "reset_token": reset_token  # Remove this in production
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Password reset failed: {str(e)}"
            }

    def reset_password(self, token, new_password):
        """Reset password using token"""
        try:
            # Find valid reset token
            reset_data = self.password_reset_collection.find_one({
                "token": token,
                "used": False,
                "expires_at": {"$gt": datetime.utcnow()}
            })
            
            if not reset_data:
                return {
                    "success": False,
                    "message": "Invalid or expired reset token"
                }
            
            # Validate new password
            if not self.is_valid_password(new_password):
                return {
                    "success": False,
                    "message": "New password must be at least 8 characters long and contain letters and numbers"
                }
            
            # Hash new password
            hashed_password = bcrypt.hash(new_password)
            
            # Update password
            result = self.user_collection.update_one(
                {"email": reset_data['email']},
                {"$set": {
                    "password": hashed_password,
                    "date_updated": datetime.utcnow().isoformat(),
                    "updated_by": reset_data['email']
                }}
            )
            
            if result.modified_count > 0:
                # Mark token as used
                self.password_reset_collection.update_one(
                    {"token": token},
                    {"$set": {"used": True}}
                )
                
                return {
                    "success": True,
                    "message": "Password reset successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to reset password"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Password reset failed: {str(e)}"
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

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            user = self.user_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return None
            
            # Remove sensitive information
            user.pop('password', None)
            user.pop('plain_password', None)
            
            # Convert ObjectId to string
            user['_id'] = str(user['_id'])
            
            return user
        except Exception as e:
            return None

    def update_last_login(self, email):
        """Update user's last login timestamp"""
        try:
            self.user_collection.update_one(
                {"$or": [{"email": email}, {"official_email_username": email}]},
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