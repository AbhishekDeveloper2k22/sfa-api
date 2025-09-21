from bson import ObjectId
from trust_rewards.database import client1
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

class SkilledWorkerService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.skilled_workers = self.client_database["skilled_workers"]
        self.users = self.client_database["users"]
        self.current_datetime = datetime.now()

    def get_skilled_workers_list(self, request_data: dict) -> dict:
        """Get paginated list of skilled workers with optional filters"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'All')

            # Build query from request data
            query = request_data.copy()
            for k in ['page', 'limit', 'filters']:
                if k in query:
                    del query[k]

            # Apply mandatory status filter
            if status and status != 'All':
                query['status'] = status

            # Get total count
            total_count = self.skilled_workers.count_documents(query)
            
            # Get workers with pagination
            workers = list(self.skilled_workers.find(query).skip(skip).limit(limit))
            
            # Convert to DataFrame for efficient join
            if workers:
                workers_df = pd.DataFrame(workers)
                
                # Get unique created_by_ids
                created_by_ids = workers_df['created_by_id'].dropna().unique().tolist()
                
                # Fetch all users in one query
                users_data = list(self.users.find({"user_id": {"$in": created_by_ids}}))
                users_df = pd.DataFrame(users_data)
                
                # Create a mapping dictionary for quick lookup
                user_mapping = {}
                if not users_df.empty:
                    for _, user in users_df.iterrows():
                        user_mapping[user['user_id']] = user.get('username', 'Unknown')
                
                # Add created_by_name information to workers
                for worker in workers:
                    worker['_id'] = str(worker['_id'])
                    created_by_id = worker.get('created_by_id')
                    if created_by_id and created_by_id in user_mapping:
                        worker['created_by_name'] = user_mapping[created_by_id]
                    else:
                        worker['created_by_name'] = 'Unknown'

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Get stats card data
            stats = self.get_stats_data()

            return {
                "success": True,
                "data": {
                    "workers": workers,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    },
                    "stats": stats
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get skilled workers list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_stats_data(self) -> dict:
        """Get statistics data for dashboard cards"""
        try:
            # Get current month and last month for comparison
            current_date = self.current_datetime
            last_month = current_date.replace(day=1) - timedelta(days=1)
            last_month_start = last_month.replace(day=1)
            current_month_start = current_date.replace(day=1)
            
            # Total Workers (all time)
            total_workers = self.skilled_workers.count_documents({})
            
            # Active Workers (current)
            active_workers = self.skilled_workers.count_documents({"status": "Active"})
            
            # KYC Pending Workers
            kyc_pending = self.skilled_workers.count_documents({"status": "KYC Pending"})
            
            # Total Redemptions (sum of redemption_count for all workers)
            redemption_pipeline = [
                {"$group": {"_id": None, "total_redemptions": {"$sum": "$redemption_count"}}}
            ]
            redemption_result = list(self.skilled_workers.aggregate(redemption_pipeline))
            total_redemptions = redemption_result[0]["total_redemptions"] if redemption_result else 0
            
            # Calculate trends (comparing with last month)
            # Workers created this month
            current_month_workers = self.skilled_workers.count_documents({
                "created_date": {"$gte": current_month_start.strftime("%Y-%m-%d")}
            })
            
            # Workers created last month
            last_month_workers = self.skilled_workers.count_documents({
                "created_date": {
                    "$gte": last_month_start.strftime("%Y-%m-%d"),
                    "$lt": current_month_start.strftime("%Y-%m-%d")
                }
            })
            
            # Calculate percentage changes
            total_workers_trend = self._calculate_percentage_change(total_workers - current_month_workers, total_workers)
            active_workers_trend = self._calculate_percentage_change(active_workers, total_workers)
            kyc_pending_trend = self._calculate_percentage_change(kyc_pending, total_workers)
            total_redemptions_trend = self._calculate_percentage_change(total_redemptions, total_redemptions)
            
            return {
                "total_workers": {
                    "value": total_workers,
                    "trend": f"+{total_workers_trend}% from last month",
                    "trend_type": "positive" if total_workers_trend > 0 else "negative"
                },
                "active_workers": {
                    "value": active_workers,
                    "trend": f"+{active_workers_trend}% from last month",
                    "trend_type": "positive" if active_workers_trend > 0 else "negative"
                },
                "kyc_pending": {
                    "value": kyc_pending,
                    "trend": "Requires attention" if kyc_pending > 0 else "All clear",
                    "trend_type": "warning" if kyc_pending > 0 else "positive"
                },
                "total_redemptions": {
                    "value": total_redemptions,
                    "trend": f"+{total_redemptions_trend}% from last month",
                    "trend_type": "positive" if total_redemptions_trend > 0 else "negative"
                }
            }
            
        except Exception as e:
            # Return default stats if calculation fails
            return {
                "total_workers": {"value": 0, "trend": "N/A", "trend_type": "neutral"},
                "active_workers": {"value": 0, "trend": "N/A", "trend_type": "neutral"},
                "kyc_pending": {"value": 0, "trend": "N/A", "trend_type": "neutral"},
                "total_redemptions": {"value": 0, "trend": "N/A", "trend_type": "neutral"}
            }

    def _calculate_percentage_change(self, old_value: int, new_value: int) -> int:
        """Calculate percentage change between two values"""
        if old_value == 0:
            return 100 if new_value > 0 else 0
        return round(((new_value - old_value) / old_value) * 100)

    def get_skilled_worker_details(self, request_data: dict) -> dict:
        """Get details of a specific skilled worker"""
        try:
            worker_id = request_data.get('_id') or request_data.get('id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID is required",
                    "data": None
                }

            # Get worker details
            worker = self.skilled_workers.find_one({"_id": ObjectId(worker_id)})
            if not worker:
                return {
                    "success": False,
                    "message": "Worker not found",
                    "data": None
                }

            # Join with users collection using efficient lookup
            created_by_id = worker.get('created_by_id')
            if created_by_id:
                user = self.users.find_one({"user_id": created_by_id})
                if user:
                    worker['created_by_name'] = user.get('username', 'Unknown')
                else:
                    worker['created_by_name'] = 'Unknown'
            else:
                worker['created_by_name'] = 'Unknown'

            worker['_id'] = str(worker['_id'])
            
            return {
                "success": True,
                "message": "Worker details retrieved successfully",
                "data": worker
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get worker details: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
