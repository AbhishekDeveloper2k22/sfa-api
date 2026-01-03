from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from typing import Optional, List, Dict, Any

from app.services.holiday_service import (
    HolidayError,
    HolidayService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["holiday"])
service = HolidayService()


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
    except HolidayError as exc:
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
# 1. Holidays
# ------------------------------------------------------------------
@router.get("/holidays")
async def get_holidays(
    request: Request,
    type: Optional[str] = None,
    year: Optional[str] = None,
    month: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {
        "type": type,
        "year": year,
        "month": month,
        "status": status,
        "search": search
    }
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_holidays(tenant_id, q)))

@router.post("/holidays")
async def create_holiday(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_holiday(tenant_id, payload)))

@router.get("/holidays/calendar")
async def get_calendar(
    request: Request,
    year: str = Query(...),
    month: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_calendar(tenant_id, year, month)))

@router.get("/holidays/validate")
async def validate_date(
    request: Request,
    date: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.validate_date(tenant_id, date)))

@router.get("/holidays/stats")
async def get_stats(request: Request, year: Optional[str] = Query(None), current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_stats(tenant_id, year)))

@router.get("/holidays/export")
async def export_holidays(request: Request, format: str = Query("csv"), current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.export_holidays(tenant_id, format)))

@router.get("/holidays/{id}")
async def get_holiday(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_holiday_by_id(tenant_id, id)))

@router.put("/holidays/{id}")
async def update_holiday(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.update_holiday(tenant_id, id, payload)))

@router.delete("/holidays/{id}")
async def delete_holiday(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.delete_holiday(tenant_id, id)))
