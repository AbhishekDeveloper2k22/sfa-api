from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File, Form
from trust_rewards.middlewares.web_category_middleware import CategoryDataProcessor
import traceback

router = APIRouter()

@router.post("/category_add")
async def add_category(request: Request):
    request_data = await request.json()
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.category_add(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/category_image")
async def category_image(category_id: str = Form(...), file: UploadFile = File(...)):
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.category_image_update(category_id, file)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})
    
@router.post("/category_list")
async def categories_list(request: Request):
    request_data = await request.json()
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.categories_list(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/check_category_exists")
async def check_category_exists(request: Request):
    request_data = await request.json()
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.check_category_exists(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/category_details")
async def category_details(request: Request):
    request_data = await request.json()
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.category_details(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})
