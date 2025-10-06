from fastapi import APIRouter, Request, Depends, Form, File, UploadFile
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_lead_services import AppLeadService
import traceback
import os

router = APIRouter()


@router.post("/create_lead")
async def create_lead(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        payload = await request.json()
        user_id = current_user.get("user_id")
        service = AppLeadService()
        result = service.create_lead(user_id=user_id, payload=payload)
        if not result.get("success"):
            return format_response(success=False, msg=result.get("message", "Failed to create lead"), statuscode=400, data={"error": result.get("error", {})})
        return format_response(success=True, msg="Lead created successfully", statuscode=200, data=result.get("data", {}))
    except Exception as e:
        print(traceback.format_exc())
        return format_response(success=False, msg=f"Internal server error: {str(e)}", statuscode=500, data={"error": {"code": "SERVER_ERROR", "details": str(e)}})


@router.post("/upload_image")
async def upload_lead_image(
    lead_id: str = Form(..., description="Lead ID"),
    image: UploadFile = File(..., description="Image file"),
    current_user: dict = Depends(get_current_user)
):
    """Upload image for a specific lead"""
    try:
        user_id = current_user.get("user_id")
        
        # Validate lead_id
        if not lead_id:
            return format_response(
                success=False,
                msg="Lead ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Lead ID is required"
                    }
                }
            )
        
        # Validate file
        if not image:
            return format_response(
                success=False,
                msg="Image file is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Image file is required"
                    }
                }
            )
        
        # Validate file size (max 5MB)
        if image.size and image.size > 5 * 1024 * 1024:
            return format_response(
                success=False,
                msg="File size too large",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "File size must be less than 5MB"
                    }
                }
            )
        
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_extension = os.path.splitext(image.filename)[1].lower()
        if file_extension not in allowed_extensions:
            return format_response(
                success=False,
                msg="Invalid file type",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"File type must be one of: {', '.join(allowed_extensions)}"
                    }
                }
            )
        
        service = AppLeadService()
        result = service.upload_lead_image(
            user_id=user_id,
            lead_id=lead_id,
            image_file=image
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Image upload failed"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Lead image uploaded successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        print(traceback.format_exc())
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": "An unexpected error occurred"
                }
            }
        )


