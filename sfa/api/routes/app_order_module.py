from fastapi import APIRouter, Request, Depends
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_order_services import AppOrderService
import traceback

router = APIRouter()


@router.post("/create_order")
async def create_order(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        payload = await request.json()
        user_id = current_user.get("user_id")

        service = AppOrderService()
        result = service.create_order(user_id=user_id, payload=payload)
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to create order"),
                statuscode=400,
                data={"error": result.get("error", {})},
            )

        return format_response(
            success=True,
            msg="Order created successfully",
            statuscode=200,
            data=result.get("data", {}),
        )
    except Exception as e:
        print(traceback.format_exc())
        return format_response(
            success=False,
            msg=f"Internal server error: {str(e)}",
            statuscode=500,
            data={
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            },
        )


