from fastapi import APIRouter, Request, HTTPException
from sfa.middlewares.web_location_middleware import LocationDataProcessor
import traceback

router = APIRouter()

@router.post("/geo")
async def location_unique(request: Request):
    request_data = await request.json()
    instance = LocationDataProcessor()
    try:
        result = instance.unique(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})


