from datetime import datetime
from typing import Dict, Any
import os
import uuid
import io

from bson import ObjectId

# Optional PIL import - will be handled gracefully if not available
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

from trust_rewards.database import client1
from trust_rewards.utils.datetime_utils import important_utilities
from trust_rewards.utils.common import AuditUtils


class WebMasterService:
    def __init__(self) -> None:
        self.db = client1["trust_rewards"]
        self.points_master = self.db["points_master"]
        self.categories = self.db["category_master"]
        self.sub_categories = self.db["sub_category_master"]
        self.product_master = self.db["product_master"]
        self.users = self.db["users"]

    def add_points_master(self, payload: Dict[str, Any], created_by: int = 1) -> Dict[str, Any]:
        """Create a new points master record with server-side validations."""
        try:
            name = (payload.get("name") or "").strip()
            category = (payload.get("category") or "").strip()
            value = payload.get("value")
            description = (payload.get("description") or "").strip()
            status = (payload.get("status") or "").strip().lower()
            valid_from = payload.get("valid_from")
            valid_to = payload.get("valid_to")

            # Validate name
            if not (2 <= len(name) <= 50):
                return {
                    "success": False,
                    "message": "Name must be 2–50 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_name"},
                }

            # Enforce uniqueness (case-insensitive)
            existing = self.points_master.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
            if existing:
                return {
                    "success": False,
                    "message": "Name already exists",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_name"},
                }

            # Validate category
            if not category:
                return {
                    "success": False,
                    "message": "Category is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_category"},
                }

            # Validate value
            if not isinstance(value, int) or value < 1 or value > 10000:
                return {
                    "success": False,
                    "message": "Value must be an integer between 1 and 10000",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_value"},
                }

            # Validate description
            if not (10 <= len(description) <= 500):
                return {
                    "success": False,
                    "message": "Description must be 10–500 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_description"},
                }

            # Validate status
            if status not in ("active", "inactive"):
                return {
                    "success": False,
                    "message": "Status must be one of active | inactive",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_status"},
                }

            # Validate dates
            try:
                vf = datetime.strptime(valid_from, "%Y-%m-%d").date()
                vt = datetime.strptime(valid_to, "%Y-%m-%d").date()
            except Exception:
                return {
                    "success": False,
                    "message": "Dates must be ISO YYYY-MM-DD",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_date_format"},
                }

            today = datetime.now().date()
            if vf < today:
                return {
                    "success": False,
                    "message": "validFrom cannot be in the past",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_validFrom"},
                }
            if vt <= vf:
                return {
                    "success": False,
                    "message": "validTo must be strictly after validFrom",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_validTo"},
                }

            # Use AuditUtils for consistent audit fields
            create_meta = AuditUtils.build_create_meta(created_by)
            
            doc = {
                "name": name,
                "name_lower": name.lower(),
                "category": category,
                "value": value,
                "description": description,
                "status": status,
                "valid_from": vf.strftime("%Y-%m-%d"),
                "valid_to": vt.strftime("%Y-%m-%d"),
                **create_meta  # Spread created_at, created_time, created_by
            }

            result = self.points_master.insert_one(doc)

            return {
                "success": True,
                "message": "Points master added successfully",
                "data": {
                    "_id": str(result.inserted_id),
                    "name": name,
                    "category": category,
                    "value": value,
                    "description": description,
                    "status": status,
                    "validFrom": doc["valid_from"],
                    "validTo": doc["valid_to"],
                    "created_at": create_meta["created_at"],
                    "created_time": create_meta["created_time"],
                    "created_by": create_meta["created_by"],
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add points master: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def update_points_master(self, payload: Dict[str, Any], created_by: int = 1) -> Dict[str, Any]:
        """Update an existing points master record with server-side validations."""
        try:
            # Extract record ID
            record_id = payload.get('_id') or payload.get('id')
            if not record_id:
                return {
                    "success": False,
                    "message": "Record ID is required for update",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_record_id"},
                }

            # Check if record exists
            existing_record = self.points_master.find_one({"_id": ObjectId(record_id)})
            if not existing_record:
                return {
                    "success": False,
                    "message": "Points master record not found",
                    "error": {"code": "VALIDATION_ERROR", "details": "record_not_found"},
                }

            # Extract and validate input data
            name = (payload.get("name") or "").strip()
            category = (payload.get("category") or "").strip()
            value = payload.get("value")
            description = (payload.get("description") or "").strip()
            status = (payload.get("status") or "").strip().lower()
            valid_from = payload.get("valid_from")
            valid_to = payload.get("valid_to")

            # Validate name
            if not (2 <= len(name) <= 50):
                return {
                    "success": False,
                    "message": "Name must be 2–50 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_name"},
                }

            # Enforce uniqueness (case-insensitive) - exclude current record
            existing = self.points_master.find_one({
                "name": {"$regex": f"^{name}$", "$options": "i"},
                "_id": {"$ne": ObjectId(record_id)}
            })
            if existing:
                return {
                    "success": False,
                    "message": "Name already exists",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_name"},
                }

            # Validate category
            if not category:
                return {
                    "success": False,
                    "message": "Category is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_category"},
                }

            # Validate value
            if not isinstance(value, int) or value < 1 or value > 10000:
                return {
                    "success": False,
                    "message": "Value must be an integer between 1 and 10000",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_value"},
                }

            # Validate description
            if not (10 <= len(description) <= 500):
                return {
                    "success": False,
                    "message": "Description must be 10–500 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_description"},
                }

            # Validate status
            if status not in ("active", "inactive"):
                return {
                    "success": False,
                    "message": "Status must be one of active | inactive",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_status"},
                }

            # Validate dates
            try:
                vf = datetime.strptime(valid_from, "%Y-%m-%d").date()
                vt = datetime.strptime(valid_to, "%Y-%m-%d").date()
            except Exception:
                return {
                    "success": False,
                    "message": "Dates must be ISO YYYY-MM-DD",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_date_format"},
                }

            today = datetime.now().date()
            if vf < today:
                return {
                    "success": False,
                    "message": "validFrom cannot be in the past",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_validFrom"},
                }
            if vt <= vf:
                return {
                    "success": False,
                    "message": "validTo must be strictly after validFrom",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_validTo"},
                }

            # Use AuditUtils for consistent audit fields
            update_meta = AuditUtils.build_update_meta(created_by)
            
            # Update record
            update_doc = {
                "name": name,
                "name_lower": name.lower(),
                "category": category,
                "value": value,
                "description": description,
                "status": status,
                "valid_from": vf.strftime("%Y-%m-%d"),
                "valid_to": vt.strftime("%Y-%m-%d"),
                **update_meta  # Spread updated_at, updated_time, updated_by
            }

            result = self.points_master.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": update_doc}
            )

            if result.modified_count == 0:
                return {
                    "success": False,
                    "message": "No changes made to the record",
                    "error": {"code": "UPDATE_ERROR", "details": "no_changes"},
                }

            # Get updated record
            updated_record = self.points_master.find_one({"_id": ObjectId(record_id)})
            updated_record['_id'] = str(updated_record['_id'])

            # Add created_by_name
            created_by_id = updated_record.get('created_by')
            if created_by_id:
                user = self.users.find_one({"user_id": created_by_id})
                if user:
                    updated_record['created_by_name'] = user.get('username', 'Unknown')
                else:
                    updated_record['created_by_name'] = 'Unknown'
            else:
                updated_record['created_by_name'] = 'Unknown'

            return {
                "success": True,
                "message": "Points master updated successfully",
                "data": {
                    "_id": updated_record['_id'],
                    "name": name,
                    "category": category,
                    "value": value,
                    "description": description,
                    "status": status,
                    "validFrom": update_doc["valid_from"],
                    "validTo": update_doc["valid_to"],
                    "created_at": updated_record.get("created_at"),
                    "created_time": updated_record.get("created_time"),
                    "created_by": updated_record.get("created_by"),
                    "created_by_name": updated_record.get("created_by_name"),
                    "updated_at": update_meta["updated_at"],
                    "updated_time": update_meta["updated_time"],
                    "updated_by": update_meta["updated_by"],
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update points master: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_points_master_list(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get paginated list of points master records with filtering."""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'all')
            category = filters.get('category', '')
            search = filters.get('search', '')

            # Build query
            query = {}
            
            # Status filter
            if status != 'all':
                query['status'] = status
            
            # Category filter
            if category:
                query['category'] = {"$regex": category, "$options": "i"}
            
            # Search filter (search in name and description)
            if search:
                query['$or'] = [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]

            # Get total count
            total_count = self.points_master.count_documents(query)
            
            # Get records with pagination
            records = list(
                self.points_master.find(query)
                .skip(skip)
                .limit(limit)
                .sort("created_at", -1)
            )
            
            # Convert ObjectId to string and add created_by_name / updated_by_name
            datetime_utils = important_utilities()
            
            for record in records:
                record['_id'] = str(record['_id'])
                
                # Combine created_at and created_time into created_datetime
                created_at = record.get('created_at', '')
                created_time = record.get('created_time', '')
                if created_at and created_time:
                    try:
                        created_datetime = datetime.strptime(f"{created_at} {created_time}", "%Y-%m-%d %H:%M:%S")
                        record['created_datetime'] = created_datetime.strftime("%d-%m-%Y %I:%M %p")
                    except:
                        record['created_datetime'] = f"{created_at} {created_time}"
                else:
                    record['created_datetime'] = None
                
                # Combine updated_at and updated_time into updated_datetime if available
                updated_at = record.get('updated_at')
                updated_time = record.get('updated_time')
                if updated_at and updated_time:
                    try:
                        updated_datetime = datetime.strptime(f"{updated_at} {updated_time}", "%Y-%m-%d %H:%M:%S")
                        record['updated_datetime'] = updated_datetime.strftime("%d-%m-%Y %I:%M %p")
                    except:
                        record['updated_datetime'] = f"{updated_at} {updated_time}"
                else:
                    record['updated_datetime'] = None
                
                # Get created_by_name from users collection
                created_by_id = record.get('created_by')
                if created_by_id:
                    user = self.users.find_one({"user_id": created_by_id})
                    if user:
                        record['created_by_name'] = user.get('username', 'Unknown')
                    else:
                        record['created_by_name'] = 'Unknown'
                else:
                    record['created_by_name'] = 'Unknown'

                # Get updated_by_name from users collection if available
                updated_by_id = record.get('updated_by')
                if updated_by_id:
                    upd_user = self.users.find_one({"user_id": updated_by_id})
                    if upd_user:
                        record['updated_by_name'] = upd_user.get('username', 'Unknown')
                    else:
                        record['updated_by_name'] = 'Unknown'
                else:
                    record['updated_by_name'] = None

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Get stats data
            stats = self.get_points_master_stats()

            return {
                "success": True,
                "data": {
                    "records": records,
                    "stats": stats,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get points master list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_points_master_stats(self) -> Dict[str, Any]:
        """Get points master statistics for dashboard."""
        try:
            # Total points master records
            total_records = self.points_master.count_documents({})
            
            # Active records
            active_records = self.points_master.count_documents({"status": "active"})
            
            # Inactive records
            inactive_records = self.points_master.count_documents({"status": "inactive"})
            
            # Total points value (sum of all active records)
            pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {"_id": None, "total_points": {"$sum": "$value"}}}
            ]
            points_result = list(self.points_master.aggregate(pipeline))
            total_points = points_result[0]["total_points"] if points_result else 0
            
            # Categories count
            categories_pipeline = [
                {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            categories = list(self.points_master.aggregate(categories_pipeline))
            
            return {
                "total_records": total_records,
                "active_records": active_records,
                "inactive_records": inactive_records,
                "total_points": total_points,
                "categories": categories
            }
            
        except Exception as e:
            return {
                "total_records": 0,
                "active_records": 0,
                "inactive_records": 0,
                "total_points": 0,
                "categories": []
            }

    def add_category(self, payload: Dict[str, Any], created_by: int = 1) -> Dict[str, Any]:
        """Add a new category with validations."""
        try:
            category_name = (payload.get("category_name") or "").strip()
            description = (payload.get("description") or "").strip()

            # Validate category_name
            if not (2 <= len(category_name) <= 50):
                return {
                    "success": False,
                    "message": "Category name must be 2–50 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_category_name"},
                }

            # Enforce uniqueness (case-insensitive)
            existing = self.categories.find_one({"category_name": {"$regex": f"^{category_name}$", "$options": "i"}})
            if existing:
                return {
                    "success": False,
                    "message": "Category name already exists",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_category_name"},
                }

            # Validate description
            if not (5 <= len(description) <= 200):
                return {
                    "success": False,
                    "message": "Description must be 5–200 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_description"},
                }

            # Use AuditUtils for consistent audit fields
            create_meta = AuditUtils.build_create_meta(created_by)
            
            doc = {
                "category_name": category_name,
                "category_name_lower": category_name.lower(),
                "description": description,
                "status": "active",
                **create_meta  # Spread created_at, created_time, created_by
            }

            result = self.categories.insert_one(doc)

            return {
                "success": True,
                "message": "Category added successfully",
                "data": {
                    "_id": str(result.inserted_id),
                    "category_name": category_name,
                    "description": description,
                    "status": "active",
                    "created_at": create_meta["created_at"],
                    "created_time": create_meta["created_time"],
                    "created_by": create_meta["created_by"],
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add category: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_categories_list(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get paginated list of categories with filtering."""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'all')
            search = filters.get('search', '')

            # Build query
            query = {}
            
            # Status filter
            if status != 'all':
                query['status'] = status
            
            # Search filter (search in category_name and description)
            if search:
                query['$or'] = [
                    {"category_name": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]

            # Get total count
            total_count = self.categories.count_documents(query)
            
            # Get records with pagination
            records = list(
                self.categories.find(query)
                .skip(skip)
                .limit(limit)
                .sort("created_at", -1)
            )
            
            # Convert ObjectId to string and add created_by_name / updated_by_name
            datetime_utils = important_utilities()
            
            for record in records:
                record['_id'] = str(record['_id'])
                
                # Combine created_at and created_time into created_datetime
                created_at = record.get('created_at', '')
                created_time = record.get('created_time', '')
                if created_at and created_time:
                    try:
                        created_datetime = datetime.strptime(f"{created_at} {created_time}", "%Y-%m-%d %H:%M:%S")
                        record['created_datetime'] = created_datetime.strftime("%d-%m-%Y %I:%M %p")
                    except:
                        record['created_datetime'] = f"{created_at} {created_time}"
                else:
                    record['created_datetime'] = None
                
                # Combine updated_at and updated_time into updated_datetime if available
                updated_at = record.get('updated_at')
                updated_time = record.get('updated_time')
                if updated_at and updated_time:
                    try:
                        updated_datetime = datetime.strptime(f"{updated_at} {updated_time}", "%Y-%m-%d %H:%M:%S")
                        record['updated_datetime'] = updated_datetime.strftime("%d-%m-%Y %I:%M %p")
                    except:
                        record['updated_datetime'] = f"{updated_at} {updated_time}"
                else:
                    record['updated_datetime'] = None
                
                # Get created_by_name from users collection
                created_by_id = record.get('created_by')
                if created_by_id:
                    user = self.users.find_one({"user_id": created_by_id})
                    if user:
                        record['created_by_name'] = user.get('username', 'Unknown')
                    else:
                        record['created_by_name'] = 'Unknown'
                else:
                    record['created_by_name'] = 'Unknown'

                # Get updated_by_name from users collection if available
                updated_by_id = record.get('updated_by')
                if updated_by_id:
                    upd_user = self.users.find_one({"user_id": updated_by_id})
                    if upd_user:
                        record['updated_by_name'] = upd_user.get('username', 'Unknown')
                    else:
                        record['updated_by_name'] = 'Unknown'
                else:
                    record['updated_by_name'] = None

                # category_name_lower ye remove
                record.pop('category_name_lower', None)

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Get stats data
            stats = self.get_categories_stats()

            return {
                "success": True,
                "data": {
                    "records": records,
                    "stats": stats,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get categories list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def update_category(self, payload: Dict[str, Any], updated_by: int = 1) -> Dict[str, Any]:
        """Update an existing category with validations."""
        try:
            # Extract record ID
            record_id = payload.get('_id') or payload.get('id')
            if not record_id:
                return {
                    "success": False,
                    "message": "Record ID is required for update",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_record_id"},
                }

            # Check if record exists
            existing_record = self.categories.find_one({"_id": ObjectId(record_id)})
            if not existing_record:
                return {
                    "success": False,
                    "message": "Category not found",
                    "error": {"code": "VALIDATION_ERROR", "details": "record_not_found"},
                }

            # Extract and validate input data
            category_name = (payload.get("category_name") or "").strip()
            description = (payload.get("description") or "").strip()
            status = (payload.get("status") or "active").strip().lower()

            # Validate category_name
            if not (2 <= len(category_name) <= 50):
                return {
                    "success": False,
                    "message": "Category name must be 2–50 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_category_name"},
                }

            # Enforce uniqueness (case-insensitive) - exclude current record
            existing = self.categories.find_one({
                "category_name": {"$regex": f"^{category_name}$", "$options": "i"},
                "_id": {"$ne": ObjectId(record_id)}
            })
            if existing:
                return {
                    "success": False,
                    "message": "Category name already exists",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_category_name"},
                }

            # Validate description
            if not (5 <= len(description) <= 200):
                return {
                    "success": False,
                    "message": "Description must be 5–200 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_description"},
                }

            # Validate status
            if status not in ("active", "inactive"):
                return {
                    "success": False,
                    "message": "Status must be one of active | inactive",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_status"},
                }

            # Use AuditUtils for consistent audit fields
            update_meta = AuditUtils.build_update_meta(updated_by)
            
            # Update record
            update_doc = {
                "category_name": category_name,
                "category_name_lower": category_name.lower(),
                "description": description,
                "status": status,
                **update_meta  # Spread updated_at, updated_time, updated_by
            }

            result = self.categories.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": update_doc}
            )

            if result.modified_count == 0:
                return {
                    "success": False,
                    "message": "No changes made to the record",
                    "error": {"code": "UPDATE_ERROR", "details": "no_changes"},
                }

            # Get updated record
            updated_record = self.categories.find_one({"_id": ObjectId(record_id)})
            updated_record['_id'] = str(updated_record['_id'])

            # Add created_by_name
            created_by_id = updated_record.get('created_by')
            if created_by_id:
                user = self.users.find_one({"user_id": created_by_id})
                if user:
                    updated_record['created_by_name'] = user.get('username', 'Unknown')
                else:
                    updated_record['created_by_name'] = 'Unknown'
            else:
                updated_record['created_by_name'] = 'Unknown'

            return {
                "success": True,
                "message": "Category updated successfully",
                "data": {
                    "_id": updated_record['_id'],
                    "category_name": category_name,
                    "description": description,
                    "status": status,
                    "created_at": updated_record.get("created_at"),
                    "created_time": updated_record.get("created_time"),
                    "created_by": updated_record.get("created_by"),
                    "created_by_name": updated_record.get("created_by_name"),
                    "updated_at": update_meta["updated_at"],
                    "updated_time": update_meta["updated_time"],
                    "updated_by": update_meta["updated_by"],
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update category: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_categories_stats(self) -> Dict[str, Any]:
        """Get categories statistics for dashboard."""
        try:
            # Total categories
            total_categories = self.categories.count_documents({})
            
            # Active categories
            active_categories = self.categories.count_documents({"status": "active"})
            
            # Inactive categories
            inactive_categories = self.categories.count_documents({"status": "inactive"})
            
            return {
                "total_categories": total_categories,
                "active_categories": active_categories,
                "inactive_categories": inactive_categories,
            }
            
        except Exception as e:
            return {
                "total_categories": 0,
                "active_categories": 0,
                "inactive_categories": 0,
            }

    def add_sub_category(self, payload: Dict[str, Any], created_by: int = 1) -> Dict[str, Any]:
        """Add a new sub category with validations."""
        try:
            sub_category_name = (payload.get("sub_category_name") or "").strip()
            category_id = payload.get("category_id")
            description = (payload.get("description") or "").strip()

            # Validate sub_category_name
            if not (2 <= len(sub_category_name) <= 50):
                return {
                    "success": False,
                    "message": "Sub category name must be 2–50 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_sub_category_name"},
                }

            # Validate category_id
            if not category_id:
                return {
                    "success": False,
                    "message": "Category ID is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_category_id"},
                }

            # Check if category exists
            category = self.categories.find_one({"_id": ObjectId(category_id)})
            if not category:
                return {
                    "success": False,
                    "message": "Category not found",
                    "error": {"code": "VALIDATION_ERROR", "details": "category_not_found"},
                }

            # Enforce uniqueness (case-insensitive) within the same category
            existing = self.sub_categories.find_one({
                "sub_category_name": {"$regex": f"^{sub_category_name}$", "$options": "i"},
                "category_id": category_id
            })
            if existing:
                return {
                    "success": False,
                    "message": "Sub category name already exists in this category",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_sub_category_name"},
                }

            # Validate description
            if not (5 <= len(description) <= 200):
                return {
                    "success": False,
                    "message": "Description must be 5–200 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_description"},
                }

            # Use AuditUtils for consistent audit fields
            create_meta = AuditUtils.build_create_meta(created_by)
            
            doc = {
                "sub_category_name": sub_category_name,
                "sub_category_name_lower": sub_category_name.lower(),
                "category_id": category_id,
                "category_name": category.get("category_name", ""),
                "description": description,
                "status": "active",
                **create_meta  # Spread created_at, created_time, created_by
            }

            result = self.sub_categories.insert_one(doc)

            return {
                "success": True,
                "message": "Sub category added successfully",
                "data": {
                    "_id": str(result.inserted_id),
                    "sub_category_name": sub_category_name,
                    "category_id": category_id,
                    "category_name": category.get("category_name", ""),
                    "description": description,
                    "status": "active",
                    "created_at": create_meta["created_at"],
                    "created_time": create_meta["created_time"],
                    "created_by": create_meta["created_by"],
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add sub category: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_sub_categories_list(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get paginated list of sub categories with filtering."""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'all')
            category_id = filters.get('category_id', '')
            search = filters.get('search', '')

            # Build query
            query = {}
            
            # Status filter
            if status != 'all':
                query['status'] = status
            
            # Category filter
            if category_id:
                query['category_id'] = category_id
            
            # Search filter (search in sub_category_name and description)
            if search:
                query['$or'] = [
                    {"sub_category_name": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]

            # Get total count
            total_count = self.sub_categories.count_documents(query)
            
            # Get records with pagination
            records = list(
                self.sub_categories.find(query)
                .skip(skip)
                .limit(limit)
                .sort("created_at", -1)
            )
            
            # Convert ObjectId to string and add created_by_name / updated_by_name
            datetime_utils = important_utilities()
            
            for record in records:
                record['_id'] = str(record['_id'])
                
                # Combine created_at and created_time into created_datetime
                created_at = record.get('created_at', '')
                created_time = record.get('created_time', '')
                if created_at and created_time:
                    try:
                        created_datetime = datetime.strptime(f"{created_at} {created_time}", "%Y-%m-%d %H:%M:%S")
                        record['created_datetime'] = created_datetime.strftime("%d-%m-%Y %I:%M %p")
                    except:
                        record['created_datetime'] = f"{created_at} {created_time}"
                else:
                    record['created_datetime'] = None
                
                # Combine updated_at and updated_time into updated_datetime if available
                updated_at = record.get('updated_at')
                updated_time = record.get('updated_time')
                if updated_at and updated_time:
                    try:
                        updated_datetime = datetime.strptime(f"{updated_at} {updated_time}", "%Y-%m-%d %H:%M:%S")
                        record['updated_datetime'] = updated_datetime.strftime("%d-%m-%Y %I:%M %p")
                    except:
                        record['updated_datetime'] = f"{updated_at} {updated_time}"
                else:
                    record['updated_datetime'] = None
                
                # Get created_by_name from users collection
                created_by_id = record.get('created_by')
                if created_by_id:
                    user = self.users.find_one({"user_id": created_by_id})
                    if user:
                        record['created_by_name'] = user.get('username', 'Unknown')
                    else:
                        record['created_by_name'] = 'Unknown'
                else:
                    record['created_by_name'] = 'Unknown'

                # Get updated_by_name from users collection if available
                updated_by_id = record.get('updated_by')
                if updated_by_id:
                    upd_user = self.users.find_one({"user_id": updated_by_id})
                    if upd_user:
                        record['updated_by_name'] = upd_user.get('username', 'Unknown')
                    else:
                        record['updated_by_name'] = 'Unknown'
                else:
                    record['updated_by_name'] = None

                # Remove internal fields
                record.pop('sub_category_name_lower', None)

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Get stats data
            stats = self.get_sub_categories_stats()

            return {
                "success": True,
                "data": {
                    "records": records,
                    "stats": stats,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get sub categories list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def update_sub_category(self, payload: Dict[str, Any], updated_by: int = 1) -> Dict[str, Any]:
        """Update an existing sub category with validations."""
        try:
            # Extract record ID
            record_id = payload.get('_id') or payload.get('id')
            if not record_id:
                return {
                    "success": False,
                    "message": "Record ID is required for update",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_record_id"},
                }

            # Check if record exists
            existing_record = self.sub_categories.find_one({"_id": ObjectId(record_id)})
            if not existing_record:
                return {
                    "success": False,
                    "message": "Sub category not found",
                    "error": {"code": "VALIDATION_ERROR", "details": "record_not_found"},
                }

            # Extract and validate input data
            sub_category_name = (payload.get("sub_category_name") or "").strip()
            category_id = payload.get("category_id")
            description = (payload.get("description") or "").strip()
            status = (payload.get("status") or "active").strip().lower()

            # Validate sub_category_name
            if not (2 <= len(sub_category_name) <= 50):
                return {
                    "success": False,
                    "message": "Sub category name must be 2–50 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_sub_category_name"},
                }

            # Validate category_id if provided
            if category_id:
                category = self.categories.find_one({"_id": ObjectId(category_id)})
                if not category:
                    return {
                        "success": False,
                        "message": "Category not found",
                        "error": {"code": "VALIDATION_ERROR", "details": "category_not_found"},
                    }
            else:
                # Use existing category_id
                category_id = existing_record.get("category_id")
                category = self.categories.find_one({"_id": ObjectId(category_id)})

            # Enforce uniqueness (case-insensitive) - exclude current record
            existing = self.sub_categories.find_one({
                "sub_category_name": {"$regex": f"^{sub_category_name}$", "$options": "i"},
                "category_id": category_id,
                "_id": {"$ne": ObjectId(record_id)}
            })
            if existing:
                return {
                    "success": False,
                    "message": "Sub category name already exists in this category",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_sub_category_name"},
                }

            # Validate description
            if not (5 <= len(description) <= 200):
                return {
                    "success": False,
                    "message": "Description must be 5–200 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_description"},
                }

            # Validate status
            if status not in ("active", "inactive"):
                return {
                    "success": False,
                    "message": "Status must be one of active | inactive",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_status"},
                }

            # Use AuditUtils for consistent audit fields
            update_meta = AuditUtils.build_update_meta(updated_by)
            
            # Update record
            update_doc = {
                "sub_category_name": sub_category_name,
                "sub_category_name_lower": sub_category_name.lower(),
                "category_id": category_id,
                "category_name": category.get("category_name", ""),
                "description": description,
                "status": status,
                **update_meta  # Spread updated_at, updated_time, updated_by
            }

            result = self.sub_categories.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": update_doc}
            )

            if result.modified_count == 0:
                return {
                    "success": False,
                    "message": "No changes made to the record",
                    "error": {"code": "UPDATE_ERROR", "details": "no_changes"},
                }

            # Get updated record
            updated_record = self.sub_categories.find_one({"_id": ObjectId(record_id)})
            updated_record['_id'] = str(updated_record['_id'])

            # Add created_by_name
            created_by_id = updated_record.get('created_by')
            if created_by_id:
                user = self.users.find_one({"user_id": created_by_id})
                if user:
                    updated_record['created_by_name'] = user.get('username', 'Unknown')
                else:
                    updated_record['created_by_name'] = 'Unknown'
            else:
                updated_record['created_by_name'] = 'Unknown'

            return {
                "success": True,
                "message": "Sub category updated successfully",
                "data": {
                    "_id": updated_record['_id'],
                    "sub_category_name": sub_category_name,
                    "category_id": category_id,
                    "category_name": category.get("category_name", ""),
                    "description": description,
                    "status": status,
                    "created_at": updated_record.get("created_at"),
                    "created_time": updated_record.get("created_time"),
                    "created_by": updated_record.get("created_by"),
                    "created_by_name": updated_record.get("created_by_name"),
                    "updated_at": update_meta["updated_at"],
                    "updated_time": update_meta["updated_time"],
                    "updated_by": update_meta["updated_by"],
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update sub category: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_sub_categories_stats(self) -> Dict[str, Any]:
        """Get sub categories statistics for dashboard."""
        try:
            # Total sub categories
            total_sub_categories = self.sub_categories.count_documents({})
            
            # Active sub categories
            active_sub_categories = self.sub_categories.count_documents({"status": "active"})
            
            # Inactive sub categories
            inactive_sub_categories = self.sub_categories.count_documents({"status": "inactive"})
            
            return {
                "total_sub_categories": total_sub_categories,
                "active_sub_categories": active_sub_categories,
                "inactive_sub_categories": inactive_sub_categories,
            }
            
        except Exception as e:
            return {
                "total_sub_categories": 0,
                "active_sub_categories": 0,
                "inactive_sub_categories": 0,
            }

    def add_product_master(self, payload: Dict[str, Any], created_by: int = 1) -> Dict[str, Any]:
        """Add a new product master with validations."""
        try:
            product_name = (payload.get("product_name") or "").strip()
            category_id = payload.get("category_id")
            sub_category_id = payload.get("sub_category_id")
            description = (payload.get("description") or "").strip()
            sku = (payload.get("sku") or "").strip()
            mrp = payload.get("mrp")
            status = (payload.get("status") or "active").strip().lower()

            # Validate product_name
            if not (2 <= len(product_name) <= 100):
                return {
                    "success": False,
                    "message": "Product name must be 2–100 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_product_name"},
                }

            # Validate category_id
            if not category_id:
                return {
                    "success": False,
                    "message": "Category ID is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_category_id"},
                }

            # Check if category exists
            category = self.categories.find_one({"_id": ObjectId(category_id)})
            if not category:
                return {
                    "success": False,
                    "message": "Category not found",
                    "error": {"code": "VALIDATION_ERROR", "details": "category_not_found"},
                }

            # Validate sub_category_id if provided
            sub_category = None
            if sub_category_id:
                sub_category = self.sub_categories.find_one({"_id": ObjectId(sub_category_id)})
                if not sub_category:
                    return {
                        "success": False,
                        "message": "Sub category not found",
                        "error": {"code": "VALIDATION_ERROR", "details": "sub_category_not_found"},
                    }
                # Verify sub_category belongs to the same category
                if sub_category.get("category_id") != category_id:
                    return {
                        "success": False,
                        "message": "Sub category does not belong to the selected category",
                        "error": {"code": "VALIDATION_ERROR", "details": "sub_category_mismatch"},
                    }

            # Enforce uniqueness (case-insensitive) for product name
            existing = self.product_master.find_one({"product_name": {"$regex": f"^{product_name}$", "$options": "i"}})
            if existing:
                return {
                    "success": False,
                    "message": "Product name already exists",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_product_name"},
                }

            # Enforce uniqueness for SKU
            existing_sku = self.product_master.find_one({"sku": {"$regex": f"^{sku}$", "$options": "i"}})
            if existing_sku:
                return {
                    "success": False,
                    "message": "SKU already exists",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_sku"},
                }

            # Validate SKU
            if not (3 <= len(sku) <= 50):
                return {
                    "success": False,
                    "message": "SKU must be 3–50 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_sku"},
                }

            # Validate MRP
            if not isinstance(mrp, (int, float)) or mrp <= 0:
                return {
                    "success": False,
                    "message": "MRP must be a positive number",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_mrp"},
                }

            # Validate description
            if not (10 <= len(description) <= 500):
                return {
                    "success": False,
                    "message": "Description must be 10–500 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_description"},
                }

            # Validate status
            if status not in ("active", "inactive"):
                return {
                    "success": False,
                    "message": "Status must be one of active | inactive",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_status"},
                }

            # Use AuditUtils for consistent audit fields
            create_meta = AuditUtils.build_create_meta(created_by)
            
            doc = {
                "product_name": product_name,
                "product_name_lower": product_name.lower(),
                "category_id": category_id,
                "category_name": category.get("category_name", ""),
                "sub_category_id": sub_category_id,
                "sub_category_name": sub_category.get("sub_category_name", "") if sub_category else "",
                "description": description,
                "sku": sku,
                "mrp": mrp,
                "status": status,
                **create_meta  # Spread created_at, created_time, created_by
            }

            result = self.product_master.insert_one(doc)

            return {
                "success": True,
                "message": "Product master added successfully",
                "data": {
                    "_id": str(result.inserted_id),
                    "product_name": product_name,
                    "category_id": category_id,
                    "category_name": category.get("category_name", ""),
                    "sub_category_id": sub_category_id,
                    "sub_category_name": sub_category.get("sub_category_name", "") if sub_category else "",
                    "description": description,
                    "sku": sku,
                    "mrp": mrp,
                    "status": status,
                    "created_at": create_meta["created_at"],
                    "created_time": create_meta["created_time"],
                    "created_by": create_meta["created_by"],
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add product master: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_product_master_list(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get paginated list of product master records with filtering."""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'all')
            category = filters.get('category', '')  # Changed from category_id to category
            sub_category_id = filters.get('sub_category_id', '')
            search = filters.get('search', '')

            # Build query
            query = {}
            
            # Status filter
            if status and status != 'all':
                query['status'] = status
            
            # Category filter (search by category name)
            if category and category.strip():
                query['category_name'] = {"$regex": category.strip(), "$options": "i"}
            
            # Sub category filter
            if sub_category_id and sub_category_id.strip():
                query['sub_category_id'] = sub_category_id
            
            # Search filter (search in product_name and description)
            if search and search.strip():
                query['$or'] = [
                    {"product_name": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]

            # Get total count
            total_count = self.product_master.count_documents(query)
            
            # Get records with pagination
            records = list(
                self.product_master.find(query)
                .skip(skip)
                .limit(limit)
                .sort("created_at", -1)
            )
            
            # Convert ObjectId to string and add created_by_name / updated_by_name
            datetime_utils = important_utilities()
            
            for record in records:
                record['_id'] = str(record['_id'])
                
                # Combine created_at and created_time into created_datetime
                created_at = record.get('created_at', '')
                created_time = record.get('created_time', '')
                if created_at and created_time:
                    try:
                        created_datetime = datetime.strptime(f"{created_at} {created_time}", "%Y-%m-%d %H:%M:%S")
                        record['created_datetime'] = created_datetime.strftime("%d-%m-%Y %I:%M %p")
                    except:
                        record['created_datetime'] = f"{created_at} {created_time}"
                else:
                    record['created_datetime'] = None
                
                # Combine updated_at and updated_time into updated_datetime if available
                updated_at = record.get('updated_at')
                updated_time = record.get('updated_time')
                if updated_at and updated_time:
                    try:
                        updated_datetime = datetime.strptime(f"{updated_at} {updated_time}", "%Y-%m-%d %H:%M:%S")
                        record['updated_datetime'] = updated_datetime.strftime("%d-%m-%Y %I:%M %p")
                    except:
                        record['updated_datetime'] = f"{updated_at} {updated_time}"
                else:
                    record['updated_datetime'] = None
                
                # Get created_by_name from users collection
                created_by_id = record.get('created_by')
                if created_by_id:
                    user = self.users.find_one({"user_id": created_by_id})
                    if user:
                        record['created_by_name'] = user.get('username', 'Unknown')
                    else:
                        record['created_by_name'] = 'Unknown'
                else:
                    record['created_by_name'] = 'Unknown'

                # Get updated_by_name from users collection if available
                updated_by_id = record.get('updated_by')
                if updated_by_id:
                    upd_user = self.users.find_one({"user_id": updated_by_id})
                    if upd_user:
                        record['updated_by_name'] = upd_user.get('username', 'Unknown')
                    else:
                        record['updated_by_name'] = 'Unknown'
                else:
                    record['updated_by_name'] = None

                # Add thumbnail image (first image from images array)
                images = record.get('images', [])
                if images and len(images) > 0:
                    # Get only the file_url from the first image
                    thumbnail = images[0]
                    record['thumbnail'] = thumbnail.get('file_url')
                else:
                    record['thumbnail'] = None

                # Remove internal fields
                record.pop('product_name_lower', None)
                # Remove full images array to keep response lightweight
                record.pop('images', None)

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Get stats data
            stats = self.get_product_master_stats()

            return {
                "success": True,
                "data": {
                    "records": records,
                    "stats": stats,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get product master list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def update_product_master(self, payload: Dict[str, Any], updated_by: int = 1) -> Dict[str, Any]:
        """Update an existing product master with validations."""
        try:
            # Extract record ID
            record_id = payload.get('_id') or payload.get('id')
            if not record_id:
                return {
                    "success": False,
                    "message": "Record ID is required for update",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_record_id"},
                }

            # Check if record exists
            existing_record = self.product_master.find_one({"_id": ObjectId(record_id)})
            if not existing_record:
                return {
                    "success": False,
                    "message": "Product master not found",
                    "error": {"code": "VALIDATION_ERROR", "details": "record_not_found"},
                }

            # Extract and validate input data
            product_name = (payload.get("product_name") or "").strip()
            category_id = payload.get("category_id")
            sub_category_id = payload.get("sub_category_id")
            description = (payload.get("description") or "").strip()
            sku = (payload.get("sku") or "").strip()
            mrp = payload.get("mrp")
            status = (payload.get("status") or "active").strip().lower()
            images = payload.get("images", [])  # Handle images array

            # Validate product_name
            if not (2 <= len(product_name) <= 100):
                return {
                    "success": False,
                    "message": "Product name must be 2–100 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_product_name"},
                }

            # Validate category_id if provided
            if category_id:
                category = self.categories.find_one({"_id": ObjectId(category_id)})
                if not category:
                    return {
                        "success": False,
                        "message": "Category not found",
                        "error": {"code": "VALIDATION_ERROR", "details": "category_not_found"},
                    }
            else:
                # Use existing category_id
                category_id = existing_record.get("category_id")
                category = self.categories.find_one({"_id": ObjectId(category_id)})

            # Validate sub_category_id if provided
            sub_category = None
            if sub_category_id:
                sub_category = self.sub_categories.find_one({"_id": ObjectId(sub_category_id)})
                if not sub_category:
                    return {
                        "success": False,
                        "message": "Sub category not found",
                        "error": {"code": "VALIDATION_ERROR", "details": "sub_category_not_found"},
                    }
                # Verify sub_category belongs to the same category
                if sub_category.get("category_id") != category_id:
                    return {
                        "success": False,
                        "message": "Sub category does not belong to the selected category",
                        "error": {"code": "VALIDATION_ERROR", "details": "sub_category_mismatch"},
                    }
            else:
                # Use existing sub_category_id if available
                sub_category_id = existing_record.get("sub_category_id")
                if sub_category_id:
                    sub_category = self.sub_categories.find_one({"_id": ObjectId(sub_category_id)})

            # Enforce uniqueness (case-insensitive) - exclude current record
            existing = self.product_master.find_one({
                "product_name": {"$regex": f"^{product_name}$", "$options": "i"},
                "_id": {"$ne": ObjectId(record_id)}
            })
            if existing:
                return {
                    "success": False,
                    "message": "Product name already exists",
                    "error": {"code": "VALIDATION_ERROR", "details": "duplicate_product_name"},
                }

            # Validate SKU
            if not (3 <= len(sku) <= 50):
                return {
                    "success": False,
                    "message": "SKU must be 3–50 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_sku"},
                }

            # Validate MRP
            if not isinstance(mrp, (int, float)) or mrp <= 0:
                return {
                    "success": False,
                    "message": "MRP must be a positive number",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_mrp"},
                }

            # Validate description
            if not (10 <= len(description) <= 500):
                return {
                    "success": False,
                    "message": "Description must be 10–500 characters",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_description"},
                }

            # Validate status
            if status not in ("active", "inactive"):
                return {
                    "success": False,
                    "message": "Status must be one of active | inactive",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_status"},
                }

            # Validate images array if provided
            if images and not isinstance(images, list):
                return {
                    "success": False,
                    "message": "Images must be an array",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_images_format"},
                }

            # Use AuditUtils for consistent audit fields
            update_meta = AuditUtils.build_update_meta(updated_by)
            
            # Update record
            update_doc = {
                "product_name": product_name,
                "product_name_lower": product_name.lower(),
                "category_id": category_id,
                "category_name": category.get("category_name", ""),
                "sub_category_id": sub_category_id,
                "sub_category_name": sub_category.get("sub_category_name", "") if sub_category else "",
                "description": description,
                "sku": sku,
                "mrp": mrp,
                "status": status,
                **update_meta  # Spread updated_at, updated_time, updated_by
            }

            # Add images array if provided
            if images:
                update_doc["images"] = images

            result = self.product_master.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": update_doc}
            )

            if result.modified_count == 0:
                return {
                    "success": False,
                    "message": "No changes made to the record",
                    "error": {"code": "UPDATE_ERROR", "details": "no_changes"},
                }

            # Get updated record
            updated_record = self.product_master.find_one({"_id": ObjectId(record_id)})
            updated_record['_id'] = str(updated_record['_id'])

            # Add created_by_name
            created_by_id = updated_record.get('created_by')
            if created_by_id:
                user = self.users.find_one({"user_id": created_by_id})
                if user:
                    updated_record['created_by_name'] = user.get('username', 'Unknown')
                else:
                    updated_record['created_by_name'] = 'Unknown'
            else:
                updated_record['created_by_name'] = 'Unknown'

            return {
                "success": True,
                "message": "Product master updated successfully",
                "data": {
                    "_id": updated_record['_id'],
                    "product_name": product_name,
                    "category_id": category_id,
                    "category_name": category.get("category_name", ""),
                    "sub_category_id": sub_category_id,
                    "sub_category_name": sub_category.get("sub_category_name", "") if sub_category else "",
                    "description": description,
                    "sku": sku,
                    "mrp": mrp,
                    "status": status,
                    "images": updated_record.get("images", []),
                    "created_at": updated_record.get("created_at"),
                    "created_time": updated_record.get("created_time"),
                    "created_by": updated_record.get("created_by"),
                    "created_by_name": updated_record.get("created_by_name"),
                    "updated_at": update_meta["updated_at"],
                    "updated_time": update_meta["updated_time"],
                    "updated_by": update_meta["updated_by"],
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update product master: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_product_master_detail(self, product_id: str) -> Dict[str, Any]:
        """Get detailed information of a single product master record."""
        try:
            # Validate product_id
            if not product_id:
                return {
                    "success": False,
                    "message": "Product ID is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_product_id"},
                }

            # Check if product exists
            product = self.product_master.find_one({"_id": ObjectId(product_id)})
            if not product:
                return {
                    "success": False,
                    "message": "Product not found",
                    "error": {"code": "VALIDATION_ERROR", "details": "product_not_found"},
                }

            # Convert ObjectId to string
            product['_id'] = str(product['_id'])

            # Combine created_at and created_time into created_datetime
            created_at = product.get('created_at', '')
            created_time = product.get('created_time', '')
            if created_at and created_time:
                try:
                    created_datetime = datetime.strptime(f"{created_at} {created_time}", "%Y-%m-%d %H:%M:%S")
                    product['created_datetime'] = created_datetime.strftime("%d-%m-%Y %I:%M %p")
                except:
                    product['created_datetime'] = f"{created_at} {created_time}"
            else:
                product['created_datetime'] = None

            # Combine updated_at and updated_time into updated_datetime if available
            updated_at = product.get('updated_at')
            updated_time = product.get('updated_time')
            if updated_at and updated_time:
                try:
                    updated_datetime = datetime.strptime(f"{updated_at} {updated_time}", "%Y-%m-%d %H:%M:%S")
                    product['updated_datetime'] = updated_datetime.strftime("%d-%m-%Y %I:%M %p")
                except:
                    product['updated_datetime'] = f"{updated_at} {updated_time}"
            else:
                product['updated_datetime'] = None

            # Get created_by_name from users collection
            created_by_id = product.get('created_by')
            if created_by_id:
                user = self.users.find_one({"user_id": created_by_id})
                if user:
                    product['created_by_name'] = user.get('username', 'Unknown')
                else:
                    product['created_by_name'] = 'Unknown'
            else:
                product['created_by_name'] = 'Unknown'

            # Get updated_by_name from users collection if available
            updated_by_id = product.get('updated_by')
            if updated_by_id:
                upd_user = self.users.find_one({"user_id": updated_by_id})
                if upd_user:
                    product['updated_by_name'] = upd_user.get('username', 'Unknown')
                else:
                    product['updated_by_name'] = 'Unknown'
            else:
                product['updated_by_name'] = None

            # Remove internal fields
            product.pop('product_name_lower', None)

            # Simplify images array to only include image_id and file_url
            if 'images' in product and product['images']:
                simplified_images = []
                for image in product['images']:
                    simplified_images.append({
                        'image_id': image.get('image_id'),
                        'file_url': image.get('file_url')
                    })
                product['images'] = simplified_images

            return {
                "success": True,
                "message": "Product master detail retrieved successfully",
                "data": product
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get product master detail: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_product_master_stats(self) -> Dict[str, Any]:
        """Get product master statistics for dashboard."""
        try:
            # Total products
            total_products = self.product_master.count_documents({})
            
            # Active products
            active_products = self.product_master.count_documents({"status": "active"})
            
            # Inactive products
            inactive_products = self.product_master.count_documents({"status": "inactive"})
            
            # Total MRP value (sum of all active products)
            pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {"_id": None, "total_mrp": {"$sum": "$mrp"}}}
            ]
            mrp_result = list(self.product_master.aggregate(pipeline))
            total_mrp = mrp_result[0]["total_mrp"] if mrp_result else 0
            
            # Categories count
            categories_pipeline = [
                {"$group": {"_id": "$category_name", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            categories = list(self.product_master.aggregate(categories_pipeline))
            
            return {
                "total_products": total_products,
                "active_products": active_products,
                "inactive_products": inactive_products,
                "total_mrp": total_mrp,
                "categories": categories
            }
            
        except Exception as e:
            return {
                "total_products": 0,
                "active_products": 0,
                "inactive_products": 0,
                "total_mrp": 0,
                "categories": []
            }

    def upload_product_image(self, product_id: str, image_file, created_by: int = 1) -> Dict[str, Any]:
        """Upload product image and save file details in product_master images array."""
        try:

            # Validate product_id
            if not product_id:
                return {
                    "success": False,
                    "message": "Product ID is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_product_id"},
                }

            # Check if product exists
            product = self.product_master.find_one({"_id": ObjectId(product_id)})
            if not product:
                return {
                    "success": False,
                    "message": "Product not found",
                    "error": {"code": "VALIDATION_ERROR", "details": "product_not_found"},
                }

            # Validate image file
            if not image_file:
                return {
                    "success": False,
                    "message": "Image file is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "missing_image_file"},
                }

            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return {
                    "success": False,
                    "message": "Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed",
                    "error": {"code": "VALIDATION_ERROR", "details": "invalid_file_type"},
                }

            # Check file size (max 5MB)
            max_size = 5 * 1024 * 1024  # 5MB in bytes
            if len(image_file.file.read()) > max_size:
                return {
                    "success": False,
                    "message": "File size too large. Maximum size is 5MB",
                    "error": {"code": "VALIDATION_ERROR", "details": "file_too_large"},
                }

            # Reset file pointer
            image_file.file.seek(0)

            # Generate unique filename
            file_extension = image_file.filename.split('.')[-1] if '.' in image_file.filename else 'jpg'
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            
            # Create upload directory if it doesn't exist
            upload_dir = "uploads/trust_rewards/products"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file path
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Process and save image
            try:
                if PIL_AVAILABLE:
                    # Use PIL for image processing
                    image = Image.open(io.BytesIO(image_file.file.read()))
                    
                    # Convert to RGB if necessary (for JPEG compatibility)
                    if image.mode in ('RGBA', 'LA', 'P'):
                        image = image.convert('RGB')
                    
                    # Resize image if too large (max 1920x1080)
                    max_width, max_height = 1920, 1080
                    if image.width > max_width or image.height > max_height:
                        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                    
                    # Save processed image
                    image.save(file_path, 'JPEG', quality=85, optimize=True)
                    
                    # Get image dimensions
                    image_width, image_height = image.size
                else:
                    # Fallback: Save file without processing if PIL is not available
                    with open(file_path, 'wb') as f:
                        f.write(image_file.file.read())
                    
                    # Set default dimensions if PIL is not available
                    image_width, image_height = 0, 0
                
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Failed to process image: {str(e)}",
                    "error": {"code": "PROCESSING_ERROR", "details": str(e)},
                }

            file_size = os.path.getsize(file_path)

            # Use AuditUtils for consistent audit fields
            create_meta = AuditUtils.build_create_meta(created_by)
            
            # Prepare image data for array
            image_data = {
                "image_id": str(uuid.uuid4()),  # Unique ID for each image
                "original_filename": image_file.filename,
                "stored_filename": unique_filename,
                "file_path": file_path.replace("\\", "/"),  # Use forward slashes
                "file_url": f"/{file_path.replace(chr(92), '/')}",  # URL for frontend
                "content_type": image_file.content_type,  # Use original content type
                "file_size": file_size,
                "image_width": image_width,
                "image_height": image_height,
                "is_primary": False,  # Default to False, can be updated later
            }

            # Get existing images array or create empty one
            existing_images = product.get("images", [])
            
            # Add new image to the array
            existing_images.append(image_data)

            # Update product with new images array
            result = self.product_master.update_one(
                {"_id": ObjectId(product_id)},
                {"$set": {"images": existing_images}}
            )

            if result.modified_count == 0:
                return {
                    "success": False,
                    "message": "Failed to update product with image",
                    "error": {"code": "UPDATE_ERROR", "details": "no_changes"},
                }

            return {
                "success": True,
                "message": "Product image uploaded successfully",
                "data": {
                    "product_id": product_id,
                    "product_name": product.get("product_name", ""),
                    "image_data": image_data,
                    "total_images": len(existing_images)
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to upload product image: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }


    def get_categories_for_select(self) -> Dict[str, Any]:
        """Get categories list optimized for select options."""
        try:
            # Get only active categories with minimal fields
            categories = list(
                self.categories.find(
                    {"status": "active"},
                    {"_id": 1, "category_name": 1}
                ).sort("category_name", 1)
            )
            
            # Format for select options
            select_options = []
            for category in categories:
                select_options.append({
                    "value": str(category["_id"]),
                    "label": category["category_name"]
                })
            
            return {
                "success": True,
                "data": {
                    "categories": select_options,
                    "total": len(select_options)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get categories for select: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_sub_categories_for_select(self, category_id: str = None) -> Dict[str, Any]:
        """Get sub-categories list optimized for select options."""
        try:
            # Build query
            query = {"status": "active"}
            if category_id:
                query["category_id"] = category_id
            
            # Get sub-categories with minimal fields
            sub_categories = list(
                self.sub_categories.find(
                    query,
                    {"_id": 1, "sub_category_name": 1, "category_id": 1, "category_name": 1}
                ).sort("sub_category_name", 1)
            )
            
            # Format for select options
            select_options = []
            for sub_category in sub_categories:
                select_options.append({
                    "value": str(sub_category["_id"]),
                    "label": sub_category["sub_category_name"],
                    "category_id": sub_category.get("category_id"),
                    "category_name": sub_category.get("category_name", "")
                })
            
            return {
                "success": True,
                "data": {
                    "sub_categories": select_options,
                    "total": len(select_options),
                    "category_id": category_id
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get sub-categories for select: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }

    def get_categories_with_sub_categories(self) -> Dict[str, Any]:
        """Get categories with their sub-categories for hierarchical select options."""
        try:
            # Get all active categories
            categories = list(
                self.categories.find(
                    {"status": "active"},
                    {"_id": 1, "category_name": 1}
                ).sort("category_name", 1)
            )
            
            # Get all active sub-categories
            sub_categories = list(
                self.sub_categories.find(
                    {"status": "active"},
                    {"_id": 1, "sub_category_name": 1, "category_id": 1}
                ).sort("sub_category_name", 1)
            )
            
            # Group sub-categories by category_id
            sub_categories_by_category = {}
            for sub_cat in sub_categories:
                cat_id = sub_cat["category_id"]
                if cat_id not in sub_categories_by_category:
                    sub_categories_by_category[cat_id] = []
                sub_categories_by_category[cat_id].append({
                    "value": str(sub_cat["_id"]),
                    "label": sub_cat["sub_category_name"]
                })
            
            # Build hierarchical structure
            hierarchical_options = []
            for category in categories:
                cat_id = str(category["_id"])
                category_option = {
                    "value": cat_id,
                    "label": category["category_name"],
                    "sub_categories": sub_categories_by_category.get(cat_id, [])
                }
                hierarchical_options.append(category_option)
            
            return {
                "success": True,
                "data": {
                    "categories": hierarchical_options,
                    "total_categories": len(hierarchical_options),
                    "total_sub_categories": len(sub_categories)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get hierarchical categories: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }


