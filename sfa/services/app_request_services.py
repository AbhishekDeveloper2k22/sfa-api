import os
import requests
from datetime import datetime, timedelta, date
from sfa.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import pytz
import math
import uuid
import shutil

load_dotenv()

class AppRequestService:
    def __init__(self):
        self.client_database = client1['hrms_master']
        self.request_collection = self.client_database['requests']  # Single collection for all requests
        self.employee_collection = self.client_database['employee_master']
        self.leave_balance_collection = self.client_database['leave_balances']
        self.timezone = pytz.timezone('Asia/Kolkata')  # Default to IST

    def _format_date(self, date_str):
        """Format date string to readable format"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d %b %Y")
        except:
            return date_str

    def _calculate_leave_days(self, start_date, end_date, half_day=False, half_day_type=None):
        """Calculate number of leave days between start and end date"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            if start > end:
                return 0
            
            # Calculate working days (excluding weekends)
            current = start
            working_days = 0
            
            while current <= end:
                # Monday = 0, Sunday = 6
                if current.weekday() < 5:  # Monday to Friday
                    working_days += 1
                current += timedelta(days=1)
            
            # Handle half day
            if half_day and working_days == 1:
                return 0.5
            
            return working_days
        except:
            return 0

    def _get_request_type_display_name(self, request_type):
        """Get display name for request type"""
        request_type_names = {
            "leave": "Leave Request",
            "regularisation": "Regularisation Request",
            "wfh": "Work From Home Request",
            "compensatory_off": "Compensatory Off Request",
            "expense": "Expense Request"
        }
        return request_type_names.get(request_type, request_type.title())

    def _get_leave_type_display_name(self, leave_type):
        """Get display name for leave type"""
        leave_type_names = {
            "casual": "Casual Leave",
            "sick": "Sick Leave",
            "annual": "Annual Leave",
            "maternity": "Maternity Leave",
            "paternity": "Paternity Leave",
            "bereavement": "Bereavement Leave",
            "other": "Other Leave"
        }
        return leave_type_names.get(leave_type, leave_type.title())

    def apply_request(self, user_id, request_type, start_date=None, end_date=None, reason="", half_day=False, half_day_type=None, regularisation_data={}, wfh_data={}, compensatory_off_data={}, expense_data={}):
        """Apply for any type of request"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Handle different request types
            if request_type == "leave":
                return self._apply_leave_request(user_id, start_date, end_date, reason, half_day, half_day_type)
            elif request_type == "regularisation":
                return self._apply_regularisation_request(user_id, start_date, end_date, reason, regularisation_data)
            elif request_type == "wfh":
                return self._apply_wfh_request(user_id, start_date, end_date, reason, wfh_data)
            elif request_type == "compensatory_off":
                return self._apply_compensatory_off_request(user_id, start_date, end_date, reason, compensatory_off_data)
            elif request_type == "expense":
                return self._apply_expense_request(user_id, reason, expense_data)
            else:
                return {
                    "success": False,
                    "message": "Invalid request type",
                    "error": {"code": "VALIDATION_ERROR", "details": "Invalid request type"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to apply request: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _apply_leave_request(self, user_id, start_date, end_date, reason, half_day, half_day_type):
        """Apply for leave request"""
        # Fetch valid leave types from leave_balances
        balance_record = self.leave_balance_collection.find_one({"user_id": user_id})
        if not balance_record:
            # Create default balance if not exists
            default_balance = {
                "user_id": user_id,
                "casual": {"total": 12, "used": 0, "remaining": 12},
                "sick": {"total": 15, "used": 0, "remaining": 15},
                "annual": {"total": 21, "used": 0, "remaining": 21},
                "maternity": {"total": 180, "used": 0, "remaining": 180},
                "paternity": {"total": 15, "used": 0, "remaining": 15},
                "bereavement": {"total": 7, "used": 0, "remaining": 7},
                "other": {"total": 10, "used": 0, "remaining": 10},
                "created_at": datetime.now(self.timezone).isoformat(),
                "updated_at": datetime.now(self.timezone).isoformat()
            }
            self.leave_balance_collection.insert_one(default_balance)
            balance_record = default_balance

        # Get leave type from reason or default to casual
        leave_type = "casual"  # Default
        valid_leave_types = [k for k in balance_record.keys() if k not in ["user_id", "_id", "created_at", "updated_at"]]
        
        # Check if no remaining leave for any type
        leave_balance = balance_record.get(leave_type, {})
        if leave_balance.get("remaining", 0) <= 0:
            return {
                "success": False,
                "message": f"No remaining leave for {leave_type}",
                "error": {"code": "INSUFFICIENT_BALANCE", "details": f"No remaining leave for {leave_type}"}
            }

        # Validate dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            today = datetime.now(self.timezone).date()
            if start < today:
                return {
                    "success": False,
                    "message": "Cannot apply leave for past dates",
                    "error": {"code": "VALIDATION_ERROR", "details": "Start date cannot be in the past"}
                }
            if end < start:
                return {
                    "success": False,
                    "message": "End date cannot be before start date",
                    "error": {"code": "VALIDATION_ERROR", "details": "End date must be after start date"}
                }
        except ValueError:
            return {
                "success": False,
                "message": "Invalid date format",
                "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
            }

        # Calculate leave days
        leave_days = self._calculate_leave_days(start_date, end_date, half_day, half_day_type)
        if leave_days <= 0:
            return {
                "success": False,
                "message": "Invalid leave duration",
                "error": {"code": "VALIDATION_ERROR", "details": "Leave duration must be at least 0.5 days"}
            }

        # Check leave balance
        if leave_balance.get("remaining", 0) < leave_days:
            return {
                "success": False,
                "message": f"Insufficient {leave_type} leave balance",
                "error": {"code": "INSUFFICIENT_BALANCE", "details": f"You have {leave_balance.get('remaining', 0)} days remaining, but requested {leave_days} days"}
            }

        # Check for overlapping requests
        overlap_query = {
            "user_id": user_id,
            "request_type": "leave",
            "status": {"$in": ["pending", "approved"]},
            "$or": [
                {
                    "start_date": {"$lte": end_date},
                    "end_date": {"$gte": start_date}
                }
            ]
        }
        existing_request = self.request_collection.find_one(overlap_query)
        if existing_request:
            return {
                "success": False,
                "message": "Leave request overlaps with existing request",
                "error": {"code": "OVERLAP_ERROR", "details": "You already have a request for these dates"}
            }

        # Create request
        request_data = {
            "user_id": user_id,
            "employee_id": user_id,
            "request_type": "leave",
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "leave_days": leave_days,
            "reason": reason,
            "half_day": half_day,
            "half_day_type": half_day_type,
            "status": "pending",
            "applied_by": user_id,
            "applied_at": datetime.now(self.timezone).isoformat(),
            "created_at": datetime.now(self.timezone).isoformat(),
            "updated_at": datetime.now(self.timezone).isoformat()
        }

        result = self.request_collection.insert_one(request_data)
        if result.inserted_id:
            # Deduct leave from leave_balances
            self.leave_balance_collection.update_one(
                {"user_id": user_id},
                {"$inc": {f"{leave_type}.used": leave_days, f"{leave_type}.remaining": -leave_days}, "$set": {"updated_at": datetime.now(self.timezone).isoformat()}}
            )
            return {
                "success": True,
                "message": "Leave request submitted successfully",
                "data": {
                    "request_id": str(result.inserted_id),
                    "request_type": "leave",
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "leave_days": leave_days,
                    "status": "pending"
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to submit leave request",
                "error": {"code": "DATABASE_ERROR", "details": "Could not save request"}
            }

    def _apply_regularisation_request(self, user_id, start_date, end_date, reason, regularisation_data):
        """Apply for regularisation request"""
        # Validate dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            today = datetime.now(self.timezone).date()
            if end > today:
                return {
                    "success": False,
                    "message": "Regularisation can only be applied for past dates",
                    "error": {"code": "VALIDATION_ERROR", "details": "Regularisation can only be applied for past dates"}
                }
        except ValueError:
            return {
                "success": False,
                "message": "Invalid date format",
                "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
            }

        # Check for duplicate regularisation request for same date and punch times
        punch_in = regularisation_data.get("punchIn")
        punch_out = regularisation_data.get("punchOut")
        
        existing_request = self.request_collection.find_one({
            "user_id": user_id,
            "request_type": "regularisation",
            "start_date": start_date,
            "end_date": end_date,
            "status": {"$in": ["pending", "approved"]}  # Check both pending and approved requests
        })
        
        if existing_request:
            return {
                "success": False,
                "message": "Regularisation request already exists for this date and punch times",
                "error": {
                    "code": "DUPLICATE_REQUEST", 
                    "details": f"Regularisation request for {start_date} with punch in {punch_in} and punch out {punch_out} already exists"
                }
            }

        # Create request
        request_data = {
            "user_id": user_id,
            "employee_id": user_id,
            "request_type": "regularisation",
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
            "punch_in": regularisation_data.get("punchIn"),
            "punch_out": regularisation_data.get("punchOut"),
            "status": "pending",
            "applied_by": user_id,
            "applied_at": datetime.now(self.timezone).isoformat(),
            "created_at": datetime.now(self.timezone).isoformat(),
            "updated_at": datetime.now(self.timezone).isoformat()
        }

        result = self.request_collection.insert_one(request_data)
        if result.inserted_id:
            return {
                "success": True,
                "message": "Regularisation request submitted successfully",
                "data": {
                    "request_id": str(result.inserted_id),
                    "request_type": "regularisation",
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": "pending"
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to submit regularisation request",
                "error": {"code": "DATABASE_ERROR", "details": "Could not save request"}
            }

    def _apply_wfh_request(self, user_id, start_date, end_date, reason, wfh_data):
        """Apply for work from home request"""
        # Validate dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            today = datetime.now(self.timezone).date()
            if start < today:
                return {
                    "success": False,
                    "message": "Cannot apply WFH for past dates",
                    "error": {"code": "VALIDATION_ERROR", "details": "Start date cannot be in the past"}
                }
        except ValueError:
            return {
                "success": False,
                "message": "Invalid date format",
                "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
            }

        # Check for duplicate WFH request for same date range and location
        location = wfh_data.get("location")
        
        existing_request = self.request_collection.find_one({
            "user_id": user_id,
            "request_type": "wfh",
            "start_date": start_date,
            "end_date": end_date,
            "status": {"$in": ["pending", "approved"]}  # Check both pending and approved requests
        })
        
        if existing_request:
            return {
                "success": False,
                "message": "WFH request already exists for this date range and location",
                "error": {
                    "code": "DUPLICATE_REQUEST", 
                    "details": f"WFH request for {start_date} to {end_date} at {location} already exists"
                }
            }

        # Create request
        request_data = {
            "user_id": user_id,
            "employee_id": user_id,
            "request_type": "wfh",
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
            "location": wfh_data.get("location"),
            "status": "pending",
            "applied_by": user_id,
            "applied_at": datetime.now(self.timezone).isoformat(),
            "created_at": datetime.now(self.timezone).isoformat(),
            "updated_at": datetime.now(self.timezone).isoformat()
        }

        result = self.request_collection.insert_one(request_data)
        if result.inserted_id:
            return {
                "success": True,
                "message": "Work from home request submitted successfully",
                "data": {
                    "request_id": str(result.inserted_id),
                    "request_type": "wfh",
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": "pending"
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to submit WFH request",
                "error": {"code": "DATABASE_ERROR", "details": "Could not save request"}
            }

    def _apply_compensatory_off_request(self, user_id, start_date, end_date, reason, compensatory_off_data):
        """Apply for compensatory off request"""
        # Validate dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            today = datetime.now(self.timezone).date()
            if start < today:
                return {
                    "success": False,
                    "message": "Cannot apply compensatory off for past dates",
                    "error": {"code": "VALIDATION_ERROR", "details": "Start date cannot be in the past"}
                }
        except ValueError:
            return {
                "success": False,
                "message": "Invalid date format",
                "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
            }

        # Check for duplicate compensatory off request for same work date and compensatory off date
        work_hours = compensatory_off_data.get("workHours")
        
        existing_request = self.request_collection.find_one({
            "user_id": user_id,
            "request_type": "compensatory_off",
            "start_date": start_date,  # work date
            "end_date": end_date,      # compensatory off date
            "status": {"$in": ["pending", "approved"]}  # Check both pending and approved requests
        })
        
        if existing_request:
            return {
                "success": False,
                "message": "Compensatory off request already exists for this work date and compensatory off date",
                "error": {
                    "code": "DUPLICATE_REQUEST", 
                    "details": f"Compensatory off request for work date {start_date} and compensatory off date {end_date} already exists"
                }
            }

        # Create request
        request_data = {
            "user_id": user_id,
            "employee_id": user_id,
            "request_type": "compensatory_off",
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
            "workHours": work_hours, 
            "status": "pending",
            "applied_by": user_id,
            "applied_at": datetime.now(self.timezone).isoformat(),
            "created_at": datetime.now(self.timezone).isoformat(),
            "updated_at": datetime.now(self.timezone).isoformat()
        }

        result = self.request_collection.insert_one(request_data)
        if result.inserted_id:
            return {
                "success": True,
                "message": "Compensatory off request submitted successfully",
                "data": {
                    "request_id": str(result.inserted_id),
                    "request_type": "compensatory_off",
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": "pending"
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to submit compensatory off request",
                "error": {"code": "DATABASE_ERROR", "details": "Could not save request"}
            }

    def _apply_expense_request(self, user_id, reason, expense_data):
        """Apply for expense request"""
        # Validate expense data
        if not expense_data.get("amount"):
            return {
                "success": False,
                "message": "Expense amount is required",
                "error": {"code": "VALIDATION_ERROR", "details": "Expense amount is required"}
            }

        # Check for duplicate expense request for same expense type, amount, and date
        expense_type = expense_data.get("expenseType")
        amount = expense_data.get("amount")
        expense_date = expense_data.get("date")
        
        existing_request = self.request_collection.find_one({
            "user_id": user_id,
            "request_type": "expense",
            "expenseType": expense_type,
            "date": expense_date,
            "status": {"$in": ["pending", "approved"]}  # Check both pending and approved requests
        })
        
        if existing_request:
            return {
                "success": False,
                "message": "Expense request already exists for this expense type, amount, and date",
                "error": {
                    "code": "DUPLICATE_REQUEST", 
                    "details": f"Expense request for {expense_type} with amount {amount} on {expense_date} already exists"
                }
            }

        # Create request
        request_data = {
            "user_id": user_id,
            "employee_id": user_id,
            "request_type": "expense",
            "expenseType": expense_type,
            "amount": amount,
            "start_date": expense_date,
            "status": "pending",
            "applied_by": user_id,
            "applied_at": datetime.now(self.timezone).isoformat(),
            "created_at": datetime.now(self.timezone).isoformat(),
            "updated_at": datetime.now(self.timezone).isoformat()
        }

        result = self.request_collection.insert_one(request_data)
        if result.inserted_id:
            return {
                "success": True,
                "message": "Expense request submitted successfully",
                "data": {
                    "request_id": str(result.inserted_id),
                    "request_type": "expense",
                    "amount": expense_data.get("amount"),
                    "status": "pending"
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to submit expense request",
                "error": {"code": "DATABASE_ERROR", "details": "Could not save request"}
            }

    def get_request_list(self, user_id, page=1, limit=20, status="all", request_type=None, year=None):
        """Get user's request history with pagination and filtering"""
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
            query = {"user_id": user_id}
            
            if status != "all":
                query["status"] = status
            
            # Handle request_type filtering
            if request_type and request_type != "all":
                query["request_type"] = request_type
            
            if year:
                query["start_date"] = {"$regex": f"^{year}-"}

            # Get total count
            total_records = self.request_collection.count_documents(query)
            
            # Apply pagination
            skip = (page - 1) * limit
            request_records = list(self.request_collection.find(query).sort("applied_at", -1).skip(skip).limit(limit))

            # Process records
            request_list = []
            for record in request_records:
                # Base request data
                request_data = {
                    "id": str(record["_id"]),
                    "requestType": record["request_type"],
                    "requestTypeDisplay": self._get_request_type_display_name(record["request_type"]),
                    "reason": record.get("reason", ""),
                    "status": record["status"],
                    "appliedAt": record["applied_at"],
                    "appliedAtFormatted": self._format_date(record["applied_at"].split("T")[0]),
                    "approvedBy": record.get("approved_by"),
                    "approvedAt": record.get("approved_at"),
                    "rejectedBy": record.get("rejected_by"),
                    "rejectedAt": record.get("rejected_at"),
                    "rejectionReason": record.get("rejection_reason", ""),
                    "cancelledBy": record.get("cancelled_by"),
                    "cancelledAt": record.get("cancelled_at"),
                    "cancellationReason": record.get("cancellation_reason", ""),
                    "attachments": record.get("attachments", [])
                }

                # Add type-specific data based on request_type
                if record["request_type"] == "leave":
                    request_data.update({
                        "startDate": record.get("start_date"),
                        "endDate": record.get("end_date"),
                        "startDateFormatted": self._format_date(record.get("start_date")) if record.get("start_date") else None,
                        "endDateFormatted": self._format_date(record.get("end_date")) if record.get("end_date") else None,
                        "leaveDays": record.get("leave_days"),
                        "leaveType": record.get("leave_type"),
                        "leaveTypeDisplay": self._get_leave_type_display_name(record.get("leave_type")) if record.get("leave_type") else None,
                        "halfDay": record.get("half_day", False),
                        "halfDayType": record.get("half_day_type")
                    })
                
                elif record["request_type"] == "regularisation":
                    request_data.update({
                        "startDate": record.get("start_date"),
                        "endDate": record.get("end_date"),
                        "startDateFormatted": self._format_date(record.get("start_date")) if record.get("start_date") else None,
                        "endDateFormatted": self._format_date(record.get("end_date")) if record.get("end_date") else None,
                        "punchIn": record.get("punch_in"),
                        "punchOut": record.get("punch_out")
                    })
                
                elif record["request_type"] == "wfh":
                    request_data.update({
                        "startDate": record.get("start_date"),
                        "endDate": record.get("end_date"),
                        "startDateFormatted": self._format_date(record.get("start_date")) if record.get("start_date") else None,
                        "endDateFormatted": self._format_date(record.get("end_date")) if record.get("end_date") else None,
                        "location": record.get("location")
                    })
                
                elif record["request_type"] == "compensatory_off":
                    request_data.update({
                        "startDate": record.get("start_date"),  # work date
                        "endDate": record.get("end_date"),      # compensatory off date
                        "startDateFormatted": self._format_date(record.get("start_date")) if record.get("start_date") else None,
                        "endDateFormatted": self._format_date(record.get("end_date")) if record.get("end_date") else None,
                        "workHours": record.get("workHours")
                    })
                
                elif record["request_type"] == "expense":
                    request_data.update({
                        "expenseType": record.get("expenseType"),
                        "amount": record.get("amount"),
                        "date": record.get("date"),
                        "dateFormatted": self._format_date(record.get("date")) if record.get("date") else None,
                        "description": record.get("description", "")
                    })

                request_list.append(request_data)

            # Calculate pagination
            total_pages = (total_records + limit - 1) // limit
            
            pagination = {
                "page": page,
                "limit": limit,
                "total": total_records,
                "totalPages": total_pages,
                "hasNext": page < total_pages,
                "hasPrev": page > 1
            }

            # Get count summary for each request type
            summary = self._get_request_type_summary(user_id, status, year)

            return {
                "success": True,
                "data": {
                    "requests": request_list,
                    "pagination": pagination,
                    "summary": summary
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get request list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _get_request_type_summary(self, user_id, status="all", year=None):
        """Get count summary for each request type"""
        try:
            # Base query
            base_query = {"user_id": user_id}
            
            if status != "all":
                base_query["status"] = status
            
            if year:
                base_query["start_date"] = {"$regex": f"^{year}-"}

            # Get counts for each request type
            request_types = ["leave", "regularisation", "wfh", "compensatory_off", "expense"]
            summary = {}
            
            for req_type in request_types:
                query = base_query.copy()
                query["request_type"] = req_type
                count = self.request_collection.count_documents(query)
                summary[req_type] = {
                    "count": count,
                    "displayName": self._get_request_type_display_name(req_type)
                }

            # Get total count
            total_count = self.request_collection.count_documents(base_query)
            summary["total"] = {
                "count": total_count,
                "displayName": "All"
            }

            return summary

        except Exception as e:
            return {}

    def get_leave_balance(self, user_id, status=None, start_date=None, end_date=None, filter_leave_type=None):
        """Get user's leave balance for different leave types and leave requests with filtering"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get leave balance
            balance_record = self.leave_balance_collection.find_one({"user_id": user_id})
            
            if not balance_record:
                # Create default balance if not exists
                default_balance = {
                    "user_id": user_id,
                    "casual": {"total": 12, "used": 0, "remaining": 12},
                    "sick": {"total": 15, "used": 0, "remaining": 15},
                    "annual": {"total": 21, "used": 0, "remaining": 21},
                    "maternity": {"total": 180, "used": 0, "remaining": 180},
                    "paternity": {"total": 15, "used": 0, "remaining": 15},
                    "bereavement": {"total": 7, "used": 0, "remaining": 7},
                    "other": {"total": 10, "used": 0, "remaining": 10},
                    "created_at": datetime.now(self.timezone).isoformat(),
                    "updated_at": datetime.now(self.timezone).isoformat()
                }
                self.leave_balance_collection.insert_one(default_balance)
                balance_record = default_balance

            # Format balance data
            balance_data = []
            for leave_type, balance in balance_record.items():
                if leave_type not in ["user_id", "_id", "created_at", "updated_at"]:
                    balance_data.append({
                        "leaveType": leave_type,
                        "leaveTypeDisplay": self._get_leave_type_display_name(leave_type),
                        "total": balance.get("total", 0),
                        "used": balance.get("used", 0),
                        "remaining": balance.get("remaining", 0)
                    })

            # Build leave requests query with filters
            leave_requests_query = {
                "user_id": user_id,
                "request_type": "leave"
            }
            
            # Apply filters only if they are provided and not empty
            if status and status != "all" and status.strip():
                leave_requests_query["status"] = status

            print("status", status)

            if filter_leave_type and filter_leave_type.strip():
                leave_requests_query["leave_type"] = filter_leave_type
            
            if start_date and start_date.strip():
                leave_requests_query["start_date"] = {"$gte": start_date}
            
            if end_date and end_date.strip():
                if "start_date" in leave_requests_query:
                    leave_requests_query["start_date"]["$lte"] = end_date
                else:
                    leave_requests_query["start_date"] = {"$lte": end_date}

            print("leave_requests_query", leave_requests_query)
            
            leave_requests = list(self.request_collection.find(leave_requests_query).sort("applied_at", -1))
            
            # Format leave requests
            leave_requests_data = []
            for request in leave_requests:
                leave_request = {
                    "id": str(request["_id"]),
                    "leaveType": request.get("leave_type"),
                    "leaveTypeDisplay": self._get_leave_type_display_name(request.get("leave_type")) if request.get("leave_type") else None,
                    "startDate": request.get("start_date"),
                    "endDate": request.get("end_date"),
                    "startDateFormatted": self._format_date(request.get("start_date")) if request.get("start_date") else None,
                    "endDateFormatted": self._format_date(request.get("end_date")) if request.get("end_date") else None,
                    "leaveDays": request.get("leave_days"),
                    "reason": request.get("reason", ""),
                    "status": request["status"],
                    "halfDay": request.get("half_day", False),
                    "halfDayType": request.get("half_day_type"),
                    "appliedAt": request["applied_at"],
                    "appliedAtFormatted": self._format_date(request["applied_at"].split("T")[0]),
                    "approvedBy": request.get("approved_by"),
                    "approvedAt": request.get("approved_at"),
                    "rejectedBy": request.get("rejected_by"),
                    "rejectedAt": request.get("rejected_at"),
                    "rejectionReason": request.get("rejection_reason", ""),
                    "cancelledBy": request.get("cancelled_by"),
                    "cancelledAt": request.get("cancelled_at"),
                    "cancellationReason": request.get("cancellation_reason", ""),
                    "attachments": request.get("attachments", [])
                }
                leave_requests_data.append(leave_request)

            return {
                "success": True,
                "data": {
                    "balances": balance_data,
                    "leaveRequests": leave_requests_data
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get leave balance: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_request_details(self, user_id, request_id):
        """Get detailed information for a specific request"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get request record
            request_record = self.request_collection.find_one({
                "_id": ObjectId(request_id),
                "user_id": user_id
            })

            if not request_record:
                return {
                    "success": False,
                    "message": "Request not found",
                    "error": {"code": "REQUEST_NOT_FOUND", "details": "Request does not exist"}
                }

            # Base request details
            request_details = {
                "id": str(request_record["_id"]),
                "requestType": request_record["request_type"],
                "requestTypeDisplay": self._get_request_type_display_name(request_record["request_type"]),
                "reason": request_record.get("reason", ""),
                "status": request_record["status"],
                "appliedAt": request_record["applied_at"],
                "appliedAtFormatted": self._format_date(request_record["applied_at"].split("T")[0]),
                "approvedBy": request_record.get("approved_by"),
                "approvedAt": request_record.get("approved_at"),
                "rejectedBy": request_record.get("rejected_by"),
                "rejectedAt": request_record.get("rejected_at"),
                "rejectionReason": request_record.get("rejection_reason", ""),
                "cancelledBy": request_record.get("cancelled_by"),
                "cancelledAt": request_record.get("cancelled_at"),
                "cancellationReason": request_record.get("cancellation_reason", ""),
                "attachments": request_record.get("attachments", [])
            }

            # Add type-specific data based on request_type
            if request_record["request_type"] == "leave":
                request_details.update({
                    "startDate": request_record.get("start_date"),
                    "endDate": request_record.get("end_date"),
                    "startDateFormatted": self._format_date(request_record.get("start_date")) if request_record.get("start_date") else None,
                    "endDateFormatted": self._format_date(request_record.get("end_date")) if request_record.get("end_date") else None,
                    "leaveDays": request_record.get("leave_days"),
                    "leaveType": request_record.get("leave_type"),
                    "leaveTypeDisplay": self._get_leave_type_display_name(request_record.get("leave_type")) if request_record.get("leave_type") else None,
                    "halfDay": request_record.get("half_day", False),
                    "halfDayType": request_record.get("half_day_type")
                })
            
            elif request_record["request_type"] == "regularisation":
                request_details.update({
                    "startDate": request_record.get("start_date"),
                    "endDate": request_record.get("end_date"),
                    "startDateFormatted": self._format_date(request_record.get("start_date")) if request_record.get("start_date") else None,
                    "endDateFormatted": self._format_date(request_record.get("end_date")) if request_record.get("end_date") else None,
                    "punchIn": request_record.get("punch_in"),
                    "punchOut": request_record.get("punch_out")
                })
            
            elif request_record["request_type"] == "wfh":
                request_details.update({
                    "startDate": request_record.get("start_date"),
                    "endDate": request_record.get("end_date"),
                    "startDateFormatted": self._format_date(request_record.get("start_date")) if request_record.get("start_date") else None,
                    "endDateFormatted": self._format_date(request_record.get("end_date")) if request_record.get("end_date") else None,
                    "location": request_record.get("location")
                })
            
            elif request_record["request_type"] == "compensatory_off":
                request_details.update({
                    "startDate": request_record.get("start_date"),  # work date
                    "endDate": request_record.get("end_date"),      # compensatory off date
                    "startDateFormatted": self._format_date(request_record.get("start_date")) if request_record.get("start_date") else None,
                    "endDateFormatted": self._format_date(request_record.get("end_date")) if request_record.get("end_date") else None,
                    "workHours": request_record.get("workHours")
                })
            
            elif request_record["request_type"] == "expense":
                request_details.update({
                    "expenseType": request_record.get("expenseType"),
                    "amount": request_record.get("amount"),
                    "date": request_record.get("start_date"),  # Using start_date as date for expense
                    "dateFormatted": self._format_date(request_record.get("start_date")) if request_record.get("start_date") else None,
                    "description": request_record.get("description", "")
                })

            return {
                "success": True,
                "data": request_details
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get request details: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def cancel_request(self, user_id, request_id, reason=""):
        """Cancel a request"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get request record
            request_record = self.request_collection.find_one({
                "_id": ObjectId(request_id),
                "user_id": user_id
            })

            if not request_record:
                return {
                    "success": False,
                    "message": "Request not found",
                    "error": {"code": "REQUEST_NOT_FOUND", "details": "Request does not exist"}
                }

            # Check if request can be cancelled
            if request_record["status"] not in ["pending", "approved"]:
                return {
                    "success": False,
                    "message": "Request cannot be cancelled",
                    "error": {"code": "INVALID_STATUS", "details": "Only pending or approved requests can be cancelled"}
                }

            # Check if request has already started (for date-based requests)
            if request_record.get("start_date"):
                start_date = datetime.strptime(request_record["start_date"], "%Y-%m-%d").date()
                today = datetime.now(self.timezone).date()
                
                if start_date <= today:
                    return {
                        "success": False,
                        "message": "Cannot cancel request that has already started",
                        "error": {"code": "INVALID_CANCELLATION", "details": "Request has already started"}
                    }

            # Update request record
            update_data = {
                "status": "cancelled",
                "cancelled_by": user_id,
                "cancelled_at": datetime.now(self.timezone).isoformat(),
                "cancellation_reason": reason,
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            result = self.request_collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Request cancelled successfully",
                    "data": {
                        "request_id": request_id,
                        "status": "cancelled"
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to cancel request",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update request"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to cancel request: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_request_types(self):
        """Get available request types and their descriptions"""
        try:
            request_types = [
                {
                    "type": "leave",
                    "displayName": "Leave Request",
                    "description": "Apply for various types of leave",
                    "requiresApproval": True,
                    "requiresDates": True
                },
                {
                    "type": "regularisation",
                    "displayName": "Regularisation Request",
                    "description": "Regularise attendance for past dates",
                    "requiresApproval": True,
                    "requiresDates": True
                },
                {
                    "type": "wfh",
                    "displayName": "Work From Home Request",
                    "description": "Request to work from home",
                    "requiresApproval": True,
                    "requiresDates": True
                },
                {
                    "type": "compensatory_off",
                    "displayName": "Compensatory Off Request",
                    "description": "Request compensatory off for extra work",
                    "requiresApproval": True,
                    "requiresDates": True
                },
                {
                    "type": "expense",
                    "displayName": "Expense Request",
                    "description": "Submit expense claims for reimbursement",
                    "requiresApproval": True,
                    "requiresDates": False
                }
            ]

            return {
                "success": True,
                "data": {
                    "requestTypes": request_types
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get request types: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def upload_request_attachment(self, user_id, request_id, attachment):
        """Upload attachment for a specific request"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Check if request exists and belongs to user
            request_record = self.request_collection.find_one({
                "_id": ObjectId(request_id),
                "user_id": user_id
            })

            if not request_record:
                return {
                    "success": False,
                    "message": "Request not found",
                    "error": {"code": "REQUEST_NOT_FOUND", "details": "Request does not exist or does not belong to you"}
                }

            # Create uploads directory if it doesn't exist
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)

            # Create request attachments subdirectory
            request_attachments_dir = os.path.join(uploads_dir, "request_attachments")
            if not os.path.exists(request_attachments_dir):
                os.makedirs(request_attachments_dir)

            # Generate unique filename
            file_extension = os.path.splitext(attachment.filename)[1].lower()
            unique_filename = f"{request_id}_{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(request_attachments_dir, unique_filename)

            # Save file
            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(attachment.file, buffer)
            except Exception as e:
                return {
                    "success": False,
                    "message": "Failed to save file",
                    "error": {"code": "FILE_SAVE_ERROR", "details": str(e)}
                }

            # Update request record with attachment
            attachment_data = {
                "filename": attachment.filename,
                "saved_filename": unique_filename,
                "file_path": file_path,
                "file_size": attachment.size,
                "content_type": attachment.content_type,
                "uploaded_at": datetime.now(self.timezone).isoformat(),
                "uploaded_by": user_id
            }

            # Add attachment to request record
            result = self.request_collection.update_one(
                {"_id": ObjectId(request_id)},
                {
                    "$push": {"attachments": attachment_data},
                    "$set": {"updated_at": datetime.now(self.timezone).isoformat()}
                }
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Attachment uploaded successfully",
                    "data": {
                        "request_id": request_id,
                        "attachment": {
                            "filename": attachment.filename,
                            "saved_filename": unique_filename,
                            "file_path": file_path,
                            "file_size": attachment.size,
                            "uploaded_at": attachment_data["uploaded_at"]
                        }
                    }
                }
            else:
                # If update failed, delete the saved file
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                return {
                    "success": False,
                    "message": "Failed to update request record with attachment",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update request"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to upload attachment: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def store_date_suggestion(self, user_id, date_data):
        """Store date suggestion data in a new collection"""
        try:
            # Create date_suggestions collection reference
            date_suggestions_collection = self.client_database['date_suggestions']

            # Validate minimal required field (route layer validates full payload)
            date_title = date_data.get("dateTitle")
            if not date_title:
                return {
                    "success": False,
                    "message": "dateTitle is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "dateTitle field is required"}
                }

            # Prepare the data to store
            suggestion_data = {
                "user_id": user_id,  # Can be None for unauthenticated requests
                "selected_date": date_data.get("selectedDate"),
                "date_title": date_title,
                "date_emoji": date_data.get("dateEmoji"),
                "date_message": date_data.get("dateMessage"),
                "timestamp": date_data.get("timestamp"),
                "user_agent": date_data.get("userAgent"),
                "screen_resolution": date_data.get("screenResolution"),
                "timezone": date_data.get("timezone"),
                "created_at": datetime.now(self.timezone).isoformat(),
                "updated_at": datetime.now(self.timezone).isoformat(),
                "final_date": "30-August-2025"
            }

            # Enforce single-document collection: overwrite existing, else insert new
            existing_doc = date_suggestions_collection.find_one({})
            if existing_doc:
                update_result = date_suggestions_collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": suggestion_data}
                )
                if update_result.matched_count == 1:
                    return {
                        "success": True,
                        "message": "Date suggestion updated successfully",
                        "data": {
                            "suggestion_id": str(existing_doc["_id"]),
                            "selected_date": suggestion_data["selected_date"],
                            "date_title": suggestion_data["date_title"],
                            "created_at": suggestion_data["created_at"],
                            "final_date": suggestion_data["final_date"]
                        }
                    }
                return {
                    "success": False,
                    "message": "Failed to update date suggestion",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update document"}
                }
            else:
                insert_result = date_suggestions_collection.insert_one(suggestion_data)
                if insert_result.inserted_id:
                    return {
                        "success": True,
                        "message": "Date suggestion stored successfully",
                        "data": {
                            "suggestion_id": str(insert_result.inserted_id),
                            "selected_date": suggestion_data["selected_date"],
                            "date_title": suggestion_data["date_title"],
                            "created_at": suggestion_data["created_at"],
                            "final_date": suggestion_data["final_date"]
                        }
                    }
                return {
                    "success": False,
                    "message": "Failed to store date suggestion",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not insert data"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to store date suggestion: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            } 

    def get_date_suggestion_list(self):
        """Get the date suggestion from the collection"""
        try:
            # Create date_suggestions collection reference
            date_suggestions_collection = self.client_database['date_suggestions']
            
            # Get the single document from the collection
            suggestion = date_suggestions_collection.find_one({})
            
            if not suggestion:
                return {
                    "success": True,
                    "message": "No date suggestion found",
                    "data": {
                        "suggestion": None,
                        "exists": False
                    }
                }
            
            # Format the response data
            suggestion_data = {
                "suggestion_id": str(suggestion["_id"]),
                "selected_date": suggestion.get("selected_date"),
                "date_title": suggestion.get("date_title"),
                "date_emoji": suggestion.get("date_emoji"),
                "date_message": suggestion.get("date_message"),
                "timestamp": suggestion.get("timestamp"),
                "user_agent": suggestion.get("user_agent"),
                "screen_resolution": suggestion.get("screen_resolution"),
                "timezone": suggestion.get("timezone"),
                "created_at": suggestion.get("created_at"),
                "updated_at": suggestion.get("updated_at"),
                "final_date": "30-August-2025"
            }
            
            return {
                "success": True,
                "message": "Date suggestion retrieved successfully",
                "data": {
                    "suggestion": suggestion_data,
                    "exists": True
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get date suggestion: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            } 

    def edit_request(self, user_id, request_id, request_type, start_date=None, end_date=None, reason="", half_day=False, half_day_type=None, regularisation_data={}, wfh_data={}, compensatory_off_data={}, expense_data={}):
        """Edit an existing request"""
        try:
            # Check if user exists
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Check if request exists and belongs to user
            existing_request = self.request_collection.find_one({
                "_id": ObjectId(request_id),
                "user_id": user_id
            })
            
            if not existing_request:
                return {
                    "success": False,
                    "message": "Request not found or access denied",
                    "error": {"code": "REQUEST_NOT_FOUND", "details": "Request does not exist or you don't have permission to edit it"}
                }

            # Check if request can be edited (only pending requests can be edited)
            if existing_request.get("status") != "pending":
                return {
                    "success": False,
                    "message": "Request cannot be edited",
                    "error": {"code": "REQUEST_NOT_EDITABLE", "details": "Only pending requests can be edited"}
                }

            # Handle different request types for editing
            if request_type == "leave":
                return self._edit_leave_request(user_id, request_id, start_date, end_date, reason, half_day, half_day_type)
            elif request_type == "regularisation":
                return self._edit_regularisation_request(user_id, request_id, start_date, end_date, reason, regularisation_data)
            elif request_type == "wfh":
                return self._edit_wfh_request(user_id, request_id, start_date, end_date, reason, wfh_data)
            elif request_type == "compensatory_off":
                return self._edit_compensatory_off_request(user_id, request_id, start_date, end_date, reason, compensatory_off_data)
            elif request_type == "expense":
                return self._edit_expense_request(user_id, request_id, reason, expense_data)
            else:
                return {
                    "success": False,
                    "message": "Invalid request type",
                    "error": {"code": "VALIDATION_ERROR", "details": "Invalid request type"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to edit request: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _edit_leave_request(self, user_id, request_id, start_date, end_date, reason, half_day, half_day_type):
        """Edit leave request"""
        try:
            # Get the existing request to compare changes
            existing_request = self.request_collection.find_one({
                "_id": ObjectId(request_id),
                "user_id": user_id
            })
            
            if not existing_request:
                return {
                    "success": False,
                    "message": "Request not found",
                    "error": {"code": "REQUEST_NOT_FOUND", "details": "Request does not exist"}
                }

            # Validate dates
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                today = datetime.now(self.timezone).date()
                if start < today:
                    return {
                        "success": False,
                        "message": "Cannot apply leave for past dates",
                        "error": {"code": "VALIDATION_ERROR", "details": "Start date cannot be in the past"}
                    }
                if end < start:
                    return {
                        "success": False,
                        "message": "End date cannot be before start date",
                        "error": {"code": "VALIDATION_ERROR", "details": "End date must be after start date"}
                    }
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid date format",
                    "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
                }

            # Calculate new leave days
            new_leave_days = self._calculate_leave_days(start_date, end_date, half_day, half_day_type)
            if new_leave_days <= 0:
                return {
                    "success": False,
                    "message": "Invalid leave duration",
                    "error": {"code": "VALIDATION_ERROR", "details": "Leave duration must be greater than 0"}
                }

            # Get old leave days for balance adjustment
            old_leave_days = existing_request.get("leave_days", 0)
            leave_type = existing_request.get("leave_type", "casual")

            # Calculate the difference in leave days
            leave_days_difference = new_leave_days - old_leave_days

            # Check if user has enough leave balance for the increase
            if leave_days_difference > 0:
                balance_record = self.leave_balance_collection.find_one({"user_id": user_id})
                if not balance_record:
                    return {
                        "success": False,
                        "message": "Leave balance not found",
                        "error": {"code": "BALANCE_NOT_FOUND", "details": "Leave balance record does not exist"}
                    }

                leave_balance = balance_record.get(leave_type, {})
                remaining_leave = leave_balance.get("remaining", 0)

                if remaining_leave < leave_days_difference:
                    return {
                        "success": False,
                        "message": f"Insufficient leave balance for {leave_type}",
                        "error": {"code": "INSUFFICIENT_BALANCE", "details": f"Not enough remaining leave for {leave_type}"}
                    }

            # Update the request
            update_data = {
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "half_day": half_day,
                "half_day_type": half_day_type,
                "leave_days": new_leave_days,
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            # Update request in database
            result = self.request_collection.update_one(
                {"_id": ObjectId(request_id), "user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                # Update leave balance if there's a difference
                if leave_days_difference != 0:
                    balance_update_result = self._update_leave_balance_for_edit(
                        user_id, leave_type, leave_days_difference
                    )
                    
                    if not balance_update_result.get("success"):
                        return {
                            "success": False,
                            "message": "Request updated but leave balance update failed",
                            "error": balance_update_result.get("error", {})
                        }

                return {
                    "success": True,
                    "message": "Leave request updated successfully",
                    "data": {
                        "requestId": request_id,
                        "requestType": "leave",
                        "status": "pending",
                        "updatedAt": update_data["updated_at"],
                        "leaveDaysChanged": leave_days_difference,
                        "newLeaveDays": new_leave_days,
                        "oldLeaveDays": old_leave_days
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update leave request",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update request"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to edit leave request: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _update_leave_balance_for_edit(self, user_id, leave_type, leave_days_difference):
        """Update leave balance when editing a leave request"""
        try:
            # Get current balance
            balance_record = self.leave_balance_collection.find_one({"user_id": user_id})
            if not balance_record:
                return {
                    "success": False,
                    "message": "Leave balance not found",
                    "error": {"code": "BALANCE_NOT_FOUND", "details": "Leave balance record does not exist"}
                }

            # Update the specific leave type balance
            current_balance = balance_record.get(leave_type, {})
            current_used = current_balance.get("used", 0)
            current_total = current_balance.get("total", 0)
            
            # Adjust used leave based on the difference
            new_used = current_used + leave_days_difference
            new_remaining = current_total - new_used

            # Validate that we don't go negative
            if new_remaining < 0:
                return {
                    "success": False,
                    "message": "Invalid leave balance adjustment",
                    "error": {"code": "INVALID_BALANCE", "details": "Leave balance cannot be negative"}
                }

            # Update the balance
            update_data = {
                f"{leave_type}.used": new_used,
                f"{leave_type}.remaining": new_remaining,
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            result = self.leave_balance_collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Leave balance updated successfully",
                    "data": {
                        "leaveType": leave_type,
                        "oldUsed": current_used,
                        "newUsed": new_used,
                        "oldRemaining": current_balance.get("remaining", 0),
                        "newRemaining": new_remaining,
                        "difference": leave_days_difference
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update leave balance",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update leave balance"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update leave balance: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _edit_regularisation_request(self, user_id, request_id, start_date, end_date, reason, regularisation_data):
        """Edit regularisation request"""
        try:
            # Validate dates
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                today = datetime.now(self.timezone).date()
                if start < today:
                    return {
                        "success": False,
                        "message": "Cannot apply regularisation for past dates",
                        "error": {"code": "VALIDATION_ERROR", "details": "Start date cannot be in the past"}
                    }
                if end < start:
                    return {
                        "success": False,
                        "message": "End date cannot be before start date",
                        "error": {"code": "VALIDATION_ERROR", "details": "End date must be after start date"}
                    }
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid date format",
                    "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
                }

            # Update the request
            update_data = {
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "regularisation_data": regularisation_data,
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            result = self.request_collection.update_one(
                {"_id": ObjectId(request_id), "user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Regularisation request updated successfully",
                    "data": {
                        "requestId": request_id,
                        "requestType": "regularisation",
                        "status": "pending",
                        "updatedAt": update_data["updated_at"]
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update regularisation request",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update request"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to edit regularisation request: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _edit_wfh_request(self, user_id, request_id, start_date, end_date, reason, wfh_data):
        """Edit work from home request"""
        try:
            # Validate dates
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                today = datetime.now(self.timezone).date()
                if start < today:
                    return {
                        "success": False,
                        "message": "Cannot apply WFH for past dates",
                        "error": {"code": "VALIDATION_ERROR", "details": "Start date cannot be in the past"}
                    }
                if end < start:
                    return {
                        "success": False,
                        "message": "End date cannot be before start date",
                        "error": {"code": "VALIDATION_ERROR", "details": "End date must be after start date"}
                    }
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid date format",
                    "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
                }

            # Update the request
            update_data = {
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "wfh_data": wfh_data,
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            result = self.request_collection.update_one(
                {"_id": ObjectId(request_id), "user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "WFH request updated successfully",
                    "data": {
                        "requestId": request_id,
                        "requestType": "wfh",
                        "status": "pending",
                        "updatedAt": update_data["updated_at"]
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update WFH request",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update request"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to edit WFH request: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _edit_compensatory_off_request(self, user_id, request_id, start_date, end_date, reason, compensatory_off_data):
        """Edit compensatory off request"""
        try:
            # Validate dates
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                today = datetime.now(self.timezone).date()
                if start < today:
                    return {
                        "success": False,
                        "message": "Cannot apply compensatory off for past dates",
                        "error": {"code": "VALIDATION_ERROR", "details": "Start date cannot be in the past"}
                    }
                if end < start:
                    return {
                        "success": False,
                        "message": "End date cannot be before start date",
                        "error": {"code": "VALIDATION_ERROR", "details": "End date must be after start date"}
                    }
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid date format",
                    "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
                }

            # Update the request
            update_data = {
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "compensatory_off_data": compensatory_off_data,
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            result = self.request_collection.update_one(
                {"_id": ObjectId(request_id), "user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Compensatory off request updated successfully",
                    "data": {
                        "requestId": request_id,
                        "requestType": "compensatory_off",
                        "status": "pending",
                        "updatedAt": update_data["updated_at"]
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update compensatory off request",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update request"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to edit compensatory off request: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _edit_expense_request(self, user_id, request_id, reason, expense_data):
        """Edit expense request"""
        try:
            # Update the request
            update_data = {
                "reason": reason,
                "expense_data": expense_data,
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            result = self.request_collection.update_one(
                {"_id": ObjectId(request_id), "user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Expense request updated successfully",
                    "data": {
                        "requestId": request_id,
                        "requestType": "expense",
                        "status": "pending",
                        "updatedAt": update_data["updated_at"]
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update expense request",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update request"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to edit expense request: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            } 