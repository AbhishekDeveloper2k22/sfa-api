from fastapi import APIRouter, Request, UploadFile, File, Form
from sfa.middlewares.web_customer_middleware import CustomerDataProcessor
import traceback
from sfa.utils.response import format_response

router = APIRouter()

@router.post("/customer_add")
async def customer_add(request: Request):
    request_data = await request.json()
    instance = CustomerDataProcessor()
    try:
        result = instance.customer_add(request_data)
        return format_response(
            success=True,
            msg="Customer added successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to add customer",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/customer_list")
async def customer_list(request: Request):
    request_data = await request.json()
    instance = CustomerDataProcessor()
    try:
        result = instance.customers_list(request_data)
        return format_response(
            success=True,
            msg="Customer list retrieved successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve customer list",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/customer_details")
async def customer_details(request: Request):
    request_data = await request.json()
    instance = CustomerDataProcessor()
    try:
        result = instance.customer_details(request_data)
        return format_response(
            success=True,
            msg="Customer details retrieved successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve customer details",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/customer_image")
async def customer_image(customer_id: str = Form(...), file: UploadFile = File(...)):
    instance = CustomerDataProcessor()
    try:
        result = instance.customer_image_update(customer_id, file)
        return format_response(
            success=True,
            msg="Customer image updated successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to update customer image",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )


