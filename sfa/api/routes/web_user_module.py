from fastapi import APIRouter, Request, Response, HTTPException
from sfa.middlewares.web_user_middelware import DataProcessor
import traceback

router = APIRouter()

@router.post("/all_types")
async def all_types(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.all_types_info(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/users_add")
async def add_users(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.users_add(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})
    
@router.post("/user_list")
async def users(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.users_list(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/check_user_exists")
async def check_user_exists(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.check_user_exists(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

@router.post("/user_details")
async def user_details(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.user_details(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})
