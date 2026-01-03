from datetime import datetime
from typing import Any, Dict, Optional, List
import uuid

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class HolidayError(Exception):
    """Domain error for holiday operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class HolidayService:
    """Service layer for tenant-scoped holiday management."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Holidays
    # ------------------------------------------------------------------
    def get_holidays(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        
        if query_params.get("type"): match["type"] = query_params["type"]
        if query_params.get("year"): match["date"] = {"$regex":f"^{query_params['year']}"}
        if query_params.get("month"): 
             # If year provided, strict match. If only month, regex wildcard?
             # Usually year required or implies current year?
             # Docs just say Filter by month (MM).
             # Let's assume regex for month anywhere "-MM-".
             m = query_params["month"]
             if "date" in match: # existing year
                  # refine regex? complicated.
                  # Let's simplify: if year and month: YYYY-MM
                  if query_params.get("year"):
                       match["date"] = {"$regex":f"^{query_params['year']}-{m}"}
                  else:
                       # month only
                       match["date"] = {"$regex":f"-{m}-"}

        if query_params.get("search"):
             q = query_params["search"]
             match["$or"] = [
                 {"name": {"$regex": q, "$options": "i"}},
                 {"description": {"$regex": q, "$options": "i"}}
             ]
             
        # Status filter (Upcoming/Past) is computed based on date
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if query_params.get("status") == "Upcoming":
             # Date > today
             # Can't easily mix regex and operator on same field 'date'.
             # If year regex exists, we might need $and.
             # Let's use $and if needed.
             clause = {"date": {"$gt": today}}
             if "date" in match:
                  match["$and"] = [{"date": match.pop("date")}, clause]
             else:
                  match.update(clause)
        elif query_params.get("status") == "Past":
             clause = {"date": {"$lte": today}}
             if "date" in match:
                  match["$and"] = [{"date": match.pop("date")}, clause]
             else:
                  match.update(clause)

        total = db["holidays"].count_documents(match)
        # Default sort date ascending
        cursor = db["holidays"].find(match).sort("date", 1)
        
        results = []
        for doc in cursor:
             results.append(self._enrich_status(self._sanitize(doc)))
             
        return {
            "data": results,
            "meta": {
                "total": total,
                "page": 1,
                "size": len(results),
                "totalPages": 1
            }
        }

    def get_holiday_by_id(self, tenant_id: str, holiday_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = self._find_holiday(db, tenant_id, holiday_id)
        return {"data": self._enrich_status(self._sanitize(doc))}

    def create_holiday(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        self._require(payload.get("name"), "name")
        self._require(payload.get("date"), "date")
        self._require(payload.get("type"), "type")
        
        # Check duplicate date
        existing = db["holidays"].find_one({"tenant_id": tenant_id, "date": payload["date"]})
        if existing:
             # Docs say "Validate that the same holiday doesn't already exist on the same date"
             # Strict: Only one holiday per date? Or same name?
             # "Validate that the same holiday doesn't already exist".
             # Usually means name + date.
             # usage summary: "Prevent duplicate holidays on the same date" -> implied strict per date.
             # I'll raise if date occupied.
             raise HolidayError("A holiday already exists on this date")
             
        hid = f"hol_{uuid.uuid4().hex[:8]}"
        doc = payload.copy()
        doc.update({
            "id": hid,
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        db["holidays"].insert_one(doc)
        return {"data": self._enrich_status(self._sanitize(doc))}

    def update_holiday(self, tenant_id: str, holiday_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        curr = self._find_holiday(db, tenant_id, holiday_id)
        
        # Check duplicate date if changed
        if "date" in payload and payload["date"] != curr.get("date"):
             existing = db["holidays"].find_one({"tenant_id": tenant_id, "date": payload["date"]})
             if existing:
                 raise HolidayError("A holiday already exists on this date")

        updates = payload.copy()
        if "id" in updates: del updates["id"]
        if "tenant_id" in updates: del updates["tenant_id"]
        
        updates["updated_at"] = datetime.utcnow()
        
        db["holidays"].update_one({"_id": curr["_id"]}, {"$set": updates})
        return self.get_holiday_by_id(tenant_id, holiday_id)

    def delete_holiday(self, tenant_id: str, holiday_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        res = db["holidays"].delete_one({"id": holiday_id, "tenant_id": tenant_id})
        if res.deleted_count == 0:
             raise HolidayError("Holiday not found", status_code=404)
        return {"success": True}

    # ------------------------------------------------------------------
    # 2. Calendar & Validation
    # ------------------------------------------------------------------
    def get_calendar(self, tenant_id: str, year: str, month: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id, "date": {"$regex": f"^{year}"}}
        if month:
             match["date"] = {"$regex": f"^{year}-{month}"}
             
        cursor = db["holidays"].find(match).sort("date", 1)
        holidays = []
        counts = {"total": 0, "national": 0, "festival": 0, "optional": 0}
        
        for doc in cursor:
             d = self._sanitize(doc)
             # Add day number
             try:
                 dt = datetime.strptime(d["date"], "%Y-%m-%d")
                 d["day"] = dt.day
             except: d["day"] = 0
             
             holidays.append(d)
             counts["total"] += 1
             t = d.get("type", "").lower()
             if "national" in t: counts["national"] += 1
             elif "festival" in t: counts["festival"] += 1
             elif "optional" in t: counts["optional"] += 1
             
        return {"data": {
            "year": int(year),
            "month": int(month) if month else 0,
            "holidays": holidays,
            "summary": counts
        }}

    def validate_date(self, tenant_id: str, date: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["holidays"].find_one({"tenant_id": tenant_id, "date": date})
        return {"data": {
            "is_holiday": bool(doc),
            "holiday": self._enrich_status(self._sanitize(doc)) if doc else None
        }}

    # ------------------------------------------------------------------
    # 3. Reports
    # ------------------------------------------------------------------
    def get_stats(self, tenant_id: str, year: Optional[str] = None) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        year = year or datetime.utcnow().strftime("%Y")
        match = {"tenant_id": tenant_id, "date": {"$regex": f"^{year}"}}
        
        # Aggregation
        pipeline_stats = [
             {"$match": match},
             {"$group": {
                  "_id": None,
                  "total": {"$sum": 1},
                  # Count by type
                  # ...
             }}
        ]
        
        total = db["holidays"].count_documents(match)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Upcoming in this year
        upcoming = db["holidays"].count_documents({**match, "date": {"$gt": today}})
        past = db["holidays"].count_documents({**match, "date": {"$lte": today}})
        
        # By Type
        by_type = [
            {"type": r["_id"], "count": r["count"]}
            for r in db["holidays"].aggregate([
                {"$match": match},
                {"$group": {"_id": "$type", "count": {"$sum": 1}}}
            ])
        ]
        
        # By Month
        # Need to project substring of date
        by_month = []
        pipeline_month = [
            {"$match": match},
            {"$project": {"month": {"$substr": ["$date", 5, 2]}}},
            {"$group": {"_id": "$month", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        month_names = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        for r in db["holidays"].aggregate(pipeline_month):
             try:
                 m_int = int(r["_id"])
                 by_month.append({
                     "month": m_int,
                     "count": r["count"],
                     "name": month_names[m_int] if 1 <= m_int <= 12 else "Unknown"
                 })
             except: pass

        return {"data": {
            "total": total,
            "upcoming": upcoming,
            "past": past,
            "by_type": by_type,
            "by_month": by_month
        }}

    def export_holidays(self, tenant_id: str, format: str) -> Dict[str, Any]:
        return {"data": {"download_url": "https://storage.mock/holidays_export.csv", "filename": f"holidays.{format}"}}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_holiday(self, db, tenant_id, holiday_id):
        doc = db["holidays"].find_one({"id": holiday_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["holidays"].find_one({"_id": ObjectId(holiday_id), "tenant_id": tenant_id})
             except: pass
        if not doc:
             raise HolidayError("Holiday not found", status_code=404)
        return doc

    def _enrich_status(self, doc):
        # Calculate status
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if doc.get("date"):
             doc["status"] = "Upcoming" if doc["date"] > today else "Past"
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
            raise HolidayError(f"{name} is required")
        return value
