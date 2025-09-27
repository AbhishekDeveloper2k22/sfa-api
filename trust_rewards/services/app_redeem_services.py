from datetime import datetime
from bson import ObjectId
from trust_rewards.database import client1
from trust_rewards.utils.common import DateUtils, ValidationUtils, AuditUtils
import random
import string

class AppRedeemService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.skilled_workers = self.client_database["skilled_workers"]
        self.gift_master = self.client_database["gift_master"]
        self.transaction_ledger = self.client_database["transaction_ledger"]
        self.gift_redemptions = self.client_database["gift_redemptions"]
        self.otp_verification = self.client_database["otp_verification"]

    def redeem_gift(self, request_data: dict, current_user: dict) -> dict:
        """Redeem gift using wallet points"""
        try:
            # Extract gift_id and verification_token from request
            gift_id = request_data.get('gift_id')
            verification_token = request_data.get('verification_token')
            
            if not gift_id:
                return {
                    "success": False,
                    "message": "gift_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "gift_id is mandatory"}
                }
            
            if not verification_token:
                return {
                    "success": False,
                    "message": "verification_token is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "verification_token is mandatory for gift redemption"}
                }

            # Validate gift_id format
            try:
                ObjectId(gift_id)
            except:
                return {
                    "success": False,
                    "message": "Invalid gift_id format",
                    "error": {"code": "VALIDATION_ERROR", "details": "gift_id must be a valid ObjectId"}
                }

            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID not found in user session",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid user session"}
                }

            # Get worker details
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id), "status": "Active"})
            if not worker:
                return {
                    "success": False,
                    "message": "Worker not found or inactive",
                    "error": {"code": "NOT_FOUND", "details": "Worker not found or inactive"}
                }

            # Check OTP verification for gift redemption
            verified_otp = self.otp_verification.find_one({
                "worker_id": worker_id,
                "purpose": "gift_redemption",
                "is_used": True,
                "used_at": {"$exists": True},
                "verification_token": verification_token
            })
            
            if not verified_otp:
                return {
                    "success": False,
                    "message": "OTP verification required",
                    "error": {
                        "code": "OTP_VERIFICATION_REQUIRED", 
                        "details": "Please verify OTP before redeeming gift. Call /send_otp first, then /verify_otp"
                    }
                }
            
            # Check if verification is recent (within last 10 minutes)
            verification_time = verified_otp.get('used_at')
            if verification_time:
                from datetime import datetime, timedelta
                verification_datetime = datetime.fromisoformat(verification_time.replace('Z', '+00:00'))
                current_datetime = datetime.now(verification_datetime.tzinfo)
                
                if (current_datetime - verification_datetime).total_seconds() > 600:  # 10 minutes
                    return {
                        "success": False,
                        "message": "OTP verification expired",
                        "error": {
                            "code": "OTP_VERIFICATION_EXPIRED", 
                            "details": "OTP verification has expired. Please verify OTP again before redeeming gift"
                        }
                    }

            # Get gift details
            gift = self.gift_master.find_one({"_id": ObjectId(gift_id), "status": "active"})
            if not gift:
                return {
                    "success": False,
                    "message": "Gift not found or inactive",
                    "error": {"code": "NOT_FOUND", "details": "Gift not found or inactive"}
                }

            # Check if gift has required points
            points_required = gift.get('points_required', 0)
            if points_required <= 0:
                return {
                    "success": False,
                    "message": "Invalid gift configuration",
                    "error": {"code": "VALIDATION_ERROR", "details": "Gift has invalid points requirement"}
                }

            # Get current wallet balance
            current_balance = self._get_worker_balance(worker_id)
            
            if current_balance < points_required:
                return {
                    "success": False,
                    "message": "Insufficient wallet balance",
                    "error": {
                        "code": "INSUFFICIENT_BALANCE", 
                        "details": f"Required: {points_required} points, Available: {current_balance} points"
                    }
                }

            # Calculate new balance
            new_balance = current_balance - points_required

            # Update worker's wallet balance
            update_result = self.skilled_workers.update_one(
                {"_id": ObjectId(worker_id)},
                {
                    "$set": {
                        "wallet_points": new_balance,
                        "last_activity": DateUtils.get_current_date()
                    }
                }
            )
            
            # Check if update was successful
            if update_result.modified_count == 0:
                return {
                    "success": False,
                    "message": "Failed to update wallet balance",
                    "error": {"code": "UPDATE_ERROR", "details": "Could not update worker wallet points"}
                }

            # Record gift redemption
            redemption_data = {
                "redemption_id": f"RED_{ObjectId()}",
                "worker_id": worker_id,
                "worker_name": worker.get('name', ''),
                "worker_mobile": worker.get('mobile', ''),
                "gift_id": str(gift['_id']),
                "gift_name": gift.get('name', ''),
                "points_used": points_required,
                "redemption_date": DateUtils.get_current_date(),
                "redemption_time": DateUtils.get_current_time(),
                "redemption_datetime": DateUtils.get_current_datetime(),
                "status": "redeemed",
                **AuditUtils.build_create_meta(worker_id)  # Using worker ID for app redemptions
            }

            self.gift_redemptions.insert_one(redemption_data)

            # Record transaction in ledger
            self._record_transaction(
                worker_id=worker_id,
                transaction_type="GIFT_REDEMPTION",
                amount=-points_required,  # Negative for debit
                description=f"Gift redemption: {gift.get('name', '')}",
                previous_balance=current_balance,
                new_balance=new_balance,
                reference_id=str(gift['_id']),
                reference_type="gift_master",
                redemption_id=redemption_data['redemption_id']
            )

            return {
                "success": True,
                "message": "Gift redeemed successfully",
                "data": {
                    "redemption_id": redemption_data['redemption_id'],
                    "gift_name": gift.get('name', ''),
                    "points_used": points_required,
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "redemption_datetime": redemption_data['redemption_datetime']
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to redeem gift: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_redemption_history(self, request_data: dict, current_user: dict) -> dict:
        """Get gift redemption history for worker"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID not found in user session",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid user session"}
                }

            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Build query
            query = {"worker_id": worker_id}

            # Get redemptions with pagination (sort first, then paginate)
            redemptions = list(
                self.gift_redemptions.find(query)
                .sort("redemption_datetime", -1)
                .skip(skip)
                .limit(limit)
            )

            # Get total count
            total_count = self.gift_redemptions.count_documents(query)

            # Convert ObjectId to string
            for redemption in redemptions:
                redemption['_id'] = str(redemption['_id'])

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Get current balance
            current_balance = self._get_worker_balance(worker_id)

            return {
                "success": True,
                "data": {
                    "records": redemptions,
                    "current_balance": current_balance,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get redemption history: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_wallet_balance(self, current_user: dict) -> dict:
        """Get current wallet balance for worker"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID not found in user session",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid user session"}
                }

            # Get current balance
            current_balance = self._get_worker_balance(worker_id)

            # Get total redemptions count
            total_redemptions = self.gift_redemptions.count_documents({"worker_id": worker_id})

            # Get total points spent on redemptions
            total_points_spent = self.gift_redemptions.aggregate([
                {"$match": {"worker_id": worker_id}},
                {"$group": {"_id": None, "total": {"$sum": "$points_used"}}}
            ])

            total_spent = 0
            for result in total_points_spent:
                total_spent = result.get('total', 0)
                break

            return {
                "success": True,
                "data": {
                    "current_balance": current_balance,
                    "total_redemptions": total_redemptions,
                    "total_points_spent": total_spent
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get wallet balance: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _record_transaction(self, worker_id: str, transaction_type: str, amount: int, 
                          description: str, previous_balance: int, new_balance: int,
                          reference_id: str = None, reference_type: str = None, 
                          redemption_id: str = None) -> None:
        """Record transaction in ledger"""
        try:
            transaction_data = {
                "transaction_id": f"TXN_{ObjectId()}",
                "worker_id": worker_id,
                "transaction_type": transaction_type,  # GIFT_REDEMPTION, etc.
                "amount": amount,  # Negative for debit
                "description": description,
                "reference_id": reference_id,  # ID of the related document
                "reference_type": reference_type,  # gift_master, etc.
                "redemption_id": redemption_id,
                "previous_balance": previous_balance,
                "new_balance": new_balance,
                "transaction_date": DateUtils.get_current_date(),
                "transaction_time": DateUtils.get_current_time(),
                "transaction_datetime": DateUtils.get_current_datetime(),
                "status": "completed",
                **AuditUtils.build_create_meta(worker_id)  # Using worker ID for app transactions
            }

            self.transaction_ledger.insert_one(transaction_data)
            
        except Exception as e:
            print(f"Error recording transaction: {str(e)}")

    def _get_worker_balance(self, worker_id: str) -> int:
        """Get current wallet balance of worker"""
        try:
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id)})
            if worker:
                return worker.get('wallet_points', 0)
            return 0
        except Exception as e:
            print(f"Error getting worker balance: {str(e)}")
            return 0

    def send_otp_for_redemption(self, request_data: dict, current_user: dict) -> dict:
        """Send OTP to worker's mobile for gift redemption verification"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID not found in user session",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid user session"}
                }

            # Get worker details
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id), "status": "Active"})
            if not worker:
                return {
                    "success": False,
                    "message": "Worker not found or inactive",
                    "error": {"code": "NOT_FOUND", "details": "Worker not found or inactive"}
                }

            # Get worker's mobile number
            mobile = worker.get('mobile', '')
            if not mobile:
                return {
                    "success": False,
                    "message": "Mobile number not found for worker",
                    "error": {"code": "VALIDATION_ERROR", "details": "Mobile number not available"}
                }

            # Generate 6-digit OTP
            otp = ''.join(random.choices(string.digits, k=6))
            
            # OTP expires in 5 minutes
            expiry_time = datetime.now().timestamp() + (5 * 60)  # 5 minutes from now

            # Store OTP in database
            otp_data = {
                "otp_id": f"OTP_{ObjectId()}",
                "worker_id": worker_id,
                "mobile": mobile,
                "otp": otp,
                "purpose": "gift_redemption",
                "expires_at": expiry_time,
                "is_used": False,
                "created_at": DateUtils.get_current_date(),
                "created_time": DateUtils.get_current_time(),
                "created_datetime": DateUtils.get_current_datetime(),
                **AuditUtils.build_create_meta(worker_id)
            }

            # Remove any existing unused OTPs for this worker
            self.otp_verification.delete_many({
                "worker_id": worker_id,
                "purpose": "gift_redemption",
                "is_used": False
            })

            # Insert new OTP
            self.otp_verification.insert_one(otp_data)

            # TODO: Integrate with SMS service to send OTP
            # For now, we'll return the OTP in response for testing
            # In production, remove the OTP from response and send via SMS
            
            return {
                "success": True,
                "message": f"OTP sent to mobile number ending with {mobile[-4:]}",
                "data": {
                    "otp_id": otp_data['otp_id'],
                    "mobile_masked": f"******{mobile[-4:]}",
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

    def verify_otp_for_redemption(self, request_data: dict, current_user: dict) -> dict:
        """Verify OTP for gift redemption"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID not found in user session",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid user session"}
                }

            # Extract OTP and OTP ID from request
            otp = request_data.get('otp')
            otp_id = request_data.get('otp_id')

            if not otp or not otp_id:
                return {
                    "success": False,
                    "message": "OTP and OTP ID are required",
                    "error": {"code": "VALIDATION_ERROR", "details": "OTP and OTP ID are mandatory"}
                }

            # Find OTP record
            otp_record = self.otp_verification.find_one({
                "otp_id": otp_id,
                "worker_id": worker_id,
                "purpose": "gift_redemption",
                "is_used": False
            })

            if not otp_record:
                return {
                    "success": False,
                    "message": "Invalid or expired OTP",
                    "error": {"code": "INVALID_OTP", "details": "OTP not found or already used"}
                }

            # Check if OTP has expired
            current_time = datetime.now().timestamp()
            if current_time > otp_record.get('expires_at', 0):
                return {
                    "success": False,
                    "message": "OTP has expired",
                    "error": {"code": "OTP_EXPIRED", "details": "OTP has expired, please request a new one"}
                }

            # Verify OTP
            if otp_record.get('otp') != otp:
                return {
                    "success": False,
                    "message": "Invalid OTP",
                    "error": {"code": "INVALID_OTP", "details": "OTP does not match"}
                }

            # Generate verification token for gift redemption
            verification_token = f"VERIFIED_{ObjectId()}"
            
            # Mark OTP as used and store verification token
            self.otp_verification.update_one(
                {"otp_id": otp_id},
                {
                    "$set": {
                        "is_used": True,
                        "used_at": DateUtils.get_current_datetime(),
                        "verification_token": verification_token,
                        **AuditUtils.build_update_meta(worker_id)
                    }
                }
            )

            return {
                "success": True,
                "message": "OTP verified successfully",
                "data": {
                    "otp_id": otp_id,
                    "verified_at": DateUtils.get_current_datetime(),
                    "verification_token": verification_token,
                    "expires_in_minutes": 10  # Verification valid for 10 minutes
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to verify OTP: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
