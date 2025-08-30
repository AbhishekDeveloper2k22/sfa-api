from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sfa.services.attendance_services import AttendanceService
from sfa.utils.response import format_response
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
    """Get attendance list for admin with filtering options for all employees"""
    try:
        # Get request body
        body = await request.json()
        
        # Extract parameters from request body
        page = body.get("page", 1)
        limit = body.get("limit", 20)
        month = body.get("month")  # Format: "January" or "January 2025"
        year = body.get("year")    # Format: 2025
        date = body.get("date")    # Format: "2025-01-15" - specific date filter
        status = body.get("status", "all")  # all, present, absent, late, leave, wfh, incomplete
        employee_id = body.get("employee_id")  # Specific employee ID
        department = body.get("department")  # Department filter
        search = body.get("search")  # Search by name, email, or employee ID
        
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
        
        service = AttendanceService()
        result = service.get_attendance_list_admin(
            page=page,
            limit=limit,
            month=month,
            year=year,
            date_filter=date,
            status=status,
            employee_id=employee_id,
            department=department,
            search=search
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

@router.get("/employee-summary/{employee_id}")
async def get_employee_attendance_summary(
    employee_id: str,
    month: Optional[str] = Query(None, description="Month name (e.g., 'January')"),
    year: Optional[int] = Query(None, description="Year (e.g., 2025)"),
    current_user: dict = Depends(get_current_user)
):
    """Get attendance summary for a specific employee"""
    try:
        # Validate employee_id
        if not employee_id:
            return format_response(
                success=False,
                msg="Employee ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Employee ID is required"
                    }
                }
            )
        
        # Validate month and year if provided
        if month and year:
            try:
                # Validate year
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
        
        service = AttendanceService()
        result = service.get_employee_attendance_summary(
            employee_id=employee_id,
            month=month,
            year=year
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get employee attendance summary"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Employee attendance summary retrieved successfully",
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

@router.get("/department-summary")
async def get_department_attendance_summary(
    department: Optional[str] = Query(None, description="Department name"),
    month: Optional[str] = Query(None, description="Month name (e.g., 'January')"),
    year: Optional[int] = Query(None, description="Year (e.g., 2025)"),
    current_user: dict = Depends(get_current_user)
):
    """Get attendance summary for a department or all departments"""
    try:
        # Validate month and year if provided
        if month and year:
            try:
                # Validate year
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
        
        service = AttendanceService()
        result = service.get_department_attendance_summary(
            department=department,
            month=month,
            year=year
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get department attendance summary"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Department attendance summary retrieved successfully",
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
