from fastapi import APIRouter, Depends, HTTPException, Request, Query, status

from app.services.employee_config_service import (
    EmployeeConfigError,
    EmployeeConfigService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(prefix="/api/web/employee_config", tags=["employee-config"])
service = EmployeeConfigService()


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
    except EmployeeConfigError as exc:
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


@router.get("/departments_list")
async def get_departments(current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        items, total = service.list_departments(tenant_id)
        return format_response(
            success=True,
            statuscode=200,
            data={"departments": items, "total": total},
        )

    return handle_service_call(action)


@router.post("/add_departments")
async def create_department(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        doc = service.create_department(tenant_id, payload, actor)
        return format_response(
            success=True,
            msg="Department created successfully",
            statuscode=status.HTTP_201_CREATED,
            data=doc,
        )

    return handle_service_call(action)


@router.put("/update_departments/{department_id}")
async def update_department(department_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        doc = service.update_department(tenant_id, department_id, payload, actor)
        return format_response(
            success=True,
            msg="Department updated successfully",
            statuscode=200,
            data=doc,
        )

    return handle_service_call(action)


@router.delete("/delete_departments/{department_id}")
async def delete_department(department_id: str, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)

    def action():
        service.delete_department(tenant_id, department_id, actor)
        return format_response(
            success=True,
            msg="Department deleted successfully",
            statuscode=200,
            data=None,
        )

    return handle_service_call(action)


@router.get("/designations_list")
async def get_designations(
    department: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    tenant_id, _ = tenant_context(current_user)

    def action():
        items, total = service.list_designations(tenant_id, department)
        return format_response(
            success=True,
            statuscode=200,
            data={"designations": items, "total": total},
        )

    return handle_service_call(action)


@router.post("/add_designations")
async def create_designation(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        doc = service.create_designation(tenant_id, payload, actor)
        return format_response(
            success=True,
            msg="Designation created successfully",
            statuscode=status.HTTP_201_CREATED,
            data=doc,
        )

    return handle_service_call(action)


@router.put("/update_designations/{designation_id}")
async def update_designation(designation_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        doc = service.update_designation(tenant_id, designation_id, payload, actor)
        return format_response(
            success=True,
            msg="Designation updated successfully",
            statuscode=200,
            data=doc,
        )

    return handle_service_call(action)


@router.delete("/delete_designations/{designation_id}")
async def delete_designation(designation_id: str, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)

    def action():
        service.delete_designation(tenant_id, designation_id, actor)
        return format_response(
            success=True,
            msg="Designation deleted successfully",
            statuscode=200,
            data=None,
        )

    return handle_service_call(action)


@router.post("/save-all")
async def save_all(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        stats = service.bulk_save(tenant_id, payload, actor)
        return format_response(
            success=True,
            msg="Configuration saved successfully",
            statuscode=200,
            data=stats,
        )

    return handle_service_call(action)
