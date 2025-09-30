from fastapi import APIRouter, Request, Depends
from trust_rewards.services.web_redeem_request_services import WebRedeemRequestService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
import traceback

router = APIRouter()

@router.post("/redemption_requests_list")
async def get_all_redemption_requests(request: Request, current_user: dict = Depends(get_current_user)):
    """Get all redemption requests with pagination and filtering"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = WebRedeemRequestService()
        result = service.get_all_redemption_requests(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get redemption requests"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Redemption requests retrieved successfully",
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

@router.post("/update_redemption_status")
async def update_redemption_status(request: Request, current_user: dict = Depends(get_current_user)):
    """Update redemption status with history tracking"""
    try:
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = WebRedeemRequestService()
        result = service.update_redemption_status(request_data, current_user)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to update redemption status"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg=result.get("message", "Redemption status updated successfully"),
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

@router.post("/redemption_detail")
async def get_redemption_detail(request: Request, current_user: dict = Depends(get_current_user)):
    """Get comprehensive redemption detail with worker info, wallet balance, reward details, and timeline"""
    try:
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = WebRedeemRequestService()
        result = service.get_redemption_detail(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get redemption detail"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Redemption detail retrieved successfully",
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

@router.post("/redeem_request_status_change")
async def change_redemption_status(request: Request, current_user: dict = Depends(get_current_user)):
    """Change redemption request status with proper point management"""
    try:
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        # Add admin_id from current_user
        request_data['admin_id'] = str(current_user.get('_id', ''))
        
        service = WebRedeemRequestService()
        result = service.change_redemption_status(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to change redemption status"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg=result.get("message", "Redemption status changed successfully"),
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
