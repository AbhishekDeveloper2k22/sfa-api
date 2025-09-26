from fastapi import APIRouter, Depends, Request

from trust_rewards.utils.response import format_response
from trust_rewards.utils.auth import get_current_user
from trust_rewards.services.web_master_services import WebMasterService


router = APIRouter(tags=["web_master"])


@router.post("/points_master_add")
async def add_points_master(request: Request, current_user: dict = Depends(get_current_user)):
    """Add a new points master record with validations."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        created_by = current_user.get("user_id", 1)  # Get user_id from JWT payload
        result = service.add_points_master(body, created_by=created_by)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Validation failed"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg=result.get("message", "Points master added successfully"),
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to add points master: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/points_master_list")
async def get_points_master_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of points master records with filtering."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        result = service.get_points_master_list(body)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get points master list"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg="Points master list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to get points master list: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/points_master_edit")
async def update_points_master(request: Request, current_user: dict = Depends(get_current_user)):
    """Update an existing points master record with validations."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        updated_by = current_user.get("user_id", 1)  # Get user_id from JWT payload
        result = service.update_points_master(body, created_by=updated_by)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Validation failed"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg=result.get("message", "Points master updated successfully"),
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to update points master: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/category_master_add")
async def add_category(request: Request, current_user: dict = Depends(get_current_user)):
    """Add a new category with validations."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        created_by = current_user.get("user_id", 1)  # Get user_id from JWT payload
        result = service.add_category(body, created_by=created_by)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Validation failed"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg=result.get("message", "Category added successfully"),
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to add category: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/category_master_list")
async def get_categories_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of categories with filtering."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        result = service.get_categories_list(body)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get categories list"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg="Categories list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to get categories list: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/category_master_edit")
async def update_category(request: Request, current_user: dict = Depends(get_current_user)):
    """Update an existing category with validations."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        updated_by = current_user.get("user_id", 1)  # Get user_id from JWT payload
        result = service.update_category(body, updated_by=updated_by)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Validation failed"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg=result.get("message", "Category updated successfully"),
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to update category: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/sub_category_master_add")
async def add_sub_category(request: Request, current_user: dict = Depends(get_current_user)):
    """Add a new sub category with validations."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        created_by = current_user.get("user_id", 1)  # Get user_id from JWT payload
        result = service.add_sub_category(body, created_by=created_by)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Validation failed"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg=result.get("message", "Sub category added successfully"),
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to add sub category: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/sub_category_master_list")
async def get_sub_categories_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of sub categories with filtering."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        result = service.get_sub_categories_list(body)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get sub categories list"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg="Sub categories list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to get sub categories list: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


@router.post("/sub_category_master_edit")
async def update_sub_category(request: Request, current_user: dict = Depends(get_current_user)):
    """Update an existing sub category with validations."""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        service = WebMasterService()
        updated_by = current_user.get("user_id", 1)  # Get user_id from JWT payload
        result = service.update_sub_category(body, updated_by=updated_by)

        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Validation failed"),
                statuscode=400,
                data={"error": result.get("error")}
            )

        return format_response(
            success=True,
            msg=result.get("message", "Sub category updated successfully"),
            statuscode=200,
            data=result.get("data", {})
        )
    except Exception as e:
        return format_response(
            success=False,
            msg=f"Failed to update sub category: {str(e)}",
            statuscode=500,
            data={"error": str(e)}
        )


