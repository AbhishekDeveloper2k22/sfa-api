from config import settings
import json
import pandas as pd
import pytz
from bson import ObjectId
from sfa.database import client1
from datetime import datetime, timedelta
import re
from passlib.hash import bcrypt

class users_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.all_type = self.client_database["all_type"]
        self.users = self.client_database["users"]
        self.current_datetime = datetime.now()
      
    def users_types(self, query: str):

        all_data = pd.DataFrame(list(self.all_type.find(query, {})))
        if all_data.empty:
            return []
        all_data_json = json.loads(
            all_data.to_json(orient="records", default_handler=str)
        )
        return all_data_json
    
    def check_user_exists(self, request_data):
        """
        Check if user already exists based on email, mobile, or employee_code
        """
        or_conditions = []
        
        # Check for email if provided
        if request_data.get('email'):
            or_conditions.append({'email': request_data['email']})
        
        # Check for mobile if provided
        if request_data.get('mobile'):
            or_conditions.append({'mobile': request_data['mobile']})
        
        # Check for employee_code if provided
        if request_data.get('employee_code'):
            or_conditions.append({'employee_code': request_data['employee_code']})
        
        # If no unique fields to check, return False
        if not or_conditions:
            return {
                "exists": False,
                "message": "No unique fields provided to check"
            }
        
        # Check if any user exists with these criteria
        query = {'$or': or_conditions}
        existing_user = self.users.find_one(query)
        
        if existing_user:
            return {
                "exists": True,
                "message": "User already exists",
                "existing_user": {
                    "id": str(existing_user.get('_id')),
                    "email": existing_user.get('email'),
                    "name": existing_user.get('name'),
                    "mobile": existing_user.get('mobile'),
                    "employee_code": existing_user.get('employee_code')
                }
            }
        else:
            return {
                "exists": False,
                "message": "User does not exist"
            }
    
    def add_users(self, request_data):
        # First check if user already exists
        
        user_check = self.check_user_exists(request_data)
        if user_check and user_check.get('exists'):
            return {
                "success": False,
                "message": "User already exists with this email/phone/employee ID",
                "existing_user": user_check.get('existing_user'),
                "inserted_id": None,
            }
        
        # Add current date and time
        request_data['created_at'] = self.current_datetime.strftime("%Y-%m-%d")
        request_data['created_at_time'] = self.current_datetime.strftime("%H:%M:%S")
        request_data['employment_status'] = 'Active'
        request_data['del'] = 0
        request_data['last_login'] = self.current_datetime.strftime("%Y-%m-%d")
        
        # Hash password if provided and store in hash_password, do not store plaintext
        if request_data.get('password'):
            try:
                request_data['hash_password'] = bcrypt.hash(request_data['password'])
            except Exception:
                pass
        # Add default permissions
        request_data['permissions'] = {
            "view": True,
            "edit": True,
            "delete": False,
            "add": True,
            "export": True,
            "import": False
        }
        print(request_data)
        result = self.users.insert_one(request_data)
        
        # Return a proper JSON-serializable response
        if result.inserted_id:
            return {
                "success": True,
                "message": "User added successfully",
                "inserted_id": str(result.inserted_id),
            }
        else:
            return {
                "success": False,
                "message": "Failed to add user",
                "inserted_id": None,
            }
    
    def update_users(self, request_data):
        # First check if the fields being updated are not already assigned to another user
        user_id = request_data.get('_id')
        if user_id:
            # Use the existing check_user_exists function
            user_check = self.check_user_exists(request_data)
            if user_check and user_check.get('exists'):
                # Check if the existing user is different from the current user being updated
                existing_user_id = user_check.get('existing_user', {}).get('id')
                if existing_user_id != user_id:
                    return {
                        "success": False,
                        "message": "Email/Mobile/Employee Code is already assigned to another user",
                        "existing_user": user_check.get('existing_user'),
                        "matched_count": 0,
                        "modified_count": 0,
                    }
        
        request_data['updated_at'] = self.current_datetime.strftime("%Y-%m-%d")
        request_data['updated_at_time'] = self.current_datetime.strftime("%H:%M:%S")
        
        # Remove _id from update data since it's immutable
        update_data = request_data.copy()
        if '_id' in update_data:
            del update_data['_id']
        
        # If password provided, hash and set hash_password; do not store plaintext
        if update_data.get('password'):
            try:
                update_data['hash_password'] = bcrypt.hash(update_data['password'])
            except Exception:
                pass
        
        result = self.users.update_one({"_id": ObjectId(request_data['_id'])}, {"$set": update_data})
        
        # Return a proper JSON-serializable response
        if result.matched_count > 0:
            return {
                "success": True,
                "message": "User updated successfully",
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
            }
        else:
            return {
                "success": False,
                "message": "Failed to update user - user not found",
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
            }

    def users_list(self, request_data):
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
        
        # Get total count of users matching the query
        total_count = self.users.count_documents(query)
        
        # Get paginated results
        result = list(self.users.find(query).skip(skip).limit(limit))
        
        # Convert ObjectId to string for JSON serialization
        for user in result:
            if '_id' in user:
                user['_id'] = str(user['_id'])
        
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
    
    def user_details(self, request_data):
        """
        Get specific user details by ID
        """
        user_id = request_data.get('_id') or request_data.get('id')
        
        if not user_id:
            return {
                "success": False,
                "message": "User ID is required",
                "data": None
            }
        
        try:
            # Find user by ID
            user = self.users.find_one({"_id": ObjectId(user_id)})
            
            if user:
                # Convert ObjectId to string for JSON serialization
                user['_id'] = str(user['_id'])
                
                return {
                    "success": True,
                    "message": "User details retrieved successfully",
                    "data": user
                }
            else:
                return {
                    "success": False,
                    "message": "User not found",
                    "data": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving user details: {str(e)}",
                "data": None
            }
