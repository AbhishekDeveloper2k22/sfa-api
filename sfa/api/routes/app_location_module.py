from fastapi import APIRouter, Request, Depends
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_location_services import AppLocationService
import traceback

router = APIRouter()


@router.post("/geo")
async def get_location_data(request: Request, current_user: dict = Depends(get_current_user)):
    """Get location data based on state, district, or pincode"""
    try:
        # Get request body
        body = await request.body()
        
        # Check if body is empty
        if not body:
            return format_response(
                success=False,
                msg="Request body is empty",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Request body cannot be empty"
                    }
                }
            )
        
        # Try to parse JSON
        try:
            request_data = await request.json()
        except Exception as json_error:
            return format_response(
                success=False,
                msg="Invalid JSON format",
                statuscode=400,
                data={
                    "error": {
                        "code": "INVALID_JSON",
                        "details": f"Invalid JSON format: {str(json_error)}"
                    }
                }
            )
        
        user_id = current_user.get("user_id")
        
        service = AppLocationService()
        result = service.get_location_data(request_data, user_id)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get location data"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Location data retrieved successfully",
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
