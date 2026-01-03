from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from typing import Optional, List, Dict, Any

from app.services.asset_service import (
    AssetError,
    AssetService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(tags=["asset"])
service = AssetService()


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
    except AssetError as exc:
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
# 1. Categories & Locations
# ------------------------------------------------------------------
@router.get("/categories")
async def get_categories(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_categories(tenant_id)))

@router.get("/locations")
async def get_locations(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_locations(tenant_id)))

# ------------------------------------------------------------------
# 2. Assets
# ------------------------------------------------------------------
@router.get("/assets")
async def get_assets(
    request: Request,
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {"status": status, "category": category, "search": search}
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_assets(tenant_id, q)))

@router.post("/assets")
async def create_asset(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_asset(tenant_id, payload)))

@router.get("/assets/{id}")
async def get_asset(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_asset_by_id(tenant_id, id)))

@router.put("/assets/{id}")
async def update_asset(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.update_asset(tenant_id, id, payload)))

@router.post("/assets/{id}/assign")
async def assign_asset(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.assign_asset(tenant_id, id, payload)))

@router.post("/assets/{id}/return")
async def return_asset(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.return_asset(tenant_id, id)))

@router.post("/assets/{id}/dispose")
async def dispose_asset(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.dispose_asset(tenant_id, id, payload)))

# ------------------------------------------------------------------
# 3. Requests
# ------------------------------------------------------------------
@router.get("/requests")
async def get_requests(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_requests(tenant_id)))

@router.post("/requests")
async def create_request(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_request(tenant_id, payload, actor)))

@router.post("/requests/{id}/{action}")
async def request_action(id: str, action: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.perform_request_action(tenant_id, id, action)))

# ------------------------------------------------------------------
# 4. Maintenance
# ------------------------------------------------------------------
@router.get("/maintenance")
async def get_maintenance(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_maintenance_logs(tenant_id)))

@router.post("/maintenance")
async def create_maintenance(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_maintenance_log(tenant_id, payload)))

@router.post("/maintenance/{id}/complete")
async def complete_maintenance(id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.complete_maintenance_log(tenant_id, id, payload)))

# ------------------------------------------------------------------
# 5. Reports
# ------------------------------------------------------------------
@router.get("/depreciation")
async def get_depreciation(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_depreciation(tenant_id)))

@router.get("/stats")
async def get_stats(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_stats(tenant_id)))

@router.get("/filter-options")
async def get_filter_options(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_filter_options(tenant_id)))
