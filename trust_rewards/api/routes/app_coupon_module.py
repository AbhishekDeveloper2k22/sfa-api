from fastapi import APIRouter, Depends, HTTPException, Request
from trust_rewards.services.app_coupon_services import AppCouponService
from trust_rewards.utils.response import format_response
from trust_rewards.utils.auth import get_current_user

router = APIRouter()

@router.post("/scan_coupon")
async def scan_coupon(request: Request, current_user: dict = Depends(get_current_user)):
    """Scan coupon codes and award points to skilled workers"""
    try:
        request_data = await request.json()
        service = AppCouponService()
        result = service.scan_coupon(request_data, current_user)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "Coupons scanned successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Failed to scan coupons"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error scanning coupons: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )

@router.post("/coupon_history")
async def coupon_history(request: Request, current_user: dict = Depends(get_current_user)):
    """Get coupon scan history for the worker"""
    try:
        request_data = await request.json()
        service = AppCouponService()
        result = service.get_coupon_history(request_data, current_user)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "Coupon scan history retrieved successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get coupon scan history"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error getting coupon scan history: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )

@router.post("/wallet_balance")
async def wallet_balance(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current wallet balance for the worker"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = AppCouponService()
        result = service.get_wallet_balance(request_data, current_user)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "Wallet balance retrieved successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get wallet balance"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error getting wallet balance: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )

@router.post("/transaction_ledger")
async def transaction_ledger(request: Request, current_user: dict = Depends(get_current_user)):
    """Get transaction ledger for the worker"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = AppCouponService()
        result = service.get_transaction_ledger(request_data, current_user)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "Transaction ledger retrieved successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get transaction ledger"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error getting transaction ledger: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )

@router.post("/ledger_summary")
async def ledger_summary(request: Request, current_user: dict = Depends(get_current_user)):
    """Get ledger summary with statistics for the worker"""
    try:
        # Handle empty request body gracefully
        try:
            request_data = await request.json()
        except:
            request_data = {}
        
        service = AppCouponService()
        result = service.get_ledger_summary(request_data, current_user)
        
        if result.get("success"):
            return format_response(
                success=True,
                msg=result.get("message", "Ledger summary retrieved successfully"),
                statuscode=200,
                data=result.get("data", {})
            )
        else:
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get ledger summary"),
                statuscode=400,
                data=result.get("error", {})
            )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Error getting ledger summary: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )
