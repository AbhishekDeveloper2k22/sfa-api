from fastapi import APIRouter, Request
from sfa.middlewares.web_attendance_middleware import AttendanceDataProcessor
import traceback
from sfa.utils.response import format_response

router = APIRouter()

@router.post("/attendance_list")
async def attendance_list(request: Request):
    request_data = await request.json()
    instance = AttendanceDataProcessor()
    try:
        result = instance.attendance_list(request_data)
        return format_response(
            success=True, 
            msg="Attendance list retrieved successfully", 
            statuscode=200, 
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve attendance list",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )


