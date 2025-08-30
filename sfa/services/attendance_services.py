import os
import requests
from datetime import datetime, timedelta, date
from sfa.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import pytz
import math

load_dotenv()

class AttendanceService:
    def __init__(self):
        self.client_database = client1['hrms_master']
        self.attendance_collection = self.client_database['attendance']
        self.employee_collection = self.client_database['employee_master']
        self.timezone = pytz.timezone('Asia/Kolkata')  # Default to IST

    def _format_time(self, time_str):
        """Format time string to 12-hour format safely for any format"""
        try:
            # Step 1: Remove timezone if present (+05:30 or -05:30)
            if "+" in time_str:
                time_str = time_str.split("+")[0]
            elif "-" in time_str[1:]:  # Ignore first '-' for times like 01:23:45
                time_str = time_str.split("-", 1)[0]

            # Step 2: Remove microseconds if present
            if "." in time_str:
                time_str = time_str.split(".")[0]

            # Step 3: Parse time
            time_obj = datetime.strptime(time_str, "%H:%M:%S")

            # Step 4: Convert to 12-hour format
            return time_obj.strftime("%I:%M %p")  # e.g., 01:17 AM

        except Exception as e:
            return time_str

    def _get_month_number(self, month_str):
        """Extract month number from string like 'July' or 'July 2025'"""
        try:
            if month_str:
                # Convert month name to number
                month_map = {
                    "January": 1, "February": 2, "March": 3, "April": 4,
                    "May": 5, "June": 6, "July": 7, "August": 8,
                    "September": 9, "October": 10, "November": 11, "December": 12
                }
                
                # Handle both "July" and "July 2025" formats
                for month_name, month_num in month_map.items():
                    if month_str.startswith(month_name):
                        return month_num
            return None
        except:
            return None    

    def get_attendance_list_admin(self, page=1, limit=20, month=None, year=None, date_filter=None, status="all", employee_id=None, department=None, search=None):
        """Get attendance list for admin with filtering options for all employees"""
        try:
            # Determine month and year to use
            if date_filter:
                # Use specific date filter
                try:
                    target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
                    start_date = target_date
                    end_date = target_date
                    target_month = target_date.month
                    target_year = target_date.year
                except ValueError:
                    return {
                        "success": False,
                        "message": "Invalid date format",
                        "error": {"code": "VALIDATION_ERROR", "details": "Invalid date format"}
                    }
            elif month and year:
                # Use provided month and year
                month_num = self._get_month_number(month)
                if month_num is None:
                    return {
                        "success": False,
                        "message": "Invalid month format",
                        "error": {"code": "VALIDATION_ERROR", "details": "Invalid month name"}
                    }
                
                target_month = month_num
                target_year = int(year)
                
                # For past months, get all dates in the month
                # For current month, get dates up to today
                # For future months, return empty
                current_date = datetime.now(self.timezone)
                if target_year > current_date.year or (target_year == current_date.year and target_month > current_date.month):
                    return {
                        "success": True,
                        "data": {
                            "month": f"{month} {year}",
                            "attendance": [],
                            "summary": {"total": 0, "present": 0, "absent": 0, "incomplete": 0, "late": 0, "leave": 0, "wfh": 0, "weekend": 0},
                            "pagination": {"page": page, "limit": limit, "total": 0, "totalPages": 0, "hasNext": False, "hasPrev": False},
                            "totalDays": 0
                        }
                    }
                
                start_date = date(target_year, target_month, 1)
                if target_year == current_date.year and target_month == current_date.month:
                    end_date = current_date.date()
                else:
                    # Get last day of the month
                    if target_month == 12:
                        end_date = date(target_year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = date(target_year, target_month + 1, 1) - timedelta(days=1)
            else:
                # Use current month and year
                current_date = datetime.now(self.timezone)
                target_month = current_date.month
                target_year = current_date.year
                start_date = date(target_year, target_month, 1)
                end_date = current_date.date()
            
            # Generate all dates for the month up to today
            dates_list = []
            current_day = start_date
            while current_day <= end_date:
                dates_list.append(current_day)
                current_day += timedelta(days=1)
            
            # Build attendance query
            attendance_query = {
                "date": {
                    "$gte": start_date.strftime("%Y-%m-%d"),
                    "$lte": end_date.strftime("%Y-%m-%d")
                }
            }
            
            # Add employee filter if provided
            if employee_id:
                attendance_query["user_id"] = employee_id
            
            # Get all attendance records for the period
            attendance_records = list(self.attendance_collection.find(attendance_query))
            
            # Get employee details for the attendance records
            employee_ids = list(set([record["user_id"] for record in attendance_records]))
            employees = {}
            if employee_ids:
                employee_cursor = self.employee_collection.find({"_id": {"$in": [ObjectId(emp_id) for emp_id in employee_ids]}})
                for emp in employee_cursor:
                    employees[str(emp["_id"])] = emp
            
            # Create a dictionary for quick lookup
            attendance_dict = {}
            for record in attendance_records:
                date_key = f"{record['user_id']}_{record['date']}"
                attendance_dict[date_key] = record
            
            # Process each date and employee
            attendance_list = []
            present_count = 0
            absent_count = 0
            late_count = 0
            leave_count = 0
            wfh_count = 0
            incomplete_count = 0
            weekend_count = 0
            
            # Get all employees if no specific employee filter
            if not employee_id:
                employee_query = {}
                if department:
                    employee_query["department"] = department
                if search:
                    employee_query["$or"] = [
                        {"full_name": {"$regex": search, "$options": "i"}},
                        {"email": {"$regex": search, "$options": "i"}},
                        {"employee_id": {"$regex": search, "$options": "i"}}
                    ]
                
                all_employees = list(self.employee_collection.find(employee_query))
            else:
                all_employees = [employees.get(employee_id, {})] if employee_id in employees else []
            
            for employee in all_employees:
                employee_id_str = str(employee.get("_id", ""))
                
                for date_obj in dates_list:
                    date_str = date_obj.strftime("%Y-%m-%d")
                    date_key = f"{employee_id_str}_{date_str}"
                    
                    if date_key in attendance_dict:
                        # Attendance record exists
                        record = attendance_dict[date_key]
                        
                        # Check if attendance is complete (both punch in and punch out)
                        if record.get("punch_in_time") and record.get("punch_out_time"):
                            # Format times
                            time_in = self._format_time(record["punch_in_time"].split('T')[1])
                            time_out = self._format_time(record["punch_out_time"].split('T')[1])
                            
                            # Check status based on record data
                            status_value = "present"
                            
                            # Check if late (punch in after 9 AM)
                            is_late = False
                            try:
                                punch_in_time = datetime.fromisoformat(record["punch_in_time"])
                                is_late = punch_in_time.hour >= 9
                                if is_late:
                                    status_value = "late"
                                    late_count += 1
                                else:
                                    present_count += 1
                            except:
                                present_count += 1
                                
                            # Check for leave or WFH from notes or additional fields
                            notes = record.get("punch_in_notes", "") or record.get("punch_out_notes", "")
                            if "leave" in notes.lower() or "leave" in record.get("status", "").lower():
                                status_value = "leave"
                                leave_count += 1
                                present_count -= 1  # Adjust counts
                            elif "wfh" in notes.lower() or "work from home" in notes.lower() or "wfh" in record.get("status", "").lower():
                                status_value = "wfh"
                                wfh_count += 1
                                present_count -= 1  # Adjust counts
                                
                        else:
                            # Only punch in, not complete
                            status_value = "incomplete"
                            incomplete_count += 1
                            time_in = self._format_time(record["punch_in_time"].split('T')[1]) if record.get("punch_in_time") else None
                            time_out = None
                    else:
                        # No attendance record - check if it's a weekend or holiday
                        day_name = date_obj.strftime("%A")
                        
                        # Check if it's Saturday or Sunday (weekend)
                        if day_name in ["Saturday", "Sunday"]:
                            status_value = "weekend"
                            weekend_count += 1
                        else:
                            status_value = "absent"
                            absent_count += 1
                        time_in = None
                        time_out = None
                    
                    # Apply status filter
                    if status != "all" and status_value != status:
                        continue
                    
                    # Format date
                    formatted_date = date_obj.strftime("%d %b %Y")
                    day_name = date_obj.strftime("%A")
                    
                    # Calculate total hours if both punch in and punch out exist
                    total_hours = None
                    if date_key in attendance_dict:
                        record = attendance_dict[date_key]
                        if record.get("punch_in_time") and record.get("punch_out_time"):
                            try:
                                punch_in = datetime.fromisoformat(record["punch_in_time"])
                                punch_out = datetime.fromisoformat(record["punch_out_time"])
                                time_diff = punch_out - punch_in
                                total_hours = round(time_diff.total_seconds() / 3600, 2)  # Convert to hours with 2 decimal places
                            except:
                                total_hours = None

                    attendance_data = {
                        "employee_id": employee_id_str,
                        "employee_name": employee.get("full_name", ""),
                        "employee_email": employee.get("email", ""),
                        "department": employee.get("department", ""),
                        "position": employee.get("designation", ""),  # Position/Designation
                        "date": formatted_date,
                        "day": day_name,
                        "date_iso": date_str,
                        "status": status_value,
                        "timeIn": time_in,
                        "timeOut": time_out,
                        "totalHours": total_hours,  # Total working hours
                        "punchInAddress": attendance_dict.get(date_key, {}).get("punch_in_address", ""),
                        "punchOutAddress": attendance_dict.get(date_key, {}).get("punch_out_address", ""),
                        "notes": attendance_dict.get(date_key, {}).get("punch_in_notes", "") or attendance_dict.get(date_key, {}).get("punch_out_notes", "")
                    }
                    
                    attendance_list.append(attendance_data)
            
            # Apply pagination
            total_records = len(attendance_list)
            total_pages = (total_records + limit - 1) // limit
            start_index = (page - 1) * limit
            end_index = start_index + limit
            
            paginated_attendance = attendance_list[start_index:end_index]
            
            # Calculate summary for filtered data
            filtered_present = sum(1 for item in attendance_list if item["status"] == "present")
            filtered_absent = sum(1 for item in attendance_list if item["status"] == "absent")
            filtered_incomplete = sum(1 for item in attendance_list if item["status"] == "incomplete")
            filtered_late = sum(1 for item in attendance_list if item["status"] == "late")
            filtered_leave = sum(1 for item in attendance_list if item["status"] == "leave")
            filtered_wfh = sum(1 for item in attendance_list if item["status"] == "wfh")
            filtered_weekend = sum(1 for item in attendance_list if item["status"] == "weekend")
            
            summary = {
                "total": total_records,
                "present": filtered_present,
                "absent": filtered_absent,
                "incomplete": filtered_incomplete,
                "late": filtered_late,
                "leave": filtered_leave,
                "wfh": filtered_wfh,
                "weekend": filtered_weekend
            }
            
            # Pagination info
            pagination = {
                "page": page,
                "limit": limit,
                "total": total_records,
                "totalPages": total_pages,
                "hasNext": page < total_pages,
                "hasPrev": page > 1
            }
            
            # Format month name for response
            month_names = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            month_name = month_names[target_month - 1]
            
            return {
                "success": True,
                "data": {
                    "month": f"{month_name} {target_year}",
                    "attendance": paginated_attendance,
                    "summary": summary,
                    "pagination": pagination,
                    "totalDays": len(dates_list)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get attendance list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_employee_attendance_summary(self, employee_id, month=None, year=None):
        """Get attendance summary for a specific employee"""
        try:
            # Check if employee exists
            employee = self.employee_collection.find_one({"_id": ObjectId(employee_id)})
            if not employee:
                return {
                    "success": False,
                    "message": "Employee not found",
                    "error": {"code": "EMPLOYEE_NOT_FOUND", "details": "Employee does not exist"}
                }

            # Determine month and year to use
            if month and year:
                month_num = self._get_month_number(month)
                if month_num is None:
                    return {
                        "success": False,
                        "message": "Invalid month format",
                        "error": {"code": "VALIDATION_ERROR", "details": "Invalid month name"}
                    }
                
                target_month = month_num
                target_year = int(year)
            else:
                # Use current month and year
                current_date = datetime.now(self.timezone)
                target_month = current_date.month
                target_year = current_date.year

            # Calculate date range
            start_date = date(target_year, target_month, 1)
            if target_month == 12:
                end_date = date(target_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(target_year, target_month + 1, 1) - timedelta(days=1)

            # Get attendance records for the employee
            attendance_query = {
                "user_id": employee_id,
                "date": {
                    "$gte": start_date.strftime("%Y-%m-%d"),
                    "$lte": end_date.strftime("%Y-%m-%d")
                }
            }
            
            attendance_records = list(self.attendance_collection.find(attendance_query))
            
            # Calculate summary
            total_days = 0
            present_days = 0
            absent_days = 0
            late_days = 0
            leave_days = 0
            wfh_days = 0
            incomplete_days = 0
            weekend_days = 0
            
            # Generate all dates for the month
            current_day = start_date
            while current_day <= end_date:
                total_days += 1
                date_str = current_day.strftime("%Y-%m-%d")
                day_name = current_day.strftime("%A")
                
                # Check if it's weekend
                if day_name in ["Saturday", "Sunday"]:
                    weekend_days += 1
                else:
                    # Check for attendance record
                    attendance_record = next((record for record in attendance_records if record["date"] == date_str), None)
                    
                    if attendance_record:
                        if attendance_record.get("punch_in_time") and attendance_record.get("punch_out_time"):
                            # Check if late
                            try:
                                punch_in_time = datetime.fromisoformat(attendance_record["punch_in_time"])
                                if punch_in_time.hour >= 9:
                                    late_days += 1
                                else:
                                    present_days += 1
                            except:
                                present_days += 1
                                
                            # Check for leave or WFH
                            notes = attendance_record.get("punch_in_notes", "") or attendance_record.get("punch_out_notes", "")
                            if "leave" in notes.lower() or "leave" in attendance_record.get("status", "").lower():
                                leave_days += 1
                                present_days -= 1
                            elif "wfh" in notes.lower() or "work from home" in notes.lower() or "wfh" in attendance_record.get("status", "").lower():
                                wfh_days += 1
                                present_days -= 1
                        else:
                            incomplete_days += 1
                    else:
                        absent_days += 1
                
                current_day += timedelta(days=1)
            
            # Format month name for response
            month_names = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            
            # Calculate total working hours for the month
            total_working_hours = 0
            for record in attendance_records:
                if record.get("punch_in_time") and record.get("punch_out_time"):
                    try:
                        punch_in = datetime.fromisoformat(record["punch_in_time"])
                        punch_out = datetime.fromisoformat(record["punch_out_time"])
                        time_diff = punch_out - punch_in
                        total_working_hours += time_diff.total_seconds() / 3600  # Convert to hours
                    except:
                        continue

            summary = {
                "employee_id": employee_id,
                "employee_name": employee.get("full_name", ""),
                "employee_email": employee.get("email", ""),
                "department": employee.get("department", ""),
                "position": employee.get("designation", ""),  # Position/Designation
                "month": f"{month_names[target_month - 1]} {target_year}",
                "total_days": total_days,
                "present_days": present_days,
                "absent_days": absent_days,
                "late_days": late_days,
                "leave_days": leave_days,
                "wfh_days": wfh_days,
                "incomplete_days": incomplete_days,
                "weekend_days": weekend_days,
                "total_working_hours": round(total_working_hours, 2),  # Total working hours for the month
                "attendance_percentage": round((present_days / (total_days - weekend_days)) * 100, 2) if (total_days - weekend_days) > 0 else 0
            }
            
            return {
                "success": True,
                "data": summary
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get employee attendance summary: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_department_attendance_summary(self, department=None, month=None, year=None):
        """Get attendance summary for a department or all departments"""
        try:
            # Determine month and year to use
            if month and year:
                month_num = self._get_month_number(month)
                if month_num is None:
                    return {
                        "success": False,
                        "message": "Invalid month format",
                        "error": {"code": "VALIDATION_ERROR", "details": "Invalid month name"}
                    }
                
                target_month = month_num
                target_year = int(year)
            else:
                # Use current month and year
                current_date = datetime.now(self.timezone)
                target_month = current_date.month
                target_year = current_date.year

            # Calculate date range
            start_date = date(target_year, target_month, 1)
            if target_month == 12:
                end_date = date(target_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(target_year, target_month + 1, 1) - timedelta(days=1)

            # Build employee query
            employee_query = {}
            if department:
                employee_query["department"] = department

            # Get employees
            employees = list(self.employee_collection.find(employee_query))
            
            # Format month name for response
            month_names = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            
            if not employees:
                return {
                    "success": True,
                    "data": {
                        "department": department or "All Departments",
                        "month": f"{month_names[target_month - 1]} {target_year}",
                        "total_employees": 0,
                        "total_days": 0,
                        "present_days": 0,
                        "absent_days": 0,
                        "late_days": 0,
                        "leave_days": 0,
                        "wfh_days": 0,
                        "incomplete_days": 0,
                        "weekend_days": 0,
                        "attendance_percentage": 0
                    }
                }

            # Get attendance records for all employees
            employee_ids = [str(emp["_id"]) for emp in employees]
            attendance_query = {
                "user_id": {"$in": employee_ids},
                "date": {
                    "$gte": start_date.strftime("%Y-%m-%d"),
                    "$lte": end_date.strftime("%Y-%m-%d")
                }
            }
            
            attendance_records = list(self.attendance_collection.find(attendance_query))
            
            # Calculate summary
            total_employees = len(employees)
            total_days = 0
            present_days = 0
            absent_days = 0
            late_days = 0
            leave_days = 0
            wfh_days = 0
            incomplete_days = 0
            weekend_days = 0
            
            # Generate all dates for the month
            current_day = start_date
            while current_day <= end_date:
                date_str = current_day.strftime("%Y-%m-%d")
                day_name = current_day.strftime("%A")
                
                # Check if it's weekend
                if day_name in ["Saturday", "Sunday"]:
                    weekend_days += total_employees
                else:
                    # Check for attendance records for all employees
                    day_attendance = [record for record in attendance_records if record["date"] == date_str]
                    
                    for employee in employees:
                        employee_id = str(employee["_id"])
                        attendance_record = next((record for record in day_attendance if record["user_id"] == employee_id), None)
                        
                        if attendance_record:
                            if attendance_record.get("punch_in_time") and attendance_record.get("punch_out_time"):
                                # Check if late
                                try:
                                    punch_in_time = datetime.fromisoformat(attendance_record["punch_in_time"])
                                    if punch_in_time.hour >= 9:
                                        late_days += 1
                                    else:
                                        present_days += 1
                                except:
                                    present_days += 1
                                    
                                # Check for leave or WFH
                                notes = attendance_record.get("punch_in_notes", "") or attendance_record.get("punch_out_notes", "")
                                if "leave" in notes.lower() or "leave" in attendance_record.get("status", "").lower():
                                    leave_days += 1
                                    present_days -= 1
                                elif "wfh" in notes.lower() or "work from home" in notes.lower() or "wfh" in attendance_record.get("status", "").lower():
                                    wfh_days += 1
                                    present_days -= 1
                            else:
                                incomplete_days += 1
                        else:
                            absent_days += 1
                
                current_day += timedelta(days=1)
            
            total_days = (end_date - start_date + timedelta(days=1)).days * total_employees
            
            # Calculate total working hours for the department
            total_working_hours = 0
            for record in attendance_records:
                if record.get("punch_in_time") and record.get("punch_out_time"):
                    try:
                        punch_in = datetime.fromisoformat(record["punch_in_time"])
                        punch_out = datetime.fromisoformat(record["punch_out_time"])
                        time_diff = punch_out - punch_in
                        total_working_hours += time_diff.total_seconds() / 3600  # Convert to hours
                    except:
                        continue

            summary = {
                "department": department or "All Departments",
                "month": f"{month_names[target_month - 1]} {target_year}",
                "total_employees": total_employees,
                "total_days": total_days,
                "present_days": present_days,
                "absent_days": absent_days,
                "late_days": late_days,
                "leave_days": leave_days,
                "wfh_days": wfh_days,
                "incomplete_days": incomplete_days,
                "weekend_days": weekend_days,
                "total_working_hours": round(total_working_hours, 2),  # Total working hours for the department
                "attendance_percentage": round((present_days / (total_days - weekend_days)) * 100, 2) if (total_days - weekend_days) > 0 else 0
            }
            
            return {
                "success": True,
                "data": summary
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get department attendance summary: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
