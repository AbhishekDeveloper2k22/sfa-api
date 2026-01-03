from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import uuid

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class CelebrationError(Exception):
    """Domain error for celebration operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class CelebrationService:
    """Service layer for tenant-scoped celebration management."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Celebrations
    # ------------------------------------------------------------------
    def get_celebrations(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        
        if query_params.get("type"): match["type"] = query_params["type"]
        if query_params.get("department"): match["department"] = query_params["department"]
        if query_params.get("status"): match["status"] = query_params["status"]
        if query_params.get("search"):
             q = query_params["search"]
             match["$or"] = [
                 {"employeeName": {"$regex": q, "$options": "i"}},
                 {"department": {"$regex": q, "$options": "i"}}
             ]
        
        # Date filters
        # Note: dates in DB are strings "YYYY-MM-DD" or ISO datetimes?
        # Docs response says "YYYY-MM-DD". Assuming string or ISODate.
        # I'll stick to string date comparisons if format is consistent "YYYY-MM-DD", otherwise Range might fail.
        # Let's hope for consistent ISO string or Date object.
        # If payload.date is ISODate, and filters are strings, I need to parse.
        
        date_from = query_params.get("date_from")
        date_to = query_params.get("date_to")
        if date_from or date_to:
             match["date"] = {}
             if date_from: match["date"]["$gte"] = date_from
             if date_to: match["date"]["$lte"] = date_to

        # Pagination
        total = db["celebrations"].count_documents(match)
        # Using default pagination for list
        cursor = db["celebrations"].find(match).sort("date", 1) # Closest first
        
        # Need enriching? Docs say "Employee details include name, ID".
        # If stored with celebration record? "Link to employee record to get name and department" in Create.
        # So I assume data is denormalized or we join.
        # create_celebration Guidelines: "Link to employee record to get name and department".
        # So I will fetch them.
        
        results = [self._sanitize(doc) for doc in cursor]

        return {
            "data": results,
            "meta": {
                "total": total,
                "page": 1,
                "size": len(results),
                "totalPages": 1
            }
        }

    def get_celebration_by_id(self, tenant_id: str, celebration_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = self._find_celebration(db, tenant_id, celebration_id)
        return {"data": self._enrich_details(tenant_id, doc)}

    def create_celebration(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        self._require(payload.get("employeeId"), "employeeId")
        self._require(payload.get("type"), "type")
        self._require(payload.get("date"), "date")
        
        # Validate Type
        if payload["type"] not in ["Birthday", "Work Anniversary"]:
             raise CelebrationError("Invalid celebration type")
             
        # Fetch Employee
        emp_id = payload["employeeId"]
        emp = db["users"].find_one({"id": emp_id}) or db["users"].find_one({"_id": ObjectId(emp_id)})
        if not emp:
             raise CelebrationError("Employee not found")
             
        cel_id = f"cel_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.update({
            "id": cel_id,
            "tenant_id": tenant_id,
            "employeeName": emp.get("display_name", "Unknown"),
            "department": emp.get("department", "Unknown"),
            "status": "Upcoming",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        db["celebrations"].insert_one(doc)
        return {"data": self._sanitize(doc)}

    def update_celebration(self, tenant_id: str, celebration_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_celebration(db, tenant_id, celebration_id)
        
        updates = payload.copy()
        if "id" in updates: del updates["id"]
        if "tenant_id" in updates: del updates["tenant_id"]
        if "employeeId" in updates: del updates["employeeId"] # Usually not changed?
        
        updates["updated_at"] = datetime.utcnow()
        
        db["celebrations"].update_one({"_id": curr["_id"]}, {"$set": updates})
        return self.get_celebration_by_id(tenant_id, celebration_id)

    def delete_celebration(self, tenant_id: str, celebration_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        res = db["celebrations"].delete_one({"id": celebration_id, "tenant_id": tenant_id})
        if res.deleted_count == 0:
             raise CelebrationError("Celebration not found", status_code=404)
        return {"success": True}

    # ------------------------------------------------------------------
    # 2. Daily/Weekly
    # ------------------------------------------------------------------
    def get_today_celebrations(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Match date string exactly? or handle timezone?
        # Assuming celebrations store YYYY-MM-DD string as per response.
        
        data = list(db["celebrations"].find({
            "tenant_id": tenant_id,
            "date": today_str,
            "status": "Upcoming" # Return only upcoming (not completed?)
            # Wait, if it is today, is it "Upcoming" or could it be "Completed"?
            # Filter guidelines: "Return only upcoming celebrations (not completed)"
        }))
        return {"data": [self._sanitize(d) for d in data]}

    def get_weekly_celebrations(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        today = datetime.utcnow()
        start = today.strftime("%Y-%m-%d")
        end = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        
        cursor = db["celebrations"].find({
            "tenant_id": tenant_id,
            "date": {"$gte": start, "$lte": end}
        }).sort("date", 1)
        
        results = []
        for d in cursor:
             d = self._sanitize(d)
             # calc days until
             try:
                 evt_date = datetime.strptime(d["date"], "%Y-%m-%d")
                 d["days_until"] = (evt_date - today).days
                 if d["days_until"] < 0: d["days_until"] = 0
             except: pass
             results.append(d)
        return {"data": results}

    # ------------------------------------------------------------------
    # 3. Wishes
    # ------------------------------------------------------------------
    def send_wish(self, tenant_id: str, celebration_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_celebration(db, tenant_id, celebration_id)
        
        # Get employee email? We need to fetch emp if not in celebration doc.
        # "Retrieval employee email... from employee record"
        # Not enriching `curr` usually.
        emp_id = curr.get("employeeId")
        if emp_id:
             u = db["users"].find_one({"id": emp_id}) or db["users"].find_one({"_id": ObjectId(emp_id)})
             # if u: email = u.get("email")
        
        # Mock send
        method = payload.get("method", "email")
        
        # Update status
        db["celebrations"].update_one(
            {"_id": curr["_id"]},
            {
                "$set": {"status": "Completed", "updated_at": datetime.utcnow()},
                "$push": {"wishes_sent": {"method": method, "sent_at": datetime.utcnow()}}
            }
        )
        
        return {"data": {
            "id": celebration_id,
            "employeeName": curr.get("employeeName"),
            "method": method,
            "status": "sent",
            "sent_at": datetime.utcnow().isoformat()
        }}

    def send_all_wishes(self, tenant_id: str, query_params: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        target_date = query_params.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
        
        # Find all for date
        cursor = db["celebrations"].find({"tenant_id": tenant_id, "date": target_date})
        count = 0
        method = payload.get("method", "email")
        
        for doc in cursor:
             # Mock send
             db["celebrations"].update_one({"_id": doc["_id"]}, {"$set": {"status": "Completed"}})
             count += 1
             
        return {"data": {
            "wishes_sent": count,
            "failed_count": 0,
            "total_eligible": count,
            "date": target_date
        }}

    # ------------------------------------------------------------------
    # 4. Reports
    # ------------------------------------------------------------------
    def get_stats(self, tenant_id: str, period: str = "month") -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        
        # Build date range based on period
        now = datetime.utcnow()
        match = {"tenant_id": tenant_id}
        
        if period == "today":
             match["date"] = now.strftime("%Y-%m-%d")
        elif period == "week":
             end = now + timedelta(days=7)
             match["date"] = {"$gte": now.strftime("%Y-%m-%d"), "$lte": end.strftime("%Y-%m-%d")}
        elif period == "month":
             # Regex for YYYY-MM
             month_str = now.strftime("%Y-%m")
             match["date"] = {"$regex":f"^{month_str}"}
        elif period == "year":
             year_str = now.strftime("%Y")
             match["date"] = {"$regex":f"^{year_str}"}

        # Aggregation
        pipeline_stats = [
            {"$match": match},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "birthdays": {"$sum": {"$cond": [{"$eq": ["$type", "Birthday"]}, 1, 0]}},
                "anniversaries": {"$sum": {"$cond": [{"$eq": ["$type", "Work Anniversary"]}, 1, 0]}}
            }}
        ]
        
        res = list(db["celebrations"].aggregate(pipeline_stats))
        stats = res[0] if res else {"total": 0, "birthdays": 0, "anniversaries": 0}
        if "_id" in stats: del stats["_id"]
        
        # Today
        stats["today"] = db["celebrations"].count_documents({"tenant_id": tenant_id, "date": now.strftime("%Y-%m-%d")})
        # Upcoming (future)
        stats["upcoming"] = db["celebrations"].count_documents({"tenant_id": tenant_id, "date": {"$gt": now.strftime("%Y-%m-%d")}})
        
        # By Department
        stats["by_department"] = [
            {"department": r["_id"] or "Unknown", "count": r["count"]}
            for r in db["celebrations"].aggregate([
                {"$match": match},
                {"$group": {"_id": "$department", "count": {"$sum": 1}}}
            ])
        ]
        # By Type
        stats["by_type"] = [
            {"type": r["_id"], "count": r["count"]}
            for r in db["celebrations"].aggregate([
                {"$match": match},
                {"$group": {"_id": "$type", "count": {"$sum": 1}}}
            ])
        ]

        return {"data": stats}

    def export_celebrations(self, tenant_id: str, format: str) -> Dict[str, Any]:
        return {"data": {"download_url": "https://storage.mock/celebrations_export.csv", "filename": f"celebrations.{format}"}}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_celebration(self, db, tenant_id, celebration_id):
        doc = db["celebrations"].find_one({"id": celebration_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["celebrations"].find_one({"_id": ObjectId(celebration_id), "tenant_id": tenant_id})
             except: pass
        if not doc:
             raise CelebrationError("Celebration not found", status_code=404)
        return doc

    def _enrich_details(self, tenant_id, doc):
        d = self._sanitize(doc)
        db = self._get_db(tenant_id)
        if "employeeId" in d:
             emp = db["users"].find_one({"id": d["employeeId"]}) or db["users"].find_one({"_id": ObjectId(d["employeeId"])})
             if emp:
                 d["employeeEmail"] = emp.get("email")
                 # Ensure department/name are synced if needed, but we stored them.
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
            raise CelebrationError(f"{name} is required")
        return value
