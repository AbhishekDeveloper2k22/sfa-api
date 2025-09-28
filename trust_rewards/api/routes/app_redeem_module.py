from fastapi import APIRouter, Request, HTTPException, Depends
from trust_rewards.services.app_redeem_services import AppRedeemService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
import traceback

router = APIRouter()

@router.post("/redeem_gift")
async def redeem_gift(request: Request, current_user: dict = Depends(get_current_user)):
    """Redeem gift using wallet points"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        # Validate required parameters
        if not request_data.get('gift_id'):
            return format_response(
                success=False,
                msg="gift_id is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "gift_id is mandatory"
                    }
                }
            )
        
        if not request_data.get('verification_token'):
            return format_response(
                success=False,
                msg="verification_token is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "verification_token is mandatory for gift redemption"
                    }
                }
            )
        
        service = AppRedeemService()
        result = service.redeem_gift(request_data, current_user)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to redeem gift"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Gift redeemed successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/redemption_history")
async def get_redemption_history(request: Request, current_user: dict = Depends(get_current_user)):
    """Get gift redemption history for worker"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = AppRedeemService()
        result = service.get_redemption_history(request_data, current_user)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get redemption history"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Redemption history retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/wallet_balance")
async def get_wallet_balance(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current wallet balance for worker"""
    try:
        service = AppRedeemService()
        result = service.get_wallet_balance(current_user)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get wallet balance"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Wallet balance retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/send_otp")
async def send_otp_for_redemption(request: Request, current_user: dict = Depends(get_current_user)):
    """Send OTP to worker's mobile for gift redemption verification"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = AppRedeemService()
        result = service.send_otp_for_redemption(request_data, current_user)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to send OTP"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="OTP sent successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/verify_otp")
async def verify_otp_for_redemption(request: Request, current_user: dict = Depends(get_current_user)):
    """Verify OTP for gift redemption"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        # Validate required parameters
        if not request_data.get('otp'):
            return format_response(
                success=False,
                msg="OTP is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "OTP is mandatory"
                    }
                }
            )
        
        if not request_data.get('otp_id'):
            return format_response(
                success=False,
                msg="OTP ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "OTP ID is mandatory"
                    }
                }
            )
        
        service = AppRedeemService()
        result = service.verify_otp_for_redemption(request_data, current_user)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to verify OTP"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="OTP verified successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/cancel_redemption")
async def cancel_redemption(request: Request, current_user: dict = Depends(get_current_user)):
    """Cancel a gift redemption and return points to wallet"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        # Validate required parameters
        if not request_data.get('redemption_id'):
            return format_response(
                success=False,
                msg="redemption_id is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "redemption_id is mandatory"
                    }
                }
            )
        
        service = AppRedeemService()
        result = service.cancel_redemption(request_data, current_user)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to cancel redemption"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Redemption cancelled successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )