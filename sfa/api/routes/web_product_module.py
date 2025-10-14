from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from sfa.middlewares.web_product_middleware import ProductDataProcessor
import traceback
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user

router = APIRouter()

@router.post("/product_add")
async def add_product(request: Request, current_user: dict = Depends(get_current_user)):
    request_data = await request.json()
    request_data['created_by'] = current_user.get('user_id')
    print("request_data", request_data)
    instance = ProductDataProcessor()
    try:
        result = instance.product_add(request_data)
        
        # Check if the service returned an error
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to add product"),
                statuscode=400,
                data=result
            )
        
        return format_response(
            success=True,
            msg=result.get("message", "Product added successfully"),
            statuscode=200,
            data={
                "product_id": result.get("inserted_id"),
                "product_code": result.get("product_code")
            }
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to add product",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/product_list")
async def product_list(request: Request, current_user: dict = Depends(get_current_user)):
    request_data = await request.json()
    request_data['created_by'] = current_user.get('user_id')
    print("request_data", request_data)
    instance = ProductDataProcessor()
    try:
        result = instance.products_list(request_data)
        return format_response(
            success=True,
            msg="Product list retrieved successfully",
            statuscode=200,
            data=result if isinstance(result, dict) else {}
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve product list",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/product_details")
async def product_details(request: Request):
    request_data = await request.json()
    instance = ProductDataProcessor()
    try:
        result = instance.product_details(request_data)
        return format_response(
            success=True,
            msg="Product details retrieved successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve product details",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/product_image")
async def product_image(product_id: str = Form(...), file: UploadFile = File(...)):
    instance = ProductDataProcessor()
    try:
        result = instance.product_image_update(product_id, file)
        
        # Check if the service returned an error
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to update product image"),
                statuscode=400,
                data=result.get("error", {})
            )
        
        return format_response(
            success=True,
            msg=result.get("message", "Product image updated successfully"),
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to update product image",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )


