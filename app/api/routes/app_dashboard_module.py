from fastapi import APIRouter, Request, HTTPException, Depends, Query
from app.services.app_dashboard_services import AppDashboardService
from app.utils.response import format_response
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

@router.post("/punch-in")
async def punch_in(request: Request, current_user: dict = Depends(get_current_user)):
    """Punch in for attendance"""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        # Validate required fields - only location is required from frontend
        location = body.get("location", {})
        notes = body.get("notes", "")
        
        # Validate location with enhanced validation
        location_valid, location_error = validate_location(location)
        if not location_valid:
            return format_response(
                success=False,
                msg="Invalid location data",
                statuscode=400,
                data={
                    "error": {
                        "code": "INVALID_LOCATION",
                        "details": location_error
                    }
                }
            )
        
        # Validate notes length
        if notes and len(notes) > 1000:
            return format_response(
                success=False,
                msg="Notes too long",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "notes must be less than 1000 characters"
                    }
                }
            )
        
        service = AppDashboardService()
        result = service.punch_in(
            user_id=user_id,
            location=location,
            notes=notes
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Punch in failed"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Punch in successful",
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

@router.post("/punch-out")
async def punch_out(request: Request, current_user: dict = Depends(get_current_user)):
    """Punch out for attendance - date and time generated on backend, address from coordinates"""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        # Validate required fields - only location is required from frontend
        location = body.get("location", {})
        notes = body.get("notes", "")
        
        # Validate location with enhanced validation
        location_valid, location_error = validate_location(location)
        if not location_valid:
            return format_response(
                success=False,
                msg="Invalid location data",
                statuscode=400,
                data={
                    "error": {
                        "code": "INVALID_LOCATION",
                        "details": location_error
                    }
                }
            )
        
        # Validate notes length
        if notes and len(notes) > 1000:
            return format_response(
                success=False,
                msg="Notes too long",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "notes must be less than 1000 characters"
                    }
                }
            )
        
        service = AppDashboardService()
        result = service.punch_out(
            user_id=user_id,
            location=location,
            notes=notes
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Punch out failed"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Punch out successful",
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

 