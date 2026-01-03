from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import uuid

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class ExpenseError(Exception):
    """Domain error for expense operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class ExpenseService:
    """Service layer for tenant-scoped expense & travel module."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Expense Categories
    # ------------------------------------------------------------------
    def get_categories(self, tenant_id: str) -> Dict[str, Any]:
        # Return hardcoded or db fetched categories
        # For MVP, returning hardcoded as per docs example or mock db
        # I will fetch from DB if exists, else return defaults
        db = self._get_db(tenant_id)
        # Seed or fetch
        cats = list(db["expense_categories"].find({"tenant_id": tenant_id}))
        if not cats:
             # Default categories
             defaults = [
                 {"code": "TRAVEL_TAXI", "name": "Taxi/Cab", "icon": "🚕", "requires_receipt": True, "daily_limit": 2000, "per_claim_limit": 5000},
                 {"code": "TRAVEL_FLIGHT", "name": "Flight", "icon": "✈️", "requires_receipt": True, "daily_limit": None, "per_claim_limit": None},
                 {"code": "FOOD", "name": "Food", "icon": "🍔", "requires_receipt": True, "daily_limit": 1000, "per_claim_limit": 1000},
                 {"code": "HOTEL", "name": "Hotel", "icon": "🏨", "requires_receipt": True, "daily_limit": 5000, "per_claim_limit": 20000},
                 {"code": "MISC", "name": "Miscellaneous", "icon": "📝", "requires_receipt": False, "daily_limit": 500, "per_claim_limit": 500}
             ]
             return {"data": defaults}
        return {"data": [self._sanitize(c) for c in cats]}

    # ------------------------------------------------------------------
    # 2. Expense Claims
    # ------------------------------------------------------------------
    def get_claims(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        if query_params.get("status"): match["status"] = query_params["status"]
        if query_params.get("employee_id"): match["employee_id"] = query_params["employee_id"]
        # approver logic? If approver=true, maybe filter by those waiting approval? 
        # For now simple filter.

        data = list(db["expense_claims"].find(match).sort("created_at", -1))
        
        # Calculate stats (mock calculation on full set or aggregated query)
        # Using aggregation for accurate stats
        pipeline = [
            {"$match": {"tenant_id": tenant_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}, "amount": {"$sum": "$total_amount"}}}
        ]
        stats_raw = list(db["expense_claims"].aggregate(pipeline))
        stats = {
            "total": sum(s["count"] for s in stats_raw),
            "total_amount": sum(s["amount"] for s in stats_raw),
            "draft": 0, "pending": 0, "approved": 0, "rejected": 0, "settled": 0, "pending_amount": 0
        }
        for s in stats_raw:
            stats[s["_id"]] = s["count"]
            if s["_id"] == "pending": stats["pending_amount"] = s["amount"]

        # Join employee data for list
        # Optimization: Do it in aggregation or loop with cache. Loop is fine for small scale.
        results = []
        for d in data:
            results.append(self._enrich_claim(tenant_id, d))

        return {"data": results, "stats": stats}

    def get_claim_by_id(self, tenant_id: str, claim_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["expense_claims"].find_one({"id": claim_id, "tenant_id": tenant_id})
        if not doc:
             # Try _id
             try:
                doc = db["expense_claims"].find_one({"_id": ObjectId(claim_id), "tenant_id": tenant_id})
             except:
                pass
        if not doc:
            raise ExpenseError("Expense claim not found", status_code=404)
        return {"data": self._enrich_claim(tenant_id, doc)}

    def create_claim(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        # Validation
        self._require(payload.get("employee_id"), "employee_id")
        
        claim_id = f"exp_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.pop("submit", None)
        
        doc.update({
            "id": claim_id,
            "tenant_id": tenant_id,
            "status": "pending" if payload.get("submit") else "draft",
            "created_at": datetime.utcnow(),
            "submitted_at": datetime.utcnow() if payload.get("submit") else None,
            "approved_at": None,
            "rejection_reason": None,
            "trip_id": payload.get("trip_id")
        })
        
        db["expense_claims"].insert_one(doc)
        return {"data": self._enrich_claim(tenant_id, doc)}

    def update_claim(self, tenant_id: str, claim_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        # Fetch existing
        curr = self.get_claim_by_id(tenant_id, claim_id)["data"]
        if curr["status"] != "draft":
             raise ExpenseError("Only draft claims can be updated")
             
        updates = payload.copy()
        db["expense_claims"].update_one({"id": curr["id"]}, {"$set": updates})
        return self.get_claim_by_id(tenant_id, claim_id)

    def submit_claim(self, tenant_id: str, claim_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self.get_claim_by_id(tenant_id, claim_id)["data"]
        if curr["status"] != "draft":
             raise ExpenseError("Only draft claims can be submitted")
             
        updates = {
            "status": "pending",
            "submitted_at": datetime.utcnow()
        }
        db["expense_claims"].update_one({"id": curr["id"]}, {"$set": updates})
        return {"data": {"id": curr["id"], "status": "pending", "submitted_at": updates["submitted_at"]}}

    def perform_claim_action(self, tenant_id: str, claim_id: str, action: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self.get_claim_by_id(tenant_id, claim_id)["data"]
        
        updates = {}
        if action == "approve":
             updates = {"status": "approved", "approved_at": datetime.utcnow(), "approved_by": actor}
        elif action == "reject":
             self._require(payload.get("reason"), "reason")
             updates = {"status": "rejected", "rejection_reason": payload["reason"]}
        elif action == "request_changes":
             self._require(payload.get("comments"), "comments")
             updates = {"status": "changes_requested", "change_comments": payload["comments"]}
        elif action == "settle":
             if curr["status"] != "approved": raise ExpenseError("Only approved claims can be settled")
             updates = {"status": "settled", "settled_at": datetime.utcnow()}
        else:
             raise ExpenseError("Invalid action")
             
        db["expense_claims"].update_one({"id": curr["id"]}, {"$set": updates})
        
        res_data = {"id": curr["id"], "status": updates["status"]}
        if "approved_at" in updates: res_data["approved_at"] = updates["approved_at"]
        if "settled_at" in updates: res_data["settled_at"] = updates["settled_at"]
        
        return {"data": res_data}

    def preview_claim(self, tenant_id: str, claim_id: str) -> Dict[str, Any]:
        # Mock validation logic
        curr = self.get_claim_by_id(tenant_id, claim_id)["data"]
        return {
            "data": {
                "expense": curr,
                "warnings": [],
                "blockers": [],
                "can_submit": True,
                "reimbursable_amount": curr.get("total_amount", 0),
                "tax_total": 0
            }
        }

    # ------------------------------------------------------------------
    # 3. Travel Requests
    # ------------------------------------------------------------------
    def get_travel_requests(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        if query_params.get("status"): match["status"] = query_params["status"]
        if query_params.get("employee_id"): match["employee_id"] = query_params["employee_id"]
        
        data = list(db["travel_requests"].find(match).sort("created_at", -1))
        results = []
        for d in data:
            results.append(self._enrich_claim(tenant_id, d)) # Reusing enrich logic as structure is similar for employee
        return {"data": results}

    def get_travel_request(self, tenant_id: str, request_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["travel_requests"].find_one({"id": request_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["travel_requests"].find_one({"_id": ObjectId(request_id), "tenant_id": tenant_id})
             except:
                 pass
        if not doc:
             raise ExpenseError("Travel request not found", status_code=404)
        return {"data": self._enrich_claim(tenant_id, doc)}

    def create_travel_request(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        self._require(payload.get("employee_id"), "employee_id")
        
        req_id = f"tr_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.update({
            "id": req_id,
            "tenant_id": tenant_id,
            "status": "pending",
            "created_at": datetime.utcnow()
        })
        db["travel_requests"].insert_one(doc)
        return {"data": self._enrich_claim(tenant_id, doc)}

    def perform_travel_action(self, tenant_id: str, request_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self.get_travel_request(tenant_id, request_id)["data"]
        
        updates = {}
        if action == "approve":
             updates = {"status": "approved", "approved_at": datetime.utcnow()}
        elif action == "reject":
             self._require(payload.get("reason"), "reason")
             updates = {"status": "rejected", "rejection_reason": payload["reason"]}
        else:
             raise ExpenseError("Invalid action")
             
        db["travel_requests"].update_one({"id": curr["id"]}, {"$set": updates})
        
        res = {"id": curr["id"], "status": updates["status"]}
        if "approved_at" in updates: res["approved_at"] = updates["approved_at"]
        if "rejection_reason" in updates: res["rejection_reason"] = updates["rejection_reason"]
        return {"data": res}
        
    # ------------------------------------------------------------------
    # 4. Advances
    # ------------------------------------------------------------------
    def get_advances(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        if query_params.get("status"): match["status"] = query_params["status"]
        if query_params.get("employee_id"): match["employee_id"] = query_params["employee_id"]
        
        data = list(db["expense_advances"].find(match))
        results = [self._enrich_claim(tenant_id, d) for d in data]
        return {"data": results}

    def create_advance(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        self._require(payload.get("employee_id"), "employee_id")
        
        adv_id = f"adv_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.update({
            "id": adv_id,
            "tenant_id": tenant_id,
            "status": "pending",
            "created_at": datetime.utcnow()
        })
        db["expense_advances"].insert_one(doc)
        return {"data": self._enrich_claim(tenant_id, doc)}

    def disburse_advance(self, tenant_id: str, advance_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["expense_advances"].find_one({"id": advance_id, "tenant_id": tenant_id})
        if not doc: raise ExpenseError("Advance not found", 404)
        
        if doc["status"] != "pending": raise ExpenseError("Only pending advances can be disbursed")
        
        updates = {"status": "disbursed", "disbursed_at": datetime.utcnow()}
        db["expense_advances"].update_one({"_id": doc["_id"]}, {"$set": updates})
        return {"data": {"id": doc["id"], "status": "disbursed", "disbursed_at": updates["disbursed_at"]}}

    # ------------------------------------------------------------------
    # 5. Reports & Analytics
    # ------------------------------------------------------------------
    def get_ledger(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        # Combine advances and confirmed expenses
        db = self._get_db(tenant_id)
        q_adv = {"tenant_id": tenant_id}
        q_exp = {"tenant_id": tenant_id, "status": "settled"}
        
        if query_params.get("employee_id"):
             q_adv["employee_id"] = query_params["employee_id"]
             q_exp["employee_id"] = query_params["employee_id"]
             
        advances = list(db["expense_advances"].find(q_adv))
        expenses = list(db["expense_claims"].find(q_exp))
        
        ledger = []
        for a in advances:
            a = self._enrich_claim(tenant_id, a)
            ledger.append({
                "id": a["id"], "type": "advance", "employee": a.get("employee"),
                "amount": a.get("amount", 0), "status": a["status"], "date": a["created_at"], "description": a.get("purpose")
            })
        for e in expenses:
            e = self._enrich_claim(tenant_id, e)
            ledger.append({
                "id": e["id"], "type": "reimbursement", "employee": e.get("employee"),
                "amount": e.get("total_amount", 0), "status": e["status"], "date": e.get("settled_at"), "description": e.get("claim_title")
            })
            
        ledger.sort(key=lambda x: x["date"] or datetime.min, reverse=True)
        return {"data": ledger}

    def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        # Delegated to aggregation in get_claims part, here global stats
        db = self._get_db(tenant_id)
        return {"data": {
            "total_claims": db["expense_claims"].count_documents({"tenant_id": tenant_id}),
            "pending_claims": db["expense_claims"].count_documents({"tenant_id": tenant_id, "status": "pending"}),
            "total_travel_requests": db["travel_requests"].count_documents({"tenant_id": tenant_id}),
            "pending_travel": db["travel_requests"].count_documents({"tenant_id": tenant_id, "status": "pending"}),
            "advances_outstanding": 0, # To be calc
            "settled_this_month": 0
        }}

    def export_expenses(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        return {"data": {"download_url": f"#export_exp_{uuid.uuid4().hex}", "filename": "expenses.csv"}}
        
    def extract_receipt(self, tenant_id: str, upload_id: str) -> Dict[str, Any]:
        return {"data": {
            "upload_id": upload_id, "status": "completed",
            "extracted": {"vendor": "Uber", "amount": 100, "date": "2024-01-01", "tax_amount": 5},
            "confidence": 0.95
        }}

    def get_filter_options(self, tenant_id: str) -> Dict[str, Any]:
        return {"data": {
            "statuses": [{"value": "pending", "label": "Pending"}, {"value": "approved", "label": "Approved"}],
            "categories": [{"value": "TRAVEL", "label": "Travel"}],
            "employees": [] # Populate if needed
        }}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _enrich_claim(self, tenant_id, doc):
        """Add employee details to claim."""
        db = self._get_db(tenant_id)
        d = self._sanitize(doc)
        if "employee_id" in d:
             emp = db["users"].find_one({"_id": ObjectId(d["employee_id"])}) or db["users"].find_one({"id": d["employee_id"]})
             if emp:
                 d["employee"] = {
                     "id": str(emp["_id"]),
                     "name": emp.get("display_name"),
                     "employee_code": emp.get("employee_code"),
                     "department": emp.get("department"),
                     "email": emp.get("email")
                 }
        return d

    def _get_db(self, tenant_id: str):
        return self.client[tenant_id]

    def _sanitize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(doc)
        if "_id" in doc:
             doc["id"] = str(doc.pop("_id"))
        return doc

    def _require(self, value, name):
        if not value:
            raise ExpenseError(f"{name} is required")
        return value
