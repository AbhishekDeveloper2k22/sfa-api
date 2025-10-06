from typing import Dict, Any, Optional
from datetime import datetime
from sfa.database import client1
import pytz
from bson import ObjectId
from sfa.utils.date_utils import build_audit_fields
import os
import uuid


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
            ok, missing = self._required(payload, ["company_name","type_id" ,"mobile", "source","contact_person", "pincode", "city", "state"])
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

    def upload_lead_image(self, user_id: str, lead_id: str, image_file) -> Dict[str, Any]:
        """Upload image for a specific lead"""
        try:
            # Validate lead_id
            if not lead_id:
                return {"success": False, "message": "Lead ID is required", "error": {"code": "VALIDATION_ERROR"}}
            
            # Verify lead exists
            try:
                lead = self.leads_collection.find_one({"_id": ObjectId(lead_id), "del": {"$ne": 1}})
                if not lead:
                    return {"success": False, "message": "Lead not found", "error": {"code": "NOT_FOUND"}}
            except Exception as e:
                return {"success": False, "message": f"Invalid lead ID: {str(e)}", "error": {"code": "INVALID_ID"}}
            
            # Create upload directory if it doesn't exist
            upload_dir = "uploads/sfa_uploads/leads"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            file_extension = os.path.splitext(image_file.filename)[1].lower()
            unique_filename = f"lead_{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save image file
            try:
                # Reset file pointer to beginning
                image_file.file.seek(0)
                
                with open(file_path, "wb") as buffer:
                    content = image_file.file.read()
                    buffer.write(content)
                    
            except Exception as e:
                return {
                    "success": False,
                    "message": "Failed to save image file",
                    "error": {"code": "FILE_SAVE_ERROR", "details": f"Could not save image: {str(e)}"}
                }
            
            # Update lead document with image info
            now_iso = datetime.now(self.timezone).isoformat()
            normalized_path = file_path.replace("\\", "/")
            
            update_data = {
                "image": unique_filename,
                "image_path": normalized_path,
                "image_updated_at": now_iso,
                "updated_at": now_iso
            }
            
            # Add audit fields
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
            update_data.update(updated_fields)
            
            result = self.leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                return {"success": False, "message": "Lead not found for update", "error": {"code": "NOT_FOUND"}}
            
            return {
                "success": True,
                "message": "Lead image uploaded successfully",
                "data": {
                    "lead_id": lead_id,
                    "image_filename": unique_filename,
                    "image_path": normalized_path,
                    "uploaded_at": now_iso
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Failed to upload image: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e)}}


