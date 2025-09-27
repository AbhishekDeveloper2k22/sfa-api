from datetime import datetime
from bson import ObjectId
from trust_rewards.database import client1
from trust_rewards.utils.common import DateUtils, ValidationUtils

class AppCouponService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.skilled_workers = self.client_database["skilled_workers"]
        self.coupon_code = self.client_database["coupon_code"]
        self.coupon_master = self.client_database["coupon_master"]
        self.coupon_scanned_history = self.client_database["coupon_scanned_history"]
        self.transaction_ledger = self.client_database["transaction_ledger"]

    def scan_coupon(self, request_data: dict, current_user: dict) -> dict:
        """Scan coupon codes and award points"""
        try:
            # Extract coupon codes from request
            coupon_codes = request_data.get('coupon_code', [])
            if not coupon_codes or not isinstance(coupon_codes, list):
                return {
                    "success": False,
                    "message": "coupon_code list is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Missing or invalid coupon_code list"}
                }

            # Validate coupon codes format
            for coupon_code in coupon_codes:
                if not coupon_code or not isinstance(coupon_code, str):
                    return {
                        "success": False,
                        "message": f"Invalid coupon code format: {coupon_code}",
                        "error": {"code": "VALIDATION_ERROR", "details": "Invalid coupon code format"}
                    }

            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker information not found",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid worker token"}
                }

            # Get worker details
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id)})
            if not worker:
                return {
                    "success": False,
                    "message": "Worker not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "Worker not found in database"}
                }

            # Check if worker is active
            if worker.get('status') != 'Active':
                return {
                    "success": False,
                    "message": "Worker account is not active",
                    "error": {"code": "ACCOUNT_INACTIVE", "details": "Worker account is not active"}
                }

            # Process each coupon
            results = []
            total_points_earned = 0
            successful_scans = 0
            failed_scans = 0

            for coupon_code in coupon_codes:
                coupon_result = self._process_single_coupon(coupon_code, worker)
                results.append(coupon_result)
                
                if coupon_result['success']:
                    successful_scans += 1
                    total_points_earned += coupon_result.get('points_earned', 0)
                else:
                    failed_scans += 1

            # Get current balance before updating
            current_balance = self._get_worker_balance(worker_id)
            new_balance = current_balance + total_points_earned

            # Update worker's wallet points and coupons scanned count
            if successful_scans > 0:
                self.skilled_workers.update_one(
                    {"_id": ObjectId(worker_id)},
                    {
                        "$inc": {
                            "wallet_points": total_points_earned,
                            "coupons_scanned": successful_scans
                        },
                        "$set": {
                            "last_activity": DateUtils.get_current_date()
                        }
                    }
                )

            # Record transaction in ledger for successful scans
            if successful_scans > 0:
                self._record_transaction(
                    worker_id=worker_id,
                    transaction_type="COUPON_SCAN",
                    amount=total_points_earned,
                    description=f"Scanned {successful_scans} coupons",
                    previous_balance=current_balance,
                    new_balance=new_balance,
                    reference_id="",  # Multiple coupons, no single reference
                    reference_type="multiple_coupons",
                    batch_number=""
                )

            return {
                "success": True,
                "message": f"Processed {len(coupon_codes)} coupons. {successful_scans} successful, {failed_scans} failed.",
                "data": {
                    "total_coupons": len(coupon_codes),
                    "successful_scans": successful_scans,
                    "failed_scans": failed_scans,
                    "total_points_earned": total_points_earned,
                    "results": results,
                    "worker": {
                        "worker_id": str(worker['_id']),
                        "name": worker.get('name', ''),
                        "worker_type": worker.get('worker_type', ''),
                        "new_wallet_balance": new_balance,
                        "total_coupons_scanned": worker.get('coupons_scanned', 0) + successful_scans
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to scan coupons: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _process_single_coupon(self, coupon_code: str, worker: dict) -> dict:
        """Process a single coupon scan"""
        try:
            # Find coupon in database by coupon_code
            coupon = self.coupon_code.find_one({"coupon_code": coupon_code})
            if not coupon:
                return {
                    "success": False,
                    "coupon_code": coupon_code,
                    "error": "Coupon not found",
                    "points_earned": 0
                }

            # Check if coupon is already scanned
            if coupon.get('is_scanned', False):
                return {
                    "success": False,
                    "coupon_code": coupon_code,
                    "error": "Coupon already scanned",
                    "points_earned": 0
                }

            # Check coupon status
            if coupon.get('status') != 'active':
                return {
                    "success": False,
                    "coupon_code": coupon_code,
                    "error": f"Coupon status is {coupon.get('status', 'unknown')}",
                    "points_earned": 0
                }

            # Check coupon validity dates
            current_date = DateUtils.get_current_date()
            valid_from = coupon.get('valid_from')
            valid_to = coupon.get('valid_to')

            if valid_from and current_date < valid_from:
                return {
                    "success": False,
                    "coupon_code": coupon_code,
                    "error": "Coupon not yet valid",
                    "points_earned": 0
                }

            if valid_to and current_date > valid_to:
                return {
                    "success": False,
                    "coupon_code": coupon_code,
                    "error": "Coupon has expired",
                    "points_earned": 0
                }

            # Get coupon master details
            coupon_master_id = coupon.get('coupon_master_id')
            coupon_master = None
            if coupon_master_id:
                coupon_master = self.coupon_master.find_one({"_id": ObjectId(coupon_master_id)})

            # Calculate points to award
            points_earned = coupon.get('coupon_value', 0)
            if coupon_master:
                points_earned = coupon_master.get('points_value', points_earned)

            # Mark coupon as scanned
            scanned_data = {
                "coupon_id": str(coupon['_id']),
                "coupon_code": coupon_code,
                "worker_id": str(worker['_id']),
                "worker_name": worker.get('name', ''),
                "worker_mobile": worker.get('mobile', ''),
                "points_earned": points_earned,
                "scanned_at": DateUtils.get_current_datetime(),
                "scanned_date": DateUtils.get_current_date(),
                "scanned_time": DateUtils.get_current_time(),
                "coupon_master_id": coupon_master_id,
                "batch_number": coupon_master.get('batch_number', '') if coupon_master else ''
            }

            # Update coupon as scanned
            self.coupon_code.update_one(
                {"coupon_code": coupon_code},
                {
                    "$set": {
                        "is_scanned": True,
                        "scanned_by": str(worker['_id']),
                        "scanned_at": DateUtils.get_current_datetime(),
                        "status": "scanned"
                    }
                }
            )

            # Record scan history
            self.coupon_scanned_history.insert_one(scanned_data)

            # Record transaction in ledger (will be called from main scan_coupon method)
            # Transaction will be recorded after all coupons are processed

            return {
                "success": True,
                "coupon_code": coupon_code,
                "points_earned": points_earned,
                "batch_number": coupon_master.get('batch_number', '') if coupon_master else '',
                "message": "Coupon scanned successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "coupon_code": coupon_code,
                "error": f"Processing error: {str(e)}",
                "points_earned": 0
            }

    def _record_transaction(self, worker_id: str, transaction_type: str, amount: int, 
                          description: str, previous_balance: int, new_balance: int,
                          reference_id: str = None, reference_type: str = None, 
                          batch_number: str = None) -> None:
        """Record transaction in ledger"""
        try:
            transaction_data = {
                "transaction_id": f"TXN_{ObjectId()}",
                "worker_id": worker_id,
                "transaction_type": transaction_type,  # COUPON_SCAN, POINTS_DEDUCTION, etc.
                "amount": amount,  # Positive for credit, negative for debit
                "description": description,
                "reference_id": reference_id,  # ID of the related document
                "reference_type": reference_type,  # coupon_code, order, etc.
                "batch_number": batch_number,
                "previous_balance": previous_balance,
                "new_balance": new_balance,
                "transaction_date": DateUtils.get_current_date(),
                "transaction_time": DateUtils.get_current_time(),
                "transaction_datetime": DateUtils.get_current_datetime(),
                "status": "completed",
                "created_at": DateUtils.get_current_datetime()
            }

            self.transaction_ledger.insert_one(transaction_data)
            
        except Exception as e:
            print(f"Error recording transaction: {str(e)}")

    def _get_worker_balance(self, worker_id: str) -> int:
        """Get current wallet balance of worker"""
        try:
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id)})
            return worker.get('wallet_points', 0) if worker else 0
        except Exception as e:
            print(f"Error getting worker balance: {str(e)}")
            return 0

    def get_transaction_ledger(self, request_data: dict, current_user: dict) -> dict:
        """Get transaction ledger for worker"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker information not found",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid worker token"}
                }

            # Extract pagination and filter parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 20)
            transaction_type = request_data.get('transaction_type', 'ALL')  # ALL, COUPON_SCAN, etc.
            start_date = request_data.get('start_date')
            end_date = request_data.get('end_date')
            
            skip = (page - 1) * limit

            # Build query
            query = {"worker_id": worker_id}
            
            if transaction_type != 'ALL':
                query["transaction_type"] = transaction_type
            
            if start_date and end_date:
                query["transaction_date"] = {
                    "$gte": start_date,
                    "$lte": end_date
                }

            # Get transactions
            transactions = list(
                self.transaction_ledger.find(query)
                .sort("transaction_datetime", -1)
                .skip(skip)
                .limit(limit)
            )

            # Get total count
            total_count = self.transaction_ledger.count_documents(query)

            # Get current balance
            current_balance = self._get_worker_balance(worker_id)

            # Format transactions
            formatted_transactions = []
            for transaction in transactions:
                formatted_transactions.append({
                    "transaction_id": transaction.get('transaction_id', ''),
                    "transaction_type": transaction.get('transaction_type', ''),
                    "amount": transaction.get('amount', 0),
                    "description": transaction.get('description', ''),
                    "reference_id": transaction.get('reference_id', ''),
                    "reference_type": transaction.get('reference_type', ''),
                    "batch_number": transaction.get('batch_number', ''),
                    "previous_balance": transaction.get('previous_balance', 0),
                    "new_balance": transaction.get('new_balance', 0),
                    "transaction_date": transaction.get('transaction_date', ''),
                    "transaction_time": transaction.get('transaction_time', ''),
                    "status": transaction.get('status', '')
                })

            return {
                "success": True,
                "message": "Transaction ledger retrieved successfully",
                "data": {
                    "current_balance": current_balance,
                    "total_transactions": total_count,
                    "transactions": formatted_transactions,
                    "pagination": {
                        "current_page": page,
                        "total_pages": (total_count + limit - 1) // limit,
                        "total_count": total_count,
                        "limit": limit
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get transaction ledger: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_ledger_summary(self, request_data: dict, current_user: dict) -> dict:
        """Get ledger summary with statistics"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker information not found",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid worker token"}
                }

            # Get current balance
            current_balance = self._get_worker_balance(worker_id)

            # Get transaction statistics
            pipeline = [
                {"$match": {"worker_id": worker_id}},
                {
                    "$group": {
                        "_id": "$transaction_type",
                        "count": {"$sum": 1},
                        "total_amount": {"$sum": "$amount"}
                    }
                }
            ]

            stats = list(self.transaction_ledger.aggregate(pipeline))

            # Get recent transactions (last 5)
            recent_transactions = list(
                self.transaction_ledger.find({"worker_id": worker_id})
                .sort("transaction_datetime", -1)
                .limit(5)
            )

            # Format recent transactions
            formatted_recent = []
            for transaction in recent_transactions:
                formatted_recent.append({
                    "transaction_id": transaction.get('transaction_id', ''),
                    "transaction_type": transaction.get('transaction_type', ''),
                    "amount": transaction.get('amount', 0),
                    "description": transaction.get('description', ''),
                    "transaction_date": transaction.get('transaction_date', ''),
                    "transaction_time": transaction.get('transaction_time', '')
                })

            return {
                "success": True,
                "message": "Ledger summary retrieved successfully",
                "data": {
                    "current_balance": current_balance,
                    "transaction_stats": stats,
                    "recent_transactions": formatted_recent
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get ledger summary: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_coupon_history(self, request_data: dict, current_user: dict) -> dict:
        """Get coupon scan history for the worker"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker information not found",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid worker token"}
                }

            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 20)
            skip = (page - 1) * limit

            # Get scan history
            scans = list(
                self.coupon_scanned_history.find({"worker_id": worker_id})
                .sort("scanned_at", -1)
                .skip(skip)
                .limit(limit)
            )

            # Get total count
            total_count = self.coupon_scanned_history.count_documents({"worker_id": worker_id})

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Format scans
            formatted_scans = []
            for scan in scans:
                formatted_scans.append({
                    "coupon_id": scan.get('coupon_id', ''),
                    "coupon_code": scan.get('coupon_code', ''),
                    "points_earned": scan.get('points_earned', 0),
                    "batch_number": scan.get('batch_number', ''),
                    "scanned_at": scan.get('scanned_at', ''),
                    "scanned_date": scan.get('scanned_date', ''),
                    "scanned_time": scan.get('scanned_time', '')
                })

            return {
                "success": True,
                "message": "Coupon scan history retrieved successfully",
                "data": {
                    "scans": formatted_scans,
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
                "message": f"Failed to get coupon history: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_wallet_balance(self, request_data: dict, current_user: dict) -> dict:
        """Get current wallet balance for the worker"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker information not found",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid worker token"}
                }

            # Get worker details
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id)})
            if not worker:
                return {
                    "success": False,
                    "message": "Worker not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "Worker not found in database"}
                }

            # Get total scans count
            total_scans = self.coupon_scanned_history.count_documents({"worker_id": worker_id})

            # Get total points earned from scans
            total_points_earned = self.coupon_scanned_history.aggregate([
                {"$match": {"worker_id": worker_id}},
                {"$group": {"_id": None, "total": {"$sum": "$points_earned"}}}
            ])
            
            total_points_from_scans = 0
            for result in total_points_earned:
                total_points_from_scans = result.get('total', 0)
                break

            return {
                "success": True,
                "message": "Wallet balance retrieved successfully",
                "data": {
                    "worker": {
                        "worker_id": str(worker['_id']),
                        "name": worker.get('name', ''),
                        "worker_type": worker.get('worker_type', ''),
                        "mobile": worker.get('mobile', '')
                    },
                    "wallet": {
                        "current_balance": worker.get('wallet_points', 0),
                        "total_coupons_scanned": worker.get('coupons_scanned', 0),
                        "total_scans": total_scans,
                        "total_points_earned": total_points_from_scans,
                        "last_activity": worker.get('last_activity', '')
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get wallet balance: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_coupon_scanned_history(self, request_data: dict, current_user: dict) -> dict:
        """Get coupon scanned history for the worker"""
        try:
            # Get worker information
            worker_id = current_user.get('worker_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker information not found",
                    "error": {"code": "AUTH_ERROR", "details": "Invalid worker token"}
                }

            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 20)
            skip = (page - 1) * limit

            # Get scan history with pagination (sort first, then paginate)
            scans = list(
                self.coupon_scanned_history.find({"worker_id": worker_id})
                .sort("scanned_at", -1)
                .skip(skip)
                .limit(limit)
            )

            # Get total count
            total_count = self.coupon_scanned_history.count_documents({"worker_id": worker_id})

            # Convert ObjectId to string and format scans
            formatted_scans = []
            for scan in scans:
                scan['_id'] = str(scan['_id'])
                formatted_scans.append({
                    "_id": scan['_id'],
                    "coupon_id": scan.get('coupon_id', ''),
                    "coupon_code": scan.get('coupon_code', ''),
                    "worker_id": scan.get('worker_id', ''),
                    "worker_name": scan.get('worker_name', ''),
                    "worker_mobile": scan.get('worker_mobile', ''),
                    "points_earned": scan.get('points_earned', 0),
                    "scanned_at": scan.get('scanned_at', ''),
                    "scanned_date": scan.get('scanned_date', ''),
                    "scanned_time": scan.get('scanned_time', ''),
                    "coupon_master_id": scan.get('coupon_master_id', ''),
                    "batch_number": scan.get('batch_number', '')
                })

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "message": "Coupon scanned history retrieved successfully",
                "data": {
                    "records": formatted_scans,
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
                "message": f"Failed to get coupon scanned history: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
