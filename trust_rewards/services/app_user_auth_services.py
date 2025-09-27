import random
import jwt as pyjwt
import os
from datetime import datetime, timedelta
from bson import ObjectId
from trust_rewards.database import client1
# from trust_rewards.utils.hashing import hash_password, verify_password
from trust_rewards.utils.common import ValidationUtils, SecurityUtils, DateUtils, AuditUtils
from dotenv import load_dotenv

load_dotenv()

class AppUserAuthService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.skilled_workers = self.client_database["skilled_workers"]
        self.otp_verification = self.client_database["otp_verification"]
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key")
        self.jwt_algorithm = "HS256"
        self.otp_expiry_minutes = 5  # OTP expires in 5 minutes
        self.max_otp_attempts = 3  # Maximum OTP attempts

    def send_otp(self, request_data: dict) -> dict:
        """Send OTP to mobile number"""
        try:
            mobile = request_data.get('mobile')
            if not mobile:
                return {
                    "success": False,
                    "message": "Mobile number is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Missing mobile number"}
                }

            # Validate and normalize mobile number
            normalized_mobile = self._normalize_mobile(mobile)
            if not normalized_mobile:
                return {
                    "success": False,
                    "message": "Invalid mobile number format",
                    "error": {"code": "VALIDATION_ERROR", "details": "Mobile number must be 10 digits or 12 digits with country code"}
                }

            # Check if skilled worker exists (try multiple mobile formats)
            worker = self._find_worker_by_mobile(normalized_mobile)
            if not worker:
                return {
                    "success": False,
                    "message": "Skilled worker not found with this mobile number",
                    "error": {"code": "USER_NOT_FOUND", "details": "No skilled worker registered with this mobile"}
                }

            # Check if worker is active
            if worker.get('status') != 'Active':
        return {
                    "success": False,
                    "message": "Account is inactive. Please contact support.",
                    "error": {"code": "ACCOUNT_INACTIVE", "details": "Worker account is not active"}
                }

            # Generate 6-digit OTP
            otp = SecurityUtils.generate_otp(6)
            
            # OTP expires in 5 minutes
            expiry_time = datetime.now().timestamp() + (5 * 60)  # 5 minutes from now
            
            # Store OTP in database
            otp_data = {
                "otp_id": f"OTP_{ObjectId()}",
                "worker_id": str(worker['_id']),
                "mobile": normalized_mobile,
                "otp": otp,
                "purpose": "login",
                "expires_at": expiry_time,
                "is_used": False,
                "created_at": DateUtils.get_current_date(),
                "created_time": DateUtils.get_current_time(),
                "created_datetime": DateUtils.get_current_datetime(),
                **AuditUtils.build_create_meta(str(worker['_id']))
            }
            
            # Remove any existing unused OTPs for this worker and purpose
            self.otp_verification.delete_many({
                "worker_id": str(worker['_id']),
                "purpose": "login",
                "is_used": False
            })
            
            # Insert new OTP
            result = self.otp_verification.insert_one(otp_data)
            
            # In production, send OTP via SMS service
            # For now, we'll return it in response (remove in production)
                return {
                    "success": True,
                "message": f"OTP sent to mobile number ending with {normalized_mobile[-4:]}",
                "data": {
                    "otp_id": otp_data['otp_id'],
                    "mobile_masked": f"******{normalized_mobile[-4:]}",
                    "expires_in_minutes": 5,
                    "otp": otp  # Remove this in production
                }
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send OTP: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def verify_otp(self, request_data: dict) -> dict:
        """Verify OTP and generate JWT token"""
        try:
            mobile = request_data.get('mobile')
            otp = request_data.get('otp')
            otp_id = request_data.get('otp_id')
            
            if not mobile or not otp:
                return {
                    "success": False,
                    "message": "Mobile number and OTP are required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Missing mobile or OTP"}
                }

            # Normalize mobile number
            normalized_mobile = self._normalize_mobile(mobile)
            if not normalized_mobile:
                return {
                    "success": False,
                    "message": "Invalid mobile number format",
                    "error": {"code": "VALIDATION_ERROR", "details": "Mobile number must be 10 digits or 12 digits with country code"}
                }

            # Find OTP record - use otp_id if provided, otherwise fallback to mobile
            if otp_id:
                otp_record = self.otp_verification.find_one({
                    "otp_id": otp_id,
                    "mobile": normalized_mobile,
                    "purpose": "login",
                    "is_used": False
                })
            else:
                # Fallback to mobile-based lookup for backward compatibility
                otp_record = self.otp_verification.find_one({
                    "mobile": normalized_mobile,
                    "purpose": "login",
                    "is_used": False
                })
            
            if not otp_record:
                return {
                    "success": False,
                    "message": "OTP not found or already used",
                    "error": {"code": "OTP_NOT_FOUND", "details": "No valid OTP found for this mobile"}
                }

            # Check if OTP has expired
            current_time = datetime.now().timestamp()
            if current_time > otp_record.get('expires_at', 0):
                return {
                    "success": False,
                    "message": "OTP has expired. Please request a new one.",
                    "error": {"code": "OTP_EXPIRED", "details": "OTP has expired"}
                }

            # Verify OTP
            if otp_record.get('otp') != otp:
                return {
                    "success": False,
                    "message": "Invalid OTP",
                    "error": {"code": "INVALID_OTP", "details": "OTP does not match"}
                }
            
            # OTP is correct - get worker details
            worker = self.skilled_workers.find_one({"_id": ObjectId(otp_record['worker_id'])})
            if not worker:
                return {
                    "success": False,
                    "message": "Worker not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "Worker associated with OTP not found"}
                }

            # Mark OTP as used
            self.otp_verification.update_one(
                {"otp_id": otp_record['otp_id']},
                {
                    "$set": {
                        "is_used": True,
                        "used_at": DateUtils.get_current_datetime(),
                        **AuditUtils.build_update_meta(otp_record['worker_id'])
                    }
                }
            )

            # Generate JWT token
            token_payload = {
                "worker_id": str(worker['_id']),
                "mobile": worker['mobile'],
                "role": "skilled_worker",
                "exp": datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
            }
            
            token = pyjwt.encode(token_payload, self.jwt_secret, algorithm=self.jwt_algorithm)

            # Update last activity
            self.skilled_workers.update_one(
                {"_id": worker['_id']},
                {"$set": {"last_activity": DateUtils.get_current_date()}}
            )

                return {
                    "success": True,
                "message": "OTP verified successfully",
                "data": {
                    "token": token,
                    "worker": {
                        "worker_id": str(worker['_id']),
                        "worker_code": worker.get('worker_id', ''),
                        "mobile": worker['mobile'],
                        "name": worker.get('name', ''),
                        "worker_type": worker.get('worker_type', ''),
                        "wallet_points": worker.get('wallet_points', 0),
                        "kyc_status": worker.get('kyc_status', ''),
                        "status": worker.get('status', ''),
                        "state": worker.get('state', ''),
                        "city": worker.get('city', '')
                    },
                    "expires_in": 24 * 60 * 60  # 24 hours in seconds
                }
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to verify OTP: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def resend_otp(self, request_data: dict) -> dict:
        """Resend OTP to mobile number"""
        try:
            mobile = request_data.get('mobile')
            if not mobile:
                return {
                    "success": False,
                    "message": "Mobile number is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Missing mobile number"}
                }

            # Normalize mobile number
            normalized_mobile = self._normalize_mobile(mobile)
            if not normalized_mobile:
                return {
                    "success": False,
                    "message": "Invalid mobile number format",
                    "error": {"code": "VALIDATION_ERROR", "details": "Mobile number must be 10 digits or 12 digits with country code"}
                }

            # Check if skilled worker exists
            worker = self._find_worker_by_mobile(normalized_mobile)
            if not worker:
                return {
                    "success": False,
                    "message": "Skilled worker not found with this mobile number",
                    "error": {"code": "USER_NOT_FOUND", "details": "No skilled worker registered with this mobile"}
                }

            # Check if there's a recent OTP request (prevent spam)
            recent_otp = self.otp_verification.find_one({
                "worker_id": str(worker['_id']),
                "purpose": "login",
                "created_datetime": {"$gte": DateUtils.add_minutes_to_datetime(DateUtils.get_current_datetime(), -1)}
            })
            
            if recent_otp:
                return {
                    "success": False,
                    "message": "Please wait before requesting another OTP",
                    "error": {"code": "RATE_LIMIT", "details": "OTP can be requested once per minute"}
                }

            # Generate new OTP
            otp = SecurityUtils.generate_otp(6)
            expiry_time = datetime.now().timestamp() + (5 * 60)  # 5 minutes from now
            
            # Remove existing unused OTPs for this worker and purpose
            self.otp_verification.delete_many({
                "worker_id": str(worker['_id']),
                "purpose": "login",
                "is_used": False
            })
            
            # Insert new OTP
            otp_data = {
                "otp_id": f"OTP_{ObjectId()}",
                "worker_id": str(worker['_id']),
                "mobile": normalized_mobile,
                "otp": otp,
                "purpose": "login",
                "expires_at": expiry_time,
                "is_used": False,
                "created_at": DateUtils.get_current_date(),
                "created_time": DateUtils.get_current_time(),
                "created_datetime": DateUtils.get_current_datetime(),
                **AuditUtils.build_create_meta(str(worker['_id']))
            }
            
            result = self.otp_verification.insert_one(otp_data)
            
            return {
                "success": True,
                "message": f"OTP sent to mobile number ending with {normalized_mobile[-4:]}",
                "data": {
                    "otp_id": otp_data['otp_id'],
                    "mobile_masked": f"******{normalized_mobile[-4:]}",
                    "expires_in_minutes": 5,
                    "otp": otp  # Remove this in production
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to resend OTP: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def logout(self, request_data: dict, current_user: dict) -> dict:
        """Logout user and invalidate token"""
        try:
            # In a more sophisticated implementation, you might want to:
            # 1. Add token to a blacklist
            # 2. Store logout time
            # 3. Clear any active sessions
            
            # For now, we'll just return success
            # The token will naturally expire
            
                return {
                "success": True,
                "message": "Logged out successfully",
                "data": {
                    "worker_id": current_user.get('worker_id'),
                    "logout_time": DateUtils.get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                }
            }

        except Exception as e:
                return {
                    "success": False,
                "message": f"Failed to logout: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def refresh_token(self, request_data: dict, current_user: dict) -> dict:
        """Refresh JWT token"""
        try:
            # Generate new token with extended expiry
            token_payload = {
                "worker_id": current_user.get('worker_id'),
                "mobile": current_user.get('mobile'),
                "role": "skilled_worker",
                "exp": datetime.utcnow() + timedelta(hours=24)  # New 24-hour expiry
            }
            
            new_token = pyjwt.encode(token_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
                
                return {
                    "success": True,
                "message": "Token refreshed successfully",
                "data": {
                    "token": new_token,
                    "expires_in": 24 * 60 * 60,  # 24 hours in seconds
                    "worker_id": current_user.get('worker_id')
                }
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to refresh token: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _normalize_mobile(self, mobile: str) -> str:
        """Normalize mobile number to standard format"""
        if not mobile:
            return None
            
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, mobile))
        
        # Handle different formats
        if len(digits_only) == 10:
            # 10 digits: 9876543210
            return digits_only
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            # 12 digits with country code: 919876543210
            return digits_only[2:]  # Remove country code
        elif len(digits_only) == 11 and digits_only.startswith('0'):
            # 11 digits starting with 0: 09876543210
            return digits_only[1:]  # Remove leading 0
        else:
                return None
            
    def _find_worker_by_mobile(self, normalized_mobile: str):
        """Find worker by mobile number, trying different formats"""
        if not normalized_mobile:
            return None

        # Try different mobile formats that might be stored in database
        mobile_formats = [
            normalized_mobile,  # 9876543210
            f"+91{normalized_mobile}",  # +919876543210
            f"91{normalized_mobile}",  # 919876543210
            f"0{normalized_mobile}"  # 09876543210
        ]
        
        # Search for worker with any of these mobile formats
        for mobile_format in mobile_formats:
            worker = self.skilled_workers.find_one({"mobile": mobile_format})
            if worker:
                return worker
                
        return None