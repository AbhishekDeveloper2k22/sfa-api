from config import settings
import json
import pandas as pd
import pytz
from bson import ObjectId
from sfa.database import client1
from datetime import datetime, timedelta
import re
import os
import uuid
from sfa.utils.date_utils import build_audit_fields
from sfa.utils.code_generator import generate_unique_code

class category_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.categories = self.client_database["categories"]
        # Get users and products collections
        self.products_collection = self.client_database["products"]
        self.field_squad_database = client1["field_squad"]
        self.users_collection = self.field_squad_database["users"]
        self.current_datetime = datetime.now()
    
    def check_category_exists(self, request_data):
        """
        Check if category already exists based on name
        """
        or_conditions = []
        
        # Check for category name if provided
        if request_data.get('category_name'):
            or_conditions.append({'category_name': request_data['category_name']})
            
        # If no unique fields to check, return False
        if not or_conditions:
            return {
                "exists": False,
                "message": "No unique fields provided to check"
            }
        
        # Check if any category exists with these criteria
        query = {'$or': or_conditions}
        existing_category = self.categories.find_one(query)
        
        if existing_category:
            return {
                "exists": True,
                "message": "Category already exists",
                "existing_category": {
                    "id": str(existing_category.get('_id')),
                    "category_name": existing_category.get('category_name'),
                }
            }
        else:
            return {
                "exists": False,
                "message": "Category does not exist"
            }
    
    def add_category(self, request_data):
        # First check if category already exists
        category_check = self.check_category_exists(request_data)
        if category_check and category_check.get('exists'):
            return {
                "success": False,
                "message": "Category already exists with this name",
                "existing_category": category_check.get('existing_category'),
                "inserted_id": None,
            }
        
        # Get user_id from request_data or use default
        user_id = request_data.get('created_by', 1)
        
        # Build audit fields using utility
        created_fields = build_audit_fields(prefix="created", by=user_id, timezone="Asia/Kolkata")
        updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
        
        # Set default status if not provided
        if 'status' not in request_data:
            request_data['status'] = 'active'
        
        # Add audit fields and default values
        request_data['del'] = 0
        request_data.update(created_fields)
        request_data.update(updated_fields)
        
        print(request_data)
        result = self.categories.insert_one(request_data)
        
        # Return a proper JSON-serializable response
        if result.inserted_id:
            # Generate unique category code
            category_code = generate_unique_code(
                entity_type="category",
                prefix="CAT",
                date_value=created_fields.get("created_at"),
                sequence_length=3
            )
            
            # Update category with category_code
            self.categories.update_one(
                {"_id": result.inserted_id},
                {"$set": {"category_code": category_code}}
            )
            
            return {
                "success": True,
                "message": "Category added successfully",
                "inserted_id": str(result.inserted_id),
                "category_code": category_code,
            }
        else:
            return {
                "success": False,
                "message": "Failed to add category",
                "inserted_id": None,
            }
    
    def update_category(self, request_data):
        # First check if the fields being updated are not already assigned to another category
        category_id = request_data.get('_id')
        if category_id:
            # Use the existing check_category_exists function
            category_check = self.check_category_exists(request_data)
            if category_check and category_check.get('exists'):
                # Check if the existing category is different from the current category being updated
                existing_category_id = category_check.get('existing_category', {}).get('id')
                if existing_category_id != category_id:
                    return {
                        "success": False,
                        "message": "Category name is already assigned to another category",
                        "existing_category": category_check.get('existing_category'),
                        "matched_count": 0,
                        "modified_count": 0,
                    }
        
        # Get user_id from request_data or use default
        user_id = request_data.get('updated_by', 1)
        
        # Build audit fields using utility
        updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
        
        # Remove _id from update data since it's immutable
        update_data = request_data.copy()
        if '_id' in update_data:
            del update_data['_id']
        
        # Add updated audit fields
        update_data.update(updated_fields)
        
        result = self.categories.update_one({"_id": ObjectId(request_data['_id'])}, {"$set": update_data})
        
        # Return a proper JSON-serializable response
        if result.matched_count > 0:
            return {
                "success": True,
                "message": "Category updated successfully",
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
            }
        else:
            return {
                "success": False,
                "message": "Failed to update category - category not found",
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
            }
    
    def categories_list(self, request_data):
        # Extract pagination parameters
        limit = request_data.get('limit', 10)  # Default limit of 10
        page = request_data.get('page', 1)     # Default page 1
        skip = (page - 1) * limit              # Calculate skip value
        
        # Remove pagination and non-query parameters
        query = request_data.copy()
        if 'limit' in query:
            del query['limit']
        if 'page' in query:
            del query['page']
        if 'created_by' in query:
            del query['created_by']  # Remove audit field from query filter
        
        # Add default filter for non-deleted categories
        if 'del' not in query:
            query['del'] = 0
        
        # Get total count of categories matching the query
        total_count = self.categories.count_documents(query)
        
        # Get paginated results sorted by created_at in descending order (latest first)
        result = list(self.categories.find(query).sort("created_at", -1).skip(skip).limit(limit))
        
        # Enrich each category with user names and product count
        for category in result:
            # Convert ObjectId to string for JSON serialization
            if '_id' in category:
                category['_id'] = str(category['_id'])
            
            # Get created_by user name
            created_by_id = category.get('created_by')
            if created_by_id:
                try:
                    created_user = self.users_collection.find_one({"_id": ObjectId(created_by_id)})
                    category['created_by_name'] = created_user.get('name', 'Unknown') if created_user else 'Unknown'
                except Exception:
                    category['created_by_name'] = 'Unknown'
            else:
                category['created_by_name'] = 'Unknown'
            
            # Get updated_by user name
            updated_by_id = category.get('updated_by')
            if updated_by_id:
                try:
                    updated_user = self.users_collection.find_one({"_id": ObjectId(updated_by_id)})
                    category['updated_by_name'] = updated_user.get('name', 'Unknown') if updated_user else 'Unknown'
                except Exception:
                    category['updated_by_name'] = 'Unknown'
            else:
                category['updated_by_name'] = 'Unknown'
            
            # Get product count for this category
            category_id = category.get('_id')
            try:
                product_count = self.products_collection.count_documents({
                    "category_id": category_id,
                    "del": {"$ne": 1}
                })
                category['product_count'] = product_count
            except Exception:
                category['product_count'] = 0
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "data": result,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "limit": limit,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
    
    def category_details(self, request_data):
        """
        Get specific category details by ID
        """
        category_id = request_data.get('_id') or request_data.get('id')
        
        if not category_id:
            return {
                "success": False,
                "message": "Category ID is required",
                "data": None
            }
        
        try:
            # Find category by ID
            category = self.categories.find_one({"_id": ObjectId(category_id)})
            
            if category:
                # Convert ObjectId to string for JSON serialization
                category['_id'] = str(category['_id'])
                
                return {
                    "success": True,
                    "message": "Category details retrieved successfully",
                    "data": category
                }
            else:
                return {
                    "success": False,
                    "message": "Category not found",
                    "data": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving category details: {str(e)}",
                "data": None
            }

    def update_category_image(self, category_id: str, upload_file):
        if not category_id:
            return {"success": False, "message": "Category ID is required"}
        
        # Validate category exists
        try:
            cat = self.categories.find_one({"_id": ObjectId(category_id)})
            if not cat:
                return {"success": False, "message": "Category not found"}
        except Exception as e:
            return {"success": False, "message": f"Invalid category ID: {e}"}

        # Create upload directory if it doesn't exist
        upload_dir = "uploads/sfa_uploads/talbros/categories"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        original_filename = upload_file.filename or "file"
        file_extension = os.path.splitext(original_filename)[1].lower()
        unique_filename = f"cat_{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)

        # Save image file
        try:
            # Reset file pointer to beginning
            upload_file.file.seek(0)
            
            with open(file_path, 'wb') as buffer:
                content = upload_file.file.read()
                buffer.write(content)
        except Exception as e:
            return {
                "success": False,
                "message": "Failed to save image file",
                "error": {"code": "FILE_SAVE_ERROR", "details": f"Could not save image: {str(e)}"}
            }

        # Get current timestamp
        now_iso = datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
        
        # Normalize path for API response (use forward slashes)
        normalized_path = file_path.replace("\\", "/")
        
        # Update category with image details
        update_data = {
            "category_image_path": file_path,
            "category_image_filename": unique_filename,
            "category_image_original_name": original_filename,
            "category_image_uploaded_at": now_iso,
            "image": unique_filename,  # Keep for backward compatibility
            "image_updated_at": now_iso
        }
        
        res = self.categories.update_one(
            {"_id": ObjectId(category_id)}, 
            {"$set": update_data}
        )
        
        if res.matched_count > 0:
            return {
                "success": True,
                "message": "Category image updated successfully",
                "data": {
                    "category_id": category_id,
                    "image_path": normalized_path,
                    "image_filename": unique_filename,
                    "original_filename": original_filename,
                    "uploaded_at": now_iso
                }
            }
        
        return {"success": False, "message": "Failed to update image"}
    