import os
import requests
from datetime import datetime, timedelta, date
from sfa.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import pytz
import math

load_dotenv()

class AppAttendanceService:
    def __init__(self):
        self.client_database = client1['talbros']
        self.field_squad_database = client1['field_squad']
        self.attendance_collection = self.client_database['attendance']
        self.users_collection = self.field_squad_database['users']
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

    def get_attendance_list_current_month(self, user_id, page=1, limit=20, month=None, year=None, date_filter=None, status="all"):
        """Get attendance list for current month with present/absent status for each date"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

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
                            "summary": {"total": 0, "present": 0, "absent": 0, "incomplete": 0, "late": 0, "weekend": 0},
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
            
            # Get all attendance records for the current month
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            attendance_query = {
                "user_id": user_id,
                "date": {
                    "$gte": start_date_str,
                    "$lte": end_date_str
                }
            }
            
            attendance_records = list(self.attendance_collection.find(attendance_query))
            
            # Create a dictionary for quick lookup
            attendance_dict = {}
            for record in attendance_records:
                attendance_dict[record["date"]] = record
            
            # Process each date
            attendance_list = []
            present_count = 0
            absent_count = 0
            late_count = 0
            incomplete_count = 0
            weekend_count = 0
            
            for date_obj in dates_list:
                date_str = date_obj.strftime("%Y-%m-%d")
                
                if date_str in attendance_dict:
                    # Attendance record exists
                    record = attendance_dict[date_str]
                    
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
                
                # No need for search date filter since we're already filtering by month/year
                
                # Format date
                formatted_date = date_obj.strftime("%d %b %Y")
                day_name = date_obj.strftime("%A")
                
                attendance_data = {
                    "date": formatted_date,
                    "day": day_name,
                    "date_iso": date_str,
                    "status": status_value,
                    "timeIn": time_in,
                    "timeOut": time_out,
                    "punchInAddress": attendance_dict.get(date_str, {}).get("punch_in_address", ""),
                    "punchOutAddress": attendance_dict.get(date_str, {}).get("punch_out_address", ""),
                    "notes": attendance_dict.get(date_str, {}).get("punch_in_notes", "") or attendance_dict.get(date_str, {}).get("punch_out_notes", "")
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
            filtered_weekend = sum(1 for item in attendance_list if item["status"] == "weekend")
            
            summary = {
                "total": total_records,
                "present": filtered_present,
                "absent": filtered_absent,
                "incomplete": filtered_incomplete,
                "late": filtered_late,
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

 