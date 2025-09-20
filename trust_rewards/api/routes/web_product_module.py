from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from trust_rewards.middlewares.web_product_middleware import ProductDataProcessor
import traceback

router = APIRouter()

@router.post("/product_add")
async def add_product(request: Request):
    request_data = await request.json()
    instance = ProductDataProcessor()
    try:
        result = instance.product_add(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/product_list")
async def product_list(request: Request):
    request_data = await request.json()
    instance = ProductDataProcessor()
    try:
        result = instance.products_list(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/product_details")
async def product_details(request: Request):
    request_data = await request.json()
    instance = ProductDataProcessor()
    try:
        result = instance.product_details(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/product_image")
async def product_image(product_id: str = Form(...), file: UploadFile = File(...)):
    instance = ProductDataProcessor()
    try:
        result = instance.product_image_update(product_id, file)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})


