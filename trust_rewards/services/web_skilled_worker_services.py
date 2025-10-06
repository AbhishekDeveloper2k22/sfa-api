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
        self.transaction_ledger = self.client_database["transaction_ledger"]
        self.gift_redemptions = self.client_database["gift_redemptions"]
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
            
            # Get workers with pagination (sort first, then paginate)
            workers = list(self.skilled_workers.find(query).sort("_id", -1).skip(skip).limit(limit))
            
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

    def get_super30_list(self, request_data: dict) -> dict:
        """Return top 30 workers with ranking and requested fields.

        Optional request_data:
          - page, limit (default 1, 30) if frontend wants pagination
          - sort_by: one of ['points', 'wallet_points', 'coupon_scans', 'redemption_count']
          - sort_dir: 1 or -1
        """
        try:
            page = int(request_data.get('page', 1) or 1)
            limit = int(request_data.get('limit', 30) or 30)
            skip = (page - 1) * limit

            sort_by = request_data.get('sort_by', 'points')
            sort_dir = int(request_data.get('sort_dir', -1))

            # Compute coupon scans count per worker from transaction_ledger
            scans_pipeline = [
                {"$match": {"transaction_type": "COUPON_SCAN"}},
                {"$group": {"_id": "$worker_id", "coupon_scans": {"$sum": 1}}}
            ]
            scans_map = {d['_id']: d.get('coupon_scans', 0) for d in self.transaction_ledger.aggregate(scans_pipeline)}

            # Compute redemption counts per worker (completed)
            redeem_done_pipeline = [
                {"$match": {"status": "redeemed"}},
                {"$group": {"_id": "$worker_id", "redeem_completed": {"$sum": 1}}}
            ]
            redeem_done_map = {d['_id']: d.get('redeem_completed', 0) for d in self.gift_redemptions.aggregate(redeem_done_pipeline)}

            # Compute total earned points per worker (sum of positive amounts)
            earned_pipeline = [
                {"$group": {
                    "_id": "$worker_id",
                    "earned_points": {"$sum": {"$cond": [{"$gt": ["$amount", 0]}, "$amount", 0]}}
                }}
            ]
            earned_map = {d['_id']: int(d.get('earned_points', 0) or 0) for d in self.transaction_ledger.aggregate(earned_pipeline)}

            # Get candidate workers sorted by requested metric
            mongo_sort_field = {
                'points': 'points',
                'wallet_points': 'wallet_points',
                'coupon_scans': None,  # will sort in Python after enriching
                'redemption_count': 'redemption_count',
            }.get(sort_by, 'points')

            # Base query: Active only unless explicitly specified
            query = request_data.get('filters', {}) or {}
            if 'status' not in query:
                query['status'] = 'Active'

            projection = {
                "_id": 1,
                "created_by_id": 1,
                "user_id": 1,
                "name": 1,
                "mobile": 1,
                "points": 1,
                "wallet_points": 1,
                "redemption_count": 1,
                "state": 1,
                "district": 1,
                "city": 1,
                "pincode": 1,
                "last_activity": 1,
            }

            if mongo_sort_field:
                cursor = self.skilled_workers.find(query, projection).sort(mongo_sort_field, sort_dir).limit(limit)
                workers = list(cursor)
            else:
                # need more than limit to sort by scans in python; fetch top 200 by points as a heuristic
                workers = list(self.skilled_workers.find(query, projection).sort('points', -1).limit(max(limit, 200)))

            # Enrich and shape output
            created_by_ids = []
            rows = []
            for w in workers:
                wid = str(w.get('_id'))
                created_by_id = w.get('created_by_id')
                if created_by_id:
                    created_by_ids.append(created_by_id)

                row = {
                    "worker_id": wid,
                    "created_by_id": created_by_id,
                    "worker_name": w.get('name', ''),
                    "mobile": w.get('mobile', ''),
                    # Points earned till date from ledger (overrides worker doc points)
                    "points": int(earned_map.get(wid, w.get('points', 0) or 0)),
                    "wallet_points": int(w.get('wallet_points', 0) or 0),
                    "coupon_scans": int(scans_map.get(wid, 0)),
                    "redemption_count": int(w.get('redemption_count', 0) or 0) + int(redeem_done_map.get(wid, 0)),
                    "state": w.get('state', ''),
                    "district": w.get('district', ''),
                    "city": w.get('city', ''),
                    "pincode": w.get('pincode', ''),
                    "last_activity": w.get('last_activity', ''),
                }
                rows.append(row)

            # If sorting by coupon_scans, do it now
            if sort_by == 'coupon_scans':
                rows.sort(key=lambda r: r['coupon_scans'], reverse=(sort_dir == -1))

            # Apply pagination (in case of python sorting)
            rows = rows[skip: skip + limit]

            # Rank assignment
            rows.sort(key=lambda r: (
                -r['points'],
                -r['wallet_points'],
                -r['coupon_scans'],
                -r['redemption_count'],
            ))
            for idx, r in enumerate(rows, start=1 + skip):
                r['rank'] = idx

            # Resolve Created By names
            if created_by_ids:
                users_data = list(self.users.find({"user_id": {"$in": list(set(created_by_ids))}}, {"user_id": 1, "username": 1}))
                name_map = {u.get('user_id'): u.get('username', 'Unknown') for u in users_data}
                for r in rows:
                    r['created_by_name'] = name_map.get(r.get('created_by_id'), 'Unknown')
            else:
                for r in rows:
                    r['created_by_name'] = 'Unknown'

            # Final shape for frontend columns
            listing = []
            for r in rows:
                listing.append({
                    "rank": r['rank'],
                    "created_by_id": r['created_by_id'],
                    "created_by_name": r['created_by_name'],
                    "worker_id": r['worker_id'],
                    "worker_name": r['worker_name'],
                    "mobile": r['mobile'],
                    "points": r['points'],
                    "wallet_points": r['wallet_points'],
                    "coupons_scanned": r['coupon_scans'],
                    "redemption_count": r['redemption_count'],
                    "state": r['state'],
                    "district": r['district'],
                    "city": r['city'],
                    "pincode": r['pincode'],
                    "last_activity": r['last_activity'],
                })

            return {
                "success": True,
                "data": {
                    "records": listing,
                    "pagination": {"current_page": page, "limit": limit}
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get super30 list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
