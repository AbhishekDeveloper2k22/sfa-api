from fastapi import APIRouter, Request

from app.services.onboarding_user_services import TenantOnboardingOTPService
from app.services.user_auth_services import UserAuthService
from app.utils.response import format_response

router = APIRouter()


@router.post("/login")
async def login(request: Request):
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        if not email or not password:
            return format_response(
                success=False,
                msg="Email and password are required.",
                statuscode=400,
                data={"user": None, "message": "Email and password are required."},
            )
        service = UserAuthService()
        result = service.login(email, password)
        if not result:
            return format_response(
                success=False,
                msg="Invalid email or password.",
                statuscode=401,
                data={"user": None, "message": "Invalid email or password."},
            )
        return format_response(
            success=True,
            msg="Login successful",
            statuscode=200,
            data=result,
        )
    except Exception:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"user": None, "message": "Something went wrong."},
        )


@router.post("/tenant-onboarding/send-otp")
async def send_tenant_onboarding_otp(request: Request):
    try:
        body = await request.json()
        email = body.get("email")
        if not email:
            return format_response(
                success=False,
                msg="Email is required.",
                statuscode=400,
                data=None,
            )
        otp_service = TenantOnboardingOTPService()
        result = otp_service.send_otp(email=email)
        return format_response(
            success=True,
            msg="OTP sent successfully.",
            statuscode=200,
            data=result,
        )
    except ValueError as exc:
        return format_response(
            success=False,
            msg=str(exc),
            statuscode=400,
            data=None,
        )
    except Exception:
        return format_response(
            success=False,
            msg="Failed to send OTP.",
            statuscode=500,
            data=None,
        )


@router.post("/tenant-onboarding/verify-otp")
async def verify_tenant_onboarding_otp(request: Request):
    try:
        body = await request.json()
        email = body.get("email")
        otp = body.get("otp")
        if not email or not otp:
            return format_response(
                success=False,
                msg="Email and OTP are required.",
                statuscode=400,
                data=None,
            )
        otp_service = TenantOnboardingOTPService()
        result = otp_service.verify_otp(email=email, otp=otp)
        return format_response(
            success=True,
            msg="OTP verified successfully.",
            statuscode=200,
            data=result,
        )
    except ValueError as exc:
        return format_response(
            success=False,
            msg=str(exc),
            statuscode=400,
            data=None,
        )
    except Exception:
        return format_response(
            success=False,
            msg="Failed to verify OTP.",
            statuscode=500,
            data=None,
        )
 