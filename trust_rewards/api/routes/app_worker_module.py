from fastapi import APIRouter, Request, Depends
from trust_rewards.services.app_worker_services import AppWorkerService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
import traceback

router = APIRouter()

@router.post("/super30_leaderboard")
async def super30_leaderboard(request: Request, current_user: dict = Depends(get_current_user)):
    """Mobile leaderboard (Super 30) - supports This Month and All Time.

    Request body (optional):
      {
        "period": "this_month" | "all_time"  // default: this_month
      }
    """
    try:
        try:
            request_data = await request.json()
        except Exception:
            request_data = {}

        service = AppWorkerService()
        result = service.get_super30_leaderboard(request_data, current_user)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to fetch leaderboard"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )

        return format_response(
            success=True,
            msg="Leaderboard fetched",
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