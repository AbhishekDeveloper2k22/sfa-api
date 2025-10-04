from fastapi import APIRouter, Request, Depends
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_lead_services import AppLeadService
import traceback

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


