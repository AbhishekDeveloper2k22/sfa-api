from fastapi import APIRouter, Depends, Request

from trust_rewards.utils.response import format_response
from trust_rewards.utils.auth import get_current_user
from trust_rewards.services.web_master_services import WebMasterService


router = APIRouter(tags=["web_master"])


@router.post("/points_master_add")
async def add_points_master(request: Request, current_user: dict = Depends(get_current_user)):
    """Add a new points master record with validations."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        created_by = current_user.get("user_id", 1)  # Get user_id from JWT payload
        result = service.add_points_master(body, created_by=created_by)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Validation failed"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg=result.get("message", "Points master added successfully"),
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to add points master: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/points_master_list")
async def get_points_master_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of points master records with filtering."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        result = service.get_points_master_list(body)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get points master list"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg="Points master list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to get points master list: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


