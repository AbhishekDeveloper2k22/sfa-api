from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from typing import Optional, List, Dict, Any

from app.services.document_service import (
    DocumentError,
    DocumentService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["document"])
service = DocumentService()


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
    except DocumentError as exc:
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
# 2. Documents
# ------------------------------------------------------------------
@router.get("/documents")
async def get_documents(
    request: Request,
    category_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    search: Optional[str] = None,
    expiring_within_days: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {
        "category_id": category_id,
        "employee_id": employee_id,
        "search": search,
        "expiring_within_days": expiring_within_days
    }
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_documents(tenant_id, q)))

@router.post("/documents")
async def create_document(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_document(tenant_id, payload)))

@router.get("/documents/{id}")
async def get_document(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_document_by_id(tenant_id, id)))

@router.put("/documents/{id}")
async def update_document(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.update_document(tenant_id, id, payload)))

@router.delete("/documents/{id}")
async def delete_document(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.delete_document(tenant_id, id)))

# ------------------------------------------------------------------
# 3. Versions
# ------------------------------------------------------------------
@router.get("/documents/{id}/versions")
async def get_document_versions(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_document_versions(tenant_id, id)))

@router.post("/documents/{id}/versions")
async def upload_document_version(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.upload_document_version(tenant_id, id, payload)))

@router.post("/documents/{id}/versions/{versionId}/restore")
async def restore_document_version(id: str, versionId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.restore_document_version(tenant_id, id, versionId)))

# ------------------------------------------------------------------
# 4. Downloads & Extensions
# ------------------------------------------------------------------
@router.get("/documents/{id}/download")
async def get_download_url(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_download_url(tenant_id, id)))

@router.post("/documents/{id}/extend")
async def extend_expiry(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.extend_expiry(tenant_id, id, payload)))

# ------------------------------------------------------------------
# 5. Expiring & Misc
# ------------------------------------------------------------------
@router.get("/expiring")
async def get_expiring_documents(
    request: Request,
    days: int = Query(30),
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_expiring_documents(tenant_id, days)))

@router.post("/upload/init")
async def init_upload(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.init_upload(tenant_id)))

@router.post("/upload/{uploadId}/complete")
async def complete_upload(uploadId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.complete_upload(tenant_id, uploadId)))

@router.get("/stats")
async def get_stats(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_stats(tenant_id)))

@router.get("/filter-options")
async def get_filter_options(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_filter_options(tenant_id)))
