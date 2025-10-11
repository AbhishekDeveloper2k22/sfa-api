from sfa.database import client1
from bson import ObjectId
from typing import Dict, Any
from datetime import datetime
from sfa.utils.date_utils import build_audit_fields
import traceback

class AppFollowupService:
    def __init__(self):
        self.talbros_db = client1['talbros']
        self.followups = self.talbros_db['followups']
        self.customers = self.talbros_db['customers']
        self.leads = self.talbros_db['leads']
        self.all_types = self.talbros_db['all_type']

    def add_followup(self, user_id: str, followup_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Extract data from request
            followup_date = followup_data.get("followup_date")
            followup_time = followup_data.get("followup_time")
            network_type = followup_data.get("network_type")  # "lead" or "non-lead"
            customer_type = followup_data.get("customer_type")
            entity_id = followup_data.get("entity_id")  # customer_id or lead_id
            remarks = followup_data.get("remarks", "")

            # Validate required fields
            if not followup_date:
                return {"success": False, "message": "Followup date is required", "error": {"code": "VALIDATION_ERROR"}}
            
            if not followup_time:
                return {"success": False, "message": "Followup time is required", "error": {"code": "VALIDATION_ERROR"}}
            
            if not network_type or network_type not in ["lead", "non-lead"]:
                return {"success": False, "message": "Network type must be 'lead' or 'non-lead'", "error": {"code": "VALIDATION_ERROR"}}
            
            if not entity_id:
                return {"success": False, "message": "Entity ID is required", "error": {"code": "VALIDATION_ERROR"}}

            # Validate entity_id format
            try:
                entity_obj_id = ObjectId(entity_id)
            except Exception:
                return {"success": False, "message": "Invalid entity ID format", "error": {"code": "VALIDATION_ERROR"}}

            # Verify entity exists and is assigned to user
            entity_name = ""
            entity_company = ""
            entity_phone = ""
            
            if network_type == "lead":
                # Check if lead exists and is assigned to user
                lead = self.leads.find_one({
                    "_id": entity_obj_id,
                    "assign_user_id": user_id,
                    "del": {"$ne": 1}
                })
                if not lead:
                    return {"success": False, "message": "Lead not found or not assigned to you", "error": {"code": "ENTITY_NOT_FOUND"}}
                
                entity_name = lead.get("name", "")
                entity_company = lead.get("company_name", "")
                entity_phone = lead.get("mobile") or lead.get("phone", "")
                
            else:  # non-lead (customer)
                # Check if customer exists and is assigned to user
                customer = self.customers.find_one({
                    "_id": entity_obj_id,
                    "assign_user_id": user_id,
                    "del": {"$ne": 1}
                })
                if not customer:
                    return {"success": False, "message": "Customer not found or not assigned to you", "error": {"code": "ENTITY_NOT_FOUND"}}
                
                entity_name = customer.get("name", "")
                entity_company = customer.get("company_name", "")
                entity_phone = customer.get("mobile") or customer.get("phone", "")

            # Get customer type name if provided
            customer_type_name = ""
            if customer_type:
                customer_type_doc = self.all_types.find_one({
                    "customer_type": customer_type,
                    "del": {"$ne": 1}
                })
                if customer_type_doc:
                    customer_type_name = customer_type_doc.get("name", "")

            # Create followup document
            created_fields = build_audit_fields(prefix="created", by=user_id, timezone="Asia/Kolkata")
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
            
            followup_doc = {
                "followup_date": followup_date,
                "followup_time": followup_time,
                "network_type": network_type,
                "customer_type": customer_type,
                "customer_type_name": customer_type_name,
                "entity_id": entity_id,
                "entity_name": entity_name,
                "entity_company": entity_company,
                "entity_phone": entity_phone,
                "remarks": remarks,
                "status": "pending",  # pending, completed, cancelled
                "del": 0
            }
            
            # Add audit fields
            followup_doc.update(created_fields)
            followup_doc.update(updated_fields)

            # Insert followup
            result = self.followups.insert_one(followup_doc)
            followup_id = str(result.inserted_id)

            return {
                "success": True,
                "data": {
                    "followup_id": followup_id,
                    "followup_date": followup_date,
                    "followup_time": followup_time,
                    "network_type": network_type,
                    "customer_type_name": customer_type_name,
                    "entity_name": entity_name,
                    "entity_company": entity_company,
                    "remarks": remarks,
                    "status": "pending"
                }
            }

        except Exception as e:
            return {"success": False, "message": f"Failed to add followup: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e), "traceback": traceback.format_exc()}}

    def get_followup_list(self, user_id: str, status_filter: str = "all", page: int = 1, limit: int = 20) -> Dict[str, Any]:
        try:
            # Build query
            query = {
                "created_by": user_id,
                "del": {"$ne": 1}
            }
            
            # Apply status filter
            if status_filter == "pending":
                query["status"] = "pending"
            elif status_filter == "completed":
                query["status"] = "completed"
            elif status_filter == "cancelled":
                query["status"] = "cancelled"
            # For "all", no additional status filter needed
            
            # Calculate skip for pagination
            skip = (page - 1) * limit
            
            # Get total count
            total_count = self.followups.count_documents(query)
            
            # Get followups with pagination
            followups_cursor = self.followups.find(query).skip(skip).limit(limit).sort("followup_date", -1)
            followups = list(followups_cursor)
            
            # Format followup list
            followup_list = []
            for followup in followups:
                followup_data = {
                    "id": str(followup["_id"]),
                    "followup_date": followup.get("followup_date", ""),
                    "followup_time": followup.get("followup_time", ""),
                    "network_type": followup.get("network_type", ""),
                    "customer_type": followup.get("customer_type"),
                    "customer_type_name": followup.get("customer_type_name", ""),
                    "entity_id": followup.get("entity_id", ""),
                    "entity_name": followup.get("entity_name", ""),
                    "entity_company": followup.get("entity_company", ""),
                    "entity_phone": followup.get("entity_phone", ""),
                    "remarks": followup.get("remarks", ""),
                    "status": followup.get("status", "pending"),
                    "created_at": followup.get("created_at", ""),
                    "created_at_time": followup.get("created_at_time", "")
                }
                followup_list.append(followup_data)
            
            # Count by status for summary
            status_counts = {
                "all": total_count,
                "pending": 0,
                "completed": 0,
                "cancelled": 0
            }
            
            # Get status counts
            try:
                pending_count = self.followups.count_documents({
                    "created_by": user_id,
                    "status": "pending",
                    "del": {"$ne": 1}
                })
                completed_count = self.followups.count_documents({
                    "created_by": user_id,
                    "status": "completed",
                    "del": {"$ne": 1}
                })
                cancelled_count = self.followups.count_documents({
                    "created_by": user_id,
                    "status": "cancelled",
                    "del": {"$ne": 1}
                })
                status_counts["pending"] = pending_count
                status_counts["completed"] = completed_count
                status_counts["cancelled"] = cancelled_count
            except Exception:
                pass
            
            return {
                "success": True,
                "data": {
                    "followups": followup_list,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total_count,
                        "total_pages": (total_count + limit - 1) // limit
                    },
                    "status_counts": status_counts
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Failed to get followup list: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e), "traceback": traceback.format_exc()}}

    def update_followup_status(self, user_id: str, followup_id: str, status: str, remarks: str = "") -> Dict[str, Any]:
        try:
            # Validate status
            if status not in ["pending", "completed", "cancelled"]:
                return {"success": False, "message": "Invalid status. Must be 'pending', 'completed', or 'cancelled'", "error": {"code": "VALIDATION_ERROR"}}

            # Validate followup_id format
            try:
                followup_obj_id = ObjectId(followup_id)
            except Exception:
                return {"success": False, "message": "Invalid followup ID format", "error": {"code": "VALIDATION_ERROR"}}

            # Check if followup exists and belongs to user
            followup = self.followups.find_one({
                "_id": followup_obj_id,
                "created_by": user_id,
                "del": {"$ne": 1}
            })
            if not followup:
                return {"success": False, "message": "Followup not found or not created by you", "error": {"code": "FOLLOWUP_NOT_FOUND"}}

            # Update followup
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
            status_changed_fields = build_audit_fields(prefix="status_changed", by=user_id, timezone="Asia/Kolkata")
            
            # Get current status for history
            current_status = followup.get("status", "")
            
            # Prepare status history entry
            status_history_entry = {
                "from_status": current_status,
                "to_status": status,
                **status_changed_fields,
                "remarks": remarks if remarks else ""
            }
            
            update_data = {
                "status": status
            }
            
            if remarks:
                update_data["completion_remarks"] = remarks
            
            # Add status change tracking fields
            update_data.update(status_changed_fields)
            
            # Add audit fields
            update_data.update(updated_fields)
            
            # Perform update with both $set and $push operations
            result = self.followups.update_one(
                {"_id": followup_obj_id},
                {
                    "$set": update_data,
                    "$push": {"status_history": status_history_entry}
                }
            )

            if result.modified_count == 0:
                return {"success": False, "message": "Failed to update followup status", "error": {"code": "UPDATE_FAILED"}}

            return {
                "success": True,
                "data": {
                    "followup_id": followup_id,
                    "status": status,
                    "previous_status": current_status,
                    **status_changed_fields,
                    **updated_fields,
                }
            }

        except Exception as e:
            return {"success": False, "message": f"Failed to update followup status: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e), "traceback": traceback.format_exc()}}

    def get_followup_status_history(self, user_id: str, followup_id: str) -> Dict[str, Any]:
        try:
            # Validate followup_id format
            try:
                followup_obj_id = ObjectId(followup_id)
            except Exception:
                return {"success": False, "message": "Invalid followup ID format", "error": {"code": "VALIDATION_ERROR"}}

            # Check if followup exists and belongs to user
            followup = self.followups.find_one({
                "_id": followup_obj_id,
                "created_by": user_id,
                "del": {"$ne": 1}
            })
            if not followup:
                return {"success": False, "message": "Followup not found or not created by you", "error": {"code": "FOLLOWUP_NOT_FOUND"}}

            # Get status history
            status_history = followup.get("status_history", [])
            
            return {
                "success": True,
                "data": {
                    "followup_id": followup_id,
                    "current_status": followup.get("status", ""),
                    "status_history": status_history,
                    "total_status_changes": len(status_history)
                }
            }

        except Exception as e:
            return {"success": False, "message": f"Failed to get followup status history: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e), "traceback": traceback.format_exc()}}
