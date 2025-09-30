import os
import requests
from datetime import datetime, timedelta, date
from sfa.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import pytz
import math

load_dotenv()

class AppDashboardService:
    def __init__(self):
        self.client_database = client1['talbros']
        self.attendance_collection = self.client_database['attendance']
        self.employee_collection = self.client_database['employee_master']
        self.address_cache_collection = self.client_database['address_cache']  # New collection for caching

        self.field_squad_client_database = client1['field_squad']
        self.users_collection = self.field_squad_client_database['users']

        self.timezone = pytz.timezone('Asia/Kolkata')  # Default to IST
        
        # Office location (configurable)
        self.office_location = {
            # "latitude": 28.348456,  # Default to Ballabgarh coordinates
            # "longitude": 77.3304092,
            "latitude": 37.421998333333335,
            "longitude": -122.084,   
            "radius": 500  # meters
        }

    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two points using Haversine formula"""
        R = 6371e3  # Earth's radius in meters
        φ1 = math.radians(lat1)
        φ2 = math.radians(lat2)
        Δφ = math.radians(lat2 - lat1)
        Δλ = math.radians(lng2 - lng1)

        a = math.sin(Δφ/2) * math.sin(Δφ/2) + \
            math.cos(φ1) * math.cos(φ2) * \
            math.sin(Δλ/2) * math.sin(Δλ/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def _validate_location(self, latitude, longitude):
        """Validate if location is within office radius"""
        distance = self._calculate_distance(
            latitude, longitude,
            self.office_location["latitude"],
            self.office_location["longitude"]
        )
        return distance <= self.office_location["radius"], distance

    def _validate_working_hours(self, punch_time):
        """Validate if punch time is within working hours"""
        # Working hours: 6 AM to 10 PM (flexible)
        hour = punch_time.hour
        return 6 <= hour <= 22

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

    def _format_duration(self, hours):
        """Format duration in hours to readable format"""
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes}m"
        else:
            whole_hours = int(hours)
            minutes = int((hours - whole_hours) * 60)
            if minutes == 0:
                return f"{whole_hours}h"
            else:
                return f"{whole_hours}h {minutes}m"

    def _get_address_from_coordinates(self, latitude, longitude):
        """Get address from coordinates using OpenStreetMap (Nominatim) with caching"""
        try:
            # First, check if address is already cached
            cached_address = self._get_cached_address(latitude, longitude)
            if cached_address:
                return cached_address
            
            # If not cached, resolve address from OpenStreetMap API
            resolved_address = self._resolve_address_from_nominatim(latitude, longitude)

            # Cache the resolved address for future use
            if resolved_address:
                self._cache_address(latitude, longitude, resolved_address)
            
            return resolved_address
            
        except Exception as e:
            # If all geocoding fails, return a more descriptive coordinate format
            return self._format_coordinates_as_address(latitude, longitude)
    
    def _resolve_address_from_nominatim(self, latitude, longitude):
        """Resolve address from OpenStreetMap (Nominatim) API"""
        
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                "addressdetails": 1,
                "zoom": 18,
                "accept-language": "en"
            }

            # ✅ Required User-Agent to avoid 403
            headers = {
                "User-Agent": "HRMS-App/1.0 (contact@example.com)"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get("display_name"):
                    return data["display_name"]

                # ✅ Build structured address
                if data.get("address"):
                    address_parts = []
                    address_data = data["address"]

                    # Building address in order of specificity
                    if address_data.get("house_number"):
                        address_parts.append(address_data["house_number"])

                    if address_data.get("road"):
                        address_parts.append(address_data["road"])

                    if address_data.get("suburb"):
                        address_parts.append(address_data["suburb"])

                    if address_data.get("city") or address_data.get("town"):
                        city = address_data.get("city") or address_data.get("town")
                        address_parts.append(city)

                    if address_data.get("state"):
                        address_parts.append(address_data["state"])

                    if address_data.get("postcode"):
                        address_parts.append(address_data["postcode"])

                    if address_data.get("country"):
                        address_parts.append(address_data["country"])

                    if address_parts:
                        return ", ".join(address_parts)

            # ✅ If Nominatim fails, fallback to coordinates
            return self._format_coordinates_as_address(latitude, longitude)

        except Exception as e:

            return self._format_coordinates_as_address(latitude, longitude)

    
    def _format_coordinates_as_address(self, latitude, longitude):
        """Format coordinates as a readable address-like string"""
        try:
            # Convert decimal coordinates to degrees, minutes, seconds for better readability
            lat_deg = int(abs(latitude))
            lat_min = int((abs(latitude) - lat_deg) * 60)
            lat_sec = ((abs(latitude) - lat_deg - lat_min/60) * 3600)
            lat_dir = "N" if latitude >= 0 else "S"
            
            lng_deg = int(abs(longitude))
            lng_min = int((abs(longitude) - lng_deg) * 60)
            lng_sec = ((abs(longitude) - lng_deg - lng_min/60) * 3600)
            lng_dir = "E" if longitude >= 0 else "W"
            
            # Format as readable coordinates
            lat_str = f"{lat_deg}°{lat_min}'{lat_sec:.1f}\"{lat_dir}"
            lng_str = f"{lng_deg}°{lng_min}'{lng_sec:.1f}\"{lng_dir}"
            
            return f"Location: {lat_str}, {lng_str}"
            
        except Exception:
            # Final fallback to simple decimal format
            return f"Location: {latitude:.6f}, {longitude:.6f}"
    
    def _get_cached_address(self, latitude, longitude):
        """Get cached address for coordinates if available"""
        try:
            # Round coordinates to 4 decimal places for caching (approximately 11 meters precision)
            lat_rounded = round(latitude, 4)
            lng_rounded = round(longitude, 4)
            
            # Check if address is cached
            cached_address = self.address_cache_collection.find_one({
                "latitude": lat_rounded,
                "longitude": lng_rounded
            })
            
            if cached_address and cached_address.get("address"):
                return cached_address["address"]
            
            return None
        except Exception:
            return None
    
    def _cache_address(self, latitude, longitude, address):
        """Cache address for coordinates"""
        try:
            # Round coordinates to 4 decimal places for caching
            lat_rounded = round(latitude, 4)
            lng_rounded = round(longitude, 4)
            
            # Store in cache with timestamp
            cache_data = {
                "latitude": lat_rounded,
                "longitude": lng_rounded,
                "address": address,
                "cached_at": datetime.now(self.timezone).isoformat(),
                "original_lat": latitude,
                "original_lng": longitude
            }
            
            # Use upsert to avoid duplicates
            self.address_cache_collection.update_one(
                {"latitude": lat_rounded, "longitude": lng_rounded},
                {"$set": cache_data},
                upsert=True
            )
            
            return True
        except Exception:
            return False

    def start_attend(self, user_id, location=None):
        """Start workday attendance (Punch-in)"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Check if user is active
            if user.get('employment_status') != 'Active':
                return {
                    "success": False,
                    "message": "Account is inactive",
                    "error": {"code": "ACCOUNT_INACTIVE", "details": "User account is not active"}
                }

            # Generate current date and time in Asia/Kolkata timezone
            current_datetime = datetime.now(self.timezone)
            punch_date = current_datetime.strftime("%Y-%m-%d")
            punch_time = current_datetime.strftime("%H:%M:%S")
            punch_datetime = current_datetime

            # Generate address from coordinates if location provided
            if location and location.get("latitude") and location.get("longitude"):
                lat = float(location["latitude"])
                lng = float(location["longitude"])
                
                # Generate address from coordinates
                address = self._get_address_from_coordinates(lat, lng)
                location["address"] = address

            # Check if already punched in for the given date
            existing_attendance = self.attendance_collection.find_one({
                "user_id": user_id,
                "date": punch_date,
                "punch_in_time": {"$exists": True},
                "punch_out_time": {"$exists": False}
            })

            if existing_attendance:
                return {
                    "success": False,
                    "message": "Already started attendance today",
                    "error": {"code": "ALREADY_STARTED", "details": "You have already started attendance for this date"}
                }

            # Create attendance record
            attendance_data = {
                "user_id": user_id,
                "employee_id": user_id,
                "date": punch_date,
                "punch_in_time": punch_datetime.isoformat(),
                "punch_in_latitude": location.get("latitude") if location else None,
                "punch_in_longitude": location.get("longitude") if location else None,
                "punch_in_accuracy": location.get("accuracy") if location else None,
                "punch_in_address": location.get("address") if location else None,
                "punch_in_notes": "",
                "punch_in_timestamp": punch_datetime.timestamp(),
                "status": "in",
                "created_at": datetime.now(self.timezone).isoformat(),
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            result = self.attendance_collection.insert_one(attendance_data)

            if result.inserted_id:
                return {
                    "success": True,
                    "message": "Attendance started successfully",
                    "data": {
                        "attendanceId": str(result.inserted_id),
                        "status": "in",
                        "punchTime": self._format_time(punch_time),
                        "punchDateTime": punch_datetime.isoformat(),
                        "location": location or {},
                        "nextAction": "punch_out"
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to start attendance",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not save attendance record"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Attendance start failed: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def stop_attend(self, user_id, attendance_id, location=None):
        """Stop workday attendance (Punch-out)"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User does not exist",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Check if user is active
            if user.get('employment_status') != 'Active':
                return {
                    "success": False,
                    "message": "User account is not active",
                    "error": {"code": "ACCOUNT_INACTIVE", "details": "User account is not active"}
                }

            # Validate attendance_id
            try:
                attendance_object_id = ObjectId(attendance_id)
            except Exception:
                return {
                    "success": False,
                    "message": "Invalid attendance ID format",
                    "error": {"code": "INVALID_ATTENDANCE_ID", "details": "Attendance ID must be a valid ObjectId"}
                }

            # Find existing attendance record
            existing_attendance = self.attendance_collection.find_one({
                "_id": attendance_object_id,
                "user_id": user_id,
                "punch_in_time": {"$exists": True},
                "punch_out_time": {"$exists": False}
            })

            if not existing_attendance:
                # Check if user has already punched out today
                completed_attendance = self.attendance_collection.find_one({
                    "user_id": user_id,
                    "date": datetime.now(self.timezone).strftime("%Y-%m-%d"),
                    "punch_in_time": {"$exists": True},
                    "punch_out_time": {"$exists": True}
                })
                
                if completed_attendance:
                    return {
                        "success": False,
                        "message": "Already stopped attendance today",
                        "error": {"code": "ALREADY_STOPPED", "details": "You have already stopped attendance for today"}
                    }
                else:
                    return {
                        "success": False,
                        "message": "No active attendance found",
                        "error": {"code": "NO_ACTIVE_ATTENDANCE", "details": "Please start attendance before stopping it"}
                    }

            # Generate current date and time in Asia/Kolkata timezone
            current_datetime = datetime.now(self.timezone)
            punch_out_time = current_datetime.strftime("%H:%M:%S")
            punch_out_datetime = current_datetime

            # Generate address from coordinates if location provided
            if location and location.get("latitude") and location.get("longitude"):
                lat = float(location["latitude"])
                lng = float(location["longitude"])
                
                # Generate address from coordinates
                address = self._get_address_from_coordinates(lat, lng)
                location["address"] = address

            # Calculate working hours
            punch_in_time = datetime.fromisoformat(existing_attendance['punch_in_time'])
            working_hours = (punch_out_datetime - punch_in_time).total_seconds() / 3600

            # Update attendance record with punch out
            update_data = {
                "punch_out_time": punch_out_datetime.isoformat(),
                "punch_out_latitude": location.get("latitude") if location else None,
                "punch_out_longitude": location.get("longitude") if location else None,
                "punch_out_accuracy": location.get("accuracy") if location else None,
                "punch_out_address": location.get("address") if location else None,
                "punch_out_timestamp": punch_out_datetime.timestamp(),
                "working_hours": round(working_hours, 2),
                "status": "completed",
                "updated_at": datetime.now(self.timezone).isoformat()
            }

            result = self.attendance_collection.update_one(
                {"_id": attendance_object_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                # Format working hours as HH:MM
                hours = int(working_hours)
                minutes = int((working_hours - hours) * 60)
                formatted_working_hours = f"{hours:02d}:{minutes:02d}"
                
                return {
                    "success": True,
                    "message": "Attendance stopped successfully",
                    "data": {
                        "attendanceId": str(attendance_object_id),
                        "status": "completed",
                        "punchOutTime": self._format_time(punch_out_time),
                        "punchOutDateTime": punch_out_datetime.isoformat(),
                        "working_hours": formatted_working_hours,
                        "location": location or {},
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Could not update attendance record",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update attendance record"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Attendance stop failed: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def upload_attendance_image(self, user_id, attendance_id, image_file):
        """Upload attendance image for a specific attendance record"""
        return self._upload_attendance_image_common(user_id, attendance_id, image_file, image_type="stop")

    def upload_start_attendance_image(self, user_id, attendance_id, image_file):
        """Upload start attendance image for a specific attendance record (punch-in image)."""
        return self._upload_attendance_image_common(user_id, attendance_id, image_file, image_type="start")

    def _upload_attendance_image_common(self, user_id, attendance_id, image_file, image_type="stop"):
        """Common helper to upload attendance images.
        image_type: "start" for punch-in image, "stop" for punch-out image.
        """
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User does not exist",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Check if user is active
            if user.get('employment_status') != 'Active':
                return {
                    "success": False,
                    "message": "User account is not active",
                    "error": {"code": "ACCOUNT_INACTIVE", "details": "User account is not active"}
                }

            # Validate attendance_id
            try:
                attendance_object_id = ObjectId(attendance_id)
            except Exception:
                return {
                    "success": False,
                    "message": "Invalid attendance ID format",
                    "error": {"code": "INVALID_ATTENDANCE_ID", "details": "Attendance ID must be a valid ObjectId"}
                }

            # Find existing attendance record
            existing_attendance = self.attendance_collection.find_one({
                "_id": attendance_object_id,
                "user_id": user_id
            })

            if not existing_attendance:
                return {
                    "success": False,
                    "message": "Attendance record not found",
                    "error": {"code": "ATTENDANCE_NOT_FOUND", "details": "No attendance record found with this ID"}
                }

            # Create upload directory if it doesn't exist
            import os
            upload_dir = "uploads/sfa_uploads/attendance"
            os.makedirs(upload_dir, exist_ok=True)

            # Generate unique filename
            import uuid
            file_extension = os.path.splitext(image_file.filename)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)

            # Save image file
            try:
                # Reset file pointer to beginning
                image_file.file.seek(0)

                with open(file_path, "wb") as buffer:
                    content = image_file.file.read()
                    buffer.write(content)

            except Exception as e:
                return {
                    "success": False,
                    "message": "Failed to save image file",
                    "error": {"code": "FILE_SAVE_ERROR", "details": f"Could not save image: {str(e)}"}
                }

            # Build update fields depending on type
            now_iso = datetime.now(self.timezone).isoformat()
            # Normalize path for API response (use forward slashes)
            normalized_path = file_path.replace("\\", "/")
            if image_type == "start":
                update_data = {
                    "start_attendance_image_path": file_path,
                    "start_attendance_image_filename": unique_filename,
                    "start_attendance_image_original_name": image_file.filename,
                    "start_attendance_image_uploaded_at": now_iso,
                    "updated_at": now_iso
                }
                uploaded_at_key = "start_attendance_image_uploaded_at"
            else:
                update_data = {
                    "stop_attendance_image_path": file_path,
                    "stop_attendance_image_filename": unique_filename,
                    "stop_attendance_image_original_name": image_file.filename,
                    "stop_attendance_image_uploaded_at": now_iso,
                    "updated_at": now_iso
                }
                uploaded_at_key = "stop_attendance_image_uploaded_at"

            result = self.attendance_collection.update_one(
                {"_id": attendance_object_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Attendance image uploaded successfully" if image_type == "stop" else "Start attendance image uploaded successfully",
                    "data": {
                        "attendanceId": str(attendance_object_id),
                        "imagePath": normalized_path,
                        "imageFilename": unique_filename,
                        "originalFilename": image_file.filename,
                        "uploadedAt": update_data[uploaded_at_key]
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Could not update attendance record",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update attendance record"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Image upload failed: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
    def get_dashboard_overview(self, user_id, date=None):
        """Get dashboard overview data for the user"""
        try:
            # Use provided date or current date
            if date:
                try:
                    target_date = datetime.strptime(date, "%Y-%m-%d").date()
                except ValueError:
                    return {
                        "success": False,
                        "message": "Invalid date format",
                        "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
                    }
            else:
                target_date = datetime.now(self.timezone).date()
            
            # Get user info
            user = self.employee_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get attendance for the target date
            attendance = self.attendance_collection.find_one({
                "user_id": user_id,
                "date": target_date.isoformat()
            })

            # Build attendance data
            attendance_data = {
                "status": "out"
            }

            if attendance:
                punch_in_time = attendance.get('punch_in_time')
                punch_out_time = attendance.get('punch_out_time')
                
                if punch_in_time and not punch_out_time:
                    attendance_data = {
                        "status": "in",
                        "punchInTime": self._format_time(punch_in_time.split('T')[1]),
                        "punchInDateTime": punch_in_time,
                        "duration": self._format_duration(self._calculate_working_hours(punch_in_time)),
                        "location": {
                            "punchIn": {
                                "latitude": attendance.get('punch_in_latitude'),
                                "longitude": attendance.get('punch_in_longitude'),
                                "address": attendance.get('punch_in_address', '')
                            }
                        }
                    }
                elif punch_in_time and punch_out_time:
                    duration = self._format_duration(attendance.get('working_hours', 0))
                    attendance_data = {
                        "status": "completed",
                        "punchInTime": self._format_time(punch_in_time.split('T')[1]),
                        "punchOutTime": self._format_time(punch_out_time.split('T')[1]),
                        "punchInDateTime": punch_in_time,
                        "punchOutDateTime": punch_out_time,
                        "duration": duration,
                        "location": {
                            "punchIn": {
                                "latitude": attendance.get('punch_in_latitude'),
                                "longitude": attendance.get('punch_in_longitude'),
                                "address": attendance.get('punch_in_address', '')
                            },
                            "punchOut": {
                                "latitude": attendance.get('punch_out_latitude'),
                                "longitude": attendance.get('punch_out_longitude'),
                                "address": attendance.get('punch_out_address', '')
                            }
                        }
                    }

            # Attendance progress (dynamic calculation)
            target_hours = 9  # Can be made configurable
            tz = pytz.timezone("Asia/Kolkata")
            today = datetime.now(tz).date()

            attendance_record = self.attendance_collection.find_one({
                "user_id": user_id,
                "date": today.isoformat()
            })

            worked_hours = 0
            if attendance_record and "punch_in_time" in attendance_record:
                punch_in_time = datetime.fromisoformat(attendance_record["punch_in_time"]).astimezone(tz)
                if "punch_out_time" in attendance_record:
                    punch_out_time = datetime.fromisoformat(attendance_record["punch_out_time"]).astimezone(tz)
                else:
                    punch_out_time = datetime.now(tz)
                worked_hours = (punch_out_time - punch_in_time).total_seconds() / 3600

            attendance_progress = {
                "percentage": round((worked_hours / target_hours) * 100) if target_hours else 0,
                "workedHours": round(worked_hours, 2),
                "targetHours": target_hours,
                "status": "on track" if worked_hours >= target_hours else "behind"
            }

            return {
                "success": True,
                "data": {
                    "attendance": attendance_data,
                    "attendanceProgress": attendance_progress
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get dashboard overview: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_todays_celebrations(self, user_id, date=None, limit=10):
        """Get today's birthdays and work anniversaries"""
        try:
            # Use provided date or current date
            if date:
                try:
                    target_date = datetime.strptime(date, "%Y-%m-%d").date()
                except ValueError:
                    return {
                        "success": False,
                        "message": "Invalid date format",
                        "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
                    }
            else:
                target_date = datetime.now(self.timezone).date()

            celebrations = []
            total_birthdays = 0
            total_anniversaries = 0

            # Get all active employees
            employees = list(self.employee_collection.find({
                "employment_status": "Active"
            }).limit(limit * 2))  # Get more to filter

            for employee in employees:
                # Check for birthdays
                if employee.get('date_of_birth'):
                    try:
                        dob = datetime.strptime(employee['date_of_birth'], "%Y-%m-%d").date()
                        if dob.month == target_date.month and dob.day == target_date.day:
                            celebrations.append({
                                "id": str(employee["_id"]),
                                "employeeId": str(employee["_id"]),
                                "name": employee.get("full_name", ""),
                                "designation": employee.get("designation", ""),
                                "department": employee.get("department", ""),
                                "type": "birthday",
                                "date": target_date.isoformat(),
                                "years": None,
                                "profileImage": employee.get("profile_image", "/images/profile_img.png"),
                                "color": "#ec4899",
                                "backgroundColor": "#fdf2f8"
                            })
                            total_birthdays += 1
                    except:
                        pass

                # Check for work anniversaries
                if employee.get('joining_date'):
                    try:
                        join_date = datetime.strptime(employee['joining_date'], "%Y-%m-%d").date()
                        if join_date.month == target_date.month and join_date.day == target_date.day:
                            years = target_date.year - join_date.year
                            celebrations.append({
                                "id": str(employee["_id"]),
                                "employeeId": str(employee["_id"]),
                                "name": employee.get("full_name", ""),
                                "designation": employee.get("designation", ""),
                                "department": employee.get("department", ""),
                                "type": "anniversary",
                                "date": target_date.isoformat(),
                                "years": years,
                                "profileImage": employee.get("profile_image", "/images/profile_img.png"),
                                "color": "#3b82f6",
                                "backgroundColor": "#eff6ff"
                            })
                            total_anniversaries += 1
                    except:
                        pass

            # Limit results
            celebrations = celebrations[:limit]

            return {
                "success": True,
                "data": {
                    "celebrations": celebrations,
                    "summary": {
                        "totalBirthdays": total_birthdays,
                        "totalAnniversaries": total_anniversaries,
                        "totalCelebrations": len(celebrations)
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get celebrations data: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_notifications_count(self, user_id):
        """Get unread notifications count for badge"""
        try:
            # For now, return mock data
            # In a real implementation, this would query a notifications collection
            mock_data = {
                "unreadCount": 3,
                "categories": {
                    "announcements": 1,
                    "attendance": 0,
                    "leave": 2,
                    "general": 0
                }
            }

            return {
                "success": True,
                "data": mock_data
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get notifications count: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _calculate_working_hours(self, punch_in_time_str):
        """Calculate working hours from punch in time to now"""
        try:
            punch_in_time = datetime.fromisoformat(punch_in_time_str)
            current_time = datetime.now(self.timezone)
            working_hours = (current_time - punch_in_time).total_seconds() / 3600
            return round(working_hours, 2)
        except:
            return 0 

    def get_today_attendance(self, user_id):
        """Get today's attendance status for the user"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "message": "User does not exist",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Check if user is active
            if user.get('employment_status') != 'Active':
                return {
                    "success": False,
                    "message": "User account is not active",
                    "error": {"code": "ACCOUNT_INACTIVE", "details": "User account is not active"}
                }

            # Get today's date in Asia/Kolkata timezone
            today = datetime.now(self.timezone).strftime("%Y-%m-%d")
            
            # Find today's attendance record
            attendance_record = self.attendance_collection.find_one({
                "user_id": user_id,
                "date": today
            })

            # Initialize response data
            attendance_data = {
                "date": today,
                "status": "not_started",
                "attendance_id": None,
                "punch_in_time": None,
                "punch_out_time": None,
                "working_hours": "00:00",
                "kms": "0",
                "punch_in_location": None,
                "punch_out_location": None
            }

            if attendance_record:
                # Check if user has punched in
                if attendance_record.get("punch_in_time"):
                    punch_in_time = attendance_record.get("punch_in_time")
                    attendance_data["attendance_id"] = str(attendance_record["_id"])
                    attendance_data["punch_in_time"] = self._format_time(punch_in_time.split('T')[1]) if 'T' in punch_in_time else self._format_time(punch_in_time)
                    attendance_data["punch_in_location"] = {
                        "latitude": attendance_record.get("punch_in_latitude"),
                        "longitude": attendance_record.get("punch_in_longitude"),
                        "address": attendance_record.get("punch_in_address", "")
                    }
                    
                    # Check if user has punched out
                    if attendance_record.get("punch_out_time"):
                        punch_out_time = attendance_record.get("punch_out_time")
                        attendance_data["status"] = "completed"
                        attendance_data["punch_out_time"] = self._format_time(punch_out_time.split('T')[1]) if 'T' in punch_out_time else self._format_time(punch_out_time)
                        attendance_data["punch_out_location"] = {
                            "latitude": attendance_record.get("punch_out_latitude"),
                            "longitude": attendance_record.get("punch_out_longitude"),
                            "address": attendance_record.get("punch_out_address", "")
                        }
                        
                        # Calculate working hours
                        if attendance_record.get("working_hours"):
                            hours = float(attendance_record["working_hours"])
                            hours_int = int(hours)
                            minutes = int((hours - hours_int) * 60)
                            attendance_data["working_hours"] = f"{hours_int:02d}:{minutes:02d}"
                        
                        # Calculate distance between punch-in and punch-out locations
                        if (attendance_record.get("punch_in_latitude") and attendance_record.get("punch_in_longitude") and 
                            attendance_record.get("punch_out_latitude") and attendance_record.get("punch_out_longitude")):
                            try:
                                distance = self._calculate_distance(
                                    attendance_record["punch_in_latitude"], attendance_record["punch_in_longitude"],
                                    attendance_record["punch_out_latitude"], attendance_record["punch_out_longitude"]
                                )
                                attendance_data["kms"] = f"{distance/1000:.1f}"  # Convert meters to kilometers
                            except:
                                attendance_data["kms"] = "0"
                        else:
                            attendance_data["kms"] = "0"
                    else:
                        # User has punched in but not punched out
                        attendance_data["status"] = "in_progress"
                        
                        # Calculate current working hours
                        try:
                            punch_in_dt = datetime.fromisoformat(punch_in_time)
                            current_time = datetime.now(self.timezone)
                            working_hours = (current_time - punch_in_dt).total_seconds() / 3600
                            hours_int = int(working_hours)
                            minutes = int((working_hours - hours_int) * 60)
                            attendance_data["working_hours"] = f"{hours_int:02d}:{minutes:02d}"
                        except:
                            attendance_data["working_hours"] = "00:00"

            return {
                "success": True,
                "message": "Today's attendance retrieved successfully",
                "data": attendance_data
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get today's attendance: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            } 