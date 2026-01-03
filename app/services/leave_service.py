from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class LeaveError(Exception):
    """Domain error for leave operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class LeaveService:
    """Service layer for tenant-scoped leave module."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Leave Types APIs
    # ------------------------------------------------------------------
    def get_leave_types(self, tenant_id: str) -> List[Dict[str, Any]]:
        db = self._get_db(tenant_id)
        # Assuming leave_types are stored in a collection or config.
        # Based on docs, it returns a list without separate ID in example, but usually they have IDs or unique codes.
        # Let's assume a collection 'leave_types'.
        docs = db["leave_types"].find({"tenant_id": tenant_id, "del": {"$ne": 1}})
        return [self._sanitize(d) for d in docs]

    # ------------------------------------------------------------------
    # 2. Leave Request APIs
    # ------------------------------------------------------------------
    def get_leave_requests(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match_query = {"tenant_id": tenant_id}
        
        if query_params.get("applicant_id"):
            match_query["applicant_id"] = query_params["applicant_id"]
            
        if query_params.get("status"):
            statuses = query_params["status"].split(",")
            match_query["status"] = {"$in": statuses}
            
        if query_params.get("leave_type"):
            match_query["leave_type"] = query_params["leave_type"]
            
        if query_params.get("from") and query_params.get("to"):
            # Overlap logic or range check. Docs say "Filter from" and "Filter to".
            # Usually means requests overlapping this range.
            # Request: [start, end], Filter: [from, to]
            # Overlap if: Start <= to AND End >= from
            match_query["$and"] = [
                {"from_date": {"$lte": query_params["to"]}},
                {"to_date": {"$gte": query_params["from"]}}
            ]
        elif query_params.get("from"):
             match_query["from_date"] = {"$gte": query_params["from"]}
        elif query_params.get("to"):
             match_query["to_date"] = {"$lte": query_params["to"]}

        if query_params.get("department"):
             # Requires lookup on applicant. 
             # We will do aggregation for that.
             pass

        page = int(query_params.get("page", 1))
        page_size = int(query_params.get("page_size", 25))
        skip = (page - 1) * page_size
        
        pipeline = []
        pipeline.append({"$match": match_query})
        
        # Join applicant
        pipeline.append({
            "$lookup": {
                "from": "users",
                "localField": "applicant_id",
                "foreignField": "_id",
                "as": "applicant_data"
            }
        })
        pipeline.append({"$unwind": {"path": "$applicant_data", "preserveNullAndEmptyArrays": True}})

        if query_params.get("department"):
            pipeline.append({"$match": {"applicant_data.department": query_params["department"]}})
        
        if query_params.get("q"):
            q = query_params["q"]
            pipeline.append({
                 "$match": {
                     "$or": [
                         {"applicant_data.display_name": {"$regex": q, "$options": "i"}},
                         {"applicant_data.employee_code": {"$regex": q, "$options": "i"}}
                     ]
                 }
             })

        pipeline.append({"$sort": {"created_at": -1}})
        
        facet_stage = {
            "$facet": {
                "metadata": [{"$count": "total"}],
                "data": [{"$skip": skip}, {"$limit": page_size}]
            }
        }
        pipeline.append(facet_stage)
        
        result = list(db["leave_requests"].aggregate(pipeline))[0]
        
        data = []
        for doc in result["data"]:
            clean_doc = self._sanitize(doc)
            # Cleanup applicant
            app_data = doc.get("applicant_data", {})
            if app_data:
                clean_doc["applicant"] = self._sanitize_user(app_data)
            del clean_doc["applicant_data"]
            data.append(clean_doc)
            
        total = result["metadata"][0]["total"] if result["metadata"] else 0
        
        return {
            "data": data,
            "meta": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if page_size else 0
            }
        }

    def get_leave_request(self, tenant_id: str, request_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = self._get_doc_or_404(db["leave_requests"], request_id)
        
        # Populate applicant and approvals if needed
        # Simple implementation: fetch user
        if doc.get("applicant_id"):
            user = self._get_user(db, doc["applicant_id"])
            doc["applicant"] = self._sanitize_user(user)
        
        return self._sanitize(doc)

    def apply_leave(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        
        # Validation
        self._require(payload.get("leave_type"), "leave_type")
        self._require(payload.get("from_date"), "from_date")
        self._require(payload.get("to_date"), "to_date")
        self._require(payload.get("reason"), "reason")
        
        applicant_id = payload.get("applicant_id")
        # If no applicant_id provided, maybe use actor? 
        # But payload usually has it or we infer. Assuming payload has it or caller handles it.
        # Ideally we should verify if actor == applicant or actor is admin/manager.
        
        doc = payload.copy()
        doc["tenant_id"] = tenant_id
        doc["status"] = "pending"
        audit = build_audit_fields(prefix="created", by=actor)
        doc.update(audit)
        doc["updated_at"] = audit["created_at"]
        
        # Calculate duration? Assuming frontend sends it or we calc it.
        # Doc response shows "duration_days".
        
        res = db["leave_requests"].insert_one(doc)
        
        return {
            "id": str(res.inserted_id),
            "status": "pending",
            "duration_days": doc.get("duration", 0), # placeholder
            "message": "Leave request created and routed for approval."
        }

    def leave_action(self, tenant_id: str, request_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        action = payload.get("action")
        comment = payload.get("comment")
        
        if action not in ["approve", "reject", "cancel", "forward", "request_changes"]:
            raise LeaveError("Invalid action")
            
        req = self._get_doc_or_404(db["leave_requests"], request_id)
        
        new_status = req["status"]
        if action == "approve":
            new_status = "approved"
        elif action == "reject":
            new_status = "rejected"
        elif action == "cancel":
            new_status = "cancelled"
            
        updates = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        if action == "approve":
            updates["approved_at"] = datetime.utcnow()
        elif action == "reject":
            updates["rejected_at"] = datetime.utcnow()
            
        # Add to approvals list
        approval_entry = {
            "id": f"apr_{ObjectId()}",
            "approver_id": actor, # In real sys, fetch user details
            "action": new_status,
            "comment": comment,
            "acted_at": datetime.utcnow()
        }
        
        db["leave_requests"].update_one(
            {"_id": req["_id"]},
            {
                "$set": updates,
                "$push": {"approvals": approval_entry}
            }
        )
        
        return {
            "id": request_id,
            "status": new_status,
            "message": f"Leave request {new_status} successfully"
        }

    def bulk_approve(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        ids = payload.get("ids", [])
        comment = payload.get("comment")
        
        results = []
        success_count = 0
        
        for rid in ids:
            try:
                # Reuse logic or direct update
                self.leave_action(tenant_id, rid, {"action": "approve", "comment": comment}, actor)
                results.append({"id": rid, "success": True})
                success_count += 1
            except Exception as e:
                # Log error
                results.append({"id": rid, "success": False, "error": str(e)})
                
        return {
            "success": success_count,
            "failed": len(ids) - success_count,
            "results": results
        }

    # ------------------------------------------------------------------
    # 3. Leave Balance APIs
    # ------------------------------------------------------------------
    def get_leave_balances(self, tenant_id: str, employee_id: str) -> List[Dict[str, Any]]:
        db = self._get_db(tenant_id)
        # Assuming aggregation or simple fetch.
        # "leave_balances" collection or inside user doc?
        # Docs imply API: /employees/:id/leave-balances.
        # Let's assume a collection `leave_balances` where {employee_id, balances: [...]}.
        
        doc = db["leave_balances"].find_one({"tenant_id": tenant_id, "employee_id": employee_id})
        if not doc:
            # Return defaults or empty
             return []
        
        return doc.get("balances", [])

    def get_leave_history(self, tenant_id: str, employee_id: str, year: Optional[int] = None) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        # Fetch requests
        # Fetch transactions
        
        requests = list(db["leave_requests"].find({
            "tenant_id": tenant_id, 
            "applicant_id": employee_id
            # Filter by year if needed based on from_date
        }).sort("created_at", -1))
        
        transactions = list(db["leave_transactions"].find({
            "tenant_id": tenant_id,
            "employee_id": employee_id
        }).sort("date", -1))
        
        return {
            "requests": [self._sanitize(r) for r in requests],
            "transactions": [self._sanitize(t) for t in transactions],
            "year": year or datetime.now().year
        }

    def adjust_balance(self, tenant_id: str, employee_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        leave_type = self._require(payload.get("leave_type"), "leave_type")
        delta = payload.get("delta", 0)
        
        # Update balance
        # This requires atomic update in `leave_balances`
        
        # 1. Ensure document exists
        db["leave_balances"].update_one(
            {"tenant_id": tenant_id, "employee_id": employee_id},
            {"$setOnInsert": {"balances": []}},
            upsert=True
        )
        
        # 2. Check if leave type exists in balances, if not add it.
        # This is complex in mongo shell, simplified python logic:
        bal_doc = db["leave_balances"].find_one({"tenant_id": tenant_id, "employee_id": employee_id})
        balances = bal_doc.get("balances", [])
        
        found = False
        new_balance = 0
        for b in balances:
            if b["leave_type"] == leave_type:
                b["available"] = b.get("available", 0) + delta
                # Update other fields like 'adjusted' if tracked
                b["adjusted"] = b.get("adjusted", 0) + delta
                new_balance = b["available"]
                found = True
                break
        
        if not found:
             # Add new type entry
             new_balance = delta
             balances.append({
                 "leave_type": leave_type,
                 "opening": 0,
                 "accrued": 0,
                 "taken": 0,
                 "pending": 0,
                 "adjusted": delta,
                 "available": delta
             })
             
        db["leave_balances"].update_one(
            {"_id": bal_doc["_id"]},
            {"$set": {"balances": balances}}
        )
        
        # Log transaction
        db["leave_transactions"].insert_one({
            "tenant_id": tenant_id,
            "employee_id": employee_id,
            "type": "adjustment",
            "leave_type": leave_type,
            "delta": delta,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "reason": payload.get("reason"),
            "created_by": actor,
            "created_at": datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": f"Balance adjusted by {delta} for {leave_type}",
            "new_balance": new_balance
        }

    # ------------------------------------------------------------------
    # 4. Holiday APIs
    # ------------------------------------------------------------------
    def get_holidays(self, tenant_id: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        db = self._get_db(tenant_id)
        query = {"tenant_id": tenant_id}
        if year:
            # Assuming date is YYYY-MM-DD
            query["date"] = {"$regex": f"^{year}"}
            
        docs = db["holidays"].find(query).sort("date", 1)
        return [self._sanitize(d) for d in docs]

    def get_blackout_dates(self, tenant_id: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        db = self._get_db(tenant_id)
        query = {"tenant_id": tenant_id}
        docs = db["leave_blackout_dates"].find(query)
        return [self._sanitize(d) for d in docs]

    # ------------------------------------------------------------------
    # 5. Leave Policy APIs
    # ------------------------------------------------------------------
    def get_leave_policies(self, tenant_id: str) -> List[Dict[str, Any]]:
        db = self._get_db(tenant_id)
        docs = db["leave_policies"].find({"tenant_id": tenant_id}).sort("created_at", -1)
        return [self._sanitize(d) for d in docs]

    def get_leave_policy(self, tenant_id: str, policy_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = self._get_doc_or_404(db["leave_policies"], policy_id)
        return self._sanitize(doc)

    def create_leave_policy(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = payload.copy()
        doc["tenant_id"] = tenant_id
        doc.update(build_audit_fields(prefix="created", by=actor))
        res = db["leave_policies"].insert_one(doc)
        doc["id"] = str(res.inserted_id)
        del doc["_id"]
        return doc

    # ------------------------------------------------------------------
    # 6. Calendar APIs
    # ------------------------------------------------------------------
    def get_calendar(self, tenant_id: str, employee_id: Optional[str], month: int, year: int) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        # Calculate from/to dates for the month
        from_date = f"{year}-{month:02d}-01"
        # simple end date approx
        to_date = f"{year}-{month:02d}-31"
        
        # Fetch leaves
        query = {
            "tenant_id": tenant_id,
            "status": "approved",
            "$or": [
                {"from_date": {"$regex": f"^{year}-{month:02d}"}},
                {"to_date": {"$regex": f"^{year}-{month:02d}"}}
            ]
        }
        
        # If employee_id is null, it's team calendar (all employees?), or we might restrict?
        # Docs say 6.1 Team Calendar (no emp id in param, but implies context)
        # 6.2 My Calendar (emp id in param)
        
        if employee_id:
             query["applicant_id"] = employee_id
             
        # Fetch leaves
        leaves_cursor = db["leave_requests"].find(query)
        
        events = []
        for l in leaves_cursor:
             evt = self._sanitize(l)
             # populate employee if team calendar
             if not employee_id and l.get("applicant_id"):
                 u = self._get_user(db, l["applicant_id"])
                 evt["employee"] = self._sanitize_user(u)
             events.append(evt)
             
        # Fetch holidays
        holidays = self.get_holidays(tenant_id, year)
        # Filter holidays for month
        holidays = [h for h in holidays if h.get("date", "").startswith(f"{year}-{month:02d}")]
        
        return {
            "month": month,
            "year": year,
            "events": events,
            "holidays": holidays
        }

    # ------------------------------------------------------------------
    # 7. Encashment APIs
    # ------------------------------------------------------------------
    def request_encashment(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = payload.copy()
        doc["tenant_id"] = tenant_id
        doc["status"] = "pending"
        doc.update(build_audit_fields(prefix="created", by=actor))
        
        res = db["leave_encashments"].insert_one(doc)
        
        return {
            "id": str(res.inserted_id),
            "status": "pending",
            "message": "Encashment request submitted for approval"
        }

    # ------------------------------------------------------------------
    # 8. Stats APIs
    # ------------------------------------------------------------------
    def get_stats(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        
        # Filter stats by dept/location? Queries might need lookup. 
        # For simplicity, returning global tenant stats or approximate.
        
        pending = db["leave_requests"].count_documents({**match, "status": "pending"})
        # approved_this_month calculation...
        
        return {
            "pending_requests": pending,
            "approved_this_month": 0, # Implement date filter counts
            "rejected_this_month": 0,
            "upcoming_leaves": 0,
            "on_leave_today": 0,
            "leave_by_type": []
        }
        
    def get_filter_options(self, tenant_id: str) -> Dict[str, Any]:
        # Implementation for getting departments, leave types etc.
        return {
            "departments": [], # Fetch unique departments or from config
            "leave_types": self.get_leave_types(tenant_id)
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_db(self, tenant_id: str):
        return self.client[tenant_id]

    def _sanitize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(doc)
        if "_id" in doc:
             doc["id"] = str(doc.pop("_id"))
        return doc

    def _get_doc_or_404(self, collection, doc_id: str) -> Dict[str, Any]:
        try:
            oid = ObjectId(doc_id)
        except:
             raise LeaveError("Not found", status_code=404, code="NOT_FOUND")
        doc = collection.find_one({"_id": oid})
        if not doc:
             raise LeaveError("Not found", status_code=404, code="NOT_FOUND")
        return doc
        
    def _require(self, value, name):
        if not value:
            raise LeaveError(f"{name} is required")
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
            "display_name": user.get("display_name"),
            "employee_code": user.get("employee_code"),
            "department": user.get("department"),
            "designation": user.get("designation")
        }
