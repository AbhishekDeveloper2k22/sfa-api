from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body, UploadFile, File
from typing import Optional, List, Dict, Any
from fastapi.responses import Response

from app.services.policy_service import (
    PolicyError,
    PolicyService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["policy"])
service = PolicyService()


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
    except PolicyError as exc:
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
# 1. Policies
# ------------------------------------------------------------------
@router.get("/policies")
async def get_policies(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {"category": category, "search": search, "status": status}
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_policies(tenant_id, q)))

@router.post("/policies")
async def create_policy(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, user_id = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_policy(tenant_id, payload, user_id)))

@router.get("/policies/stats")
async def get_stats(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_stats(tenant_id)))

@router.post("/policies/export")
async def export_policies(request: Request, format: str = Query("pdf"), current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.export_policies(tenant_id, format)))

@router.get("/policies/{id}")
async def get_policy(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_policy_by_id(tenant_id, id)))

@router.put("/policies/{id}")
async def update_policy(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, user_id = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.update_policy(tenant_id, id, payload, user_id)))

@router.delete("/policies/{id}")
async def delete_policy(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.delete_policy(tenant_id, id)))

# ------------------------------------------------------------------
# 2. Attachments
# ------------------------------------------------------------------
@router.post("/policies/{id}/attachments")
async def add_attachment(id: str, request: Request, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    # Mocking file storage url
    file_info = {
        "filename": file.filename,
        "size": "1MB", # Mock size
        "url": f"/mock/storage/{file.filename}"
    }
    return handle_service_call(lambda: format_response(True, 200, service.add_attachment(tenant_id, id, file_info)))

@router.delete("/policies/{policy_id}/attachments/{attachment_id}")
async def remove_attachment(policy_id: str, attachment_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.remove_attachment(tenant_id, policy_id, attachment_id)))

# ------------------------------------------------------------------
# 3. Downloads & Actions
# ------------------------------------------------------------------
@router.get("/policies/{id}/download")
async def download_policy(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    # Return raw PDF content
    content = service.download_policy(tenant_id, id)
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=policy_{id}.pdf"})

@router.post("/policies/{id}/email")
async def email_policy(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.email_policy(tenant_id, id, payload)))
