from datetime import datetime
from bson import ObjectId
from trust_rewards.database import client1
from trust_rewards.utils.common import DateUtils, ValidationUtils, AuditUtils
from trust_rewards.utils.activity import RecentActivityLogger
from trust_rewards.utils.transaction import TransactionLogger
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
                try:
                    # Handle different datetime formats
                    if isinstance(verification_time, str):
                        # Try to parse ISO format first
                        try:
                            verification_datetime = datetime.fromisoformat(verification_time.replace('Z', '+00:00'))
                        except ValueError:
                            # If ISO format fails, try parsing as datetime string
                            verification_datetime = datetime.strptime(verification_time, '%Y-%m-%d %H:%M:%S')
                    else:
                        # If it's already a datetime object
                        verification_datetime = verification_time
                    
                    current_datetime = datetime.now()
                    
                    # Calculate time difference
                    time_diff = (current_datetime - verification_datetime).total_seconds()
                    print(f"DEBUG: OTP verification time check - Used at: {verification_datetime}, Current: {current_datetime}, Diff: {time_diff} seconds")
                    
                    if time_diff > 600:  # 10 minutes
                        return {
                            "success": False,
                            "message": "OTP verification expired",
                            "error": {
                                "code": "OTP_VERIFICATION_EXPIRED", 
                                "details": "OTP verification has expired. Please verify OTP again before redeeming gift"
                            }
                        }
                except Exception as e:
                    print(f"DEBUG: Error parsing verification time: {str(e)}")
                    # If we can't parse the time, allow the redemption to proceed
                    # This is a fallback to prevent blocking legitimate redemptions

            # Get gift details
            gift = self.gift_master.find_one({"_id": ObjectId(gift_id), "status": "active"})
            if not gift:
                return {
                    "success": False,
                    "message": "Gift not found or inactive",
                    "error": {"code": "NOT_FOUND", "details": "Gift not found or inactive"}
                }
            
            # Debug: Print gift details
            print(f"DEBUG: Gift found - ID: {gift['_id']}, Name: {gift.get('name', 'N/A')}, Points Required: {gift.get('points_required', 'N/A')}")
            print(f"DEBUG: Full gift document keys: {list(gift.keys())}")
            print(f"DEBUG: Gift name field value: '{gift.get('name', 'NOT_FOUND')}'")
            print(f"DEBUG: Gift title field value: '{gift.get('title', 'NOT_FOUND')}'")
            print(f"DEBUG: Gift gift_name field value: '{gift.get('gift_name', 'NOT_FOUND')}'")

            # Check if gift has required points
            points_required = gift.get('points_required', 0)
            # Ensure points_required is an integer
            try:
                points_required = int(points_required)
            except (ValueError, TypeError):
                points_required = 0
                
            if points_required <= 0:
                return {
                    "success": False,
                    "message": "Invalid gift configuration",
                    "error": {"code": "VALIDATION_ERROR", "details": "Gift has invalid points requirement"}
                }

            # Get current wallet balance
            current_balance = self._get_worker_balance(worker_id)
            print(f"DEBUG: Worker ID: {worker_id}, Current Balance: {current_balance}, Points Required: {points_required}")
            
            # Check if worker has sufficient balance
            if current_balance < points_required:
                return {
                    "success": False,
                    "message": "Insufficient wallet balance",
                    "error": {
                        "code": "INSUFFICIENT_BALANCE", 
                        "details": f"Required: {points_required} points, Available: {current_balance} points"
                    }
                }

            # Calculate new balance and deduct points immediately
            new_balance = current_balance - points_required
            # Ensure new_balance is an integer
            new_balance = int(new_balance)
            print(f"DEBUG: Balance calculation - Current: {current_balance} (type: {type(current_balance)}), Required: {points_required} (type: {type(points_required)}), New: {new_balance} (type: {type(new_balance)})")

            # Update worker's wallet balance immediately
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

            # Get gift name from multiple possible fields
            gift_name = gift.get('name') or gift.get('title') or gift.get('gift_name') or gift.get('product_name') or 'Unknown Gift'
            
            # Record gift redemption request (initially pending, but points already deducted)
            redemption_data = {
                "redemption_id": f"RED_{ObjectId()}",
                "worker_id": worker_id,
                "worker_name": worker.get('name', ''),
                "worker_mobile": worker.get('mobile', ''),
                "gift_id": str(gift['_id']),
                "gift_name": gift_name,
                "points_used": int(points_required),  # Ensure it's an integer
                "redemption_date": DateUtils.get_current_date(),
                "redemption_time": DateUtils.get_current_time(),
                "redemption_datetime": DateUtils.get_current_datetime(),
                "status": "pending",  # Initially pending, admin will approve
                "request_date": DateUtils.get_current_date(),
                "request_time": DateUtils.get_current_time(),
                "request_datetime": DateUtils.get_current_datetime(),
                "status_history": [
                    {
                        "status": "pending",
                        "status_date": DateUtils.get_current_date(),
                        "status_time": DateUtils.get_current_time(),
                        "status_datetime": DateUtils.get_current_datetime(),
                        "updated_by": worker.get('name', 'Worker'),
                        "updated_by_id": worker_id,
                        "comments": f"Request submitted by {worker.get('name', 'Worker')}"
                    }
                ],
                **AuditUtils.build_create_meta(worker_id)  # Using worker ID for app redemptions
            }
            
            print(f"DEBUG: Redemption data - Gift Name: {redemption_data['gift_name']}, Points Used: {redemption_data['points_used']}")

            self.gift_redemptions.insert_one(redemption_data)

            # Record transaction in ledger (points already deducted)
            TransactionLogger.record(
                worker_id=worker_id,
                transaction_type="GIFT_REDEMPTION_REQUEST",
                amount=-int(points_required),
                description=f"Gift redemption request: {gift_name}",
                previous_balance=int(current_balance),
                new_balance=int(new_balance),
                reference_id=str(gift['_id']),
                reference_type="gift_master",
                redemption_id=redemption_data['redemption_id'],
                created_by=worker_id
            )

            # Log recent activity for redemption request (non-blocking)
            try:
                RecentActivityLogger.log_activity(
                    worker_id=worker_id,
                    title=f"Redeemed {int(points_required)} points for {gift_name}",
                    points_change=-int(points_required),
                    activity_type="GIFT_REDEMPTION_REQUEST",
                    description=f"Redemption request created for {gift_name}",
                    reference_id=str(gift['_id']),
                    reference_type="gift_master",
                    metadata={
                        "redemption_id": redemption_data['redemption_id']
                    }
                )
            except Exception as _e:
                print(f"Activity log failed (redeem request): {_e}")

            return {
                "success": True,
                "message": "Gift redemption request submitted successfully",
                "data": {
                    "redemption_id": redemption_data['redemption_id'],
                    "gift_name": gift_name,
                    "points_used": points_required,
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "status": "pending",
                    "message": "Points deducted. Your redemption request is pending admin approval",
                    "request_datetime": redemption_data['request_datetime']
                }
            }

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"DEBUG: Error in redeem_gift: {str(e)}")
            print(f"DEBUG: Traceback: {tb}")
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
        """Get wallet overview for wallet screen.

        Returns:
            {
                success: true,
                data: {
                    balance: int,
                    totals: { earned: int, redeemed: int, redeemed_abs: int },
                    recent_transactions: [
                        {
                            transaction_id, transaction_type, description,
                            amount, is_credit, date_label, transaction_date,
                            transaction_time
                        }
                    ]
                }
            }
        """
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID not found in user session",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid user session"}
                }

            # Current balance from worker document
            balance = self._get_worker_balance(worker_id)

            # Aggregate totals from transaction_ledger
            pipeline = [
                {"$match": {"worker_id": worker_id}},
                {
                    "$group": {
                        "_id": None,
                        "earned": {"$sum": {"$cond": [{"$gt": ["$amount", 0]}, "$amount", 0]}},
                        "redeemed": {"$sum": {"$cond": [{"$lt": ["$amount", 0]}, "$amount", 0]}},
                    }
                }
            ]

            agg = list(self.transaction_ledger.aggregate(pipeline))
            earned_total = 0
            redeemed_total = 0
            if agg:
                earned_total = int(agg[0].get("earned", 0) or 0)
                redeemed_total = int(agg[0].get("redeemed", 0) or 0)  # negative sum

            # Recent transactions (last 10)
            recent = list(
                self.transaction_ledger.find({"worker_id": worker_id})
                .sort("transaction_datetime", -1)
                .limit(10)
            )

            # Build friendly list
            today = DateUtils.get_current_date()
            recent_list = []
            for tx in recent:
                # Normalize values
                amount = int(tx.get("amount", 0) or 0)
                tx_date = tx.get("transaction_date") or today

                # Human friendly date label
                try:
                    days = DateUtils.get_days_difference(tx_date, today)
                except Exception:
                    days = 0
                if days <= 0:
                    date_label = "Today"
                elif days == 1:
                    date_label = "Yesterday"
                else:
                    date_label = f"{days} days ago"

                recent_list.append({
                    "transaction_id": tx.get("transaction_id", ""),
                    "transaction_type": tx.get("transaction_type", ""),
                    "description": tx.get("description", ""),
                    "amount": amount,
                    "is_credit": amount > 0,
                    "date_label": date_label,
                    "transaction_date": tx_date,
                    "transaction_time": tx.get("transaction_time", ""),
                })

            return {
                "success": True,
                "data": {
                    "balance": balance,
                    "totals": {
                        "earned": earned_total,
                        "redeemed": redeemed_total,
                        "redeemed_abs": abs(redeemed_total),
                    },
                    "counts": {
                        "coupon_scans": int(self.transaction_ledger.count_documents({
                            "worker_id": worker_id,
                            "transaction_type": "COUPON_SCAN"
                        })),
                        "redeems": int(self.gift_redemptions.count_documents({
                            "worker_id": worker_id,
                            "status": "redeemed"
                        })),
                        "redeem_pending": int(self.gift_redemptions.count_documents({
                            "worker_id": worker_id,
                            "status": "pending"
                        })),
                    },
                    "recent_transactions": recent_list,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get wallet balance: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    # _record_transaction removed; using TransactionLogger.record

    def _get_worker_balance(self, worker_id: str) -> int:
        """Get current wallet balance of worker"""
        try:
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id)})
            if worker:
                balance = worker.get('wallet_points', 0)
                # Ensure balance is an integer
                try:
                    return int(balance)
                except (ValueError, TypeError):
                    print(f"Warning: Invalid wallet_points value: {balance}, defaulting to 0")
                    return 0
            return 0
        except Exception as e:
            print(f"Error getting worker balance: {str(e)}")
            return 0

    def send_otp_for_redemption(self, request_data: dict, current_user: dict) -> dict:
        """Send OTP to worker's mobile for gift redemption verification"""
        try:

            gift_id = request_data.get('gift_id')
            if not gift_id:
                return {
                    "success": False,
                    "message": "Gift ID is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Gift ID is mandatory"}
                }

            gift = self.gift_master.find_one({"_id": ObjectId(gift_id), "status": "active"})
            if not gift:
                return {
                    "success": False,
                    "message": "Gift not found or inactive",
                    "error": {"code": "NOT_FOUND", "details": "Gift not found or inactive"}
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
                "gift_id": gift_id,
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

    def cancel_redemption(self, request_data: dict, current_user: dict) -> dict:
        """Cancel a gift redemption and return points to wallet"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID not found in user session",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid user session"}
                }

            # Extract redemption_id from request
            redemption_id = request_data.get('redemption_id')
            if not redemption_id:
                return {
                    "success": False,
                    "message": "redemption_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "redemption_id is mandatory"}
                }

            # Find the redemption record
            redemption = self.gift_redemptions.find_one({
                "redemption_id": redemption_id,
                "worker_id": worker_id
            })

            if not redemption:
                return {
                    "success": False,
                    "message": "Redemption not found",
                    "error": {"code": "NOT_FOUND", "details": "Redemption record not found"}
                }

            # Check if redemption can be cancelled (only if status is "pending")
            current_status = redemption.get('status', '')
            if current_status == 'redeemed':
                return {
                    "success": False,
                    "message": "Cannot cancel redeemed gift",
                    "error": {
                        "code": "INVALID_STATUS", 
                        "details": "Gift has already been redeemed and cannot be cancelled"
                    }
                }

            if current_status == 'cancelled':
                return {
                    "success": False,
                    "message": "Redemption already cancelled",
                    "error": {
                        "code": "ALREADY_CANCELLED", 
                        "details": "This redemption has already been cancelled"
                    }
                }

            if current_status != 'pending':
                return {
                    "success": False,
                    "message": "Cannot cancel redemption in current status",
                    "error": {
                        "code": "INVALID_STATUS", 
                        "details": f"Redemption status '{current_status}' cannot be cancelled. Only 'pending' redemptions can be cancelled."
                    }
                }

            # Get points to be returned (points were already deducted)
            points_to_return = redemption.get('points_used', 0)
            if points_to_return <= 0:
                return {
                    "success": False,
                    "message": "Invalid redemption data",
                    "error": {"code": "VALIDATION_ERROR", "details": "No points to return"}
                }

            # Get current wallet balance and calculate new balance after returning points
            current_balance = self._get_worker_balance(worker_id)
            new_balance = current_balance + points_to_return

            # Update worker's wallet balance (return the points)
            update_result = self.skilled_workers.update_one(
                {"_id": ObjectId(worker_id)},
                {
                    "$set": {
                        "wallet_points": new_balance,
                        "last_activity": DateUtils.get_current_date()
                    }
                }
            )

            if update_result.modified_count == 0:
                return {
                    "success": False,
                    "message": "Failed to update wallet balance",
                    "error": {"code": "UPDATE_ERROR", "details": "Could not update worker wallet points"}
                }

            # Update redemption status to cancelled and add status history entry
            cancellation_history_entry = {
                "status": "cancelled",
                "status_date": DateUtils.get_current_date(),
                "status_time": DateUtils.get_current_time(),
                "status_datetime": DateUtils.get_current_datetime(),
                "updated_by": redemption.get('worker_name', 'Worker'),
                "updated_by_id": worker_id,
                "comments": f"Redemption cancelled by {redemption.get('worker_name', 'Worker')}"
            }
            
            self.gift_redemptions.update_one(
                {"redemption_id": redemption_id},
                {
                    "$set": {
                        "status": "cancelled",
                        "cancelled_at": DateUtils.get_current_datetime(),
                        "cancelled_date": DateUtils.get_current_date(),
                        "cancelled_time": DateUtils.get_current_time(),
                        **AuditUtils.build_update_meta(worker_id)
                    },
                    "$push": {
                        "status_history": cancellation_history_entry
                    }
                }
            )

            # Record transaction in ledger for points return
            TransactionLogger.record(
                worker_id=worker_id,
                transaction_type="REDEMPTION_CANCELLATION",
                amount=int(points_to_return),
                description=f"Redemption cancellation: {redemption.get('gift_name', 'Unknown Gift')}",
                previous_balance=current_balance,
                new_balance=new_balance,
                reference_id=redemption.get('gift_id'),
                reference_type="gift_master",
                redemption_id=redemption_id,
                created_by=worker_id
            )

            # Log recent activity for cancellation (credit back)
            try:
                RecentActivityLogger.log_activity(
                    worker_id=worker_id,
                    title=f"Redemption cancelled for {redemption.get('gift_name', 'Gift')}",
                    points_change=int(points_to_return),
                    activity_type="REDEMPTION_CANCELLED",
                    description="Points returned to wallet due to cancellation",
                    reference_id=redemption.get('gift_id'),
                    reference_type="gift_master",
                    metadata={"redemption_id": redemption_id}
                )
            except Exception as _e:
                print(f"Activity log failed (redeem cancel): {_e}")

            return {
                "success": True,
                "message": "Redemption request cancelled successfully",
                "data": {
                    "redemption_id": redemption_id,
                    "gift_name": redemption.get('gift_name', 'Unknown Gift'),
                    "points_returned": points_to_return,
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "message": "Points have been returned to your wallet",
                    "cancelled_at": DateUtils.get_current_datetime()
                }
            }

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"DEBUG: Error in cancel_redemption: {str(e)}")
            print(f"DEBUG: Traceback: {tb}")
            return {
                "success": False,
                "message": f"Failed to cancel redemption: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
