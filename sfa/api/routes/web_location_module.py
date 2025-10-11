from fastapi import APIRouter, Request
from sfa.middlewares.web_location_middleware import LocationDataProcessor
import traceback
from sfa.utils.response import format_response

router = APIRouter()

@router.post("/geo")
async def location_unique(request: Request):
    request_data = await request.json()
    instance = LocationDataProcessor()
    try:
        result = instance.unique(request_data)
        return format_response(
            success=True,
            msg="Location data retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve location data",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )


