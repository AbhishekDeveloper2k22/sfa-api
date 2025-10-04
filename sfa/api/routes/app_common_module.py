from fastapi import APIRouter, Request, Depends
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_common_services import AppCommonService
import traceback

router = APIRouter()


@router.post("/all_types")
async def get_all_types(request: Request, current_user: dict = Depends(get_current_user)):
    """Get all types data based on name parameter"""
    try:
        request_data = await request.json()
        user_id = current_user.get("user_id")
        
        service = AppCommonService()
        result = service.get_all_types(request_data, user_id)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get all types"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="All types retrieved successfully",
            statuscode=200,
            data=result.get("data", [])
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
