from bson import ObjectId
from datetime import datetime
from trust_rewards.database import client1


class AppWorkerService:
    def __init__(self):
        db = client1['trust_rewards']
        self.skilled_workers = db['skilled_workers']
        self.transaction_ledger = db['transaction_ledger']

    def _period_filter(self, period: str):
        if period == 'all_time':
            return {}
        # this_month default
        now = datetime.now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return {
            "transaction_datetime": {"$gte": start}
        }

    def get_super30_leaderboard(self, request_data: dict, current_user: dict = None) -> dict:
        try:
            period = (request_data.get('period') or 'this_month').lower()
            if period not in ['this_month', 'all_time']:
                period = 'this_month'

            match_stage = {**self._period_filter(period)}

            # Aggregate earned points and scan counts per worker
            pipeline = [
                {"$match": match_stage} if match_stage else {"$match": {}},
                {"$group": {
                    "_id": "$worker_id",
                    "earned_points": {"$sum": {"$cond": [{"$gt": ["$amount", 0]}, "$amount", 0]}},
                    "scans": {"$sum": {"$cond": [{"$eq": ["$transaction_type", "COUPON_SCAN"]}, 1, 0]}}
                }},
                {"$sort": {"earned_points": -1, "scans": -1}},
                {"$limit": 30}
            ]

            agg = list(self.transaction_ledger.aggregate(pipeline))

            # Fetch worker names for top 30
            worker_ids = [ObjectId(w) for w in [a['_id'] for a in agg] if ObjectId.is_valid(w)]
            workers_map = {}
            if worker_ids:
                for w in self.skilled_workers.find({"_id": {"$in": worker_ids}}, {"name": 1}):
                    workers_map[str(w['_id'])] = w.get('name', '')

            # Build podium and rankings list
            records = []
            current_user_rank = None
            current_user_in_top30 = False
            
            for idx, a in enumerate(agg, start=1):
                wid = a['_id']
                record = {
                    "rank": idx,
                    "worker_id": wid,
                    "worker_name": workers_map.get(wid, ""),
                    "points": int(a.get('earned_points', 0) or 0),
                    "scans": int(a.get('scans', 0) or 0),
                }
                records.append(record)
                
                # Check if current user is in top 30
                if current_user and current_user.get('worker_id') == wid:
                    current_user_rank = idx
                    current_user_in_top30 = True

            top3 = records[:3]
            rankings = records[3:]

            return {
                "success": True,
                "data": {
                    "period": period,
                    "top3": top3,
                    "rankings": rankings,
                    "current_user": {
                        "is_in_top30": current_user_in_top30,
                        "rank": current_user_rank
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to fetch leaderboard: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }


