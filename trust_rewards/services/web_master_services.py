from datetime import datetime
from typing import Dict, Any

from trust_rewards.database import client1
from trust_rewards.utils.datetime_utils import important_utilities
from trust_rewards.utils.common import AuditUtils


class WebMasterService:
    def __init__(self) -> None:
        self.db = client1["trust_rewards"]
        self.points_master = self.db["points_master"]
        self.categories = self.db["category_master"]
        self.sub_categories = self.db["sub_category_master"]
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
            from bson import ObjectId
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
            from bson import ObjectId
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
            from bson import ObjectId
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
            from bson import ObjectId
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


