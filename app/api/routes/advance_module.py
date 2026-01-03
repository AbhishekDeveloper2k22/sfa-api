from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from typing import Optional, List

from app.services.advance_service import (
    AdvanceError,
    AdvanceService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["advance"])
service = AdvanceService()


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
    except AdvanceError as exc:
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
# 1. Advance Request APIs
# ------------------------------------------------------------------
@router.get("/")
async def get_advances(
    request: Request,
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    department: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    query_params = {
        "status": status,
        "employee_id": employee_id,
        "department": department,
        "search": search
    }
    query_params = {k: v for k, v in query_params.items() if v is not None}

    def action():
        data = service.get_advances(tenant_id, query_params)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/")
async def create_advance(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.create_advance(tenant_id, payload, actor)
        return format_response(success=True, statuscode=201, data=data)

    return handle_service_call(action)

# Custom routes before /{id} to avoid conflicts if ID can be anything
# But here custom routes are things like /employees ... better put them first.

# ------------------------------------------------------------------
# 2. Reference Data APIs (Placed first to avoid ID conflict)
# ------------------------------------------------------------------
@router.get("/employees")
async def get_employees(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_employees(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/advance-reasons")
async def get_reasons(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_reasons(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/payment-modes")
async def get_payment_modes(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_payment_modes(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.get("/departments")
async def get_departments(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_departments(tenant_id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

# ------------------------------------------------------------------
# 3. Validation APIs
# ------------------------------------------------------------------
@router.get("/employees/{employeeId}/active-advance")
async def check_active_advance(employeeId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.check_active_advance(tenant_id, employeeId)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)


# ------------------------------------------------------------------
# 1. Advance Request APIs (ID specific)
# ------------------------------------------------------------------
@router.get("/{id}")
async def get_advance_by_id(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_advance_by_id(tenant_id, id)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/{id}/approve")
async def approve_advance(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.approve_advance(tenant_id, id, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/{id}/reject")
async def reject_advance(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.reject_advance(tenant_id, id, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/{id}/disburse")
async def disburse_advance(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.disburse_advance(tenant_id, id, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)

@router.post("/{id}/repayments")
async def record_repayment(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.record_repayment(tenant_id, id, payload, actor)
        return format_response(success=True, statuscode=200, data=data)

    return handle_service_call(action)
