from bson import ObjectId
from trust_rewards.database import client1
from datetime import datetime
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
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get skilled workers list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

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
