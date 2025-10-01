from fastapi import APIRouter, Depends
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_customer_services import AppCustomerService
from pydantic import BaseModel

router = APIRouter()

class CustomerProfileRequest(BaseModel):
    customer_id: str

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
