from fastapi import APIRouter, Request, Response
from sfa.middlewares.web_user_middelware import DataProcessor
import traceback
from sfa.utils.response import format_response

router = APIRouter()

@router.post("/all_types")
async def all_types(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.all_types_info(request_data)
        return format_response(
            success=True,
            msg="All types info retrieved successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve all types info",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/users_add")
async def add_users(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.users_add(request_data)
        return format_response(
            success=True,
            msg="User added successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to add user",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )
    
@router.post("/user_list")
async def users(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.users_list(request_data)
        return format_response(
            success=True,
            msg="User list retrieved successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve user list",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/check_user_exists")
async def check_user_exists(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.check_user_exists(request_data)
        return format_response(
            success=True,
            msg="User exists check completed successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to check user exists",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/user_details")
async def user_details(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.user_details(request_data)
        return format_response(
            success=True,
            msg="User details retrieved successfully",
            statuscode=200,
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve user details",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )
