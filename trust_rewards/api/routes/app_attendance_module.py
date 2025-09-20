from fastapi import APIRouter, Request, HTTPException, Depends, Query
from trust_rewards.services.app_attendance_services import AppAttendanceService
from trust_rewards.utils.response import format_response
from typing import Optional
import jwt
from datetime import datetime, timedelta
import pytz

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

@router.post("/attendance-list")
async def get_attendance_list(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get user's attendance list for current month with present/absent status for each date"""
    try:
        user_id = current_user.get("user_id")
        
        # Get request body
        body = await request.json()
        
        # Extract parameters from request body
        page = body.get("page", 1)
        limit = body.get("limit", 20)
        month = body.get("month")  # Format: "January" or "January 2025"
        year = body.get("year")    # Format: 2025
        date = body.get("date")    # Format: "2025-01-15" - specific date filter
        status = body.get("status", "all")  # all, present, absent
        
        # Validate parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20
            
        if status not in ["all", "present", "absent", "late", "leave", "wfh", "incomplete"]:
            return format_response(
                success=False,
                msg="Invalid status parameter",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Status must be 'all', 'present', 'absent', 'late', 'leave', 'wfh', or 'incomplete'"
                    }
                }
            )
        
        # Validate month and year if provided
        if month and year:
            try:
                # Validate year
                year = int(year)
                if year < 2020 or year > 2030:
                    return format_response(
                        success=False,
                        msg="Invalid year",
                        statuscode=400,
                        data={
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "details": "Year must be between 2020 and 2030"
                            }
                        }
                    )
                
                # Validate month format
                month_names = [
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"
                ]
                
                # Check if month is just name or "Month Year" format
                if month not in month_names and not any(month.startswith(m) for m in month_names):
                    return format_response(
                        success=False,
                        msg="Invalid month format",
                        statuscode=400,
                        data={
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "details": "Month must be a valid month name (e.g., 'January' or 'January 2025')"
                            }
                        }
                    )
                    
            except ValueError:
                return format_response(
                    success=False,
                    msg="Invalid year format",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Year must be a valid number"
                        }
                    }
                )
        
        # Validate specific date if provided
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return format_response(
                    success=False,
                    msg="Invalid date format",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Date must be in YYYY-MM-DD format"
                        }
                    }
                )
        
        service = AppAttendanceService()
        result = service.get_attendance_list_current_month(
            user_id=user_id,
            page=page,
            limit=limit,
            month=month,
            year=year,
            date_filter=date,
            status=status
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get attendance list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Attendance list retrieved successfully",
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
