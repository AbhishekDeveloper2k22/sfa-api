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

@router.post("/order_list")
async def list_orders(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()

        # Optional filters with sensible defaults
        page = int(body.get("page", 1))
        limit = int(body.get("limit", 20))
        status = body.get("status", "all")
        customer_id = body.get("customer_id")
        date_from = body.get("date_from")
        date_to = body.get("date_to")

        service = AppOrderService()
        result = service.list_orders(
            user_id=current_user.get("user_id"),
            page=page,
            limit=limit,
            status=status,
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
        )
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get orders"),
                statuscode=400,
                data={"error": result.get("error", {})},
            )
        return format_response(
            success=True,
            msg="Orders retrieved successfully",
            statuscode=200,
            data=result.get("data", {}),
        )
    except Exception as e:
        print(traceback.format_exc())
        return format_response(
            success=False,
            msg=f"Internal server error: {str(e)}",
            statuscode=500,
            data={"error": {"code": "SERVER_ERROR", "details": str(e)}},
        )


@router.post("/order_detail")
async def order_detail(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        order_id = body.get("order_id")
        if not order_id:
            return format_response(success=False, msg="order_id is required", statuscode=400, data={"error": {"code": "VALIDATION_ERROR"}})

        service = AppOrderService()
        result = service.get_order_detail(user_id=current_user.get("user_id"), order_id=order_id)
        if not result.get("success"):
            return format_response(success=False, msg=result.get("message", "Failed to get order detail"), statuscode=400, data={"error": result.get("error", {})})
        return format_response(success=True, msg="Order detail retrieved successfully", statuscode=200, data=result.get("data", {}))
    except Exception as e:
        print(traceback.format_exc())
        return format_response(success=False, msg=f"Internal server error: {str(e)}", statuscode=500, data={"error": {"code": "SERVER_ERROR", "details": str(e)}})