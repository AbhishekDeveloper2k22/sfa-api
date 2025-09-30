from fastapi import APIRouter, Request, HTTPException
from sfa.middlewares.web_attendance_middleware import AttendanceDataProcessor
import traceback

router = APIRouter()

@router.post("/attendance_list")
async def attendance_list(request: Request):
    request_data = await request.json()
    instance = AttendanceDataProcessor()
    try:
        result = instance.attendance_list(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})


