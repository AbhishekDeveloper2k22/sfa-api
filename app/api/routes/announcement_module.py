from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from typing import Optional, List, Dict, Any

from app.services.announcement_service import (
    AnnouncementError,
    AnnouncementService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["announcement"])
service = AnnouncementService()


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
    except AnnouncementError as exc:
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
# 1. Announcements
# ------------------------------------------------------------------
@router.get("/announcements")
async def get_announcements(
    request: Request,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    target_audience: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {
        "category": category,
        "priority": priority,
        "status": status,
        "target_audience": target_audience,
        "search": search,
        "page": page,
        "size": size
    }
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_announcements(tenant_id, q)))

@router.post("/announcements")
async def create_announcement(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, user_id = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_announcement(tenant_id, payload, user_id)))

@router.get("/announcements/stats")
async def get_stats(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_stats(tenant_id)))

@router.get("/announcements/export")
async def export_announcements(request: Request, format: str = Query("pdf"), current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.export_announcements(tenant_id, format)))

@router.get("/announcements/{id}")
async def get_announcement(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_announcement_by_id(tenant_id, id)))

@router.put("/announcements/{id}")
async def update_announcement(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.update_announcement(tenant_id, id, payload)))

@router.delete("/announcements/{id}")
async def delete_announcement(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.delete_announcement(tenant_id, id)))

# ------------------------------------------------------------------
# 2. Views & Sharing
# ------------------------------------------------------------------
@router.post("/announcements/{id}/view")
async def track_view(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, user_id = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.track_view(tenant_id, id, user_id)))

@router.post("/announcements/{id}/share")
async def share_announcement(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.share_announcement(tenant_id, id, payload)))
