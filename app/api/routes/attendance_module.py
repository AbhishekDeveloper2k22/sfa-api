from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from typing import Optional, List

from app.services.attendance_service import (
    AttendanceError,
    AttendanceService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

# Note: Prefix is just /api/v1 usually, but here based on docs:
# Docs say Base URL: /api/v1
# Endpoints are like /attendance/live
# So router prefix can be /api/v1
# However, the user file `employee_config_module.py` has prefix `/api/web/employee_config`.
# I should stick to what `attendance_api_documentation.md` says: `/api/v1`.
# But usually in this project structure, it might be scoped. 
# I will use `/api/v1` as requested in docs, but I should check if I need to register this router in `index.py`. 
# For now I will create the file.

router = APIRouter(tags=["attendance"])
service = AttendanceService()


def get_current_user(request: Request):
    return get_request_payload(request)


def tenant_context(payload: dict):
    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant associated with token")
    # user_id might be None for machine tokens, but usually required
    return tenant_id, user_id


def handle_service_call(fn):
    try:
        return fn()
    except AttendanceError as exc:
        return format_response(
            success=False,
            msg=exc.args[0],
            statuscode=exc.status_code,
            data={
                "error": {
                    "code": exc.code,
                    "message": exc.args[0],
                    "details": exc.errors,
                }
            },
        )
    except Exception as exc:
        return format_response(
            success=False,
            msg=str(exc),
            statuscode=500,
            data={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                }
            },
        )

# ------------------------------------------------------------------
# 1. Live Attendance APIs
# ------------------------------------------------------------------
@router.get("/live")
async def get_live_attendance(
    request: Request,
    q: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
    shift_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {k: v for k, v in locals().items() if k in ["q", "status", "department", "shift_id"] and v is not None}
    
    def action():
        data = service.get_live_attendance(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 2. Daily Attendance APIs
# ------------------------------------------------------------------
@router.get("/daily")
async def get_daily_attendance(
    request: Request,
    employee_id: Optional[str] = None,
    date: Optional[str] = None,
    from_date: Optional[str] = Query(None, alias="from_date"),
    to_date: Optional[str] = Query(None, alias="to_date"),
    status: Optional[str] = None,
    department: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {
        "employee_id": employee_id,
        "date": date,
        "from_date": from_date,
        "to_date": to_date,
        "status": status,
        "department": department,
        "page": page,
        "page_size": page_size
    }
    # Remove None to avoid filtering by None
    query_params = {k: v for k, v in query_params.items() if v is not None}

    def action():
        data = service.get_daily_attendance(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 4. Manual/Correction Requests APIs
# ------------------------------------------------------------------
@router.get("/manual-requests")
async def get_manual_requests(
    request: Request,
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    request_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {
        "employee_id": employee_id,
        "status": status,
        "request_type": request_type,
        "page": page,
        "page_size": page_size
    }
    query_params = {k: v for k, v in query_params.items() if v is not None}

    def action():
        data = service.get_manual_requests(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/manual-requests")
async def create_manual_request(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.create_manual_request(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

@router.post("/manual-requests/{requestId}/action")
async def action_manual_request(requestId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.action_manual_request(tenant_id, requestId, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 5. Overtime (OT) Requests APIs
# ------------------------------------------------------------------
@router.get("/ot-requests")
async def get_ot_requests(
    request: Request,
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {
        "employee_id": employee_id,
        "status": status,
        "page": page,
        "page_size": page_size
    }
    query_params = {k: v for k, v in query_params.items() if v is not None}

    def action():
        data = service.get_ot_requests(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/ot-requests")
async def create_ot_request(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.create_ot_request(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

@router.post("/ot-requests/{requestId}/action")
async def action_ot_request(requestId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.action_ot_request(tenant_id, requestId, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/ot-requests/bulk-approve")
async def bulk_approve_ot_requests(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.bulk_approve_ot_requests(tenant_id, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 6. Punch/Event APIs
# ------------------------------------------------------------------
@router.post("/punch")
async def record_punch(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.record_punch(tenant_id, payload)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/events")
async def get_events(
    request: Request,
    employee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {"employee_id": employee_id}
    query_params = {k: v for k, v in query_params.items() if v is not None}

    def action():
        data = service.get_events(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 7. Shift APIs
# ------------------------------------------------------------------
# Note: Shifts and Rosters in the doc were /shifts and /rosters.
# Under /api/web/attendance prefix, these become /attendance/shifts etc.
# If they should be root level, we would need a different router setup.
# I will assume they are grouped under attendance here.

@router.get("/shifts")
async def get_shifts(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_shifts(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/shifts/{shiftId}")
async def get_shift(shiftId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_shift(tenant_id, shiftId)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/shifts")
async def create_shift(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.create_shift(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

@router.put("/shifts/{shiftId}")
async def update_shift(shiftId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.update_shift(tenant_id, shiftId, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 8. Roster APIs
# ------------------------------------------------------------------
@router.get("/rosters")
async def get_rosters(
    request: Request,
    employee_id: Optional[str] = None,
    shift_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {"employee_id": employee_id, "shift_id": shift_id}
    query_params = {k: v for k, v in query_params.items() if v is not None}

    def action():
        data = service.get_rosters(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/rosters/assign")
async def assign_roster(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.assign_roster(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

@router.post("/rosters/bulk-assign")
async def bulk_assign_roster(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.bulk_assign_roster(tenant_id, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.delete("/rosters/{assignmentId}")
async def delete_roster_assignment(assignmentId: str, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.delete_roster_assignment(tenant_id, assignmentId)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 9. Device & Geofence APIs
# ------------------------------------------------------------------
@router.get("/devices")
async def get_devices(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_devices(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/devices")
async def register_device(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.register_device(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

@router.get("/geofences")
async def get_geofences(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_geofences(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 3. Monthly Attendance APIs
# ------------------------------------------------------------------
@router.get("/{employeeId}")
async def get_monthly_attendance(
    employeeId: str,
    month: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_monthly_attendance(tenant_id, employeeId, month)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)
