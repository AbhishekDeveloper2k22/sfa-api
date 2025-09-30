from bson import ObjectId
from typing import Optional
from trust_rewards.database import client1
from trust_rewards.utils.common import DateUtils, AuditUtils


class TransactionLogger:
    """Shared transaction ledger insertion utility.

    Ensures a single schema and consistent timestamps across services.
    """

    @staticmethod
    def _collection():
        db = client1['trust_rewards']
        return db['transaction_ledger']

    @staticmethod
    def record(
        *,
        worker_id: str,
        transaction_type: str,
        amount: int,
        description: str,
        previous_balance: int,
        new_balance: int,
        reference_id: Optional[str] = "",
        reference_type: Optional[str] = "",
        redemption_id: Optional[str] = "",
        batch_number: Optional[str] = "",
        created_by: Optional[str] = None,
    ) -> None:
        try:
            doc = {
                "transaction_id": f"TXN_{ObjectId()}",
                "worker_id": worker_id,
                "transaction_type": transaction_type,
                "amount": int(amount),
                "description": description,
                "reference_id": reference_id or "",
                "reference_type": reference_type or "",
                "batch_number": batch_number or "",
                "redemption_id": redemption_id or "",
                "previous_balance": int(previous_balance),
                "new_balance": int(new_balance),
                "transaction_date": DateUtils.get_current_date(),
                "transaction_time": DateUtils.get_current_time(),
                "transaction_datetime": DateUtils.get_current_datetime(),
                "status": "completed",
                **AuditUtils.build_create_meta(created_by or worker_id),
            }

            TransactionLogger._collection().insert_one(doc)
        except Exception as e:
            print(f"TransactionLogger error: {str(e)}")


