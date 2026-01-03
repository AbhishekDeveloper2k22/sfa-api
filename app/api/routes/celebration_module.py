from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from typing import Optional, List, Dict, Any

from app.services.celebration_service import (
    CelebrationError,
    CelebrationService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["celebration"])
service = CelebrationService()


def get_current_user(request: Request):
    return get_request_payload(request)


def tenant_context(payload: dict):
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant associated with token")
    return tenant_id, payload.get("user_id")


def handle_service_call(fn):
    try:
        return fn()
    except CelebrationError as exc:
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
# 1. Celebrations
# ------------------------------------------------------------------
@router.get("/celebrations")
async def get_celebrations(
    request: Request,
    type: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {
        "type": type,
        "department": department,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
        "search": search
    }
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_celebrations(tenant_id, q)))

@router.post("/celebrations")
async def create_celebration(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_celebration(tenant_id, payload)))

@router.get("/celebrations/today")
async def get_today_celebrations(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_today_celebrations(tenant_id)))

@router.get("/celebrations/week")
async def get_weekly_celebrations(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_weekly_celebrations(tenant_id)))

@router.post("/celebrations/send-all-wishes")
async def send_all_wishes(
    request: Request,
    date: str = Query(None), # Optional date query param
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    q = {"date": date} if date else {}
    return handle_service_call(lambda: format_response(True, 200, service.send_all_wishes(tenant_id, q, payload)))

@router.get("/celebrations/stats")
async def get_stats(request: Request, period: str = Query("month"), current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_stats(tenant_id, period)))

@router.get("/celebrations/export")
async def export_celebrations(request: Request, format: str = Query("csv"), current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.export_celebrations(tenant_id, format)))

@router.get("/celebrations/{id}")
async def get_celebration(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_celebration_by_id(tenant_id, id)))

@router.put("/celebrations/{id}")
async def update_celebration(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.update_celebration(tenant_id, id, payload)))

@router.delete("/celebrations/{id}")
async def delete_celebration(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.delete_celebration(tenant_id, id)))

@router.post("/celebrations/{id}/send-wish")
async def send_wish(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.send_wish(tenant_id, id, payload)))
