from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.services.leave_config_service import LeaveConfigError, LeaveConfigService
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(prefix="/api/web/leave_config", tags=["leave-config"])
service = LeaveConfigService()


def get_current_user(request: Request):
    return get_request_payload(request)


def tenant_context(payload: dict):
    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant associated with token")
    if not user_id:
        raise HTTPException(status_code=403, detail="No user associated with token")
    return tenant_id, user_id


def handle_service_call(fn):
    try:
        return fn()
    except LeaveConfigError as exc:
        return format_response(
            success=False,
            msg=exc.args[0],
            statuscode=exc.status_code,
            data={
                "error": {
                    "code": exc.code,
                    "message": exc.args[0],
                    "details": exc.errors,
                }
            },
        )
    except Exception as exc:  # pragma: no cover
        return format_response(
            success=False,
            msg=str(exc),
            statuscode=500,
            data={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                }
            },
        )


@router.get("/get_leave_config")
async def get_leave_config(current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        config = service.get_config(tenant_id)
        return format_response(
            success=True,
            statuscode=200,
            data=config,
        )

    return handle_service_call(action)


@router.post("/save_leave_config")
async def save_leave_config(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        config = service.save_config(tenant_id, payload, actor)
        status_code = status.HTTP_200_OK
        if payload and not payload.get("id"):
            status_code = status.HTTP_201_CREATED
        return format_response(
            success=True,
            msg="Leave configuration saved successfully",
            statuscode=status_code,
            data=config,
        )

    return handle_service_call(action)
