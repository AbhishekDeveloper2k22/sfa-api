from fastapi import APIRouter, Depends
from sfa.middlewares.web_followup_middleware import followup_middleware
from sfa.utils.response import format_response

router = APIRouter()
followup_middleware_instance = followup_middleware()


@router.post("/followup_list")
async def followup_list(request_data: dict):
    try:
        result = followup_middleware_instance.followup_list(request_data)
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
            msg=f"Error in followup list: {str(e)}",
            statuscode=500
        )


@router.post("/followup_details")
async def followup_details(request_data: dict):
    try:
        result = followup_middleware_instance.followup_details(request_data)
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
            msg=f"Error in followup details: {str(e)}",
            statuscode=500
        )
