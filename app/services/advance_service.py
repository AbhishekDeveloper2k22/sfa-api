from datetime import datetime
from typing import Any, Dict, Optional, List

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class AdvanceError(Exception):
    """Domain error for advance operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class AdvanceService:
    """Service layer for tenant-scoped salary advance module."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Advance Request APIs
    # ------------------------------------------------------------------
    def get_advances(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match_query = {"tenant_id": tenant_id}
        
        if query_params.get("status"):
            match_query["status"] = query_params["status"]
            
        if query_params.get("employee_id"):
            match_query["employee_id"] = query_params["employee_id"]

        # Search logic (q)
        search = query_params.get("search")
        
        pipeline = []
        pipeline.append({"$match": match_query})
        
        # Lookup employee
        pipeline.append({
            "$lookup": {
                "from": "users",
                "localField": "employee_id",
                "foreignField": "_id",
                "as": "employee_data"
            }
        })
        pipeline.append({"$unwind": {"path": "$employee_data", "preserveNullAndEmptyArrays": True}})
        
        if query_params.get("department"):
             pipeline.append({"$match": {"employee_data.department": query_params["department"]}})

        if search:
             pipeline.append({
                 "$match": {
                     "$or": [
                         {"employee_data.display_name": {"$regex": search, "$options": "i"}},
                         {"employee_data.employee_code": {"$regex": search, "$options": "i"}},
                         # Also search by Advance ID if stored? Docs example ADV001. 
                         # Usually stored as `code` or `id` field.
                     ]
                 }
             })

        pipeline.append({"$sort": {"requested_at": -1}})
        
        # Stats Aggregation (complex in one go, simplified here)
        # We'll just fetch data first
        
        raw_results = list(db["advances"].aggregate(pipeline))
        
        data = []
        for r in raw_results:
             data.append(self._format_advance(r))
             
        # Calculate stats
        all_docs = list(db["advances"].find({"tenant_id": tenant_id}))
        stats = {
            "total": len(all_docs),
            "pending": len([d for d in all_docs if d.get("status") == "pending"]),
            "approved": len([d for d in all_docs if d.get("status") == "approved"]),
            "active": len([d for d in all_docs if d.get("status") == "active"]),
            "closed": len([d for d in all_docs if d.get("status") == "closed"]),
            "rejected": len([d for d in all_docs if d.get("status") == "rejected"]),
            "total_disbursed": sum([d.get("amount", 0) for d in all_docs if d.get("status") in ["active", "closed"]]),
            "total_recovered": sum([d.get("total_repaid", 0) for d in all_docs]),
            "total_outstanding": sum([d.get("remaining_balance", 0) for d in all_docs]),
            "pending_amount": sum([d.get("amount", 0) for d in all_docs if d.get("status") == "pending"])
        }

        return {"data": data, "stats": stats}

    def get_advance_by_id(self, tenant_id: str, advance_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        # Try finding by _id or custom ID field? Docs use "ADV001"
        # Assuming _id for simplicity unless custom logic needed.
        # But wait, docs say "Search by advance ID... ADV001"
        # I'll try to match _id first, then maybe string id
        
        doc = None
        try:
             doc = db["advances"].find_one({"_id": ObjectId(advance_id), "tenant_id": tenant_id})
        except:
             pass
        
        if not doc:
             # Try string id if I implement custom ID generation, but for now assuming ObjectId passed or 404
             raise AdvanceError("Advance not found", status_code=404, code="NOT_FOUND")
             
        # Fetch employee
        if doc.get("employee_id"):
             emp = self._get_user(db, doc["employee_id"])
             doc["employee_data"] = emp
             
        return self._format_advance(doc)

    def create_advance(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        
        amount = payload.get("amount")
        employee_id = self._require(payload.get("employee_id"), "employee_id")
        reason = self._require(payload.get("reason"), "reason")
        
        # Validation
        if amount <= 0:
            raise AdvanceError("Amount must be positive")
            
        # Check active advance
        active = db["advances"].find_one({
            "tenant_id": tenant_id,
            "employee_id": employee_id,
            "status": {"$in": ["pending", "approved", "active"]}
        })
        if active:
             raise AdvanceError("Employee already has an active advance request")

        doc = {
            "tenant_id": tenant_id,
            "employee_id": employee_id,
            "amount": amount,
            "reason": reason,
            "reason_details": payload.get("reason_details"),
            "status": "pending",
            "requested_at": datetime.utcnow(),
            "approved_at": None,
            "disbursed_at": None,
            "total_repaid": 0,
            "remaining_balance": amount,
            "repayment_history": []
        }
        
        res = db["advances"].insert_one(doc)
        
        # Return formatted
        # Need to fetch again to get formatted struct or just construct it
        doc["_id"] = res.inserted_id
        emp = self._get_user(db, employee_id)
        doc["employee_data"] = emp
        return self._format_advance(doc)

    def approve_advance(self, tenant_id: str, id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        approver_name = payload.get("approver_name", "Admin") # In real app, fetch from actor user
        
        doc = self._get_doc_or_404(db["advances"], id)
        if doc["status"] != "pending":
             raise AdvanceError("Only pending advances can be approved")
             
        updates = {
            "status": "approved",
            "approved_at": datetime.utcnow(),
            "approved_by": approver_name
        }
        
        db["advances"].update_one({"_id": doc["_id"]}, {"$set": updates})
        
        return {
            "id": str(doc["_id"]),
            "status": "approved",
            "approved_at": updates["approved_at"],
            "approved_by": approver_name
        }

    def reject_advance(self, tenant_id: str, id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        reason = self._require(payload.get("reason"), "reason")
        rejecter_name = payload.get("rejecter_name", "Admin")
        
        doc = self._get_doc_or_404(db["advances"], id)
        if doc["status"] != "pending":
             raise AdvanceError("Only pending advances can be rejected")
             
        updates = {
            "status": "rejected",
            "rejected_at": datetime.utcnow(),
            "rejected_by": rejecter_name,
            "rejection_reason": reason
        }
        
        db["advances"].update_one({"_id": doc["_id"]}, {"$set": updates})
        
        return {
            "id": str(doc["_id"]),
            "status": "rejected",
            "rejected_at": updates["rejected_at"],
            "rejected_by": rejecter_name,
            "rejection_reason": reason
        }

    def disburse_advance(self, tenant_id: str, id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        mode = payload.get("disbursement_mode", "Bank Transfer")
        
        doc = self._get_doc_or_404(db["advances"], id)
        if doc["status"] != "approved":
             raise AdvanceError("Only approved advances can be disbursed")
             
        updates = {
            "status": "active",
            "disbursed_at": datetime.utcnow(),
            "disbursement_mode": mode
        }
        
        db["advances"].update_one({"_id": doc["_id"]}, {"$set": updates})
        
        return {
             "id": str(doc["_id"]),
             "status": "active",
             "disbursed_at": updates["disbursed_at"],
             "disbursement_mode": mode
        }

    def record_repayment(self, tenant_id: str, id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        amount = payload.get("amount", 0)
        if amount <= 0:
             raise AdvanceError("Amount must be positive")
             
        doc = self._get_doc_or_404(db["advances"], id)
        if doc["status"] != "active":
             raise AdvanceError("Advance is not active")
             
        if amount > doc["remaining_balance"]:
             raise AdvanceError("Repayment amount cannot exceed remaining balance")
             
        # Create repayment entry
        repayment = {
            "id": f"REP{int(datetime.utcnow().timestamp())}", # Simple ID gen
            "date": payload.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
            "amount": amount,
            "mode": payload.get("mode", "Cash"),
            "remarks": payload.get("remarks"),
            "recorded_by": payload.get("recorded_by", "Admin")
        }
        
        new_total_repaid = doc.get("total_repaid", 0) + amount
        new_balance = doc["remaining_balance"] - amount
        new_status = "active"
        closed_at = None
        
        if new_balance <= 0:
             new_status = "closed"
             closed_at = datetime.utcnow()
             new_balance = 0 # Safety
             
        updates = {
            "total_repaid": new_total_repaid,
            "remaining_balance": new_balance,
            "status": new_status,
            "closed_at": closed_at
        }
        
        db["advances"].update_one(
            {"_id": doc["_id"]},
            {
                "$set": updates,
                "$push": {"repayment_history": repayment}
            }
        )
        
        # Return updated structure (simplified)
        return {
            "id": str(doc["_id"]),
            "status": new_status,
            "total_repaid": new_total_repaid,
            "remaining_balance": new_balance,
            "closed_at": closed_at,
            "repayment_history": doc.get("repayment_history", []) + [repayment]
        }

    # ------------------------------------------------------------------
    # 2. Reference Data APIs
    # ------------------------------------------------------------------
    def get_employees(self, tenant_id: str) -> List[Dict[str, Any]]:
        db = self._get_db(tenant_id)
        users = db["users"].find({"tenant_id": tenant_id, "status": "active"})
        return [self._sanitize_user_full(u) for u in users]

    def get_reasons(self, tenant_id: str) -> List[str]:
        return [
          "Medical Emergency",
          "Wedding Expenses",
          "Home Renovation",
          "Education Fees",
          "Family Emergency",
          "Vehicle Purchase",
          "Festival Expenses",
          "Debt Consolidation",
          "Other Personal Needs"
        ]

    def get_payment_modes(self, tenant_id: str) -> List[str]:
        return [
          "Salary Deduction",
          "Cash",
          "UPI Transfer",
          "Bank Transfer",
          "Cheque"
        ]

    def get_departments(self, tenant_id: str) -> List[str]:
        db = self._get_db(tenant_id)
        depts = db["tenant_departments"].find({"tenant_id": tenant_id, "del": 0})
        return [d["name"] for d in depts]

    # ------------------------------------------------------------------
    # 3. Validation APIs
    # ------------------------------------------------------------------
    def check_active_advance(self, tenant_id: str, employee_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        active = db["advances"].find_one({
            "tenant_id": tenant_id,
            "employee_id": employee_id,
            "status": {"$in": ["pending", "approved", "active"]}
        })
        
        if active:
             return {
                 "hasActive": True,
                 "advance": {
                     "id": str(active["_id"]),
                     "status": active["status"],
                     "amount": active["amount"],
                     "remaining_balance": active.get("remaining_balance")
                 }
             }
        
        return {"hasActive": False}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_db(self, tenant_id: str):
        return self.client[tenant_id]

    def _get_doc_or_404(self, collection, doc_id: str) -> Dict[str, Any]:
        try:
            oid = ObjectId(doc_id)
        except:
             raise AdvanceError("Not found", status_code=404, code="NOT_FOUND")
        doc = collection.find_one({"_id": oid})
        if not doc:
             raise AdvanceError("Not found", status_code=404, code="NOT_FOUND")
        return doc
        
    def _require(self, value, name):
        if not value:
            raise AdvanceError(f"{name} is required")
        return value

    def _get_user(self, db, user_id):
        try:
            return db["users"].find_one({"_id": ObjectId(user_id)})
        except:
            return None

    def _sanitize_user(self, user):
        if not user: return {}
        return {
            "id": str(user.get("_id")),
            "name": user.get("display_name"), # Docs say 'name'
            "employee_code": user.get("employee_code"),
            "department": user.get("department"),
            "designation": user.get("designation"),
            "salary": user.get("salary", 0) # Assumed
        }
        
    def _sanitize_user_full(self, user):
        return self._sanitize_user(user)

    def _format_advance(self, doc):
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        if "employee_data" in doc:
             doc["employee"] = self._sanitize_user(doc.pop("employee_data"))
        return doc
