from fastapi import APIRouter, Request, Response, UploadFile, File, Form
from sfa.middlewares.web_category_middleware import CategoryDataProcessor
import traceback
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from fastapi import Depends

router = APIRouter()

@router.post("/category_add")
async def add_category(request: Request, current_user: dict = Depends(get_current_user)):
    request_data = await request.json()
    request_data['created_by'] = current_user.get('user_id')
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.category_add(request_data)
        return format_response(
            success=True, 
            msg="Category added successfully", 
            statuscode=200, 
            data={
                "category_id": result.get("inserted_id"),
                "category_code": result.get("category_code")
            } if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to add category",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/category_image")
async def category_image(category_id: str = Form(...), file: UploadFile = File(...)):
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.category_image_update(category_id, file)
        
        # Check if the service returned an error
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to update category image"),
                statuscode=400,
                data=result.get("error", {})
            )
        
        return format_response(
            success=True,
            msg=result.get("message", "Category image updated successfully"), 
            statuscode=200, 
            data=result.get("data", {})
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to update category image",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )
    
@router.post("/category_list")
async def categories_list(request: Request, current_user: dict = Depends(get_current_user)):
    request_data = await request.json()
    request_data['created_by'] = current_user.get('user_id')
    print("request_data", request_data)
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.categories_list(request_data)
        return format_response(
            success=True, 
            msg="Categories list retrieved successfully", 
            statuscode=200, 
            data=result if isinstance(result, dict) else {}
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve categories list",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/check_category_exists")
async def check_category_exists(request: Request):
    request_data = await request.json()
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.check_category_exists(request_data)
        return format_response(
            success=True, 
            msg="Category exists check completed successfully", 
            statuscode=200, 
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to check category exists",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )

@router.post("/category_details")
async def category_details(request: Request):
    request_data = await request.json()
    instanceClass = CategoryDataProcessor()
    try:
        result = instanceClass.category_details(request_data)
        return format_response(
            success=True, 
            msg="Category details retrieved successfully", 
            statuscode=200, 
            data=result.get("data", {}) if isinstance(result, dict) else result
        )
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Failed to retrieve category details",
            statuscode=500,
            data={"error": str(e), "traceback": tb}
        )
