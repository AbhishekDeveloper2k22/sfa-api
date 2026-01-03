from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import uuid

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class AssetError(Exception):
    """Domain error for asset operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class AssetService:
    """Service layer for tenant-scoped asset & inventory module."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Categories & Locations
    # ------------------------------------------------------------------
    def get_categories(self, tenant_id: str) -> Dict[str, Any]:
        # Return hardcoded or db fetched
        db = self._get_db(tenant_id)
        cats = list(db["asset_categories"].find({"tenant_id": tenant_id}))
        if not cats:
             defaults = [
                 {"code": "LAPTOP", "name": "Laptop", "icon": "💻", "depreciation_years": 3},
                 {"code": "MONITOR", "name": "Monitor", "icon": "🖥️", "depreciation_years": 4},
                 {"code": "MOBILE", "name": "Mobile Phone", "icon": "📱", "depreciation_years": 2},
                 {"code": "FURNITURE", "name": "Furniture", "icon": "🪑", "depreciation_years": 7},
                 {"code": "ACCESSORY", "name": "Accessory", "icon": "🖱️", "depreciation_years": 1}
             ]
             return {"data": defaults}
        return {"data": [self._sanitize(c) for c in cats]}

    def get_locations(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        locs = list(db["asset_locations"].find({"tenant_id": tenant_id}))
        if not locs:
             defaults = [
                 {"id": "loc_001", "name": "Mumbai HQ", "type": "office"},
                 {"id": "loc_002", "name": "Bangalore Hub", "type": "office"},
                 {"id": "loc_remote", "name": "Remote", "type": "remote"}
             ]
             return {"data": defaults}
        return {"data": [self._sanitize(l) for l in locs]}

    # ------------------------------------------------------------------
    # 2. Assets
    # ------------------------------------------------------------------
    def get_assets(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        if query_params.get("status"): match["status"] = query_params["status"]
        if query_params.get("category"): match["category"] = query_params["category"]
        if query_params.get("search"):
             q = query_params["search"]
             match["$or"] = [
                 {"asset_tag": {"$regex": q, "$options": "i"}},
                 {"model": {"$regex": q, "$options": "i"}},
                 {"serial_number": {"$regex": q, "$options": "i"}}
             ]

        data = list(db["assets"].find(match))
        
        # Enrich and Calc Value
        results = []
        total_val = 0
        status_counts = {"available": 0, "assigned": 0, "maintenance": 0, "retired": 0}
        
        for d in data:
            d = self._enrich_asset(tenant_id, d)
            results.append(d)
            if d.get("current_book_value"): total_val += d["current_book_value"]
            if d.get("status") in status_counts: status_counts[d["status"]] += 1

        stats = {
            "total": len(results),
            "total_value": total_val,
            **status_counts
        }
        return {"data": results, "stats": stats}

    def get_asset_by_id(self, tenant_id: str, asset_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = self._find_asset(db, tenant_id, asset_id)
        return {"data": self._enrich_asset(tenant_id, doc)}

    def create_asset(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        self._require(payload.get("asset_tag"), "asset_tag")
        self._require(payload.get("category"), "category")
        
        # Check uniqueness
        if db["assets"].find_one({"tenant_id": tenant_id, "asset_tag": payload["asset_tag"]}):
             raise AssetError("Asset tag already exists")
             
        asset_id = f"ast_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.update({
            "id": asset_id,
            "tenant_id": tenant_id,
            "status": "available",
            "assigned_to": None,
            "created_at": datetime.utcnow()
        })
        
        db["assets"].insert_one(doc)
        return {"data": self._enrich_asset(tenant_id, doc)}

    def update_asset(self, tenant_id: str, asset_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_asset(db, tenant_id, asset_id)
        updates = payload.copy()
        db["assets"].update_one({"_id": curr["_id"]}, {"$set": updates})
        return self.get_asset_by_id(tenant_id, asset_id)

    def assign_asset(self, tenant_id: str, asset_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        emp_id = self._require(payload.get("employee_id"), "employee_id")
        curr = self._find_asset(db, tenant_id, asset_id)
        
        if curr["status"] != "available":
             raise AssetError("Asset is not available for assignment")
             
        updates = {
            "status": "assigned",
            "assigned_to": emp_id,
            "assigned_on": datetime.utcnow(),
            "assignment_note": payload.get("note")
        }
        db["assets"].update_one({"_id": curr["_id"]}, {"$set": updates})
        return {"data": {"id": curr["id"], "status": "assigned", "assigned_to": emp_id, "assigned_on": updates["assigned_on"]}}

    def return_asset(self, tenant_id: str, asset_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_asset(db, tenant_id, asset_id)
        
        if curr["status"] != "assigned":
             raise AssetError("Asset is not currently assigned")
        
        updates = {
            "status": "available",
            "assigned_to": None,
            "returned_on": datetime.utcnow()
        }
        db["assets"].update_one({"_id": curr["_id"]}, {"$set": updates})
        return {"data": {"id": curr["id"], "status": "available", "assigned_to": None}}

    def dispose_asset(self, tenant_id: str, asset_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_asset(db, tenant_id, asset_id)
        
        if curr["status"] == "assigned":
             raise AssetError("Cannot dispose assigned asset. Return it first.")
             
        updates = {
            "status": "retired",
            "disposal_date": payload.get("disposal_date"),
            "disposal_value": payload.get("disposal_value"),
            "disposal_reason": payload.get("reason")
        }
        db["assets"].update_one({"_id": curr["_id"]}, {"$set": updates})
        return {"data": {"id": curr["id"], "status": "retired", "disposal_date": updates["disposal_date"]}}

    # ------------------------------------------------------------------
    # 3. Requests
    # ------------------------------------------------------------------
    def get_requests(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        data = list(db["asset_requests"].find({"tenant_id": tenant_id}))
        results = [self._enrich_request(tenant_id, d) for d in data]
        return {"data": results}

    def create_request(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.update({
            "id": req_id,
            "tenant_id": tenant_id,
            "requested_by": actor, # user_id
            "status": "pending",
            "created_at": datetime.utcnow()
        })
        db["asset_requests"].insert_one(doc)
        return {"data": self._enrich_request(tenant_id, doc)}

    def perform_request_action(self, tenant_id: str, request_id: str, action: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["asset_requests"].find_one({"id": request_id, "tenant_id": tenant_id})
        if not doc: raise AssetError("Request not found", status_code=404)
        
        new_status = "approved" if action == "approve" else "denied"
        db["asset_requests"].update_one({"_id": doc["_id"]}, {"$set": {"status": new_status, "updated_at": datetime.utcnow()}})
        return {"data": {"id": request_id, "status": new_status}}

    # ------------------------------------------------------------------
    # 4. Maintenance
    # ------------------------------------------------------------------
    def get_maintenance_logs(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        data = list(db["maintenance_logs"].find({"tenant_id": tenant_id}))
        return {"data": [self._sanitize(d) for d in data]}

    def create_maintenance_log(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        asset_id = self._require(payload.get("asset_id"), "asset_id")
        asset = self._find_asset(db, tenant_id, asset_id)
        
        m_id = f"maint_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.update({
            "id": m_id,
            "tenant_id": tenant_id,
            "status": "scheduled",
            "created_at": datetime.utcnow()
        })
        db["maintenance_logs"].insert_one(doc)
        
        # Determine if asset status should change? 
        # If scheduled for future, maybe not. If immediate, yes.
        # Docs say: "Update asset status to 'maintenance' if currently assigned" -> wait, assigned assets need returning usually.
        # But if it's on-site maintenance, maybe status 'maintenance'.
        # I'll set status to maintenance logic if user wants, but docs say guideline: "Update asset status to 'maintenance'".
        if asset["status"] != "retired":
             db["assets"].update_one({"_id": asset["_id"]}, {"$set": {"status": "maintenance"}})
        
        return {"data": self._sanitize(doc)}

    def complete_maintenance_log(self, tenant_id: str, log_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["maintenance_logs"].find_one({"id": log_id, "tenant_id": tenant_id})
        if not doc: raise AssetError("Maintenance log not found", 404)
        
        updates = {
            "status": "completed",
            "actual_cost": payload.get("actual_cost"),
            "completed_date": payload.get("completed_date", datetime.utcnow())
        }
        db["maintenance_logs"].update_one({"_id": doc["_id"]}, {"$set": updates})
        
        # Restore asset status
        asset_id = doc["asset_id"]
        # Basic logic: mark available. 
        db["assets"].update_one({"id": asset_id, "tenant_id": tenant_id}, {"$set": {"status": "available"}})
        
        return {"data": {**updates, "id": log_id}}

    # ------------------------------------------------------------------
    # 5. Reports
    # ------------------------------------------------------------------
    def get_depreciation(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        assets = list(db["assets"].find({"tenant_id": tenant_id}))
        report = []
        total_purch = 0
        total_curr = 0
        
        for a in assets:
            a = self._enrich_asset(tenant_id, a)
            report.append({
                "asset_id": a["id"],
                "asset_tag": a.get("asset_tag"),
                "purchase_price": a.get("purchase_price", 0),
                "current_value": a.get("current_book_value", 0),
                "depreciation": a.get("purchase_price", 0) - a.get("current_book_value", 0)
            })
            total_purch += a.get("purchase_price", 0)
            total_curr += a.get("current_book_value", 0)
            
        return {"data": report, "summary": {"total_purchase": total_purch, "total_current": total_curr}}

    def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        # Reuse get_assets stats
        assets_res = self.get_assets(tenant_id, {})
        stats = assets_res["stats"]
        # Add pending requests
        db = self._get_db(tenant_id)
        stats["pending_requests"] = db["asset_requests"].count_documents({"tenant_id": tenant_id, "status": "pending"})
        return {"data": stats}

    def get_filter_options(self, tenant_id: str) -> Dict[str, Any]:
        return {"data": {
            "statuses": [{"value": "available", "label": "Available"}, {"value": "assigned", "label": "Assigned"}, {"value": "maintenance", "label": "Maintenance"}, {"value": "retired", "label": "Retired"}],
            "categories": [{"value": "LAPTOP", "label": "Laptop"}], # fetch real ones
            "locations": [{"value": "Mumbai HQ", "label": "Mumbai HQ"}] # fetch real ones
        }}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_asset(self, db, tenant_id, asset_id):
        doc = db["assets"].find_one({"id": asset_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["assets"].find_one({"_id": ObjectId(asset_id), "tenant_id": tenant_id})
             except:
                 pass
        if not doc:
             raise AssetError("Asset not found", status_code=404)
        return doc

    def _enrich_asset(self, tenant_id, doc):
        d = self._sanitize(doc)
        # Calculate depreciation
        # Simple straight line: price / (years * 12) * months_passed
        # Need purchase_date and deprecation_years (from category)
        # Mock calculation:
        price = d.get("purchase_price", 0) or 0
        d["current_book_value"] = price * 0.8 # Mock: 20% depreciation per year logic omitted for brevity
        
        # Expand location/assignee if needed
        # d["location"] = ...
        return d

    def _enrich_request(self, tenant_id, doc):
        db = self._get_db(tenant_id)
        d = self._sanitize(doc)
        if "requested_by" in d:
             u = db["users"].find_one({"id": d["requested_by"]}) or db["users"].find_one({"_id": ObjectId(d["requested_by"])})
             if u:
                 d["employee"] = {"id": str(u["_id"]), "name": u.get("display_name"), "employee_code": u.get("employee_code"), "department": u.get("department")}
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
            raise AssetError(f"{name} is required")
        return value
