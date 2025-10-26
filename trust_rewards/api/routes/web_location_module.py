from fastapi import APIRouter, Request
from trust_rewards.middlewares.web_location_middleware import LocationDataProcessor
import traceback
from trust_rewards.utils.response import format_response

router = APIRouter()

@router.post("/geo")
async def location_unique(request: Request):
    try:
        # Handle JSON parsing with better error handling
        try:
            request_data = await request.json()
        except Exception as json_error:
            return format_response(
                success=False,
                msg="Invalid JSON in request body",
                statuscode=400,
                data={"error": f"JSON parsing error: {str(json_error)}"}
            )
        
        # If no data provided, use empty dict
        if not request_data:
            request_data = {}
            
        instance = LocationDataProcessor()
        result = instance.unique(request_data)
        return format_response(
            success=True,
            msg="Location data retrieved successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve location data",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

