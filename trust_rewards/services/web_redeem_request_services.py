from datetime import datetime
from typing import Dict, Any, List
from bson import ObjectId
from trust_rewards.database import client1
from trust_rewards.utils.common import DateUtils, ValidationUtils, AuditUtils

class WebRedeemRequestService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.gift_redemptions = self.client_database["gift_redemptions"]
        self.skilled_workers = self.client_database["skilled_workers"]
        self.gift_master = self.client_database["gift_master"]

    def get_all_redemption_requests(self, request_data: dict) -> dict:
        """Get all redemption requests with pagination and filtering"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', '')
            search = filters.get('search', '')
            worker_id = filters.get('worker_id', '')
            gift_id = filters.get('gift_id', '')
            date_from = filters.get('date_from', '')
            date_to = filters.get('date_to', '')

            # Build query
            query = {}
            
            # Handle status filter - only apply if not "all"
            if status and status.strip() and status.strip() != 'all':
                query['status'] = status.strip()
            
            # Handle worker_id filter
            if worker_id and worker_id.strip():
                query['worker_id'] = worker_id.strip()
            
            # Handle gift_id filter
            if gift_id and gift_id.strip():
                query['gift_id'] = gift_id.strip()
            
            # Handle search filter (searches in worker_name and gift_name)
            if search and search.strip():
                query['$or'] = [
                    {'worker_name': {"$regex": search.strip(), "$options": "i"}},
                    {'gift_name': {"$regex": search.strip(), "$options": "i"}}
                ]
            
            # Handle date range filters
            if date_from and date_from.strip():
                query['request_date'] = {"$gte": date_from.strip()}
            
            if date_to and date_to.strip():
                if 'request_date' in query:
                    query['request_date']['$lte'] = date_to.strip()
                else:
                    query['request_date'] = {"$lte": date_to.strip()}

            # Get redemption requests with pagination (sort first, then paginate)
            redemptions = list(
                self.gift_redemptions.find(query)
                .sort("request_datetime", -1)  # Latest requests first
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

            # Get statistics
            stats = self._get_redemption_stats()

            return {
                "success": True,
                "data": {
                    "records": redemptions,
                    "stats": stats,
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
                "message": f"Failed to get redemption requests: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _get_redemption_stats(self) -> dict:
        """Get redemption statistics"""
        try:
            # Total redemptions
            total_redemptions = self.gift_redemptions.count_documents({})
            
            # Status-wise counts
            pending_count = self.gift_redemptions.count_documents({"status": "pending"})
            approved_count = self.gift_redemptions.count_documents({"status": "approved"})
            redeemed_count = self.gift_redemptions.count_documents({"status": "redeemed"})
            cancelled_count = self.gift_redemptions.count_documents({"status": "cancelled"})
            
            # Total points involved
            total_points_pipeline = [
                {"$group": {"_id": None, "total_points": {"$sum": "$points_used"}}}
            ]
            total_points_result = list(self.gift_redemptions.aggregate(total_points_pipeline))
            total_points = total_points_result[0].get('total_points', 0) if total_points_result else 0
            
            # Pending points (points in pending requests)
            pending_points_pipeline = [
                {"$match": {"status": "pending"}},
                {"$group": {"_id": None, "total_points": {"$sum": "$points_used"}}}
            ]
            pending_points_result = list(self.gift_redemptions.aggregate(pending_points_pipeline))
            pending_points = pending_points_result[0].get('total_points', 0) if pending_points_result else 0

            return {
                "total_redemptions": total_redemptions,
                "pending_redemptions": pending_count,
                "approved_redemptions": approved_count,
                "redeemed_redemptions": redeemed_count,
                "cancelled_redemptions": cancelled_count,
                "total_points_involved": total_points,
                "pending_points": pending_points
            }

        except Exception as e:
            print(f"Error getting redemption stats: {str(e)}")
            return {
                "total_redemptions": 0,
                "pending_redemptions": 0,
                "approved_redemptions": 0,
                "redeemed_redemptions": 0,
                "cancelled_redemptions": 0,
                "total_points_involved": 0,
                "pending_points": 0
            }

    def update_redemption_status(self, request_data: dict, current_user: dict) -> dict:
        """Update redemption status with history tracking"""
        try:
            redemption_id = request_data.get('redemption_id')
            new_status = request_data.get('status')
            comments = request_data.get('comments', '')
            
            if not redemption_id:
                return {
                    "success": False,
                    "message": "redemption_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "redemption_id is mandatory"}
                }
            
            if not new_status:
                return {
                    "success": False,
                    "message": "status is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "status is mandatory"}
                }
            
            # Validate status
            valid_statuses = ['pending', 'approved', 'redeemed', 'cancelled']
            if new_status not in valid_statuses:
                return {
                    "success": False,
                    "message": "Invalid status",
                    "error": {"code": "VALIDATION_ERROR", "details": f"Status must be one of: {valid_statuses}"}
                }
            
            # Get current redemption
            redemption = self.gift_redemptions.find_one({"redemption_id": redemption_id})
            if not redemption:
                return {
                    "success": False,
                    "message": "Redemption not found",
                    "error": {"code": "NOT_FOUND", "details": "Redemption record not found"}
                }
            
            current_status = redemption.get('status', '')
            
            # Check if status change is valid
            if current_status == new_status:
                return {
                    "success": False,
                    "message": "Status is already the same",
                    "error": {"code": "INVALID_STATUS", "details": f"Status is already '{new_status}'"}
                }
            
            # Get admin user info
            admin_id = current_user.get('user_id', 'admin')
            admin_name = current_user.get('name', 'Admin')
            
            # Create status history entry
            status_history_entry = {
                "status": new_status,
                "status_date": DateUtils.get_current_date(),
                "status_time": DateUtils.get_current_time(),
                "status_datetime": DateUtils.get_current_datetime(),
                "updated_by": admin_name,
                "updated_by_id": admin_id,
                "comments": comments or f"Status changed from {current_status} to {new_status} by {admin_name}"
            }
            
            # Prepare update data
            update_data = {
                "status": new_status,
                **AuditUtils.build_update_meta(admin_id)
            }
            
            # Add specific timestamp fields based on status
            if new_status == 'approved':
                update_data.update({
                    "approved_at": DateUtils.get_current_datetime(),
                    "approved_date": DateUtils.get_current_date(),
                    "approved_time": DateUtils.get_current_time()
                })
            elif new_status == 'redeemed':
                update_data.update({
                    "redeemed_at": DateUtils.get_current_datetime(),
                    "redeemed_date": DateUtils.get_current_date(),
                    "redeemed_time": DateUtils.get_current_time()
                })
            
            # Update redemption with status history
            update_result = self.gift_redemptions.update_one(
                {"redemption_id": redemption_id},
                {
                    "$set": update_data,
                    "$push": {
                        "status_history": status_history_entry
                    }
                }
            )
            
            if update_result.modified_count == 0:
                return {
                    "success": False,
                    "message": "Failed to update redemption status",
                    "error": {"code": "UPDATE_ERROR", "details": "Could not update redemption status"}
                }
            
            return {
                "success": True,
                "message": f"Redemption status updated to {new_status} successfully",
                "data": {
                    "redemption_id": redemption_id,
                    "previous_status": current_status,
                    "new_status": new_status,
                    "updated_at": DateUtils.get_current_datetime(),
                    "updated_by": admin_name
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update redemption status: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_redemption_detail(self, request_data: dict) -> dict:
        """Get comprehensive redemption detail with worker info, wallet balance, reward details, and timeline"""
        try:
            redemption_id = request_data.get('redemption_id')
            
            if not redemption_id:
                return {
                    "success": False,
                    "message": "redemption_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "redemption_id is mandatory"}
                }
            
            # Get redemption with all related data
            redemption = self.gift_redemptions.find_one({"redemption_id": redemption_id})
            
            if not redemption:
                return {
                    "success": False,
                    "message": "Redemption not found",
                    "error": {"code": "NOT_FOUND", "details": "Redemption record not found"}
                }
            
            worker_id = redemption.get('worker_id')
            gift_id = redemption.get('gift_id')
            
            # Get worker information
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id)})
            worker_info = {
                "worker_name": worker.get('name', '') if worker else '',
                "mobile_number": worker.get('mobile', '') if worker else '',
                "region": worker.get('region', '') if worker else '',
                "worker_id": worker_id,
                "email": worker.get('email', '') if worker else '',
                "kyc_status": worker.get('kyc_status', 'Not Verified') if worker else 'Not Verified'
            }
            
            # Get gift/reward information
            gift = self.gift_master.find_one({"_id": ObjectId(gift_id)})
            reward_details = {
                "reward_name": gift.get('name') or gift.get('title') or gift.get('gift_name') or gift.get('product_name', '') if gift else '',
                "description": gift.get('description', '') if gift else '',
                "points_redeemed": redemption.get('points_used', 0),
                "reward_type": gift.get('category', '') if gift else '',
                "request_date": redemption.get('request_date', ''),
                "request_time": redemption.get('request_time', ''),
                "request_datetime": redemption.get('request_datetime', '')
            }
            
            # Get points used for summary
            points_used = redemption.get('points_used', 0)
            status = redemption.get('status', 'pending')
            
            # Get status history (redemption timeline)
            status_history = redemption.get('status_history', [])
            # Sort by datetime (latest first for display)
            status_history.sort(key=lambda x: x.get('status_datetime', ''), reverse=True)
            
            # Format timeline entries
            redemption_timeline = []
            for entry in status_history:
                timeline_entry = {
                    "status": entry.get('status', ''),
                    "updated_by": entry.get('updated_by', ''),
                    "timestamp": entry.get('status_time', ''),
                    "comment": entry.get('comments', ''),
                    "date": entry.get('status_date', ''),
                    "datetime": entry.get('status_datetime', '')
                }
                redemption_timeline.append(timeline_entry)
            
            return {
                "success": True,
                "data": {
                    "worker_information": worker_info,
                    "reward_request_details": reward_details,
                    "redemption_timeline": redemption_timeline,
                    "redemption_summary": {
                        "redemption_id": redemption_id,
                        "current_status": status,
                        "total_points_involved": points_used,
                        "request_date": redemption.get('request_date', ''),
                        "request_time": redemption.get('request_time', '')
                    }
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get redemption detail: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
