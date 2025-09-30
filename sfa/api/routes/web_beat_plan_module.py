from fastapi import APIRouter, Depends
from sfa.middlewares.web_beat_plan_middleware import beat_plan_middleware
from sfa.utils.response import format_response

router = APIRouter()
beat_plan_middleware_instance = beat_plan_middleware()


@router.post("/beat_plan_list")
async def beat_plan_list(request_data: dict):
    try:
        result = beat_plan_middleware_instance.beat_plan_list(request_data)
        if result.get("success"):
            response_data = {"data": result.get("data")}
            if result.get("pagination"):
                response_data["pagination"] = result.get("pagination")
            return format_response(
                success=True,
                msg=result.get("message"),
                data=response_data
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message"),
                statuscode=400
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error in beat plan list: {str(e)}",
            statuscode=500
        )


@router.post("/beat_plan_details")
async def beat_plan_details(request_data: dict):
    try:
        result = beat_plan_middleware_instance.beat_plan_details(request_data)
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message"),
                data={"data": result.get("data")}
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message"),
                statuscode=400
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error in beat plan details: {str(e)}",
            statuscode=500
        )
