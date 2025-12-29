from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, UploadFile, File, Form
from pydantic import BaseModel

from app.services.onboarding_user_services import TenantOnboardingService
from app.utils.response import format_response

router = APIRouter()
service = TenantOnboardingService()


class Step1Payload(BaseModel):
    company: Dict[str, Any]


class Step2Payload(BaseModel):
    onboarding_id: str
    admin_user: Dict[str, Any]


class Step3Payload(BaseModel):
    onboarding_id: str
    branding: Dict[str, Any]


@router.post("/step-1")
async def save_step1(payload: Step1Payload):
    try:
        data = service.save_step1(payload.company)
        return format_response(
            success=True,
            msg="Step 1 completed successfully.",
            statuscode=200,
            data=data,
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
            msg="Failed to save company details.",
            statuscode=500,
            data=None,
        )


@router.post("/step-2")
async def save_step2(payload: Step2Payload):
    try:
        data = service.save_step2(payload.onboarding_id, payload.admin_user)
        return format_response(
            success=True,
            msg="Step 2 completed successfully.",
            statuscode=200,
            data=data,
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
            msg="Failed to save admin user details.",
            statuscode=500,
            data=None,
        )


@router.post("/step-3")
async def save_step3(payload: Step3Payload):
    try:
        data = service.save_step3(payload.onboarding_id, payload.branding)
        return format_response(
            success=True,
            msg="Tenant onboarded successfully",
            statuscode=200,
            data=data,
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
            msg="Failed to complete onboarding.",
            statuscode=500,
            data=None,
        )


@router.get("/check")
async def check_progress(email: str = Query(..., description="Business email used during onboarding")):
    try:
        progress = service.check_progress(email)
        if not progress:
            return format_response(
                success=False,
                msg="No onboarding found for this email",
                statuscode=404,
                data=None,
            )
        return format_response(
            success=True,
            msg="Onboarding progress fetched successfully.",
            statuscode=200,
            data=progress,
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
            msg="Failed to check onboarding progress.",
            statuscode=500,
            data=None,
        )


@router.get("/{onboarding_id}")
async def get_onboarding(onboarding_id: str):
    try:
        data = service.get_onboarding_data(onboarding_id)
        if not data:
            return format_response(
                success=False,
                msg="Onboarding session not found.",
                statuscode=404,
                data=None,
            )
        return format_response(
            success=True,
            msg="Onboarding data fetched successfully.",
            statuscode=200,
            data=data,
        )
    except Exception:
        return format_response(
            success=False,
            msg="Failed to fetch onboarding data.",
            statuscode=500,
            data=None,
        )


@router.post("/upload")
async def upload_asset(
    onboarding_id: Optional[str] = Form(None),
    asset_type: str = Form(...),
    file: UploadFile = File(...),
    uploaded_by: Optional[str] = Form(None),
):
    try:
        saved = service.save_uploaded_asset(
            onboarding_id=onboarding_id,
            asset_type=asset_type,
            upload=file,
            uploaded_by=uploaded_by,
        )
        return format_response(
            success=True,
            msg="File uploaded successfully.",
            statuscode=200,
            data=saved,
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
            msg="Failed to upload file.",
            statuscode=500,
            data=None,
        )
