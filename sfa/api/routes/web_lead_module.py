from fastapi import APIRouter, Request, UploadFile, File, Form
from sfa.middlewares.web_lead_middleware import LeadDataProcessor
import traceback
from sfa.utils.response import format_response

router = APIRouter()

@router.post("/lead_add")
async def lead_add(request: Request):
    request_data = await request.json()
    instance = LeadDataProcessor()
    try:
        result = instance.lead_add(request_data)
        return format_response(
            success=True,
            msg="Lead added successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to add lead",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/lead_list")
async def lead_list(request: Request):
    request_data = await request.json()
    instance = LeadDataProcessor()
    try:
        result = instance.leads_list(request_data)
        return format_response(
            success=True,
            msg="Lead list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve lead list",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/lead_details")
async def lead_details(request: Request):
    request_data = await request.json()
    instance = LeadDataProcessor()
    try:
        result = instance.lead_details(request_data)
        return format_response(
            success=True,
            msg="Lead details retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve lead details",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/lead_image")
async def lead_image(lead_id: str = Form(...), file: UploadFile = File(...)):
    instance = LeadDataProcessor()
    try:
        result = instance.lead_image_update(lead_id, file)
        return format_response(
            success=True,
            msg="Lead image updated successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to update lead image",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )


