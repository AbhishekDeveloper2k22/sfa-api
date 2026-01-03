from datetime import datetime
from typing import Any, Dict, Optional, List
import uuid

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class PolicyError(Exception):
    """Domain error for policy operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class PolicyService:
    """Service layer for tenant-scoped policy management."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Policies
    # ------------------------------------------------------------------
    def get_policies(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        if query_params.get("category"): match["category"] = query_params["category"]
        if query_params.get("status"): match["status"] = query_params["status"]
        if query_params.get("search"):
             q = query_params["search"]
             match["$or"] = [
                 {"title": {"$regex": q, "$options": "i"}},
                 {"description": {"$regex": q, "$options": "i"}}
             ]

        total = db["policies"].count_documents(match)
        # Pagination not explicitly requested in params of method signature, but docs mention 'meta'.
        # I'll default to all or simple pagination if params present. 
        # For this implementation I'll return list.
        cursor = db["policies"].find(match).sort("createdDate", -1)
        
        data = [self._sanitize(doc) for doc in cursor]
        return {
            "data": data,
            "meta": {
                "total": total,
                "page": 1,
                "size": len(data),
                "totalPages": 1
            }
        }

    def get_policy_by_id(self, tenant_id: str, policy_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = self._find_policy(db, tenant_id, policy_id)
        return {"data": self._sanitize(doc)}

    def create_policy(self, tenant_id: str, payload: Dict[str, Any], user_id: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        self._require(payload.get("title"), "title")
        self._require(payload.get("category"), "category")
        
        policy_id = f"pol_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        
        # User details for audit
        user_name = "System"
        if user_id:
             u = db["users"].find_one({"id": user_id}) or db["users"].find_one({"_id": ObjectId(user_id)})
             if u: user_name = u.get("display_name", "Unknown")

        doc.update({
            "id": policy_id,
            "tenant_id": tenant_id,
            "createdDate": datetime.utcnow(),
            "createdBy": user_name,
            "lastUpdated": datetime.utcnow(),
            "updatedBy": user_name,
            "status": payload.get("status", "Draft"),
            "version": payload.get("version", "1.0"),
            "revisionHistory": [
                {
                    "version": payload.get("version", "1.0"),
                    "date": datetime.utcnow(),
                    "updatedBy": user_name,
                    "changes": "Initial creation"
                }
            ],
            "attachments": []
        })
        
        db["policies"].insert_one(doc)
        return {"data": self._sanitize(doc)}

    def update_policy(self, tenant_id: str, policy_id: str, payload: Dict[str, Any], user_id: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_policy(db, tenant_id, policy_id)
        
        updates = payload.copy()
        for k in ["id", "tenant_id", "createdDate", "createdBy", "revisionHistory", "attachments"]:
             if k in updates: del updates[k]
             
        # Audit
        user_name = "System"
        if user_id:
             u = db["users"].find_one({"id": user_id}) or db["users"].find_one({"_id": ObjectId(user_id)})
             if u: user_name = u.get("display_name", "Unknown")

        updates["lastUpdated"] = datetime.utcnow()
        updates["updatedBy"] = user_name
        
        # Revision history
        new_rev = {
            "version": updates.get("version", curr.get("version", "1.0")),
            "date": datetime.utcnow(),
            "updatedBy": user_name,
            "changes": "Policy updated"
        }
        
        db["policies"].update_one(
            {"_id": curr["_id"]}, 
            {
                "$set": updates,
                "$push": {"revisionHistory": new_rev}
            }
        )
        return self.get_policy_by_id(tenant_id, policy_id)

    def delete_policy(self, tenant_id: str, policy_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        res = db["policies"].delete_one({"id": policy_id, "tenant_id": tenant_id})
        if res.deleted_count == 0:
             raise PolicyError("Policy not found", status_code=404)
        return {"success": True}

    # ------------------------------------------------------------------
    # 2. Attachments
    # ------------------------------------------------------------------
    def add_attachment(self, tenant_id: str, policy_id: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_policy(db, tenant_id, policy_id)
        
        att_id = int(str(uuid.uuid4().int)[:8]) # number as per docs
        attachment = {
            "id": att_id,
            "name": file_info["filename"],
            "size": file_info.get("size", "0KB"),
            "uploadedOn": datetime.utcnow(),
            "url": file_info.get("url", f"#att_{att_id}")
        }
        
        db["policies"].update_one(
            {"_id": curr["_id"]},
            {"$push": {"attachments": attachment}}
        )
        return {"data": attachment}

    def remove_attachment(self, tenant_id: str, policy_id: str, attachment_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_policy(db, tenant_id, policy_id)
        
        # attachment_id in docs is number, but URL param is string. Cast as needed.
        try:
             att_id_int = int(attachment_id)
             db["policies"].update_one(
                 {"_id": curr["_id"]},
                 {"$pull": {"attachments": {"id": att_id_int}}}
             )
        except ValueError:
             # Try string match if legacy
             db["policies"].update_one(
                 {"_id": curr["_id"]},
                 {"$pull": {"attachments": {"id": attachment_id}}}
             )
             
        return {"success": True}

    # ------------------------------------------------------------------
    # 3. Actions & Reports
    # ------------------------------------------------------------------
    def download_policy(self, tenant_id: str, policy_id: str) -> Any:
        # Stub for PDF content
        return b"%PDF-1.4..."

    def email_policy(self, tenant_id: str, policy_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Stub email job
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        return {"data": {"job_id": job_id, "recipients_count": len(payload.get("recipients", [])), "status": "processing"}}

    def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        policies = list(db["policies"].find({"tenant_id": tenant_id}))
        
        total = len(policies)
        active = 0
        draft = 0
        archived = 0
        updated_month = 0
        by_cat = {}
        now = datetime.utcnow()
        
        for p in policies:
            st = p.get("status", "Draft")
            if st == "Active": active += 1
            elif st == "Draft": draft += 1
            elif st == "Archived": archived += 1
            
            cat = p.get("category", "General")
            by_cat[cat] = by_cat.get(cat, 0) + 1
            
            lu = p.get("lastUpdated")
            if lu and isinstance(lu, datetime) and lu.month == now.month and lu.year == now.year:
                 updated_month += 1
                 
        return {"data": {
            "total_policies": total,
            "active": active,
            "draft": draft,
            "archived": archived,
            "updated_this_month": updated_month,
            "by_category": [{"category": k, "count": v} for k, v in by_cat.items()]
        }}

    def export_policies(self, tenant_id: str, format: str) -> Dict[str, Any]:
        return {"data": {"download_url": "https://storage.mock/policies_export.pdf", "filename": "policies_export.pdf"}}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_policy(self, db, tenant_id, policy_id):
        doc = db["policies"].find_one({"id": policy_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["policies"].find_one({"_id": ObjectId(policy_id), "tenant_id": tenant_id})
             except: pass
        if not doc:
             raise PolicyError("Policy not found", status_code=404)
        return doc

    def _get_db(self, tenant_id: str):
        return self.client[tenant_id]

    def _sanitize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(doc)
        if "_id" in doc:
             doc["id"] = str(doc.pop("_id"))
        return doc

    def _require(self, value, name):
        if not value:
            raise PolicyError(f"{name} is required")
        return value
