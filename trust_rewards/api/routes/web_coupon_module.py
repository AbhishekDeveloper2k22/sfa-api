from fastapi import APIRouter, Request, HTTPException, Depends
from trust_rewards.services.web_coupon_services import CouponService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
import traceback

router = APIRouter()

@router.post("/generate_points_coupons")
async def generate_points_coupons(request: Request, current_user: dict = Depends(get_current_user)):
    """Generate points redemption coupons for skilled workers"""
    try:
        request_data = await request.json()
        
        # Add created_by_id from current user
        request_data['created_by_id'] = current_user.get('user_id', 1)
        
        service = CouponService()
        result = service.generate_points_coupons(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to generate points coupons"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg=result.get("message", "Points coupons generated successfully"),
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

@router.post("/coupon_code_list")
async def get_coupons_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of individual coupons with filters"""
    try:
        request_data = await request.json()
        
        service = CouponService()
        result = service.get_coupons_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get coupons list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Coupons list retrieved successfully",
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

@router.post("/coupon_code_list_csv")
async def get_coupon_code_list_csv(request: Request, current_user: dict = Depends(get_current_user)):
    """Download coupon codes as CSV for a specific batch"""
    try:
        request_data = await request.json()
        
        service = CouponService()
        result = service.get_coupon_code_list_csv(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to generate CSV"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        # Return CSV data using format_response
        return format_response(
            success=True,
            msg=result.get("message", "CSV generated successfully"),
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

@router.post("/coupon_master_list")
async def get_coupon_master_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of coupon master batches"""
    try:
        request_data = await request.json()
        
        service = CouponService()
        result = service.get_coupon_master_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get coupon master list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Coupon master list retrieved successfully",
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