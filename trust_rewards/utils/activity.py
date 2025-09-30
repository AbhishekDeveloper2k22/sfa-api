from bson import ObjectId
from typing import Optional, Dict, Any
from trust_rewards.database import client1
from trust_rewards.utils.common import DateUtils, AuditUtils


class RecentActivityLogger:
    """Utility to log recent activities for skilled workers.

    Creates documents in `recent_activity` collection with a consistent schema so
    the app can render the worker's recent activity feed.
    """

    @staticmethod
    def _collection():
        db = client1['trust_rewards']
        return db['recent_activity']

    @staticmethod
    def log_activity(
        *,
        worker_id: str,
        title: str,
        points_change: int,
        activity_type: str,
        description: Optional[str] = "",
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert a recent activity record.

        - points_change: positive for credit, negative for debit
        - activity_type: e.g. COUPON_SCAN, GIFT_REDEMPTION_REQUEST, REDEMPTION_CANCELLED, REDEMPTION_REDEEMED
        - metadata: any extra key/values to store
        """
        try:
            now_dt = DateUtils.get_current_datetime()
            doc = {
                "activity_id": f"ACT_{ObjectId()}",
                "worker_id": worker_id,
                "title": title,
                "description": description or "",
                "points_change": int(points_change or 0),
                "activity_type": activity_type,
                "reference_id": reference_id or "",
                "reference_type": reference_type or "",
                "created_at": now_dt,
                "created_date": DateUtils.get_current_date(),
                "created_time": DateUtils.get_current_time(),
                **AuditUtils.build_create_meta(worker_id),
            }

            if metadata:
                # Avoid overwriting core fields
                for k, v in metadata.items():
                    if k not in doc:
                        doc[k] = v

            RecentActivityLogger._collection().insert_one(doc)
        except Exception as e:
            # Non-blocking: logging failure should not affect main flows
            print(f"RecentActivityLogger error: {str(e)}")


