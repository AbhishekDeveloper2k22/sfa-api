from fastapi import APIRouter
from sfa.middlewares.web_order_middleware import order_middleware
from sfa.utils.response import format_response

router = APIRouter()
mw = order_middleware()


@router.post("/order_list")
async def order_list(request_data: dict):
    try:
        result = mw.order_list(request_data)
        if result.get("success"):
            response_data = {"data": result.get("data")}
            if result.get("pagination"):
                response_data["pagination"] = result.get("pagination")
            return format_response(success=True, msg=result.get("message"), data=response_data)
        return format_response(success=False, msg=result.get("message"), statuscode=400)
    except Exception as e:
        return format_response(success=False, msg=str(e), statuscode=500)


@router.post("/order_details")
async def order_details(request_data: dict):
    try:
        result = mw.order_details(request_data)
        if result.get("success"):
            return format_response(success=True, msg=result.get("message"), data={"data": result.get("data")})
        return format_response(success=False, msg=result.get("message"), statuscode=400)
    except Exception as e:
        return format_response(success=False, msg=str(e), statuscode=500)


@router.post("/order_update")
async def order_update(request_data: dict):
    try:
        result = mw.order_update(request_data)
        if result.get("success"):
            return format_response(success=True, msg=result.get("message"))
        return format_response(success=False, msg=result.get("message"), statuscode=400)
    except Exception as e:
        return format_response(success=False, msg=str(e), statuscode=500)


