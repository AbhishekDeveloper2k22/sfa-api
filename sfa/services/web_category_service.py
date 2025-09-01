from config import settings
import json
import pandas as pd
import pytz
from bson import ObjectId
from sfa.database import client1
from datetime import datetime, timedelta
import re

class category_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.categories = self.client_database["categories"]
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
        
        # Add required fields
        request_data['created_at'] = self.current_datetime.strftime("%Y-%m-%d")
        request_data['created_at_time'] = self.current_datetime.strftime("%H:%M:%S")
        request_data['del'] = 0
        
        # Set default status if not provided
        if 'status' not in request_data:
            request_data['status'] = 'active'
        
        # Set created_by if not provided
        if 'created_by' not in request_data:
            request_data['created_by'] = 1  # Default admin user
        
        print(request_data)
        result = self.categories.insert_one(request_data)
        
        # Return a proper JSON-serializable response
        if result.inserted_id:
            return {
                "success": True,
                "message": "Category added successfully",
                "inserted_id": str(result.inserted_id),
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
        
        # Add updated timestamp
        request_data['updated_at'] = self.current_datetime.strftime("%Y-%m-%d")
        request_data['updated_at_time'] = self.current_datetime.strftime("%H:%M:%S")
        
        # Remove _id from update data since it's immutable
        update_data = request_data.copy()
        if '_id' in update_data:
            del update_data['_id']
        
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
        
        # Remove pagination parameters from query
        query = request_data.copy()
        if 'limit' in query:
            del query['limit']
        if 'page' in query:
            del query['page']
        
        # Add default filter for non-deleted categories
        if 'del' not in query:
            query['del'] = 0
        
        # Get total count of categories matching the query
        total_count = self.categories.count_documents(query)
        
        # Get paginated results
        result = list(self.categories.find(query).skip(skip).limit(limit))
        
        # Convert ObjectId to string for JSON serialization
        for category in result:
            if '_id' in category:
                category['_id'] = str(category['_id'])
        
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
    