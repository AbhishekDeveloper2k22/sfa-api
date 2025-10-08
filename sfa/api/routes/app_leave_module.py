from fastapi import APIRouter, Request, HTTPException, Depends, Query, UploadFile, File, Form
from sfa.services.app_leave_services import AppLeaveService
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from typing import Optional
import jwt
from datetime import datetime, timedelta
import pytz
import os
import uuid

router = APIRouter()

@router.post("/apply_leave")
async def apply_leave(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Apply for leave"""
    try:
        user_id = current_user.get("user_id")
        body = await request.json()
        
        # Extract leave application data
        leave_type = body.get("leaveType")
        from_date = body.get("fromDate")  # From Date
        to_date = body.get("toDate")      # To Date
        reason = body.get("reason", "")
        
        # Validate required fields
        if not leave_type:
            return format_response(
                success=False,
                msg="Leave type is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Leave type is required"
                    }
                }
            )
        
        if not from_date:
            return format_response(
                success=False,
                msg="From date is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "From date is required"
                    }
                }
            )
        
        if not to_date:
            return format_response(
                success=False,
                msg="To date is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "To date is required"
                    }
                }
            )
        
        # Validate date format
        try:
            datetime.strptime(from_date, "%Y-%m-%d")
            datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            return format_response(
                success=False,
                msg="Invalid date format",
                statuscode=400,
                data={
                    "error": {
                        "details": "Date must be in YYYY-MM-DD format"
                    }
                }
            )
        
        # Validate leave type
        valid_leave_types = ["casual", "sick", "other"]
        if leave_type not in valid_leave_types:
            return format_response(
                success=False,
                msg="Invalid leave type",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"Leave type must be one of: {', '.join(valid_leave_types)}"
                    }
                }
            )
        
        service = AppLeaveService()
        result = service.apply_leave(
            user_id=user_id,
            leave_type=leave_type,
            start_date=from_date,
            end_date=to_date,
            reason=reason
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to apply leave"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Leave application submitted successfully",
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

@router.post("/leave_list")
async def get_leave_list(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get user's leave history with pagination and filtering"""
    try:
        user_id = current_user.get("user_id")
        body = await request.json()
        
        # Extract parameters
        page = body.get("page", 1)
        limit = body.get("limit", 20)
        status = body.get("status", "all")  # all, pending, approved, rejected, cancelled
        leave_type = body.get("leaveType")  # Filter by leave type
        year = body.get("year")  # Filter by year
        
        # Validate parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20
            
        if status not in ["all", "pending", "approved", "rejected", "cancelled"]:
            return format_response(
                success=False,
                msg="Invalid status parameter",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Status must be 'all', 'pending', 'approved', 'rejected', or 'cancelled'"
                    }
                }
            )
        
        service = AppLeaveService()
        result = service.get_leave_list(
            user_id=user_id,
            page=page,
            limit=limit,
            status=status,
            leave_type=leave_type,
            year=year
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get leave list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Leave list retrieved successfully",
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

# Used
@router.get("/leave_balance")
async def get_leave_balance(
    current_user: dict = Depends(get_current_user)
):
    """Get user's leave balance for different leave types"""
    try:
        user_id = current_user.get("user_id")
        
        service = AppLeaveService()
        result = service.get_leave_balance(user_id=user_id)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get leave balance"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Leave balance retrieved successfully",
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

@router.post("/leave_details")
async def get_leave_details(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information for a specific leave application"""
    try:
        user_id = current_user.get("user_id")
        body = await request.json()
        leave_id = body.get("leave_id")
        
        if not leave_id:
            return format_response(
                success=False,
                msg="Leave ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Leave ID is required"
                    }
                }
            )
        
        service = AppLeaveService()
        result = service.get_leave_details(
            user_id=user_id,
            leave_id=leave_id
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get leave details"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Leave details retrieved successfully",
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

@router.post("/cancel_leave")
async def cancel_leave(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a leave application"""
    try:
        user_id = current_user.get("user_id")
        body = await request.json()
        
        leave_id = body.get("leave_id")
        reason = body.get("reason", "")
        
        if not leave_id:
            return format_response(
                success=False,
                msg="Leave ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Leave ID is required"
                    }
                }
            )
        
        service = AppLeaveService()
        result = service.cancel_leave(
            user_id=user_id,
            leave_id=leave_id,
            reason=reason
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to cancel leave"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Leave cancelled successfully",
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

@router.post("/upload_attachment")
async def upload_leave_attachment(
    leave_id: str = Form(...),
    attachment: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload attachment for a specific leave application"""
    try:
        user_id = current_user.get("user_id")
        
        # Validate leave_id
        if not leave_id:
            return format_response(
                success=False,
                msg="Leave ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Leave ID is required"
                    }
                }
            )
        
        # Validate file
        if not attachment:
            return format_response(
                success=False,
                msg="Attachment file is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Attachment file is required"
                    }
                }
            )
        
        # Validate file size (max 10MB)
        if attachment.size and attachment.size > 10 * 1024 * 1024:
            return format_response(
                success=False,
                msg="File size too large",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "File size must be less than 10MB"
                    }
                }
            )
        
        # Validate file type
        allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif']
        file_extension = os.path.splitext(attachment.filename)[1].lower()
        if file_extension not in allowed_extensions:
            return format_response(
                success=False,
                msg="Invalid file type",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"File type must be one of: {', '.join(allowed_extensions)}"
                    }
                }
            )
        
        service = AppLeaveService()
        result = service.upload_leave_attachment(
            user_id=user_id,
            leave_id=leave_id,
            attachment=attachment
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to upload attachment"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Attachment uploaded successfully",
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

 