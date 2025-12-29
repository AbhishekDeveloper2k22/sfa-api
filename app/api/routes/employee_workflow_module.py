from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.services.employee_workflow_service import (
    EmployeeWorkflowError,
    EmployeeWorkflowService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

router = APIRouter(prefix="/api/web/employees", tags=["employee-workflow"])
service = EmployeeWorkflowService()


STEP_SECTION_MAP: Dict[int, str] = {
    1: "personal",
    2: "employment",
    3: "compensation",
    4: "bank_tax",
    5: "documents",
    6: "emergency_address",
}


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
    except EmployeeWorkflowError as exc:
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


@router.post("/step-1")
async def save_step_one(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    personal = payload.get("personal") or {}
    draft_id = payload.get("draft_id")

    def action():
        result = service.save_step_one(tenant_id, actor, personal, draft_id)
        return format_response(
            success=True,
            msg="Step 1 saved successfully",
            statuscode=status.HTTP_201_CREATED if not draft_id else status.HTTP_200_OK,
            data=result,
        )

    return handle_service_call(action)


@router.post("/step-2")
async def save_step_two(request: Request, current_user: dict = Depends(get_current_user)):
    return await _save_step_generic(request, current_user, target_step=2, next_step=3)


@router.post("/step-3")
async def save_step_three(request: Request, current_user: dict = Depends(get_current_user)):
    return await _save_step_generic(request, current_user, target_step=3, next_step=4)


@router.post("/step-4")
async def save_step_four(request: Request, current_user: dict = Depends(get_current_user)):
    return await _save_step_generic(request, current_user, target_step=4, next_step=5)


@router.post("/step-5")
async def save_step_five(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    draft_id = payload.get("draft_id")
    documents = payload.get("documents") or []

    def action():
        result = service.save_documents(tenant_id, actor, draft_id, documents)
        return format_response(
            success=True,
            msg="Documents saved successfully",
            statuscode=status.HTTP_200_OK,
            data=result,
        )

    return handle_service_call(action)


@router.post("/step-6")
async def save_step_six(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    draft_id = payload.get("draft_id")
    emergency_address = payload.get("emergency_address") or {}

    def action():
        result = service.save_emergency_and_address(tenant_id, actor, draft_id, emergency_address)
        return format_response(
            success=True,
            msg="Emergency & address saved successfully",
            statuscode=status.HTTP_200_OK,
            data=result,
        )

    return handle_service_call(action)


async def _save_step_generic(request: Request, current_user: dict, target_step: int, next_step: Optional[int]):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    draft_id = payload.get("draft_id")
    section_key = STEP_SECTION_MAP[target_step]
    section_payload = payload.get(section_key) or payload.get("data") or {}

    def action():
        result = service.save_step(
            tenant_id,
            actor,
            draft_id,
            section_key,
            section_payload,
            step_number=target_step,
            next_step=next_step,
        )
        return format_response(
            success=True,
            msg=f"Step {target_step} saved successfully",
            statuscode=status.HTTP_200_OK,
            data=result,
        )

    return handle_service_call(action)


@router.post("/complete")
async def finalize_employee(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    draft_id = payload.get("draft_id")

    def action():
        result = service.complete_employee(tenant_id, actor, draft_id)
        return format_response(
            success=True,
            msg="Employee created successfully",
            statuscode=status.HTTP_200_OK,
            data=result,
        )

    return handle_service_call(action)


@router.get("")
async def list_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    employment_status: Optional[str] = None,
    department_id: Optional[str] = None,
    designation: Optional[str] = None,
    role_id: Optional[str] = None,
    location_id: Optional[str] = None,
    manager_id: Optional[str] = None,
    tags: Optional[List[str]] = Query(default=None),
    join_date_from: Optional[str] = None,
    join_date_to: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    tenant_id, _ = tenant_context(current_user)
    filters = {
        "page": page,
        "limit": limit,
        "search": search,
        "status": status_filter,
        "employment_status": employment_status,
        "department_id": department_id,
        "designation": designation,
        "role_id": role_id,
        "location_id": location_id,
        "manager_id": manager_id,
        "tags": tags,
        "join_date_from": join_date_from,
        "join_date_to": join_date_to,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }

    def action():
        data = service.list_employees(tenant_id, filters)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data=data)

    return handle_service_call(action)


@router.get("/filter-options")
async def get_filter_options(current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_filter_options(tenant_id)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data=data)

    return handle_service_call(action)


@router.post("/bulk/export")
async def export_employees(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    filters = payload.get("filters") or {}
    limit = payload.get("limit", 1000)

    def action():
        data = service.export_employees(tenant_id, filters, limit)
        return format_response(
            success=True,
            msg="Employees export generated",
            statuscode=status.HTTP_200_OK,
            data=data,
        )

    return handle_service_call(action)


@router.post("/bulk/assign-role")
async def bulk_assign_role(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    employee_ids = payload.get("employee_ids") or []
    role_id = payload.get("role_id")
    role_name = payload.get("role_name")

    def action():
        data = service.bulk_assign_role(tenant_id, employee_ids, role_id, role_name, actor)
        return format_response(
            success=True,
            msg="Roles assigned successfully",
            statuscode=status.HTTP_200_OK,
            data=data,
        )

    return handle_service_call(action)


@router.post("/bulk/suspend")
async def bulk_suspend(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    employee_ids = payload.get("employee_ids") or []
    reason = payload.get("reason")
    effective_date = payload.get("effective_date")

    def action():
        data = service.bulk_suspend(tenant_id, employee_ids, reason, effective_date, actor)
        return format_response(
            success=True,
            msg="Employees suspended successfully",
            statuscode=status.HTTP_200_OK,
            data=data,
        )

    return handle_service_call(action)


@router.post("/bulk/terminate")
async def bulk_terminate(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    employee_ids = payload.get("employee_ids") or []
    reason = payload.get("reason")
    last_working_day = payload.get("last_working_day")

    def action():
        data = service.bulk_terminate(tenant_id, employee_ids, reason, last_working_day, actor)
        return format_response(
            success=True,
            msg="Employees terminated successfully",
            statuscode=status.HTTP_200_OK,
            data=data,
        )

    return handle_service_call(action)


@router.post("/bulk/activate-ess")
async def bulk_activate_ess(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    employee_ids = payload.get("employee_ids") or []
    enable = bool(payload.get("enable", True))

    def action():
        data = service.bulk_activate_ess(tenant_id, employee_ids, enable, actor)
        return format_response(
            success=True,
            msg="ESS access updated",
            statuscode=status.HTTP_200_OK,
            data=data,
        )

    return handle_service_call(action)


@router.post("/bulk/add-tag")
async def bulk_add_tag(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    employee_ids = payload.get("employee_ids") or []
    tag = payload.get("tag")

    def action():
        data = service.bulk_add_tag(tenant_id, employee_ids, tag, actor)
        return format_response(
            success=True,
            msg="Tag added successfully",
            statuscode=status.HTTP_200_OK,
            data=data,
        )

    return handle_service_call(action)


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        draft = service.get_draft(tenant_id, draft_id)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data=draft)

    return handle_service_call(action)


@router.get("/drafts")
async def list_drafts(current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)

    def action():
        drafts = service.list_drafts(tenant_id, actor)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data={"drafts": drafts})

    return handle_service_call(action)


@router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        service.delete_draft(tenant_id, draft_id)
        return format_response(success=True, msg="Draft deleted", statuscode=status.HTTP_200_OK, data=None)

    return handle_service_call(action)


@router.get("/{employee_id}")
async def get_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        employee = service.get_employee(tenant_id, employee_id)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data=employee)

    return handle_service_call(action)


@router.put("/{employee_id}")
async def update_employee(
    employee_id: str,
    request: Request,
    if_match: Optional[str] = Header(default=None, alias="If-Match"),
    current_user: dict = Depends(get_current_user),
):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        updated = service.update_employee(tenant_id, employee_id, payload, actor, if_match)
        return format_response(
            success=True,
            msg="Employee updated successfully",
            statuscode=status.HTTP_200_OK,
            data=updated,
        )

    return handle_service_call(action)


@router.patch("/{employee_id}/status")
async def update_employee_status(
    employee_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    status_value = payload.get("status")
    reason = payload.get("reason")
    effective_date = payload.get("effective_date")

    def action():
        updated = service.update_employee_status(
            tenant_id,
            employee_id,
            status_value,
            actor,
            reason=reason,
            effective_date=effective_date,
        )
        return format_response(
            success=True,
            msg="Employee status updated",
            statuscode=status.HTTP_200_OK,
            data=updated,
        )

    return handle_service_call(action)


@router.patch("/{employee_id}/step-{step_number}")
async def update_employee_step(
    employee_id: str,
    step_number: int,
    request: Request,
    if_match: Optional[str] = Header(default=None, alias="If-Match"),
    current_user: dict = Depends(get_current_user),
):
    if step_number not in STEP_SECTION_MAP:
        raise HTTPException(status_code=400, detail="Invalid step number")

    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    section_key = STEP_SECTION_MAP[step_number]
    section_payload = payload.get(section_key) or payload

    def action():
        updated = service.update_employee_step(
            tenant_id,
            employee_id,
            step_number,
            section_key,
            section_payload,
            actor,
            if_match,
        )
        return format_response(
            success=True,
            msg=f"Step {step_number} updated successfully",
            statuscode=status.HTTP_200_OK,
            data=updated,
        )

    return handle_service_call(action)


@router.get("/validate/email")
async def validate_email(email: str, exclude_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.validate_email(tenant_id, email, exclude_id)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data=data)

    return handle_service_call(action)


@router.get("/validate/code")
async def validate_code(code: str, exclude_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.validate_code(tenant_id, code, exclude_id)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data=data)

    return handle_service_call(action)


@router.get("/validate/username")
async def validate_username(
    username: str,
    exclude_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.validate_username(tenant_id, username, exclude_id)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data=data)

    return handle_service_call(action)


@router.get("/lookup/{resource}")
async def lookup_resource(resource: str, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)

    def action():
        data = service.get_lookup(tenant_id, resource)
        return format_response(success=True, statuscode=status.HTTP_200_OK, data=data)

    return handle_service_call(action)


@router.post("/uploads/init")
async def init_upload(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()

    def action():
        data = service.init_upload(
            tenant_id=tenant_id,
            user_id=actor,
            file_name=payload.get("file_name"),
            file_size=payload.get("file_size"),
            mime_type=payload.get("mime_type"),
            category=payload.get("category"),
        )
        return format_response(
            success=True,
            msg="Upload initialized",
            statuscode=status.HTTP_200_OK,
            data=data,
        )

    return handle_service_call(action)


@router.post("/uploads/{upload_id}/complete")
async def complete_upload(upload_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    file_url = payload.get("file_url")

    def action():
        data = service.complete_upload(tenant_id, upload_id, file_url)
        return format_response(
            success=True,
            msg="Upload completed",
            statuscode=status.HTTP_200_OK,
            data=data,
        )

    return handle_service_call(action)
