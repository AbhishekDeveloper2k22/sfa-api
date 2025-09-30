from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sfa.services.app_dashboard_services import AppDashboardService
from sfa.utils.response import format_response
from typing import Optional
import jwt
from datetime import datetime, timedelta

router = APIRouter()

# JWT Configuration
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('JWT_SECRET')
ALGORITHM = "HS256"

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

async def get_current_user(request: Request):
    """Get current authenticated user"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload

def validate_location(location: dict):
    """Validate location data"""
    if not location.get("latitude") or not location.get("longitude"):
        return False, "latitude and longitude are required in location"
    
    try:
        lat = float(location.get("latitude"))
        lng = float(location.get("longitude"))
        
        if not (-90 <= lat <= 90):
            return False, "latitude must be between -90 and 90"
        
        if not (-180 <= lng <= 180):
            return False, "longitude must be between -180 and 180"
        
        # Validate accuracy if provided
        if "accuracy" in location:
            accuracy = location.get("accuracy")
            if accuracy is not None:
                try:
                    acc = float(accuracy)
                    if acc < 0:
                        return False, "accuracy must be a positive number"
                except (ValueError, TypeError):
                    return False, "accuracy must be a valid number"
        
        # Validate address length if provided
        if "address" in location and location.get("address"):
            address = location.get("address")
            if len(address) > 500:
                return False, "address must be less than 500 characters"
        
        return True, None
    except (ValueError, TypeError):
        return False, "latitude and longitude must be valid numbers"



@router.post("/startAttendance")
async def start_attend(request: Request, current_user: dict = Depends(get_current_user)):
    """Start workday attendance (Punch-in)"""
    print("start_attend api called")
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        # Extract lat and lng from request
        lat = body.get("lat")
        lng = body.get("lng")
        
        # Validate required fields
        if not lat or not lng:
            return format_response(
                success=False,
                msg="Latitude and longitude are required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "lat and lng are required"
                    }
                }
            )
        
        # Validate lat and lng are valid numbers
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            return format_response(
                success=False,
                msg="Invalid coordinates",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "lat and lng must be valid numbers"
                    }
                }
            )
        
        # Create location object for the service
        location = {
            "latitude": lat,
            "longitude": lng
        }
        
        service = AppDashboardService()
        result = service.start_attend(
            user_id=user_id,
            location=location
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Attendance start failed"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Attendance started successfully",
            statuscode=200,
            data={
                "attendance_id": result.get("data", {}).get("attendanceId"),
            }
        )
        
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": "An unexpected error occurred"
                }
            }
        )

@router.post("/stopAttendance")
async def stop_attend(request: Request, current_user: dict = Depends(get_current_user)):
    """Stop workday attendance (Punch-out)"""
    print("stop_attend api called")
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        # Extract data from request
        attendance_id = body.get("attendance_id")
        lat = body.get("lat")
        lng = body.get("lng")
        
        # Validate required fields
        if not attendance_id:
            return format_response(
                success=False,
                msg="Attendance ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "attendance_id is required"
                    }
                }
            )
        
        if not lat or not lng:
            return format_response(
                success=False,
                msg="Latitude and longitude are required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "lat and lng are required"
                    }
                }
            )
        
        # Validate lat and lng are valid numbers
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            return format_response(
                success=False,
                msg="Invalid coordinates",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "lat and lng must be valid numbers"
                    }
                }
            )
        # Create location object for the service
        location = {
            "latitude": lat,
            "longitude": lng
        }
        
        service = AppDashboardService()
        result = service.stop_attend(
            user_id=user_id,
            attendance_id=attendance_id,
            location=location
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Attendance stop failed"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Attendance stopped successfully",
            statuscode=200,
            data={
                "attendance_id": attendance_id,
                "working_hours": result.get("data", {}).get("working_hours", "00:00")
            }
        )
        
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": "An unexpected error occurred"
                }
            }
                 )

@router.post("/upload-attendance-image")
async def upload_attendance_image(request: Request, current_user: dict = Depends(get_current_user)):
    """Upload attendance image for a specific attendance record"""
    print("upload_attendance_image api called")
    try:
        # Get form data
        form = await request.form()
        attendance_id = form.get("attendance_id")
        image_file = form.get("image")
        image_type = (form.get("type") or form.get("image_type") or "stop").strip().lower()
        
        # Validate required fields
        if not attendance_id:
            return format_response(
                success=False,
                msg="Attendance ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "attendance_id is required"
                    }
                }
            )
        
        if not image_file:
            return format_response(
                success=False,
                msg="Image file is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "image file is required"
                    }
                }
            )

        # Validate image type
        if image_type not in ["start", "stop"]:
            return format_response(
                success=False,
                msg="Invalid type",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "type must be 'start' or 'stop'"
                    }
                }
            )
        
        # Validate attendance_id format
        try:
            from bson import ObjectId
            ObjectId(attendance_id)
        except Exception:
            return format_response(
                success=False,
                msg="Invalid attendance ID format",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "attendance_id must be a valid ObjectId"
                    }
                }
            )
        
        # Validate image file
        if not hasattr(image_file, 'filename') or not image_file.filename:
            return format_response(
                success=False,
                msg="Invalid image file",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Please provide a valid image file"
                    }
                }
            )
        
        # Check file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        file_extension = os.path.splitext(image_file.filename.lower())[1]
        if file_extension not in allowed_extensions:
            return format_response(
                success=False,
                msg="Invalid file type",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"Only {', '.join(allowed_extensions)} files are allowed"
                    }
                }
            )
        
        # Check file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if hasattr(image_file, 'size') and image_file.size > max_size:
            return format_response(
                success=False,
                msg="File too large",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "File size must be less than 5MB"
                    }
                }
            )
        
        user_id = current_user.get("user_id")
        service = AppDashboardService()
        if image_type == "start":
            result = service.upload_start_attendance_image(
                user_id=user_id,
                attendance_id=attendance_id,
                image_file=image_file
            )
        else:
            result = service.upload_attendance_image(
                user_id=user_id,
                attendance_id=attendance_id,
                image_file=image_file
            )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Image upload failed"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Start attendance image uploaded successfully" if image_type == "start" else "Attendance image uploaded successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": "An unexpected error occurred"
                }
            }
        )



@router.get("/overview")
async def get_dashboard_overview(
    current_user: dict = Depends(get_current_user),
    date: Optional[str] = Query(None, description="ISO 8601 date (default: today)"),
    limit: int = Query(10, ge=1, le=50, description="Number of celebration records (max: 50)")
):
    """Get comprehensive dashboard overview data including celebrations and notifications count"""
    try:
        user_id = current_user.get("user_id")
        
        service = AppDashboardService()
        
        # Get dashboard overview data
        overview_result = service.get_dashboard_overview(user_id, date)
        
        # Get celebrations data
        celebrations_result = service.get_todays_celebrations(user_id, date, limit)
        
        # Get notifications count
        notifications_result = service.get_notifications_count(user_id)
        
        # Check if any of the main operations failed
        if not overview_result.get("success"):
            return format_response(
                success=False,
                msg=overview_result.get("message", "Failed to get dashboard overview"),
                statuscode=400,
                data={"error": overview_result.get("error", {})}
            )
        
        # Combine all data
        combined_data = overview_result.get("data", {})
        
        # Add celebrations data if successful
        if celebrations_result.get("success"):
            combined_data["celebrations"] = celebrations_result.get("data", {})
        else:
            combined_data["celebrations"] = {
                "birthdays": [],
                "anniversaries": [],
                "total": 0
            }
        
        # Add notifications count if successful
        if notifications_result.get("success"):
            combined_data["notifications"] = notifications_result.get("data", {})
        else:
            combined_data["notifications"] = {
                "unread_count": 0
            }
        
        return format_response(
            success=True,
            msg="Dashboard overview data retrieved successfully",
            statuscode=200,
            data=combined_data
        )
        
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": "An unexpected error occurred"
                }
            }
        )

@router.get("/today-attendance")
async def get_today_attendance(current_user: dict = Depends(get_current_user)):
    """Get today's attendance status for the current user"""
    print("get_today_attendance api called")
    try:
        user_id = current_user.get("user_id")
        
        service = AppDashboardService()
        result = service.get_today_attendance(user_id)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get today's attendance"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Today's attendance retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": "An unexpected error occurred"
                }
            }
        )

 