from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import uuid

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class DocumentError(Exception):
    """Domain error for document operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class DocumentService:
    """Service layer for tenant-scoped document management."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Categories
    # ------------------------------------------------------------------
    def get_categories(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        # Seed or fetch from db
        cats = list(db["document_categories"].find({"tenant_id": tenant_id}))
        if not cats:
             defaults = [
                 {"id": "cat_id_01", "name": "Identity Documents", "icon": "🪪", "required": True, "retention_days": 2555},
                 {"id": "cat_id_02", "name": "Contracts", "icon": "📄", "required": True, "retention_days": 1095},
                 {"id": "cat_id_03", "name": "Payslips", "icon": "💰", "required": False, "retention_days": 365},
                 {"id": "cat_id_04", "name": "Tax Forms", "icon": "📝", "required": True, "retention_days": 1825},
                 {"id": "cat_id_05", "name": "Other", "icon": "📂", "required": False, "retention_days": 365}
             ]
             return {"data": defaults}
        return {"data": [self._sanitize(c) for c in cats]}

    # ------------------------------------------------------------------
    # 2. Documents
    # ------------------------------------------------------------------
    def get_documents(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        if query_params.get("category_id"): match["category_id"] = query_params["category_id"]
        if query_params.get("employee_id"): match["employee_id"] = query_params["employee_id"]
        if query_params.get("search"):
             q = query_params["search"]
             match["$or"] = [
                 {"title": {"$regex": q, "$options": "i"}},
                 {"tags": {"$regex": q, "$options": "i"}}
             ]
        if query_params.get("expiring_within_days"):
             days = int(query_params["expiring_within_days"])
             target_date = datetime.utcnow() + timedelta(days=days)
             match["expiry_date"] = {"$gte": datetime.utcnow(), "$lte": target_date}

        data = list(db["documents"].find(match).sort("created_at", -1))
        
        # Enrich
        results = []
        for d in data:
            results.append(self._enrich_document(tenant_id, d))
            
        # Stats Calc (Mock or Aggregate) - Documented stats structure provided in response but GET /documents includes stats? 
        # API Docs 2.1 Response includes `stats`.
        # I'll calculate simple stats
        total = len(results)
        by_cat = {}
        exp_soon = 0
        now = datetime.utcnow()
        limit = now + timedelta(days=30)
        
        for r in results:
             c = r.get("category", {}).get("name", "Unknown")
             by_cat[c] = by_cat.get(c, 0) + 1
             if r.get("expiry_date"):
                 exp_date = r["expiry_date"]
                 if isinstance(exp_date, str): exp_date = datetime.fromisoformat(exp_date.replace("Z", ""))
                 if now <= exp_date <= limit:
                     exp_soon += 1
                     
        stats = {
            "total": total,
            "by_category": [{"category": k, "count": v} for k, v in by_cat.items()],
            "expiring_soon": exp_soon
        }
        
        return {"data": results, "stats": stats}

    def get_document_by_id(self, tenant_id: str, doc_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = self._find_document(db, tenant_id, doc_id)
        return {"data": self._enrich_document(tenant_id, doc)}

    def create_document(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        self._require(payload.get("category_id"), "category_id")
        self._require(payload.get("title"), "title")
        self._require(payload.get("file_url"), "file_url")
        
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.update({
            "id": doc_id,
            "tenant_id": tenant_id,
            "version": 1,
            "created_at": datetime.utcnow()
        })
        
        # Validate confidential level
        if doc.get("confidential_level") not in ["public", "internal", "restricted"]:
             doc["confidential_level"] = "internal"
             
        db["documents"].insert_one(doc)
        return {"data": self._enrich_document(tenant_id, doc)}

    def update_document(self, tenant_id: str, doc_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_document(db, tenant_id, doc_id)
        updates = payload.copy()
        db["documents"].update_one({"_id": curr["_id"]}, {"$set": updates})
        return self.get_document_by_id(tenant_id, doc_id)

    def delete_document(self, tenant_id: str, doc_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        res = db["documents"].delete_one({"id": doc_id, "tenant_id": tenant_id})
        if res.deleted_count == 0:
             # Try _id
             res = db["documents"].delete_one({"_id": ObjectId(doc_id), "tenant_id": tenant_id})
             if res.deleted_count == 0:
                 raise DocumentError("Document not found", status_code=404)
        return {"success": True}

    # ------------------------------------------------------------------
    # 3. Versions
    # ------------------------------------------------------------------
    def get_document_versions(self, tenant_id: str, doc_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        # Verify doc exists
        _ = self._find_document(db, tenant_id, doc_id)
        
        versions = list(db["document_versions"].find({"tenant_id": tenant_id, "document_id": doc_id}).sort("version", -1))
        return {"data": [self._sanitize(v) for v in versions]}

    def upload_document_version(self, tenant_id: str, doc_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_document(db, tenant_id, doc_id)
        
        new_ver = curr.get("version", 1) + 1
        
        # Save old version record for history if not exists? Or just save new upload as version?
        # Typically "versions" table stores history.
        # But this API implies uploading a NEW version.
        # So we update the main doc and create an entry in versions table for the NEW version?
        # Or store the OLD version in history before updating main?
        # Guidelines: "Update main document record with new version" + "Store new version in document_versions table"
        
        ver_id = f"ver_{uuid.uuid4().hex[:8]}"
        ver_doc = {
            "id": ver_id,
            "document_id": curr["id"],
            "tenant_id": tenant_id,
            "version": new_ver,
            "file_url": payload["file_url"],
            "version_note": payload.get("version_note"),
            "uploaded_at": datetime.utcnow()
        }
        db["document_versions"].insert_one(ver_doc)
        
        db["documents"].update_one({"_id": curr["_id"]}, {"$set": {"version": new_ver, "file_url": payload["file_url"]}})
        return {"data": self._sanitize(ver_doc)}

    def restore_document_version(self, tenant_id: str, doc_id: str, ver_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_document(db, tenant_id, doc_id) # Ensure doc exists
        
        target_ver = db["document_versions"].find_one({"id": ver_id, "tenant_id": tenant_id})
        # Try finding by version number if ver_id passed is number? No docs say version_id path param.
        if not target_ver:
             try:
                 target_ver = db["document_versions"].find_one({"_id": ObjectId(ver_id), "tenant_id": tenant_id})
             except: pass
        if not target_ver: raise DocumentError("Version not found", 404)
        
        new_ver_num = curr.get("version", 1) + 1
        
        # Create new version entry reflecting the restore
        restored_entry_id = f"ver_{uuid.uuid4().hex[:8]}"
        restored_entry = {
            "id": restored_entry_id,
            "document_id": curr["id"],
            "tenant_id": tenant_id,
            "version": new_ver_num,
            "file_url": target_ver["file_url"],
            "version_note": f"Restored from version {target_ver['version']}",
            "uploaded_at": datetime.utcnow()
        }
        db["document_versions"].insert_one(restored_entry)
        
        # Update main
        db["documents"].update_one({"_id": curr["_id"]}, {"$set": {"version": new_ver_num, "file_url": target_ver["file_url"]}})
        
        return {"data": {"document_id": curr["id"], "restored_version": str(new_ver_num)}}

    # ------------------------------------------------------------------
    # 4. Downloads & Uploads
    # ------------------------------------------------------------------
    def get_download_url(self, tenant_id: str, doc_id: str) -> Dict[str, Any]:
        return {"data": {"url": f"#download_doc_{doc_id}", "expires_in": 3600}}

    def init_upload(self, tenant_id: str) -> Dict[str, Any]:
        uid = f"up_{uuid.uuid4().hex[:8]}"
        return {"data": {"upload_id": uid, "upload_url": f"#upload_{uid}", "expires_in": 3600}}

    def complete_upload(self, tenant_id: str, upload_id: str) -> Dict[str, Any]:
        return {"data": {"upload_id": upload_id, "file_url": f"https://storage.mock/{upload_id}.pdf", "status": "completed"}}

    # ------------------------------------------------------------------
    # 5. Expiring & Misc
    # ------------------------------------------------------------------
    def get_expiring_documents(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        # Reusing get_documents filter logic basically, but docs want distinct endpoint 5.1
        db = self._get_db(tenant_id)
        limit = datetime.utcnow() + timedelta(days=days)
        data = list(db["documents"].find({
            "tenant_id": tenant_id,
            "expiry_date": {"$gte": datetime.utcnow(), "$lte": limit}
        }).sort("expiry_date", 1))
        
        results = []
        for d in data:
             d = self._enrich_document(tenant_id, d)
             # calc days until expiry
             if d.get("expiry_date"):
                 exp = d["expiry_date"]
                 if isinstance(exp, str): exp = datetime.fromisoformat(exp.replace("Z",""))
                 diff = (exp - datetime.utcnow()).days
                 d["days_until_expiry"] = diff
             results.append(d)
        return {"data": results}

    def extend_expiry(self, tenant_id: str, doc_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_document(db, tenant_id, doc_id)
        
        new_date = payload.get("new_date")
        self._require(new_date, "new_date")
        # Parse date if string? MongoDB driver usually handles ISO strings or datetime objects.
        # Ideally convert to datetime.
        if isinstance(new_date, str):
             try:
                 new_date = datetime.fromisoformat(new_date.replace("Z", ""))
             except: pass
             
        db["documents"].update_one({"_id": curr["_id"]}, {"$set": {"expiry_date": new_date}})
        return {"data": {"id": curr["id"], "expiry_date": new_date}}

    def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        # Heavy calculation usually, mocked or aggregated
        db = self._get_db(tenant_id)
        # Using the stats logic from get_documents but global
        docs = list(db["documents"].find({"tenant_id": tenant_id}))
        
        total = len(docs)
        cat_counts = {}
        exp_30 = 0
        total_size = 0
        emp_set = set()
        
        now = datetime.utcnow()
        limit = now + timedelta(days=30)
        
        for d in docs:
             cid = d.get("category_id", "unknown")
             cat_counts[cid] = cat_counts.get(cid, 0) + 1
             total_size += d.get("size_bytes", 0) or 0
             if d.get("employee_id"): emp_set.add(d["employee_id"])
             
             if d.get("expiry_date"):
                 exp = d["expiry_date"]
                 if isinstance(exp, str): exp = datetime.fromisoformat(exp.replace("Z", ""))
                 if now <= exp <= limit: exp_30 += 1
                 
        # Enrich category names
        cats = {c["id"]: c.get("name") for c in self.get_categories(tenant_id)["data"]}
        cat_stats = [{"id": k, "name": cats.get(k, "Unknown"), "count": v} for k, v in cat_counts.items()]
        
        return {"data": {
            "total_documents": total,
            "by_category": cat_stats,
            "expiring_30_days": exp_30,
            "total_size_bytes": total_size,
            "employees_with_docs": len(emp_set)
        }}

    def get_filter_options(self, tenant_id: str) -> Dict[str, Any]:
        cats = self.get_categories(tenant_id)["data"]
        return {"data": {
            "categories": [{"value": c["id"], "label": c["name"]} for c in cats],
            "employees": [], # Fetch real
            "confidential_levels": [{"value": "public", "label": "Public"}, {"value": "internal", "label": "Internal"}, {"value": "restricted", "label": "Restricted"}]
        }}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_document(self, db, tenant_id, doc_id):
        doc = db["documents"].find_one({"id": doc_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["documents"].find_one({"_id": ObjectId(doc_id), "tenant_id": tenant_id})
             except: pass
        if not doc:
             raise DocumentError("Document not found", status_code=404)
        return doc

    def _enrich_document(self, tenant_id, doc):
        db = self._get_db(tenant_id)
        d = self._sanitize(doc)
        
        # Category
        if "category_id" in d:
             # Optimization: Cache categories in memory for request duration? 
             # For now simple fetch or defaults match.
             # Reusing get_categories defaults logic is expensive if loop.
             # Assume category_id matches defaults or db.
             # I'll just put ID if not found or simple lookup.
             cat = db["document_categories"].find_one({"id": d["category_id"], "tenant_id": tenant_id})
             if cat: d["category"] = self._sanitize(cat)
             else: 
                 # Try defaults
                 defaults = self.get_categories(tenant_id)["data"]
                 matcher = next((c for c in defaults if c["id"] == d["category_id"]), None)
                 if matcher: d["category"] = matcher

        # Employee
        if "employee_id" in d and d["employee_id"]:
             u = db["users"].find_one({"id": d["employee_id"]}) or db["users"].find_one({"_id": ObjectId(d["employee_id"])})
             if u: d["employee"] = {"id": str(u["_id"]), "name": u.get("display_name"), "employee_code": u.get("employee_code"), "department": u.get("department")}
             
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
            raise DocumentError(f"{name} is required")
        return value
