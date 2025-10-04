from bson import ObjectId
from trust_rewards.database import client1
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

class TransactionLedgerService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.transaction_ledger = self.client_database["transaction_ledger"]
        self.skilled_workers = self.client_database["skilled_workers"]
        self.users = self.client_database["users"]
        self.current_datetime = datetime.now()

    def get_transaction_ledger_list(self, request_data: dict) -> dict:
        """Get paginated list of transaction ledger with optional filters"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'All')
            transaction_type = filters.get('transaction_type', 'All')
            worker_id = filters.get('worker_id')
            date_from = filters.get('date_from')
            date_to = filters.get('date_to')

            # Build query from request data
            query = request_data.copy()
            for k in ['page', 'limit', 'filters']:
                if k in query:
                    del query[k]

            # Apply status filter
            if status and status != 'All':
                query['status'] = status

            # Apply transaction type filter
            if transaction_type and transaction_type != 'All':
                query['transaction_type'] = transaction_type

            # Apply worker_id filter
            if worker_id:
                query['worker_id'] = worker_id

            # Apply date range filter
            if date_from or date_to:
                date_query = {}
                if date_from:
                    date_query['$gte'] = date_from
                if date_to:
                    date_query['$lte'] = date_to
                query['transaction_date'] = date_query

            # Get total count
            total_count = self.transaction_ledger.count_documents(query)
            
            # Get transactions with pagination (sort by transaction_datetime desc)
            transactions = list(self.transaction_ledger.find(query).sort("transaction_datetime", -1).skip(skip).limit(limit))
            
            # Convert to DataFrame for efficient join
            if transactions:
                transactions_df = pd.DataFrame(transactions)
                
                # Get unique worker_ids and created_by_ids
                worker_ids = transactions_df['worker_id'].dropna().unique().tolist()
                created_by_ids = transactions_df['created_by'].dropna().unique().tolist()
                
                # Fetch all workers and users in one query each
                workers_data = list(self.skilled_workers.find({"worker_id": {"$in": worker_ids}}))
                users_data = list(self.users.find({"user_id": {"$in": created_by_ids}}))
                
                workers_df = pd.DataFrame(workers_data)
                users_df = pd.DataFrame(users_data)
                
                # Create mapping dictionaries for quick lookup
                worker_mapping = {}
                if not workers_df.empty:
                    for _, worker in workers_df.iterrows():
                        worker_mapping[worker['worker_id']] = {
                            'name': worker.get('name', 'Unknown'),
                            'phone': worker.get('phone', 'N/A')
                        }
                
                user_mapping = {}
                if not users_df.empty:
                    for _, user in users_df.iterrows():
                        user_mapping[user['user_id']] = user.get('username', 'Unknown')
                
                # Add worker and user information to transactions
                for transaction in transactions:
                    transaction['_id'] = str(transaction['_id'])
                    
                    # Add worker information
                    worker_id = transaction.get('worker_id')
                    if worker_id and worker_id in worker_mapping:
                        transaction['worker_name'] = worker_mapping[worker_id]['name']
                        transaction['worker_phone'] = worker_mapping[worker_id]['phone']
                    else:
                        transaction['worker_name'] = 'Unknown'
                        transaction['worker_phone'] = 'N/A'
                    
                    # Add created_by_name
                    created_by = transaction.get('created_by')
                    if created_by and created_by in user_mapping:
                        transaction['created_by_name'] = user_mapping[created_by]
                    else:
                        transaction['created_by_name'] = 'Unknown'

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Get stats data
            stats = self.get_transaction_stats()

            return {
                "success": True,
                "data": {
                    "transactions": transactions,
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
                "message": f"Failed to get transaction ledger list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_transaction_stats(self) -> dict:
        """Get statistics data for transaction ledger dashboard"""
        try:
            # Get current month and last month for comparison
            current_date = self.current_datetime
            last_month = current_date.replace(day=1) - timedelta(days=1)
            last_month_start = last_month.replace(day=1)
            current_month_start = current_date.replace(day=1)
            
            # Total Transactions (all time)
            total_transactions = self.transaction_ledger.count_documents({})
            
            # Completed Transactions
            completed_transactions = self.transaction_ledger.count_documents({"status": "completed"})
            
            # Pending Transactions
            pending_transactions = self.transaction_ledger.count_documents({"status": "pending"})
            
            # Total Amount (sum of amount for all transactions)
            amount_pipeline = [
                {"$group": {"_id": None, "total_amount": {"$sum": "$amount"}}}
            ]
            amount_result = list(self.transaction_ledger.aggregate(amount_pipeline))
            total_amount = amount_result[0]["total_amount"] if amount_result else 0
            
            # Calculate trends (comparing with last month)
            # Transactions this month
            current_month_transactions = self.transaction_ledger.count_documents({
                "transaction_date": {"$gte": current_month_start.strftime("%Y-%m-%d")}
            })
            
            # Transactions last month
            last_month_transactions = self.transaction_ledger.count_documents({
                "transaction_date": {
                    "$gte": last_month_start.strftime("%Y-%m-%d"),
                    "$lt": current_month_start.strftime("%Y-%m-%d")
                }
            })
            
            # Calculate percentage changes
            total_transactions_trend = self._calculate_percentage_change(last_month_transactions, current_month_transactions)
            completed_transactions_trend = self._calculate_percentage_change(completed_transactions, total_transactions)
            pending_transactions_trend = self._calculate_percentage_change(pending_transactions, total_transactions)
            total_amount_trend = self._calculate_percentage_change(total_amount, total_amount)
            
            return {
                "total_transactions": {
                    "value": total_transactions,
                    "trend": f"+{total_transactions_trend}% from last month",
                    "trend_type": "positive" if total_transactions_trend > 0 else "negative"
                },
                "completed_transactions": {
                    "value": completed_transactions,
                    "trend": f"+{completed_transactions_trend}% from last month",
                    "trend_type": "positive" if completed_transactions_trend > 0 else "negative"
                },
                "pending_transactions": {
                    "value": pending_transactions,
                    "trend": "Requires attention" if pending_transactions > 0 else "All clear",
                    "trend_type": "warning" if pending_transactions > 0 else "positive"
                },
                "total_amount": {
                    "value": total_amount,
                    "trend": f"+{total_amount_trend}% from last month",
                    "trend_type": "positive" if total_amount_trend > 0 else "negative"
                }
            }
            
        except Exception as e:
            # Return default stats if calculation fails
            return {
                "total_transactions": {"value": 0, "trend": "N/A", "trend_type": "neutral"},
                "completed_transactions": {"value": 0, "trend": "N/A", "trend_type": "neutral"},
                "pending_transactions": {"value": 0, "trend": "N/A", "trend_type": "neutral"},
                "total_amount": {"value": 0, "trend": "N/A", "trend_type": "neutral"}
            }

    def _calculate_percentage_change(self, old_value: int, new_value: int) -> int:
        """Calculate percentage change between two values"""
        if old_value == 0:
            return 100 if new_value > 0 else 0
        return round(((new_value - old_value) / old_value) * 100)

    def get_transaction_details(self, request_data: dict) -> dict:
        """Get details of a specific transaction"""
        try:
            transaction_id = request_data.get('_id') or request_data.get('id') or request_data.get('transaction_id')
            if not transaction_id:
                return {
                    "success": False,
                    "message": "Transaction ID is required",
                    "data": None
                }

            # Get transaction details
            if transaction_id.startswith('TXN_'):
                transaction = self.transaction_ledger.find_one({"transaction_id": transaction_id})
            else:
                transaction = self.transaction_ledger.find_one({"_id": ObjectId(transaction_id)})
            
            if not transaction:
                return {
                    "success": False,
                    "message": "Transaction not found",
                    "data": None
                }

            # Join with workers and users collections
            worker_id = transaction.get('worker_id')
            if worker_id:
                worker = self.skilled_workers.find_one({"worker_id": worker_id})
                if worker:
                    transaction['worker_name'] = worker.get('name', 'Unknown')
                    transaction['worker_phone'] = worker.get('phone', 'N/A')
                else:
                    transaction['worker_name'] = 'Unknown'
                    transaction['worker_phone'] = 'N/A'

            created_by = transaction.get('created_by')
            if created_by:
                user = self.users.find_one({"user_id": created_by})
                if user:
                    transaction['created_by_name'] = user.get('username', 'Unknown')
                else:
                    transaction['created_by_name'] = 'Unknown'
            else:
                transaction['created_by_name'] = 'Unknown'

            transaction['_id'] = str(transaction['_id'])
            
            return {
                "success": True,
                "message": "Transaction details retrieved successfully",
                "data": transaction
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get transaction details: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_worker_transaction_history(self, request_data: dict) -> dict:
        """Get transaction history for a specific worker"""
        try:
            worker_id = request_data.get('_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID is required",
                    "data": None
                }

            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Build query
            query = {"worker_id": worker_id}
            
            # Apply additional filters if provided
            filters = request_data.get('filters', {})
            transaction_type = filters.get('transaction_type')
            status = filters.get('status')
            date_from = filters.get('date_from')
            date_to = filters.get('date_to')

            if transaction_type and transaction_type != 'All':
                query['transaction_type'] = transaction_type
            
            if status and status != 'All':
                query['status'] = status

            if date_from or date_to:
                date_query = {}
                if date_from:
                    date_query['$gte'] = date_from
                if date_to:
                    date_query['$lte'] = date_to
                query['transaction_date'] = date_query

            # Get total count
            total_count = self.transaction_ledger.count_documents(query)
            
            # Get transactions with pagination
            transactions = list(self.transaction_ledger.find(query).sort("transaction_datetime", -1).skip(skip).limit(limit))
            
            # Convert ObjectId to string
            for transaction in transactions:
                transaction['_id'] = str(transaction['_id'])

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "transactions": transactions,
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
                "message": f"Failed to get worker transaction history: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_worker_redeem_history(self, request_data: dict) -> dict:
        """Get redeem history for a specific worker from gift_redemptions collection"""
        try:
            worker_id = request_data.get('_id')
            if not worker_id:
                return {
                    "success": False,
                    "message": "Worker ID is required",
                    "data": None
                }

            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Build query for gift redemptions
            query = {"worker_id": worker_id}
            
            # Apply additional filters if provided
            filters = request_data.get('filters', {})
            status = filters.get('status')
            date_from = filters.get('date_from')
            date_to = filters.get('date_to')
            gift_id = filters.get('gift_id')

            if status and status != 'All':
                query['status'] = status

            if gift_id:
                query['gift_id'] = gift_id

            if date_from or date_to:
                date_query = {}
                if date_from:
                    date_query['$gte'] = date_from
                if date_to:
                    date_query['$lte'] = date_to
                query['redemption_date'] = date_query

            # Get total count
            total_count = self.client_database["gift_redemptions"].count_documents(query)
            
            # Get redemptions with pagination
            redemptions = list(self.client_database["gift_redemptions"].find(query).sort("redemption_datetime", -1).skip(skip).limit(limit))
            
            # Convert ObjectId to string and add additional fields
            for redemption in redemptions:
                redemption['_id'] = str(redemption['_id'])
                
                # Add gift_id as string if it exists
                if 'gift_id' in redemption:
                    redemption['gift_id'] = str(redemption['gift_id'])
                
                # Add created_by as string if it exists
                if 'created_by' in redemption:
                    redemption['created_by'] = str(redemption['created_by'])
                
                # Add updated_by as string if it exists
                if 'updated_by' in redemption:
                    redemption['updated_by'] = str(redemption['updated_by'])

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Get redeem statistics for this worker
            redeem_stats = self.get_worker_redeem_stats_from_redemptions(worker_id)

            return {
                "success": True,
                "data": {
                    "redemptions": redemptions,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    },
                    "stats": redeem_stats
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get worker redeem history: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_worker_redeem_stats_from_redemptions(self, worker_id: str) -> dict:
        """Get redeem statistics for a specific worker from gift_redemptions collection"""
        try:
            # Get worker's current balance from skilled_workers collection
            worker = self.skilled_workers.find_one({"worker_id": worker_id})
            current_balance = worker.get('current_balance', 0) if worker else 0
            
            # Total redemptions (all statuses)
            total_redemptions = self.client_database["gift_redemptions"].count_documents({
                "worker_id": worker_id
            })
            
            # Completed redemptions
            completed_redemptions = self.client_database["gift_redemptions"].count_documents({
                "worker_id": worker_id,
                "status": "completed"
            })
            
            # Pending redemptions
            pending_redemptions = self.client_database["gift_redemptions"].count_documents({
                "worker_id": worker_id,
                "status": "pending"
            })
            
            # Cancelled redemptions
            cancelled_redemptions = self.client_database["gift_redemptions"].count_documents({
                "worker_id": worker_id,
                "status": "cancelled"
            })
            
            # Total points used (sum of points_used for all redemptions)
            points_pipeline = [
                {"$match": {"worker_id": worker_id}},
                {"$group": {"_id": None, "total_points_used": {"$sum": "$points_used"}}}
            ]
            points_result = list(self.client_database["gift_redemptions"].aggregate(points_pipeline))
            total_points_used = points_result[0]["total_points_used"] if points_result else 0
            
            # Points used for completed redemptions only
            completed_points_pipeline = [
                {"$match": {"worker_id": worker_id, "status": "completed"}},
                {"$group": {"_id": None, "completed_points_used": {"$sum": "$points_used"}}}
            ]
            completed_points_result = list(self.client_database["gift_redemptions"].aggregate(completed_points_pipeline))
            completed_points_used = completed_points_result[0]["completed_points_used"] if completed_points_result else 0
            
            # Points used for cancelled redemptions (these were returned)
            cancelled_points_pipeline = [
                {"$match": {"worker_id": worker_id, "status": "cancelled"}},
                {"$group": {"_id": None, "cancelled_points_used": {"$sum": "$points_used"}}}
            ]
            cancelled_points_result = list(self.client_database["gift_redemptions"].aggregate(cancelled_points_pipeline))
            cancelled_points_used = cancelled_points_result[0]["cancelled_points_used"] if cancelled_points_result else 0
            
            # Net points used (completed - cancelled)
            net_points_used = completed_points_used - cancelled_points_used
            
            return {
                "current_balance": current_balance,
                "total_redemptions": total_redemptions,
                "completed_redemptions": completed_redemptions,
                "pending_redemptions": pending_redemptions,
                "cancelled_redemptions": cancelled_redemptions,
                "total_points_used": total_points_used,
                "completed_points_used": completed_points_used,
                "cancelled_points_used": cancelled_points_used,
                "net_points_used": net_points_used
            }
            
        except Exception as e:
            # Return default stats if calculation fails
            return {
                "current_balance": 0,
                "total_redemptions": 0,
                "completed_redemptions": 0,
                "pending_redemptions": 0,
                "cancelled_redemptions": 0,
                "total_points_used": 0,
                "completed_points_used": 0,
                "cancelled_points_used": 0,
                "net_points_used": 0
            }
