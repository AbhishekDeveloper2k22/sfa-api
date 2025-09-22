from fastapi import APIRouter, Depends, HTTPException, Request
from trust_rewards.services.app_user_auth_services import AppUserAuthService
from trust_rewards.utils.response import format_response
from trust_rewards.utils.auth import get_current_user

router = APIRouter()

@router.post("/send_otp")
async def send_otp(request: Request):
    """Send OTP to mobile number for login"""
    try:
        request_data = await request.json()
        service = AppUserAuthService()
        result = service.send_otp(request_data)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "OTP sent successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Failed to send OTP"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error sending OTP: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )

@router.post("/verify_otp")
async def verify_otp(request: Request):
    """Verify OTP and login user"""
    try:
        request_data = await request.json()
        service = AppUserAuthService()
        result = service.verify_otp(request_data)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "OTP verified successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "OTP verification failed"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error verifying OTP: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )

@router.post("/resend_otp")
async def resend_otp(request: Request):
    """Resend OTP to mobile number"""
    try:
        request_data = await request.json()
        service = AppUserAuthService()
        result = service.resend_otp(request_data)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "OTP resent successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Failed to resend OTP"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error resending OTP: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )

@router.post("/logout")
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """Logout user and invalidate token"""
    try:
        request_data = await request.json()
        service = AppUserAuthService()
        result = service.logout(request_data, current_user)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "Logged out successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Logout failed"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error during logout: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )

@router.post("/refresh_token")
async def refresh_token(request: Request, current_user: dict = Depends(get_current_user)):
    """Refresh JWT token"""
    try:
        request_data = await request.json()
        service = AppUserAuthService()
        result = service.refresh_token(request_data, current_user)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "Token refreshed successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Token refresh failed"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error refreshing token: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )
