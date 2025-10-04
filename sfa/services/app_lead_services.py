from typing import Dict, Any, Optional
from datetime import datetime
from sfa.database import client1
import pytz
from bson import ObjectId
from sfa.utils.date_utils import build_audit_fields


class AppLeadService:
    # Lead create ke liye basic validation + DB insert
    def __init__(self):
        self.client_database = client1["talbros"]
        self.leads_collection = self.client_database["leads"]
        self.timezone = pytz.timezone("Asia/Kolkata")

    def _required(self, payload: Dict[str, Any], fields):
        for f in fields:
            if f not in payload or payload[f] in [None, "", []]:
                return False, f
        return True, None

    def create_lead(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            ok, missing = self._required(payload, ["name", "mobile", "source"])
            if not ok:
                return {"success": False, "message": f"{missing} is required", "error": {"code": "VALIDATION_ERROR"}}

            # Deduplicate on mobile if desired
            existing = self.leads_collection.find_one({"mobile": payload["mobile"], "del": {"$ne": 1}})
            if existing:
                return {"success": False, "message": "Lead already exists", "error": {"code": "DUPLICATE", "details": {"lead_id": str(existing.get("_id"))}}}

            created_fields = build_audit_fields(prefix="created", by=user_id, timezone="Asia/Kolkata")
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")

            lead_doc = {
                "name": payload.get("name"),
                "mobile": payload.get("mobile"),
                "email": payload.get("email"),
                "company": payload.get("company"),
                "source": payload.get("source"),
                "status": payload.get("status", "new"),
                "notes": payload.get("notes", ""),
                "address": payload.get("address"),
                "pincode": payload.get("pincode"),
                "city": payload.get("city"),
                "state": payload.get("state"),
                "country": payload.get("country", "India"),
                "created_at": datetime.now(self.timezone).isoformat(),
                "updated_at": datetime.now(self.timezone).isoformat(),
                "del": 0,
                **created_fields,
                **updated_fields,
            }

            result = self.leads_collection.insert_one(lead_doc)
            if not result.inserted_id:
                return {"success": False, "message": "Failed to create lead", "error": {"code": "DATABASE_ERROR"}}

            return {
                "success": True,
                "message": "Lead created successfully",
                "data": {"lead_id": str(result.inserted_id)}
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to create lead: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e)}}


