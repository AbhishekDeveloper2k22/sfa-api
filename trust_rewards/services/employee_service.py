from bson import ObjectId
from datetime import datetime
from app.database import client1
from dotenv import load_dotenv
from trust_rewards.utils.response import format_response
import pytz
from passlib.hash import bcrypt
import pandas as pd
import re
load_dotenv()

class BaseService:
    def __init__(self):
        self.client_database = client1['hrms_master']
        self.user_collection = self.client_database['employee_master']

class EmployeeService(BaseService):
    def __init__(self):
        super().__init__()

    def _initialize_request(self, request):
        india_tz = pytz.timezone('Asia/Kolkata')
        self.current_datetime_in_tz = datetime.now(india_tz)
        self.current_date = self.current_datetime_in_tz.date()

    def validate_and_insert_user(self, user_data):
        existing_user = self.user_collection.find_one({"$or": [{"email": user_data['email']}, {"mobile_no": user_data['mobile_no']}]})
        if existing_user:
            return {
                "success": False,
                "msg": "User already exists.",
                "user_id": str(existing_user['_id']),
                "user_data" : existing_user
            }
        else:
            result = self.user_collection.insert_one(user_data)
            return {
                "success": True,
                "msg": "User successfully registered.",
                "user_id": str(result.inserted_id)
            }

    def update_user_data(self, update_data):
        user_id = update_data.get('_id')
        
        # Remove _id from update_data to avoid MongoDB immutable field error
        update_data_copy = update_data.copy()
        update_data_copy.pop('_id', None)
        
        # Check for duplicate email and mobile number (excluding current user)
        email = update_data_copy.get('email')
        mobile_no = update_data_copy.get('mobile_no')
        
        duplicate_check_query = {
            "_id": {"$ne": ObjectId(user_id)}  # Exclude current user
        }
        
        # Build OR condition for email or mobile number
        or_conditions = []
        if email:
            or_conditions.append({"email": email})
        if mobile_no:
            or_conditions.append({"mobile_no": mobile_no})
        
        if or_conditions:
            duplicate_check_query["$or"] = or_conditions
            
            # Check for existing user with same email or mobile
            existing_user = self.user_collection.find_one(duplicate_check_query)
            
            if existing_user:
                # Determine which field is duplicate
                duplicate_fields = []
                if email and existing_user.get('email') == email:
                    duplicate_fields.append("email")
                if mobile_no and existing_user.get('mobile_no') == mobile_no:
                    duplicate_fields.append("mobile number")
                
                duplicate_msg = f"User with this {', '.join(duplicate_fields)} already exists."
                
                return {
                    "success": False,
                    "msg": duplicate_msg,
                    "user_id": str(existing_user['_id']),
                    "user_data": existing_user
                }
        
        # If no duplicates found, proceed with update
        update_result = self.user_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data_copy})
        if update_result.modified_count > 0:
            return {
                "success": True,
                "msg": "User data updated successfully.",
                "user_id": str(user_id)
            }
        else:
            return {
                "success": False,
                "msg": "Failed to update user data.",
                "user_id": str(user_id)
            }

    def update_job_details(self, employee_id, job_details):
        update_result = self.user_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": job_details}
        )
        return update_result.modified_count > 0 or update_result.matched_count > 0

    def update_compensation_info(self, employee_id, compensation_details):
        update_result = self.user_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": compensation_details}
        )
        return update_result.modified_count > 0 or update_result.matched_count > 0

    def update_system_access(self, employee_id, access_details):
        # Save the plain password in a separate field (not recommended for production)
        if access_details.get("password"):
            access_details["plain_password"] = access_details["password"]
            access_details["password"] = bcrypt.hash(access_details["password"])
        update_result = self.user_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": access_details}
        )
        return update_result.modified_count > 0 or update_result.matched_count > 0

    def update_emergency_contact(self, employee_id, contact_details):
        update_result = self.user_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": contact_details}
        )
        return update_result.modified_count > 0 or update_result.matched_count > 0

    def update_address(self, employee_id, address_details):
        update_result = self.user_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": address_details}
        )
        return update_result.modified_count > 0 or update_result.matched_count > 0

    def update_hr_notes(self, employee_id, notes_details):
        update_result = self.user_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": notes_details}
        )
        return update_result.modified_count > 0 or update_result.matched_count > 0

    def update_documents(self, employee_id, document_details):
        update_result = self.user_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": document_details}
        )
        return update_result.modified_count > 0 or update_result.matched_count > 0

    def final_submit(self, employee_id, all_details):
        update_result = self.user_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": all_details}
        )
        return update_result.modified_count > 0 or update_result.matched_count > 0

    def validate_bulk_upload(self, file, create_by, validate_data=True):
        # Stub: parse file, validate rows, return summary
        # In production, parse CSV/XLSX, validate each row, collect errors
        # Here, return a mock response
        return {
            "success": True,
            "message": "File validated successfully",
            "data": {
                "totalRows": 150,
                "validRows": 145,
                "invalidRows": 5,
                "errors": [
                    {"row": 12, "field": "Email", "issue": "Invalid email format"},
                    {"row": 23, "field": "Employee ID", "issue": "Duplicate ID found"},
                    {"row": 45, "field": "Department", "issue": "Department not found"},
                    {"row": 67, "field": "Start Date", "issue": "Invalid date format"},
                    {"row": 89, "field": "Phone", "issue": "Missing required field"}
                ]
            }
        }

    def import_bulk_upload(self, file, create_by, skip_duplicates=True, update_existing=False, send_notifications=True, send_welcome_emails=False, validate_data=True):
        # Stub: parse file, import rows, return summary
        # In production, parse CSV/XLSX, import each row, collect errors
        # Here, return a mock response
        return {
            "success": True,
            "message": "Employees imported successfully",
            "data": {
                "importedCount": 145,
                "skippedCount": 5,
                "errors": [
                    {"row": 23, "field": "Employee ID", "issue": "Duplicate ID found"}
                ]
            }
        }

    def get_bulk_upload_template(self):
        # Generate a CSV template in memory
        columns = [
            "Full Name", "Employee ID", "Official Email", "Mobile Number", "Gender", "Date of Birth", "Department", "Designation", "Employee Type", "Joining Date", "Work Location", "Reporting Manager", "Employment Status", "Annual CTC", "Basic Salary (%)", "HRA (%)", "PAN Number", "Aadhaar Number", "Bank Account Number", "IFSC Code", "Bank Name", "PF Applicable", "Login Email/Username", "System Access Role", "Present Address", "Status",
            "Personal Email", "WhatsApp Number", "Blood Group", "Marital Status", "Special Allowance", "Performance Bonus", "Joining Bonus", "Other Benefits", "PF UAN Number", "ESI Applicable", "ESI Number", "Account Type", "Emergency Contact Name", "Emergency Contact Number", "Permanent Address"
        ]
        df = pd.DataFrame(columns=columns)
        return df.to_csv(index=False)

    def list_employees(self, page=1, limit=20, status=None, department=None, role=None, location=None, search=None):
        if page < 1 or limit < 1:
            raise ValueError("Page and limit must be positive integers")
        query = {}
        if status:
            query['status'] = status
        if department:
            query['department'] = department
        if role:
            query['position'] = role
        if location:
            query['location'] = location
        if search:
            query['$or'] = [
                {'name': {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}},
                {'id': {'$regex': search, '$options': 'i'}}
            ]
        total = self.user_collection.count_documents(query)
        employees = list(self.user_collection.find(query).skip((page-1)*limit).limit(limit))
        for emp in employees:
            emp['id'] = str(emp.get('_id', ''))
            emp.pop('_id', None)
        return {
            'success': True,
            'data': employees,
            'total': total,
            'page': page,
            'limit': limit
        }

    def get_employee_by_id(self, emp_id):
        from bson import ObjectId
        emp = self.user_collection.find_one({"_id": ObjectId(emp_id)})
        if not emp:
            return {"success": False, "data": None}
        emp['id'] = str(emp['_id'])
        emp.pop('_id', None)
        return {"success": True, "data": emp}

    def add_employee(self, employee_data):
        from bson import ObjectId
        result = self.user_collection.insert_one(employee_data)
        return {
            "success": True,
            "message": "Employee added successfully",
            "data": {"id": str(result.inserted_id)}
        }

    def edit_employee(self, emp_id, employee_data):
        from bson import ObjectId
        result = self.user_collection.update_one({"_id": ObjectId(emp_id)}, {"$set": employee_data})
        if result.modified_count > 0:
            return {"success": True, "message": "Employee updated successfully"}
        else:
            return {"success": False, "message": "Employee not found or no changes made"}

    def delete_employee(self, emp_id):
        from bson import ObjectId
        result = self.user_collection.delete_one({"_id": ObjectId(emp_id)})
        if result.deleted_count > 0:
            return {"success": True, "message": "Employee deleted successfully"}
        else:
            return {"success": False, "message": "Employee not found"}

    def get_employee_stats(self):
        from datetime import datetime, timedelta
        
        # Basic counts
        total = self.user_collection.count_documents({})
        active = self.user_collection.count_documents({"employment_status": "Active"})
        inactive = self.user_collection.count_documents({"employment_status": "Inactive"})
        
        # New employees (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new = self.user_collection.count_documents({"joining_date": {"$gte": thirty_days_ago.strftime('%Y-%m-%d')}})
        
        # Department and position counts
        departments = len(self.user_collection.distinct("department"))
        positions = len(self.user_collection.distinct("designation"))
        
        # Recently hired employees (last 30 days)
        recently_hired = list(self.user_collection.find(
            {"joining_date": {"$gte": thirty_days_ago.strftime('%Y-%m-%d')}},
            {
                "_id": 1,
                "full_name": 1,
                "designation": 1,
                "department": 1,
                "joining_date": 1,
                "employment_status": 1
            }
        ).limit(5))
        
        # Process recently hired data
        for emp in recently_hired:
            emp["id"] = str(emp["_id"])
            emp.pop("_id", None)
            emp["profile_image"] = "/images/profile_img.png"  # Default profile image
        
        # Upcoming birthdays (next 30 days)
        today = datetime.now()
        thirty_days_later = today + timedelta(days=30)
        
        upcoming_birthdays = []
        all_employees = list(self.user_collection.find({}, {
            "_id": 1,
            "full_name": 1,
            "designation": 1,
            "department": 1,
            "date_of_birth": 1,
            "joining_date": 1
        }))
        
        for emp in all_employees:
            if emp.get("date_of_birth"):
                try:
                    birth_date = datetime.strptime(emp["date_of_birth"], "%Y-%m-%d")
                    # Create this year's birthday
                    this_year_birthday = birth_date.replace(year=today.year)
                    
                    # If birthday has passed this year, check next year
                    if this_year_birthday < today:
                        this_year_birthday = birth_date.replace(year=today.year + 1)
                    
                    # Check if birthday is within next 30 days
                    if today <= this_year_birthday <= thirty_days_later:
                        days_until_birthday = (this_year_birthday - today).days
                        age = today.year - birth_date.year
                        
                        upcoming_birthdays.append({
                            "id": str(emp["_id"]),
                            "full_name": emp["full_name"],
                            "designation": emp.get("designation", ""),
                            "department": emp.get("department", ""),
                            "date_of_birth": emp["date_of_birth"],
                            "days_until_birthday": days_until_birthday,
                            "age": age,
                            "profile_image": "/images/profile_img.png"
                        })
                except (ValueError, TypeError):
                    continue
        
        # Sort by days until birthday
        upcoming_birthdays.sort(key=lambda x: x["days_until_birthday"])
        upcoming_birthdays = upcoming_birthdays[:5]  # Limit to 5
        

        # Work anniversaries (next 30 days)
        work_anniversaries = []
        for emp in all_employees:
            if emp.get("joining_date"):
                try:
                    join_date = datetime.strptime(emp["joining_date"], "%Y-%m-%d")
                    # Create this year's anniversary
                    this_year_anniversary = join_date.replace(year=today.year)
                    
                    # If anniversary has passed this year, check next year
                    if this_year_anniversary < today:
                        this_year_anniversary = join_date.replace(year=today.year + 1)
                    
                    # Check if anniversary is within next 30 days
                    if today <= this_year_anniversary <= thirty_days_later:
                        days_until_anniversary = (this_year_anniversary - today).days
                        years_of_service = today.year - join_date.year
                        
                        work_anniversaries.append({
                            "id": str(emp["_id"]),
                            "full_name": emp["full_name"],
                            "designation": emp.get("designation", ""),
                            "department": emp.get("department", ""),
                            "joining_date": emp["joining_date"],
                            "years_of_service": years_of_service,
                            "days_until_anniversary": days_until_anniversary,
                            "profile_image": "/images/profile_img.png"
                        })
                except (ValueError, TypeError):
                    continue
        
        # Sort by days until anniversary
        work_anniversaries.sort(key=lambda x: x["days_until_anniversary"])
        work_anniversaries = work_anniversaries[:5]  # Limit to 5
        
        return {
            "success": True,
            "data": {
                "total": total,
                "active": active,
                "inactive": inactive,
                "new": new,
                "departments": departments,
                "positions": positions,
                "recentlyHired": recently_hired,
                "upcomingBirthdays": upcoming_birthdays,
                "workAnniversaries": work_anniversaries
            }
        }

    def get_employee_analytics(self):
        # For demo, return mock data. You can implement aggregation pipelines for real analytics.
        return {
            "success": True,
            "data": {
                "growthTrend": [25, 35, 45, 60, 75, 85, 95, 88, 92, 98, 105, 112],
                "departmentDistribution": [
                    {"value": self.user_collection.count_documents({"department": d}), "name": d}
                    for d in self.user_collection.distinct("department")
                ],
                "performanceBar": [],
                "genderDiversity": [
                    {"name": "Male", "value": self.user_collection.count_documents({"gender": "Male"})},
                    {"name": "Female", "value": self.user_collection.count_documents({"gender": "Female"})}
                ]
            }
        }

    def get_audit_log(self, employee_id=None, action=None, date_from=None, date_to=None):
        logs_collection = self.client_database.get('employee_audit_log')
        if logs_collection is None:
            return {"success": True, "data": []}
        query = {}
        if employee_id:
            query['employee_id'] = employee_id
        if action:
            query['action'] = action
        if date_from or date_to:
            query['date'] = {}
            if date_from:
                query['date']['$gte'] = date_from
            if date_to:
                query['date']['$lte'] = date_to
            if not query['date']:
                del query['date']
        logs = list(logs_collection.find(query).sort('date', -1))
        for log in logs:
            log.pop('_id', None)
        return {"success": True, "data": logs}

    def hash_all_plaintext_passwords(self):
        bcrypt_regex = re.compile(r'^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$')
        users = self.user_collection.find({})
        for user in users:
            pwd = user.get('password')
            if pwd and not bcrypt_regex.match(pwd):
                hashed = bcrypt.hash(pwd)
                self.user_collection.update_one({'_id': user['_id']}, {'$set': {'password': hashed}})
