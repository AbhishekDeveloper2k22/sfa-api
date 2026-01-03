from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from typing import Optional, List

from app.services.leave_service import (
    LeaveError,
    LeaveService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["leave"])
service = LeaveService()


def get_current_user(request: Request):
    return get_request_payload(request)


def tenant_context(payload: dict):
    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant associated with token")
    return tenant_id, user_id


def handle_service_call(fn):
    try:
        return fn()
    except LeaveError as exc:
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
# 1. Leave Types APIs
# ------------------------------------------------------------------
@router.get("/leave-types")
async def get_leave_types(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_leave_types(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 2. Leave Request APIs
# ------------------------------------------------------------------
@router.get("/requests")
async def get_leave_requests(
    request: Request,
    applicant_id: Optional[str] = None,
    status: Optional[str] = None,
    leave_type: Optional[str] = None,
    start_date: Optional[str] = Query(None, alias="from"),
    end_date: Optional[str] = Query(None, alias="to"),
    department: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {
        "applicant_id": applicant_id,
        "status": status,
        "leave_type": leave_type,
        "from": start_date,
        "to": end_date,
        "department": department,
        "q": q,
        "page": page,
        "page_size": page_size
    }
    query_params = {k: v for k, v in query_params.items() if v is not None}

    def action():
        data = service.get_leave_requests(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/requests")
async def apply_leave(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.apply_leave(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

@router.post("/requests/bulk-approve")
async def bulk_approve(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.bulk_approve(tenant_id, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/requests/{requestId}")
async def get_leave_request(requestId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_leave_request(tenant_id, requestId)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/requests/{requestId}/action")
async def leave_action(requestId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.leave_action(tenant_id, requestId, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 3. Leave Balance APIs
# ------------------------------------------------------------------
@router.get("/balances/{employeeId}")
async def get_leave_balances(employeeId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_leave_balances(tenant_id, employeeId)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/history/{employeeId}")
async def get_leave_history(employeeId: str, request: Request, year: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_leave_history(tenant_id, employeeId, year)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/balances/{employeeId}/adjust")
async def adjust_balance(employeeId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.adjust_balance(tenant_id, employeeId, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 4. Holiday APIs
# ------------------------------------------------------------------
@router.get("/holidays")
async def get_holidays(request: Request, year: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_holidays(tenant_id, year)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/blackout-dates")
async def get_blackout_dates(request: Request, year: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_blackout_dates(tenant_id, year)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 5. Leave Policy APIs
# ------------------------------------------------------------------
@router.get("/policies")
async def get_leave_policies(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_leave_policies(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/policies")
async def create_leave_policy(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.create_leave_policy(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

@router.get("/policies/{policyId}")
async def get_leave_policy(policyId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_leave_policy(tenant_id, policyId)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 6. Calendar APIs
# ------------------------------------------------------------------
@router.get("/calendar/team")
async def get_team_calendar(
    request: Request,
    month: int = Query(..., description="Month number 1-12"),
    year: int = Query(..., description="Year"),
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_calendar(tenant_id, None, month, year)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/calendar/my")
async def get_my_calendar(
    request: Request,
    month: int = Query(..., description="Month number 1-12"),
    year: int = Query(..., description="Year"),
    current_user: dict = Depends(get_current_user)
):
    tenant_id, user_id = tenant_context(current_user)
    # Use user_id from token as employee_id for "my" calendar
    
    def action():
        data = service.get_calendar(tenant_id, user_id, month, year)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 7. Encashment APIs
# ------------------------------------------------------------------
@router.post("/encash")
async def request_encashment(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.request_encashment(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 8. Stats APIs
# ------------------------------------------------------------------
@router.get("/stats")
async def get_stats(
    request: Request,
    department: Optional[str] = None,
    location_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {"department": department, "location_id": location_id}
    query_params = {k: v for k, v in query_params.items() if v is not None}
    
    def action():
        data = service.get_stats(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/filters")
async def get_filter_options(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_filter_options(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)
