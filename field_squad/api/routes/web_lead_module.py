from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from field_squad.middlewares.web_lead_middleware import LeadDataProcessor
import traceback

router = APIRouter()

@router.post("/lead_add")
async def lead_add(request: Request):
    request_data = await request.json()
    instance = LeadDataProcessor()
    try:
        result = instance.lead_add(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/lead_list")
async def lead_list(request: Request):
    request_data = await request.json()
    instance = LeadDataProcessor()
    try:
        result = instance.leads_list(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/lead_details")
async def lead_details(request: Request):
    request_data = await request.json()
    instance = LeadDataProcessor()
    try:
        result = instance.lead_details(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/lead_image")
async def lead_image(lead_id: str = Form(...), file: UploadFile = File(...)):
    instance = LeadDataProcessor()
    try:
        result = instance.lead_image_update(lead_id, file)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})


