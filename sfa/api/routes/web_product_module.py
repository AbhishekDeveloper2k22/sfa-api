from fastapi import APIRouter, Request, UploadFile, File, Form
from sfa.middlewares.web_product_middleware import ProductDataProcessor
import traceback
from sfa.utils.response import format_response

router = APIRouter()

@router.post("/product_add")
async def add_product(request: Request):
    request_data = await request.json()
    instance = ProductDataProcessor()
    try:
        result = instance.product_add(request_data)
        return format_response(
            success=True,
            msg="Product added successfully",
            statuscode=200,
            data=result.get("data", {})
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
async def product_list(request: Request):
    request_data = await request.json()
    instance = ProductDataProcessor()
    try:
        result = instance.products_list(request_data)
        return format_response(
            success=True,
            msg="Product list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
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
            data=result.get("data", {})
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
        return format_response(
            success=True,
            msg="Product image updated successfully",
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


