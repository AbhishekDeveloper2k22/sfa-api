from fastapi import APIRouter, Request, HTTPException, Depends, Query, UploadFile, File, Form
from field_squad.services.app_request_services import AppRequestService
from field_squad.utils.response import format_response
from typing import Optional
import jwt
from datetime import datetime, timedelta
import pytz
import os
import uuid
import traceback

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

@router.post("/apply")
async def apply_request(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Apply for any type of request (leave, regularisation, work from home, compensatory off, expense)"""
    try:
        user_id = current_user.get("user_id")
        body = await request.json()
        
        # Extract request data
        request_type = body.get("requestType")  # leave, regularisation, wfh, compensatory_off, expense
        request_id = body.get("requestId")  # For editing existing request
        is_edit = bool(request_id)  # Check if this is an edit operation
                
        # Validate request type and apply type-specific validation
        if request_type == "leave":

            start_date = body.get("startDate")
            end_date = body.get("endDate")
            reason = body.get("reason", "")
            half_day = body.get("halfDay", False)
            half_day_type = body.get("halfDayType")  # "first_half" or "second_half"
            leave_type = body.get("leaveType")  # "casual", "sick", "annual", etc.

            # Validate leave type
            valid_leave_types = ["casual", "sick", "annual", "maternity", "paternity", "bereavement", "other"]
            if not leave_type:
                return format_response(
                    success=False,
                    msg="Leave type is required for leave request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Leave type is required for leave request"
                        }
                    }
                )
            
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

            # Leave request (existing logic remains)
            if not start_date:
                return format_response(
                    success=False,
                    msg="Start date is required for leave request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Start date is required for leave request"
                        }
                    }
                )
            if not end_date:
                return format_response(
                    success=False,
                    msg="End date is required for leave request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "End date is required for leave request"
                        }
                    }
                )
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return format_response(
                    success=False,
                    msg="Invalid date format for leave request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Date must be in YYYY-MM-DD format"
                        }
                    }
                )
            if half_day and half_day_type not in ["first_half", "second_half"]:
                return format_response(
                    success=False,
                    msg="Invalid half day type for leave request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Half day type must be 'first_half' or 'second_half'"
                        }
                    }
                )
            # No changes needed for leave
        
        elif request_type == "regularisation":
            # New payload: { "requestType": "regularisation", "date": "2025-08-01", "punchIn": "10:30", "punchOut": "18:00", "reason": "..." }
            reg_date = body.get("date")
            punch_in = body.get("punchIn")
            punch_out = body.get("punchOut")
            reason = body.get("reason", "")
            if not reg_date or not punch_in or not punch_out:
                return format_response(
                    success=False,
                    msg="date, punchIn, and punchOut are required for regularisation request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "date, punchIn, and punchOut are required for regularisation request"
                        }
                    }
                )
            # Validate date format
            try:
                datetime.strptime(reg_date, "%Y-%m-%d")
            except ValueError:
                return format_response(
                    success=False,
                    msg="Invalid date format for regularisation request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "date must be in YYYY-MM-DD format"
                        }
                    }
                )
            # Map to service params
            start_date = reg_date
            end_date = reg_date
            regularisation_data = {"punchIn": punch_in, "punchOut": punch_out}
        
        elif request_type == "wfh":
            # New payload: { "requestType": "wfh", "startDate": "2025-08-07", "endDate": "2025-08-07", "location": "Home", "reason": "..." }
            start_date = body.get("startDate")
            end_date = body.get("endDate")
            location = body.get("location")
            reason = body.get("reason", "")
            if not start_date or not end_date or not location:
                return format_response(
                    success=False,
                    msg="startDate, endDate, and location are required for WFH request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "startDate, endDate, and location are required for WFH request"
                        }
                    }
                )
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return format_response(
                    success=False,
                    msg="Invalid date format for WFH request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Dates must be in YYYY-MM-DD format"
                        }
                    }
                )
            wfh_data = {"location": location}
        
        elif request_type == "compensatory_off":
            # New payload: { "requestType": "compensatory_off", "workData": "2025-08-03", "compOffDate": "2025-08-03", "workHours": "8", "reason": "..." }
            work_data = body.get("workData")
            comp_off_date = body.get("compOffDate")
            work_hours = body.get("workHours")
            reason = body.get("reason", "")
            if not work_data or not comp_off_date or not work_hours:
                return format_response(
                    success=False,
                    msg="workData, compOffDate, and workHours are required for compensatory off request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "workData, compOffDate, and workHours are required for compensatory off request"
                        }
                    }
                )
            # Validate date format
            try:
                datetime.strptime(work_data, "%Y-%m-%d")
                datetime.strptime(comp_off_date, "%Y-%m-%d")
            except ValueError:
                return format_response(
                    success=False,
                    msg="Invalid date format for compensatory off request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Dates must be in YYYY-MM-DD format"
                        }
                    }
                )
            start_date = work_data
            end_date = comp_off_date
            compensatory_off_data = {"workHours": work_hours}
        
        elif request_type == "expense":
            # New payload: { "requestType": "expense", "expenseType": "Food", "amount": "1500.75", "date": "2025-08-03", "description": "..." }
            expense_type = body.get("expenseType")
            amount = body.get("amount")
            expense_date = body.get("date")
            description = body.get("description", "")
            if not expense_type or not amount or not expense_date:
                return format_response(
                    success=False,
                    msg="expenseType, amount, and date are required for expense request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "expenseType, amount, and date are required for expense request"
                        }
                    }
                )
            try:
                float(amount)
            except (ValueError, TypeError):
                return format_response(
                    success=False,
                    msg="Invalid amount format for expense request",
                    statuscode=400,
                    data={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "Amount must be a valid number"
                        }
                    }
                )
            expense_data = {
                "expenseType": expense_type,
                "amount": amount,
                "date": expense_date,
                "description": description
            }
        else:
            return format_response(
                success=False,
                msg="Invalid request type",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Request type must be one of: leave, regularisation, wfh, compensatory_off, expense"
                    }
                }
            )
        
        service = AppRequestService()
        
        # Call service based on request type and operation (create or edit)
        if request_type == "leave":
            if is_edit:
                result = service.edit_request(
                    user_id=user_id,
                    request_id=request_id,
                    request_type=request_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    half_day=half_day,
                    half_day_type=half_day_type,
                    regularisation_data={},
                    wfh_data={},
                    compensatory_off_data={},
                    expense_data={}
                )
            else:
                result = service.apply_request(
                    user_id=user_id,
                    request_type=request_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    half_day=half_day,
                    half_day_type=half_day_type,
                    regularisation_data={},
                    wfh_data={},
                    compensatory_off_data={},
                    expense_data={}
                )
        elif request_type == "regularisation":
            if is_edit:
                result = service.edit_request(
                    user_id=user_id,
                    request_id=request_id,
                    request_type=request_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    half_day=False,
                    half_day_type=None,
                    regularisation_data=regularisation_data,
                    wfh_data={},
                    compensatory_off_data={},
                    expense_data={}
                )
            else:
                result = service.apply_request(
                    user_id=user_id,
                    request_type=request_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    half_day=False,
                    half_day_type=None,
                    regularisation_data=regularisation_data,
                    wfh_data={},
                    compensatory_off_data={},
                    expense_data={}
                )
        elif request_type == "wfh":
            if is_edit:
                result = service.edit_request(
                    user_id=user_id,
                    request_id=request_id,
                    request_type=request_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    half_day=False,
                    half_day_type=None,
                    regularisation_data={},
                    wfh_data=wfh_data,
                    compensatory_off_data={},
                    expense_data={}
                )
            else:
                result = service.apply_request(
                    user_id=user_id,
                    request_type=request_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    half_day=False,
                    half_day_type=None,
                    regularisation_data={},
                    wfh_data=wfh_data,
                    compensatory_off_data={},
                    expense_data={}
                )
        elif request_type == "compensatory_off":
            if is_edit:
                result = service.edit_request(
                    user_id=user_id,
                    request_id=request_id,
                    request_type=request_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    half_day=False,
                    half_day_type=None,
                    regularisation_data={},
                    wfh_data={},
                    compensatory_off_data=compensatory_off_data,
                    expense_data={}
                )
            else:
                result = service.apply_request(
                    user_id=user_id,
                    request_type=request_type,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    half_day=False,
                    half_day_type=None,
                    regularisation_data={},
                    wfh_data={},
                    compensatory_off_data=compensatory_off_data,
                    expense_data={}
                )
        elif request_type == "expense":
            if is_edit:
                result = service.edit_request(
                    user_id=user_id,
                    request_id=request_id,
                    request_type=request_type,
                    start_date=None,
                    end_date=None,
                    reason=reason,
                    half_day=False,
                    half_day_type=None,
                    regularisation_data={},
                    wfh_data={},
                    compensatory_off_data={},
                    expense_data=expense_data
                )
            else:
                result = service.apply_request(
                    user_id=user_id,
                    request_type=request_type,
                    start_date=None,
                    end_date=None,
                    reason="",
                    half_day=False,
                    half_day_type=None,
                    regularisation_data={},
                    wfh_data={},
                    compensatory_off_data={},
                    expense_data=expense_data
                )
        else:
            return format_response(
                success=False,
                msg="Invalid request type",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Request type must be one of: leave, regularisation, wfh, compensatory_off, expense"
                    }
                }
            )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to apply request"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Request submitted successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/list")
async def get_request_list(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get user's request history with pagination and filtering"""
    try:
        user_id = current_user.get("user_id")
        body = await request.json()
        
        # Extract parameters
        page = body.get("page", 1)
        limit = body.get("limit", 20)
        status = body.get("status", "all")  # all, pending, approved, rejected, cancelled
        request_type = body.get("requestType")  # Filter by request type
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
        
        service = AppRequestService()
        result = service.get_request_list(
            user_id=user_id,
            page=page,
            limit=limit,
            status=status,
            request_type=request_type,
            year=year
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get request list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Request list retrieved successfully",
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

@router.post("/balance")
async def get_leave_balance(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get user's leave balance for different leave types with filtering options"""
    try:
        user_id = current_user.get("user_id")
        # Handle empty request body gracefully
        try:
            body = await request.json()
        except:
            # If no JSON body or invalid JSON, use empty dict
            body = {}
        
        # Extract filter parameters with defaults
        status = body.get("status", "all")  # Filter by request status
        start_date = body.get("startDate", "")  # Filter by start date
        end_date = body.get("endDate", "")  # Filter by end date
        leave_type = body.get("leaveType", "")  # Filter by leave type
        
        service = AppRequestService()
        result = service.get_leave_balance(
            user_id=user_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            filter_leave_type=leave_type
        )
        
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
        # Get detailed error information with traceback
        error_traceback = traceback.format_exc()
        error_details = {
            "code": "SERVER_ERROR",
            "details": str(e),
            "traceback": error_traceback
        }
        
        # Log the error for debugging (you can also log to file if needed)
        print(f"Error in /balance endpoint: {str(e)}")
        print(f"Traceback: {error_traceback}")
        
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": error_details
            }
        )

@router.get("/details/{request_id}")
async def get_request_details(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information for a specific request"""
    try:
        user_id = current_user.get("user_id")
        
        service = AppRequestService()
        result = service.get_request_details(
            user_id=user_id,
            request_id=request_id
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get request details"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Request details retrieved successfully",
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

@router.post("/cancel/{request_id}")
async def cancel_request(
    request_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a request"""
    try:
        user_id = current_user.get("user_id")
        body = await request.json()
        
        reason = body.get("reason", "")
        
        service = AppRequestService()
        result = service.cancel_request(
            user_id=user_id,
            request_id=request_id,
            reason=reason
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to cancel request"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Request cancelled successfully",
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

@router.post("/upload-attachment")
async def upload_request_attachment(
    request_id: str = Form(...),
    attachment: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload attachment for a specific request"""
    try:
        user_id = current_user.get("user_id")
        
        # Validate request_id
        if not request_id:
            return format_response(
                success=False,
                msg="Request ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Request ID is required"
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
        
        service = AppRequestService()
        result = service.upload_request_attachment(
            user_id=user_id,
            request_id=request_id,
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

@router.post("/store-date-suggestion")
async def store_date_suggestion(
    request: Request
):
    """Store date suggestion data in a new collection"""
    try:
        body = await request.json()
        
        # Validate required fields
        required_fields = ["selectedDate", "dateTitle", "dateEmoji", "dateMessage", "timestamp"]
        missing_fields = [field for field in required_fields if not body.get(field)]
        
        if missing_fields:
            return format_response(
                success=False,
                msg="Missing required fields",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"Missing required fields: {', '.join(missing_fields)}"
                    }
                }
            )
        
        service = AppRequestService()
        result = service.store_date_suggestion(
            user_id=None,  # No user authentication required
            date_data=body
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to store date suggestion"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Date suggestion stored successfully",
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

@router.get("/date-suggestion-list")
async def get_date_suggestion_list():
    """Get the date suggestion from the collection"""
    try:
        service = AppRequestService()
        result = service.get_date_suggestion_list()
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get date suggestion"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Date suggestion retrieved successfully",
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

@router.get("/types")
async def get_request_types(
    current_user: dict = Depends(get_current_user)
):
    """Get available request types and their descriptions"""
    try:
        service = AppRequestService()
        result = service.get_request_types()
        
        return format_response(
            success=True,
            msg="Request types retrieved successfully",
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