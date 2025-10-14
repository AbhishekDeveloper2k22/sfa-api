from fastapi import APIRouter, Request, UploadFile, File, Form
from sfa.middlewares.web_customer_middleware import CustomerDataProcessor
import traceback
import json
from sfa.utils.response import format_response

router = APIRouter()

@router.post("/customer_add")
async def customer_add(request: Request):
    # Read body first to preserve it for error messages
    body = await request.body()
    try:
        request_data = json.loads(body)
    except json.JSONDecodeError as json_error:
        return format_response(
            success=False,
            msg="Invalid JSON in request body",
            statuscode=400,
            data={
                "error": f"JSONDecodeError: {str(json_error)}",
                "error_location": f"line {json_error.lineno}, column {json_error.colno}, position {json_error.pos}",
                "raw_body_preview": body.decode('utf-8', errors='replace')[:500] if body else "<empty>",
                "hint": "Check if the JSON is valid and not concatenated with other data"
            }
        )
    
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
    body = await request.body()
    try:
        request_data = json.loads(body)
    except json.JSONDecodeError as json_error:
        return format_response(
            success=False,
            msg="Invalid JSON in request body",
            statuscode=400,
            data={
                "error": f"JSONDecodeError: {str(json_error)}",
                "error_location": f"line {json_error.lineno}, column {json_error.colno}, position {json_error.pos}",
                "raw_body_preview": body.decode('utf-8', errors='replace')[:500] if body else "<empty>",
                "hint": "Check if the JSON is valid and not concatenated with other data"
            }
        )
    
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
    body = await request.body()
    try:
        request_data = json.loads(body)
    except json.JSONDecodeError as json_error:
        return format_response(
            success=False,
            msg="Invalid JSON in request body",
            statuscode=400,
            data={
                "error": f"JSONDecodeError: {str(json_error)}",
                "error_location": f"line {json_error.lineno}, column {json_error.colno}, position {json_error.pos}",
                "raw_body_preview": body.decode('utf-8', errors='replace')[:500] if body else "<empty>",
                "hint": "Check if the JSON is valid and not concatenated with other data"
            }
        )
    
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


