from fastapi import APIRouter, Request, HTTPException, Depends
from trust_rewards.services.app_master_services import AppMasterService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
import traceback

router = APIRouter()

@router.post("/categories_list")
async def get_categories_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get list of active categories for app users"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = AppMasterService()
        result = service.get_categories_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get categories list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Categories list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/sub_categories_list")
async def get_sub_categories_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get list of active sub-categories for a specific category"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        # Validate required category_id
        if not request_data.get('category_id'):
            return format_response(
                success=False,
                msg="category_id is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "category_id is mandatory"
                    }
                }
            )
        
        service = AppMasterService()
        result = service.get_sub_categories_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get sub-categories list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Sub-categories list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/products_list")
async def get_products_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get list of active products for specific category and sub-category"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        # Validate required parameters
        if not request_data.get('category_id'):
            return format_response(
                success=False,
                msg="category_id is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "category_id is mandatory"
                    }
                }
            )
        
        if not request_data.get('sub_category_id'):
            return format_response(
                success=False,
                msg="sub_category_id is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "sub_category_id is mandatory"
                    }
                }
            )
        
        service = AppMasterService()
        result = service.get_products_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get products list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Products list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/gift_list")
async def get_gift_master_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get list of active gifts for app users"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = AppMasterService()
        result = service.get_gift_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get gift master list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Gift master list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/product_detail")
async def get_product_detail(request: Request, current_user: dict = Depends(get_current_user)):
    """Get details of a specific product for app users"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        # Validate required product_id
        if not request_data.get('product_id'):
            return format_response(
                success=False,
                msg="product_id is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "product_id is mandatory"
                    }
                }
            )
        
        service = AppMasterService()
        result = service.get_product_detail(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get product detail"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Product detail retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/gift_detail")
async def get_gift_detail(request: Request, current_user: dict = Depends(get_current_user)):
    """Get details of a specific gift for app users"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        # Validate required gift_id
        if not request_data.get('gift_id'):
            return format_response(
                success=False,
                msg="gift_id is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "gift_id is mandatory"
                    }
                }
            )
        
        service = AppMasterService()
        result = service.get_gift_detail(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get gift detail"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Gift detail retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )
