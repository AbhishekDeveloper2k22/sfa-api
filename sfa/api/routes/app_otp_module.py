from fastapi import APIRouter, Request, Depends
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from sfa.services.app_otp_services import AppOTPService
import traceback

router = APIRouter()


@router.post("/send_otp")
async def send_otp(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        try:
            body = await request.json()
        except Exception as e:
            return format_response(success=False, msg="Invalid JSON body", statuscode=400, data={"error": {"code": "INVALID_JSON", "details": str(e)}})
        user_id = current_user.get("user_id")
        target = body.get("target")         # phone/email
        purpose = body.get("purpose")       # login/password_reset/... (common API)
        channel = body.get("channel", "sms")
        ttl_minutes = 5
        entity_type = body.get("entity_type")  # e.g., "order", "expense"

        service = AppOTPService()
        result = service.send_otp(target=target, purpose=purpose, channel=channel, ttl_minutes=ttl_minutes, entity_type=entity_type, user_id=user_id)
        if not result.get("success"):
            return format_response(success=False, msg=result.get("message", "Failed to send OTP"), statuscode=400, data={"error": result.get("error", {})})
        return format_response(success=True, msg="OTP sent successfully", statuscode=200, data=result.get("data", {}))
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(success=False, msg="Internal server error", statuscode=500, data={"error": {"code": "SERVER_ERROR", "details": str(e), "traceback": tb}})


@router.post("/verify_otp")
async def verify_otp(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        try:
            body = await request.json()
        except Exception as e:
            return format_response(success=False, msg="Invalid JSON body", statuscode=400, data={"error": {"code": "INVALID_JSON", "details": str(e)}})
        target = body.get("target")
        purpose = body.get("purpose")
        otp = body.get("otp")

        service = AppOTPService()
        result = service.verify_otp(target=target, purpose=purpose, otp=otp)
        if not result.get("success"):
            return format_response(success=False, msg=result.get("message", "OTP verification failed"), statuscode=400, data={"error": result.get("error", {})})
        return format_response(success=True, msg="OTP verified successfully", statuscode=200, data=result.get("data", {}))
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(success=False, msg="Internal server error", statuscode=500, data={"error": {"code": "SERVER_ERROR", "details": str(e), "traceback": tb}})


