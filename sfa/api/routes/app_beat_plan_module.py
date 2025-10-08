from fastapi import APIRouter, Request, Depends, Query
from sfa.services.app_beat_plan_services import AppBeatPlanService
from sfa.utils.response import format_response
from sfa.utils.auth_utils import get_current_user
from typing import List, Optional

router = APIRouter()

@router.get("/areas")
async def get_areas(current_user: dict = Depends(get_current_user)):
    """Get available areas for beat plan creation"""
    try:
        user_id = current_user.get("user_id")
        
        service = AppBeatPlanService()
        result = service.get_areas(user_id)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get areas"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Areas retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
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

@router.post("/customers")
async def get_customers_by_area(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get customers in a specific area for beat plan creation"""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        area_id = body.get("area_id")
        user_lat = body.get("latitude")
        user_lng = body.get("longitude")
        
        if not area_id:
            return format_response(
                success=False,
                msg="Area ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "area_id is required in request body"
                    }
                }
            )
        
        service = AppBeatPlanService()
        result = service.get_customers_by_area(area_id, user_id, user_lat, user_lng)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get customers"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Customers retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
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

@router.post("/create_beat_plan")
async def create_beat_plan(request: Request, current_user: dict = Depends(get_current_user)):
    """Create a new beat plan"""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        # Extract required fields
        area_id = body.get("area_id")
        customer_ids = body.get("customer_ids", [])
        plan_date = body.get("plan_date")
        plan_name = body.get("plan_name")
        notes = body.get("notes")
        
        # Validate required fields
        if not area_id:
            return format_response(
                success=False,
                msg="Area ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "area_id is required"
                    }
                }
            )
        
        if not customer_ids or not isinstance(customer_ids, list):
            return format_response(
                success=False,
                msg="Customer IDs are required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "customer_ids must be a non-empty array"
                    }
                }
            )
        
        service = AppBeatPlanService()
        result = service.create_beat_plan(
            user_id=user_id,
            area_id=area_id,
            customer_ids=customer_ids,
            plan_date=plan_date,
            plan_name=plan_name,
            notes=notes
        )
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Beat plan creation failed"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Beat plan created successfully",
            statuscode=201,
            data=result.get("data", {})
        )
        
    except Exception as e:
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

@router.post("/get_beat_plan_list")
async def get_beat_plan_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get beat plans for the current user based on active_tab (today/upcoming), with required location for route optimization."""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")

        # active_tab: today|upcoming (default today)
        active_tab = body.get("active_tab", "today")

        # Required user coordinates for route optimization
        user_lat = body.get("user_lat")
        user_lng = body.get("user_lng")
        if user_lat is None or user_lng is None:
            return format_response(
                success=False,
                msg="user_lat and user_lng are required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "user_lat and user_lng are required and must be valid numbers"
                    }
                }
            )

        # Optional
        status = body.get("status")
        limit = body.get("limit", 50)

        # Coerce limit to int safely
        try:
            limit = int(limit)
        except Exception:
            limit = 50

        # Coerce coordinates to float
        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)
        except Exception:
            return format_response(
                success=False,
                msg="Invalid coordinates",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "user_lat and user_lng must be valid numbers"
                    }
                }
            )

        service = AppBeatPlanService()
        result = service.get_beat_plan_list(user_id, status=status, active_tab=active_tab, limit=limit, user_lat=user_lat, user_lng=user_lng)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get beat plans"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Beat plans retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
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

@router.get("/get_beat_plans_by_day")
async def get_beat_plans_by_day(
    day_name: str = Query(..., description="Day name (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)"),
    limit: int = Query(50, ge=1, le=100, description="Number of beat plans to return"),
    user_lat: Optional[float] = Query(None, description="User's current latitude for route optimization"),
    user_lng: Optional[float] = Query(None, description="User's current longitude for route optimization"),
    current_user: dict = Depends(get_current_user)
):
    """Get beat plans for a specific day name with route optimization"""
    try:
        user_id = current_user.get("user_id")
        
        service = AppBeatPlanService()
        result = service.get_beat_plans_by_day(user_id, day_name, limit, user_lat, user_lng)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get beat plans by day"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg=f"Beat plans for {day_name} retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
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

@router.post("/start_checkin")
async def start_checkin(request: Request, current_user: dict = Depends(get_current_user)):
    """Start a customer check-in if within 100m of customer location."""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")

        customer_id = body.get("customer_id")
        plan_date = body.get("plan_date")
        user_lat = body.get("user_lat")
        user_lng = body.get("user_lng")
        beat_plan_id = body.get("beat_plan_id")

        # Validate required fields
        missing = []
        if not customer_id: missing.append("customer_id")
        if not plan_date: missing.append("plan_date")
        if user_lat is None: missing.append("user_lat")
        if user_lng is None: missing.append("user_lng")
        if missing:
            return format_response(
                success=False,
                msg="Missing required fields",
                statuscode=400,
                data={"error": {"code": "VALIDATION_ERROR", "details": ", ".join(missing) + " are required"}}
            )

        # Coerce coordinates to float
        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)
        except Exception:
            return format_response(
                success=False,
                msg="Invalid coordinates",
                statuscode=400,
                data={"error": {"code": "VALIDATION_ERROR", "details": "user_lat and user_lng must be valid numbers"}}
            )

        service = AppBeatPlanService()
        result = service.start_checkin(
            user_id=user_id,
            customer_id=customer_id,
            latitude=user_lat,
            longitude=user_lng,
            plan_date=plan_date,
            beat_plan_id=beat_plan_id,
            radius_m=100
        )

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Start check-in failed"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )

        return format_response(
            success=True,
            msg="Check-in started successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )

@router.post("/end_checkin")
async def end_checkin(request: Request, current_user: dict = Depends(get_current_user)):
    """End a customer check-in and mark it as completed."""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")

        customer_id = body.get("customer_id")
        plan_date = body.get("plan_date")
        notes = body.get("notes")
        rating = body.get("rating")

        # Validate required fields
        if not customer_id:
            return format_response(
                success=False,
                msg="Missing required field: customer_id",
                statuscode=400,
                data={"error": {"code": "VALIDATION_ERROR", "details": "customer_id is required"}}
            )

        # Validate rating if provided
        if rating is not None:
            try:
                rating = int(rating)
                if not (1 <= rating <= 5):
                    return format_response(
                        success=False,
                        msg="Invalid rating",
                        statuscode=400,
                        data={"error": {"code": "VALIDATION_ERROR", "details": "rating must be between 1 and 5"}}
                    )
            except (ValueError, TypeError):
                return format_response(
                    success=False,
                    msg="Invalid rating format",
                    statuscode=400,
                    data={"error": {"code": "VALIDATION_ERROR", "details": "rating must be a number"}}
                )

        service = AppBeatPlanService()
        result = service.end_checkin(user_id, customer_id, plan_date, notes, rating)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to end check-in"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )

        return format_response(
            success=True,
            msg="Check-in ended successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )

@router.post("/beat_plan_history")
async def get_beat_plan_history(request: Request, current_user: dict = Depends(get_current_user)):
    """Get beat plan history with statistics for last month or this month"""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        # period: last_month | this_month (default: this_month)
        period = body.get("period", "this_month")
        
        service = AppBeatPlanService()
        result = service.get_beat_plan_history(user_id, period)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get beat plan history"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Beat plan history retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )

@router.post("/beat_plan_detail")
async def get_beat_plan_detail(request: Request, current_user: dict = Depends(get_current_user)):
    """Get detailed information about a specific beat plan"""
    try:
        body = await request.json()
        user_id = current_user.get("user_id")
        
        beat_plan_id = body.get("beat_plan_id")
        if not beat_plan_id:
            return format_response(
                success=False,
                msg="beat_plan_id is required",
                statuscode=400,
                data={"error": {"code": "VALIDATION_ERROR", "details": "beat_plan_id is required"}}
            )
        
        service = AppBeatPlanService()
        result = service.get_beat_plan_detail(user_id, beat_plan_id)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get beat plan details"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Beat plan details retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )
