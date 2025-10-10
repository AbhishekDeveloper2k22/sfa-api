from fastapi import APIRouter, Depends
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_customer_services import AppCustomerService
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class CustomerProfileRequest(BaseModel):
    customer_id: str

class CustomerListRequest(BaseModel):
    status_filter: Optional[str] = "all"  # all, active, pending
    page: Optional[int] = 1
    limit: Optional[int] = 20

@router.post("/customer_profile")
async def get_customer_profile(request: CustomerProfileRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        service = AppCustomerService()
        result = service.get_customer_profile(request.customer_id, user_id)
        if not result.get("success"):
            return format_response(success=False, msg=result.get("message", "Failed to get customer profile"), statuscode=400, data={"error": result.get("error", {})})
        return format_response(success=True, msg="Customer profile retrieved successfully", statuscode=200, data=result.get("data", {}))
    except Exception:
        return format_response(success=False, msg="Internal server error", statuscode=500, data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}})

@router.post("/customer_list")
async def get_customer_list(request: CustomerListRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        service = AppCustomerService()
        result = service.get_customer_list(
            user_id=user_id,
            status_filter=request.status_filter,
            page=request.page,
            limit=request.limit
        )
        if not result.get("success"):
            return format_response(success=False, msg=result.get("message", "Failed to get customer list"), statuscode=400, data={"error": result.get("error", {})})
        return format_response(success=True, msg="Customer list retrieved successfully", statuscode=200, data=result.get("data", {}))
    except Exception:
        return format_response(success=False, msg="Internal server error", statuscode=500, data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}})

