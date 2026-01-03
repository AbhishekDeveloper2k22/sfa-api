from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from typing import Optional, List, Dict, Any

from app.services.payroll_service import (
    PayrollError,
    PayrollService,
)
from app.utils.auth_utils import get_request_payload
from app.utils.response import format_response

# Main Router (will be mounted at /api/web)
router = APIRouter(tags=["payroll"])
service = PayrollService()

# Sub-routers
runs_router = APIRouter()
payslips_router = APIRouter()
structures_router = APIRouter()
statutory_router = APIRouter()


def get_current_user(request: Request):
    return get_request_payload(request)


def tenant_context(payload: dict):
    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant associated with token")
    return tenant_id, user_id


def handle_service_call(fn):
    try:
        return fn()
    except PayrollError as exc:
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
    except Exception as exc:
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

# ==============================================================================
# 1. PAYROLL RUNS ROUTER (/payroll)
# ==============================================================================

@runs_router.get("/runs")
async def get_payroll_runs(
    request: Request,
    status: Optional[str] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {"status": status, "year": year}
    q = {k: v for k, v in q.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_payroll_runs(tenant_id, q)))

@runs_router.get("/runs/{runId}")
async def get_payroll_run(runId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_payroll_run(tenant_id, runId)))

@runs_router.post("/preview")
async def start_preview(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 202, service.start_preview(tenant_id, payload, actor)))

@runs_router.get("/preview/{jobId}/employees")
async def get_preview_results(jobId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_preview_results(tenant_id, jobId, {})))

@runs_router.post("/run")
async def finalize_payroll(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.finalize_payroll(tenant_id, payload, actor)))

@runs_router.get("/runs/{runId}/export")
async def export_payroll_run(runId: str, request: Request, format: str, type: str, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    q = {"format": format, "type": type}
    return handle_service_call(lambda: format_response(True, 200, service.export_payroll_run(tenant_id, runId, q)))

@runs_router.get("/stats")
async def get_stats(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_stats(tenant_id)))

@runs_router.get("/filter-options")
async def get_filter_options(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_filter_options(tenant_id)))

# Jobs (Scoped under payroll context as per user request to follow docs path)
@runs_router.get("/jobs/{jobId}") # Maps to /payroll/jobs/{jobId}
async def get_job_status(jobId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_job_status(tenant_id, jobId)))

# Just in case docs meant root /jobs, I'll allow that logic in main router if needed, but scoping is better.


# ==============================================================================
# 2. PAYSLIPS ROUTER (/payslips)
# ==============================================================================

@payslips_router.get("/")
async def get_payslips(
    request: Request,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    qp = {
        "period_month": period_month,
        "period_year": period_year,
        "status": status,
        "q": q
    }
    qp = {k: v for k, v in qp.items() if v is not None}
    return handle_service_call(lambda: format_response(True, 200, service.get_payslips(tenant_id, qp)))

@payslips_router.get("/{id}")
async def get_payslip_or_employee_payslips(
    id: str, 
    request: Request,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    
    # Heuristic to distinguish PayslipID from EmployeeID
    # Payslip ID usually has "ps_" prefix or is Long. Employee ID is usually shorter or "emp_".
    # Or based on query params. 2.1 Get Employee Payslips DOES NOT require params but 2.3 DOES.
    # But 2.2 Get Payslip By ID DOES NOT have params.
    # If period_month provided, definitely Employee Payslips (2.3).
    # If id starts with "ps_" -> Payslip.
    # Fallback -> Try Payslip, if not found try Employee list? No, explicit API design preferred.
    
    def action():
        is_employee_query = period_month is not None or period_year is not None or not id.startswith("ps_")
        
        if is_employee_query:
             qp = {}
             if period_month: qp["period_month"] = period_month
             if period_year: qp["period_year"] = period_year
             return format_response(True, 200, service.get_employee_payslips(tenant_id, id, qp))
        else:
             return format_response(True, 200, service.get_payslip_by_id(tenant_id, id))

    return handle_service_call(action)

@payslips_router.get("/{id}/download")
async def download_payslip(id: str, request: Request, format: str, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.download_payslip(tenant_id, id, {"format": format})))


# ==============================================================================
# 3. SALARY STRUCTURES ROUTER (/salary-structures)
# ==============================================================================

@structures_router.get("/")
async def get_salary_structures(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_salary_structures(tenant_id)))

@structures_router.post("/")
async def create_salary_structure(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 201, service.create_salary_structure(tenant_id, payload, actor)))

@structures_router.post("/validate-formula")
async def validate_formula(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.validate_formula(tenant_id, payload)))

@structures_router.get("/{code}")
async def get_salary_structure(code: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_salary_structure(tenant_id, code)))

@structures_router.put("/{code}")
async def update_salary_structure(code: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.update_salary_structure(tenant_id, code, payload, actor)))

@structures_router.delete("/{code}")
async def delete_salary_structure(code: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.delete_salary_structure(tenant_id, code)))


# ==============================================================================
# 4. STATUTORY ROUTER (/statutory)
# ==============================================================================

@statutory_router.get("/rules")
async def get_statutory_rules(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_statutory_rules(tenant_id)))

@statutory_router.get("/rules/active")
async def get_active_statutory_rule(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_active_statutory_rule(tenant_id)))

@statutory_router.get("/challans")
async def get_challans(
    request: Request, 
    status: Optional[str] = None, 
    type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    tenant_id, _ = tenant_context(current_user)
    q = {"status": status, "type": type}
    return handle_service_call(lambda: format_response(True, 200, service.get_challans(tenant_id, q)))

@statutory_router.post("/challans")
async def generate_challan(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.generate_challan(tenant_id, payload, actor)))

@statutory_router.get("/challans/{challanId}")
async def get_challan(challanId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.get_challan(tenant_id, challanId)))

@statutory_router.post("/challans/{challanId}/mark-paid")
async def mark_challan_paid(challanId: str, request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id, actor = tenant_context(current_user)
    payload = await request.json()
    return handle_service_call(lambda: format_response(True, 200, service.mark_challan_paid(tenant_id, challanId, payload, actor)))

@statutory_router.get("/challans/{challanId}/download")
async def download_challan(challanId: str, request: Request, format: str, current_user: dict = Depends(get_current_user)):
    tenant_id, _ = tenant_context(current_user)
    return handle_service_call(lambda: format_response(True, 200, service.download_challan(tenant_id, challanId, {"format": format})))


# Integration
router.include_router(runs_router, prefix="/payroll")
router.include_router(payslips_router, prefix="/payslips")
router.include_router(structures_router, prefix="/salary-structures")
router.include_router(statutory_router, prefix="/statutory")

# Note: The jobs route is inside runs_router which is under /payroll, so /payroll/jobs/{jobId}.
# Note: /api/web mounting means /api/web/payroll/jobs/{jobId}.
