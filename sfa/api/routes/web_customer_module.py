from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from sfa.middlewares.web_customer_middleware import CustomerDataProcessor
import traceback

router = APIRouter()

@router.post("/customer_add")
async def customer_add(request: Request):
    request_data = await request.json()
    instance = CustomerDataProcessor()
    try:
        result = instance.customer_add(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/customer_list")
async def customer_list(request: Request):
    request_data = await request.json()
    instance = CustomerDataProcessor()
    try:
        result = instance.customers_list(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/customer_details")
async def customer_details(request: Request):
    request_data = await request.json()
    instance = CustomerDataProcessor()
    try:
        result = instance.customer_details(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/customer_image")
async def customer_image(customer_id: str = Form(...), file: UploadFile = File(...)):
    instance = CustomerDataProcessor()
    try:
        result = instance.customer_image_update(customer_id, file)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})


