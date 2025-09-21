from fastapi import APIRouter, Request, HTTPException, Depends
from trust_rewards.services.web_skilled_worker_services import SkilledWorkerService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
import traceback

router = APIRouter()

@router.post("/skilled_workers_list")
async def get_skilled_workers_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of skilled workers with optional filters"""
    try:
        request_data = await request.json()
        
        # Validate mandatory status filter
        filters = request_data.get('filters', {})
        status = filters.get('status')
        
        if not status:
            return format_response(
                success=False,
                msg="Status filter is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "filters.status is mandatory"
                    }
                }
            )
        
        # Validate status values
        valid_statuses = ['All', 'Active', 'Inactive', 'KYC Pending']
        if status not in valid_statuses:
            return format_response(
                success=False,
                msg="Invalid status value",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"Status must be one of: {', '.join(valid_statuses)}"
                    }
                }
            )
        
        service = SkilledWorkerService()
        result = service.get_skilled_workers_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get skilled workers list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Skilled workers list retrieved successfully",
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

@router.post("/skilled_worker_details")
async def get_skilled_worker_details(request: Request, current_user: dict = Depends(get_current_user)):
    """Get details of a specific skilled worker"""
    try:
        request_data = await request.json()
        service = SkilledWorkerService()
        result = service.get_skilled_worker_details(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get worker details"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Worker details retrieved successfully",
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
