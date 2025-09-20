from fastapi import APIRouter, Request, HTTPException, Depends, Query
from trust_rewards.services.app_sidebar_services import AppSidebarService
from trust_rewards.utils.response import format_response
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

@router.get("/upcoming-celebrations")
async def get_upcoming_celebrations(
    current_user: dict = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365, description="Number of days to look ahead (default: 30)"),
    limit: int = Query(20, ge=1, le=100, description="Number of celebrations to return (max: 100)")
):
    """Get upcoming birthdays and work anniversaries for the next N days"""
    try:
        user_id = current_user.get("user_id")
        
        service = AppSidebarService()
        result = service.get_upcoming_celebrations(user_id, days, limit)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get upcoming celebrations"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Upcoming celebrations retrieved successfully",
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

@router.get("/employee-directory")
async def get_employee_directory(
    current_user: dict = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search by name, designation, or department"),
    department: Optional[str] = Query(None, description="Filter by department"),
    designation: Optional[str] = Query(None, description="Filter by designation"),
    status: str = Query("Active", description="Filter by employment status (Active/Inactive)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of employees per page")
):
    """Get employee directory with search and filtering options"""
    try:
        user_id = current_user.get("user_id")
        
        service = AppSidebarService()
        result = service.get_employee_directory(
            user_id=user_id,
            search=search,
            department=department,
            designation=designation,
            status=status,
            page=page,
            limit=limit
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get employee directory"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Employee directory retrieved successfully",
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

@router.get("/employee/{employee_id}")
async def get_employee_details(
    employee_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific employee"""
    try:
        user_id = current_user.get("user_id")
        
        service = AppSidebarService()
        result = service.get_employee_details(user_id, employee_id)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get employee details"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Employee details retrieved successfully",
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