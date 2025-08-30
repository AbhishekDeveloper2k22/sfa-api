import os
import re
from datetime import datetime, timedelta, date
from app.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import pytz

load_dotenv()

class AppSidebarService:
    def __init__(self):
        self.client_database = client1['hrms_master']
        self.employee_collection = self.client_database['employee_master']
        self.timezone = pytz.timezone('Asia/Kolkata')

    def get_upcoming_celebrations(self, user_id, days=30, limit=20):
        """Get upcoming birthdays and work anniversaries for the next N days"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Calculate date range
            today = datetime.now(self.timezone).date()
            end_date = today + timedelta(days=days)
            
            celebrations = []
            total_birthdays = 0
            total_anniversaries = 0

            # Get all active employees
            employees = list(self.employee_collection.find({
                "employment_status": "Active"
            }).limit(limit * 3))  # Get more to filter

            for employee in employees:
                # Check for upcoming birthdays
                if employee.get('date_of_birth'):
                    try:
                        dob = datetime.strptime(employee['date_of_birth'], "%Y-%m-%d").date()
                        # Calculate next birthday
                        next_birthday = self._get_next_celebration_date(dob, today)
                        
                        if next_birthday <= end_date:
                            days_until = (next_birthday - today).days
                            celebrations.append({
                                "id": str(employee["_id"]),
                                "employeeId": str(employee["_id"]),
                                "name": employee.get("full_name", ""),
                                "designation": employee.get("designation", ""),
                                "department": employee.get("department", ""),
                                "type": "birthday",
                                "date": next_birthday.isoformat(),
                                "daysUntil": days_until,
                                "years": None,
                                "profileImage": employee.get("profile_image", "/images/profile_img.png"),
                                "color": "#ec4899",
                                "backgroundColor": "#fdf2f8"
                            })
                            total_birthdays += 1
                    except:
                        pass

                # Check for upcoming work anniversaries
                if employee.get('joining_date'):
                    try:
                        join_date = datetime.strptime(employee['joining_date'], "%Y-%m-%d").date()
                        # Calculate next anniversary
                        next_anniversary = self._get_next_celebration_date(join_date, today)
                        
                        if next_anniversary <= end_date:
                            days_until = (next_anniversary - today).days
                            years = next_anniversary.year - join_date.year
                            celebrations.append({
                                "id": str(employee["_id"]),
                                "employeeId": str(employee["_id"]),
                                "name": employee.get("full_name", ""),
                                "designation": employee.get("designation", ""),
                                "department": employee.get("department", ""),
                                "type": "anniversary",
                                "date": next_anniversary.isoformat(),
                                "daysUntil": days_until,
                                "years": years,
                                "profileImage": employee.get("profile_image", "/images/profile_img.png"),
                                "color": "#3b82f6",
                                "backgroundColor": "#eff6ff"
                            })
                            total_anniversaries += 1
                    except:
                        pass

            # Sort by days until celebration and limit results
            celebrations.sort(key=lambda x: x["daysUntil"])
            celebrations = celebrations[:limit]

            return {
                "success": True,
                "data": {
                    "celebrations": celebrations,
                    "summary": {
                        "totalBirthdays": total_birthdays,
                        "totalAnniversaries": total_anniversaries,
                        "totalCelebrations": len(celebrations),
                        "daysAhead": days
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get upcoming celebrations: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_employee_directory(self, user_id, search=None, department=None, designation=None, status="Active", page=1, limit=20):
        """Get employee directory with search and filtering options"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Build query
            query = {}
            
            # Exclude current user from results
            query["_id"] = {"$ne": ObjectId(user_id)}
            
            # Filter by employment status
            if status:
                query["employment_status"] = status
            
            # Filter by department
            if department:
                query["department"] = {"$regex": department, "$options": "i"}
            
            # Filter by designation
            if designation:
                query["designation"] = {"$regex": designation, "$options": "i"}
            
            # Search functionality
            if search:
                search_regex = {"$regex": search, "$options": "i"}
                query["$or"] = [
                    {"full_name": search_regex},
                    {"designation": search_regex},
                    {"department": search_regex},
                    {"employee_id": search_regex}
                ]

            # Calculate skip for pagination
            skip = (page - 1) * limit

            # Get total count
            total_count = self.employee_collection.count_documents(query)
            
            # Get employees with pagination
            employees = list(self.employee_collection.find(query).skip(skip).limit(limit))

            # Format employee data
            employee_list = []
            for employee in employees:
                employee_data = {
                    "id": str(employee["_id"]),
                    "employeeId": str(employee["_id"]),  # Using _id as employeeId
                    "name": employee.get("full_name", ""),
                    "designation": employee.get("designation", ""),
                    "department": employee.get("department", ""),
                    "email": employee.get("email", ""),
                    "personalEmail": employee.get("personal_email", ""),
                    "mobileNo": employee.get("mobile_no", ""),
                    "whatsappNumber": employee.get("whatsapp_number", ""),
                    "gender": employee.get("gender", ""),
                    "dateOfBirth": employee.get("date_of_birth", ""),
                    "bloodGroup": employee.get("blood_group", ""),
                    "maritalStatus": employee.get("marital_status", ""),
                    "employeeType": employee.get("employee_type", ""),
                    "employmentStatus": employee.get("employment_status", ""),
                    "joiningDate": employee.get("joining_date", ""),
                    "workLocation": employee.get("work_location", ""),
                    "reportingManager": employee.get("reporting_manager", ""),
                    "officialEmailUsername": employee.get("official_email_username", ""),
                    "roleAccessLevel": employee.get("role_access_level", ""),
                    "lastLogin": employee.get("last_login", ""),
                    "isOnline": self._check_employee_online_status(employee.get("_id"))
                }
                employee_list.append(employee_data)

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "employees": employee_list,
                    "pagination": {
                        "currentPage": page,
                        "totalPages": total_pages,
                        "totalCount": total_count,
                        "limit": limit,
                        "hasNext": has_next,
                        "hasPrev": has_prev
                    },
                    "filters": {
                        "search": search,
                        "department": department,
                        "designation": designation,
                        "status": status
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get employee directory: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_employee_details(self, user_id, employee_id):
        """Get detailed information about a specific employee"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get employee details
            employee = self.employee_collection.find_one({"_id": ObjectId(employee_id)})
            if not employee:
                return {
                    "success": False,
                    "message": "Employee not found",
                    "error": {"code": "EMPLOYEE_NOT_FOUND", "details": "Employee does not exist"}
                }

            # Format employee details
            employee_details = {
                "id": str(employee["_id"]),
                "employeeId": str(employee["_id"]),
                "name": employee.get("full_name", ""),
                "designation": employee.get("designation", ""),
                "department": employee.get("department", ""),
                "email": employee.get("email", ""),
                "personalEmail": employee.get("personal_email", ""),
                "mobileNo": employee.get("mobile_no", ""),
                "whatsappNumber": employee.get("whatsapp_number", ""),
                "gender": employee.get("gender", ""),
                "dateOfBirth": employee.get("date_of_birth", ""),
                "bloodGroup": employee.get("blood_group", ""),
                "maritalStatus": employee.get("marital_status", ""),
                "employeeType": employee.get("employee_type", ""),
                "employmentStatus": employee.get("employment_status", ""),
                "joiningDate": employee.get("joining_date", ""),
                "workLocation": employee.get("work_location", ""),
                "reportingManager": employee.get("reporting_manager", ""),
                "officialEmailUsername": employee.get("official_email_username", ""),
                "roleAccessLevel": employee.get("role_access_level", ""),
                "lastLogin": employee.get("last_login", ""),
                "isOnline": self._check_employee_online_status(employee.get("_id")),
                "workAnniversary": self._calculate_work_anniversary(employee.get("joining_date")),
                "age": self._calculate_age(employee.get("date_of_birth")),
                # Address information
                "presentAddress": {
                    "line1": employee.get("present_address_line1", ""),
                    "line2": employee.get("present_address_line2", ""),
                    "city": employee.get("present_city", ""),
                    "state": employee.get("present_state", ""),
                    "pinCode": employee.get("present_pin_code", ""),
                    "country": employee.get("present_country", "")
                },
                "permanentAddress": {
                    "line1": employee.get("permanent_address_line1", ""),
                    "line2": employee.get("permanent_address_line2", ""),
                    "city": employee.get("permanent_city", ""),
                    "state": employee.get("permanent_state", ""),
                    "pinCode": employee.get("permanent_pin_code", ""),
                    "country": employee.get("permanent_country", "")
                },
                # Emergency contact
                "emergencyContact": {
                    "name": employee.get("contact_name", ""),
                    "relationship": employee.get("relationship", ""),
                    "mobile": employee.get("emergency_mobile", ""),
                    "address": employee.get("emergency_address", "")
                },
                # Salary information
                "salary": {
                    "annualCtc": employee.get("annual_ctc", 0),
                    "monthlyGrossSalary": employee.get("monthly_gross_salary", 0),
                    "netSalaryMonthly": employee.get("net_salary_monthly", 0),
                    "netSalaryYearly": employee.get("net_salary_yearly", 0)
                },
                # Bank information
                "bankDetails": {
                    "accountNo": employee.get("bank_account_no", ""),
                    "bankName": employee.get("bank_name", ""),
                    "ifscCode": employee.get("ifsc_code", ""),
                    "accountType": employee.get("account_type", "")
                },
                # Documents
                "documents": {
                    "aadhaarCard": employee.get("aadhaar_card", ""),
                    "panCard": employee.get("pan_card", ""),
                    "bankPassbook": employee.get("bank_passbook", ""),
                    "offerLetter": employee.get("offer_letter", ""),
                    "resumeCv": employee.get("resume_cv", ""),
                    "educationalCertificates": employee.get("educational_certificates", []),
                    "experienceLetter": employee.get("experience_letter", "")
                },
                # Additional fields
                "aadhaarNo": employee.get("aadhaar_no", ""),
                "panNo": employee.get("pan_no", ""),
                "hrNotes": employee.get("hr_notes", ""),
                "finalSubmissionStatus": employee.get("final_submission_status", ""),
                "finalSubmittedAt": employee.get("final_submitted_at", ""),
                "finalSubmittedBy": employee.get("final_submitted_by", ""),
                "dateCreated": employee.get("date_created", ""),
                "dateUpdated": employee.get("date_updated", ""),
                "createdBy": employee.get("created_by", ""),
                "updatedBy": employee.get("updated_by", "")
            }

            return {
                "success": True,
                "data": employee_details
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get employee details: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _get_next_celebration_date(self, original_date, today):
        """Calculate the next celebration date (birthday or anniversary)"""
        # Create this year's celebration date
        this_year_celebration = original_date.replace(year=today.year)
        
        # If this year's celebration has passed, get next year's
        if this_year_celebration < today:
            next_year_celebration = original_date.replace(year=today.year + 1)
            return next_year_celebration
        else:
            return this_year_celebration

    def _check_employee_online_status(self, employee_id):
        """Check if employee is currently online (mock implementation)"""
        # In a real implementation, this would check attendance records
        # or real-time status from the system
        try:
            # Mock implementation - randomly return online status
            import random
            return random.choice([True, False])
        except:
            return False

    def _calculate_work_anniversary(self, joining_date):
        """Calculate work anniversary information"""
        if not joining_date:
            return None
        
        try:
            join_date = datetime.strptime(joining_date, "%Y-%m-%d").date()
            today = datetime.now(self.timezone).date()
            years = today.year - join_date.year
            
            # Adjust for if birthday hasn't occurred yet this year
            if today < join_date.replace(year=today.year):
                years -= 1
            
            return {
                "years": years,
                "nextAnniversary": self._get_next_celebration_date(join_date, today).isoformat()
            }
        except:
            return None

    def _calculate_age(self, date_of_birth):
        """Calculate employee age"""
        if not date_of_birth:
            return None
        
        try:
            dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            today = datetime.now(self.timezone).date()
            age = today.year - dob.year
            
            # Adjust for if birthday hasn't occurred yet this year
            if today < dob.replace(year=today.year):
                age -= 1
            
            return age
        except:
            return None