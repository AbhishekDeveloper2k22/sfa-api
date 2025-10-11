from fastapi import APIRouter, Request, Depends
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_followup_services import AppFollowupService
import traceback

router = APIRouter()

@router.post("/add_followup")
async def add_followup(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        followup_date = body.get("followup_date")
        followup_time = body.get("followup_time")
        network_type = body.get("network_type")
        customer_type = body.get("customer_type")
        entity_id = body.get("entity_id")
        remarks = body.get("remarks", "")
        
        followup_data = {
            "followup_date": followup_date,
            "followup_time": followup_time,
            "network_type": network_type,
            "customer_type": customer_type,
            "entity_id": entity_id,
            "remarks": remarks
        }
        
        service = AppFollowupService()
        result = service.add_followup(user_id, followup_data)
        
        if not result.get("success"):
            return format_response(
                success=False, 
                msg=result.get("message", "Failed to add followup"), 
                statuscode=400, 
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True, 
            msg="Followup added successfully", 
            statuscode=201, 
            data=result.get("data", {})
        )
        
    except Exception as e:
        print(traceback.format_exc())
        return format_response(
            success=False, 
            msg="Internal server error", 
            statuscode=500, 
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )

@router.post("/followup_list")
async def get_followup_list(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        # Pagination parameters
        page = int(body.get("page", 1))
        limit = int(body.get("limit", 20))
        
        # Filter parameters
        status_filter = body.get("status_filter", "all")  # all, pending, completed, cancelled
        
        service = AppFollowupService()
        result = service.get_followup_list(
            user_id=user_id,
            status_filter=status_filter,
            page=page,
            limit=limit
        )
        
        if not result.get("success"):
            return format_response(
                success=False, 
                msg=result.get("message", "Failed to get followup list"), 
                statuscode=400, 
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True, 
            msg="Followup list retrieved successfully", 
            statuscode=200, 
            data=result.get("data", {})
        )
        
    except Exception as e:
        print(traceback.format_exc())
        return format_response(
            success=False, 
            msg="Internal server error", 
            statuscode=500, 
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )

@router.post("/update_followup_status")
async def update_followup_status(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        followup_id = body.get("followup_id")
        status = body.get("status")
        remarks = body.get("remarks", "")
        
        if not followup_id:
            return format_response(
                success=False,
                msg="followup_id is required",
                statuscode=400,
                data={"error": {"code": "VALIDATION_ERROR", "details": "followup_id is required"}}
            )
        
        service = AppFollowupService()
        result = service.update_followup_status(
            user_id=user_id,
            followup_id=followup_id,
            status=status,
            remarks=remarks
        )
        
        if not result.get("success"):
            return format_response(
                success=False, 
                msg=result.get("message", "Failed to update followup status"), 
                statuscode=400, 
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True, 
            msg="Followup status updated successfully", 
            statuscode=200, 
            data=result.get("data", {})
        )
        
    except Exception as e:
        print(traceback.format_exc())
        return format_response(
            success=False, 
            msg="Internal server error", 
            statuscode=500, 
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )
