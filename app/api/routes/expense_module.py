from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from typing import Optional, List, Dict, Any

from app.services.expense_service import (
    ExpenseError,
    ExpenseService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["expense"])
service = ExpenseService()


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
    except ExpenseError as exc:
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
# 1. Categories
# ------------------------------------------------------------------
@router.get("/categories")
async def get_categories(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_categories(tenant_id)))

# ------------------------------------------------------------------
# 2. Claims
# ------------------------------------------------------------------
@router.get("/claims")
async def get_claims(
    request: Request,
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {"status": status, "employee_id": employee_id}
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_claims(tenant_id, q)))

@router.post("/claims")
async def create_claim(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_claim(tenant_id, payload)))

@router.get("/claims/{id}")
async def get_claim(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_claim_by_id(tenant_id, id)))

@router.put("/claims/{id}")
async def update_claim(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.update_claim(tenant_id, id, payload)))

@router.post("/claims/{id}/submit")
async def submit_claim(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.submit_claim(tenant_id, id)))

@router.post("/claims/{id}/settle")
async def settle_claim(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.perform_claim_action(tenant_id, id, "settle", {}, actor)))

@router.post("/claims/{id}/preview")
async def preview_claim(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.preview_claim(tenant_id, id)))

@router.post("/claims/{id}/{action}")
async def claim_action(id: str, action: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.perform_claim_action(tenant_id, id, action, payload, actor)))

# ------------------------------------------------------------------
# 3. Travel
# ------------------------------------------------------------------
@router.get("/travel")
async def get_travel_requests(
    request: Request,
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {"status": status, "employee_id": employee_id}
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_travel_requests(tenant_id, q)))

@router.post("/travel")
async def create_travel_request(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_travel_request(tenant_id, payload)))

@router.get("/travel/{id}")
async def get_travel_request(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_travel_request(tenant_id, id)))

@router.post("/travel/{id}/{action}")
async def travel_action(id: str, action: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.perform_travel_action(tenant_id, id, action, payload)))

# ------------------------------------------------------------------
# 4. Advances
# ------------------------------------------------------------------
@router.get("/advances")
async def get_advances(
    request: Request,
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {"status": status, "employee_id": employee_id}
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_advances(tenant_id, q)))

@router.post("/advances")
async def create_advance(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_advance(tenant_id, payload)))

@router.post("/advances/{id}/disburse")
async def disburse_advance(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.disburse_advance(tenant_id, id)))

# ------------------------------------------------------------------
# 5. Reports & Misc
# ------------------------------------------------------------------
@router.get("/ledger")
async def get_ledger(
    request: Request,
    employee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {"employee_id": employee_id}
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_ledger(tenant_id, q)))

@router.get("/stats")
async def get_stats(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_stats(tenant_id)))

@router.post("/export")
async def export_expenses(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.export_expenses(tenant_id, {})))

@router.post("/receipts/{uploadId}/extract")
async def extract_receipt(uploadId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.extract_receipt(tenant_id, uploadId)))

@router.get("/filter-options")
async def get_filter_options(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_filter_options(tenant_id)))
