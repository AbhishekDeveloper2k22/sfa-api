from typing import Dict, Any, Optional
from datetime import datetime
from sfa.database import client1
import pytz
from bson import ObjectId
from sfa.utils.date_utils import build_audit_fields
from sfa.utils.code_generator import generate_lead_code
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

            # Generate unique lead code and update the document
            lead_id_str = str(result.inserted_id)
            lead_code = generate_lead_code(
                lead_date=created_fields.get("created_at")
            )
            
            # Update lead with lead_code
            self.leads_collection.update_one(
                {"_id": result.inserted_id},
                {"$set": {"lead_code": lead_code}}
            )

            return {
                "success": True,
                "message": "Lead created successfully",
                "data": {
                    "lead_id": lead_id_str,
                    "lead_code": lead_code
                }
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

    def list_leads(self, user_id: str, page: int = 1, limit: int = 20, status: str = None, 
                   source: str = None, search: str = None, date_from: str = None, date_to: str = None) -> Dict[str, Any]:
        """Get list of leads with filters and pagination"""
        try:
            # Build query
            query: Dict[str, Any] = {"del": {"$ne": 1}}
            
            # Filter by created_by (user's own leads)
            query["created_by"] = user_id
            
            # Status filter (skip if "all" or empty)
            if status and status != "all":
                query["status"] = status
            
            # Source filter
            if source:
                query["source"] = source
            
            # Date range filter
            if date_from:
                query["created_at"] = {"$gte": date_from}
            if date_to:
                if "created_at" in query:
                    query["created_at"]["$lte"] = date_to
                else:
                    query["created_at"] = {"$lte": date_to}
            
            # Search filter (mobile, email, city)
            if search:
                search_pattern = {"$regex": search, "$options": "i"}
                query["$or"] = [
                    {"mobile": search_pattern},
                    {"email": search_pattern},
                    {"city": search_pattern},
                    {"name": search_pattern}
                ]
            
            # Count total documents
            total = self.leads_collection.count_documents(query)
            
            # Calculate pagination
            skip = (page - 1) * limit
            total_pages = (total + limit - 1) // limit
            
            # Fetch leads
            leads = list(self.leads_collection.find(query)
                        .sort("created_at", -1)
                        .skip(skip)
                        .limit(limit))
            
            # Format lead data
            lead_list = []
            for lead in leads:
                lead_list.append({
                    "lead_id": str(lead.get("_id")),
                    "lead_code": lead.get("lead_code", ""),
                    "name": lead.get("name"),
                    "mobile": lead.get("mobile"),
                    "email": lead.get("email"),
                    "company": lead.get("company"),
                    "source": lead.get("source"),
                    "status": lead.get("status", "new"),
                    "notes": lead.get("notes", ""),
                    "address": lead.get("address"),
                    "pincode": lead.get("pincode"),
                    "city": lead.get("city"),
                    "state": lead.get("state"),
                    "country": lead.get("country", "India"),
                    "created_at": lead.get("created_at"),
                    "created_time": lead.get("created_time"),
                    "updated_at": lead.get("updated_at"),
                    "updated_time": lead.get("updated_time")
                })
            
            # Status counts for filter badges
            status_list = ["new", "contacted", "qualified", "converted", "lost"]
            counts = {}
            for s in status_list:
                count_query = {**{k: v for k, v in query.items() if k != "status"}, "status": s}
                counts[s] = self.leads_collection.count_documents(count_query)
            counts["all"] = self.leads_collection.count_documents({k: v for k, v in query.items() if k != "status"})
            
            return {
                "success": True,
                "data": {
                    "list": lead_list,
                    "counts": counts,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total,
                        "totalPages": total_pages,
                        "hasNext": page < total_pages,
                        "hasPrev": page > 1
                    }
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list leads: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_lead_detail(self, user_id: str, lead_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific lead"""
        try:
            # Validate and fetch lead
            try:
                lead = self.leads_collection.find_one({
                    "_id": ObjectId(lead_id),
                    "del": {"$ne": 1}
                })
            except Exception:
                return {
                    "success": False,
                    "message": "Invalid lead_id",
                    "error": {"code": "INVALID_ID", "details": "lead_id must be a valid ObjectId"}
                }
            
            if not lead:
                return {
                    "success": False,
                    "message": "Lead not found",
                    "error": {"code": "NOT_FOUND", "details": "Lead does not exist"}
                }
            
            # Format lead details
            detail = {
                "lead_id": str(lead.get("_id")),
                "lead_code": lead.get("lead_code", ""),
                
                # Lead Information
                "lead_information": {
                    "company_name": lead.get("company") or lead.get("company_name"),
                    "contact_person": lead.get("name") or lead.get("contact_person"),
                    "lead_type": lead.get("type") or "Distributor",
                    "source": lead.get("source"),
                    "status": lead.get("status", "new")
                },
                
                # Contact Information
                "contact_information": {
                    "mobile": lead.get("mobile"),
                    "email": lead.get("email")
                },
                
                # Address Information
                "address_information": {
                    "street": lead.get("address"),
                    "city": lead.get("city"),
                    "district": lead.get("district", ""),
                    "state": lead.get("state"),
                    "pincode": lead.get("pincode"),
                    "country": lead.get("country", "India")
                },
                
                # Description/Notes
                "description": lead.get("notes", ""),
                
                # Metadata
                "created_at": lead.get("created_at"),
                "created_time": lead.get("created_time"),
                "updated_at": lead.get("updated_at"),
                "updated_time": lead.get("updated_time")
            }
            
            return {
                "success": True,
                "data": detail
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get lead detail: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }


