from fastapi import APIRouter, Request, Depends, Query
from typing import Optional
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_master_services import AppMasterService

router = APIRouter()

@router.get("/categories")
async def get_categories(
    status: Optional[str] = Query(None, description="Filter categories by status"),
    limit: int = Query(200, ge=1, le=500, description="Max number of categories"),
    current_user: dict = Depends(get_current_user)
):
    try:
        service = AppMasterService()
        result = service.get_categories(status=status, limit=limit)
        if not result.get("success"):
            return format_response(success=False, msg=result.get("message", "Failed to get categories"), statuscode=400, data={"error": result.get("error", {})})
        return format_response(success=True, msg="Categories retrieved successfully", statuscode=200, data=result.get("data", {}))
    except Exception:
        return format_response(success=False, msg="Internal server error", statuscode=500, data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}})

@router.post("/products")
async def get_products(request: Request, current_user: dict = Depends(get_current_user)):
    """Get products, optionally filter by category_id in JSON body"""
    try:
        body = await request.json()
        category_id = body.get("category_id")  # optional
        status = body.get("status")
        limit = body.get("limit", 200)
        try:
            limit = int(limit)
        except Exception:
            limit = 200
        service = AppMasterService()
        result = service.get_products(category_id=category_id, status=status, limit=limit)
        if not result.get("success"):
            return format_response(success=False, msg=result.get("message", "Failed to get products"), statuscode=400, data={"error": result.get("error", {})})
        return format_response(success=True, msg="Products retrieved successfully", statuscode=200, data=result.get("data", {}))
    except Exception:
        return format_response(success=False, msg="Internal server error", statuscode=500, data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}})
