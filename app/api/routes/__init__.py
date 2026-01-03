from fastapi import APIRouter
from app.api.routes import employee_module
from app.api.routes import user_auth_module
from app.api.routes import app_user_auth_module
from app.api.routes import app_dashboard_module
from app.api.routes import app_attendance_module
from app.api.routes import app_request_module
from app.api.routes import app_sidebar_module
from app.api.routes import attendance_module
from app.api.routes import leave_module
from app.api.routes import advance_module
from app.api.routes import payroll_module
from app.api.routes import expense_module
from app.api.routes import asset_module
from app.api.routes import document_module
from app.api.routes import policy_module
from app.api.routes import announcement_module
from app.api.routes import celebration_module
from app.api.routes import holiday_module
from app.api.routes import app_ai_agent_module
from app.api.routes import onboarding_user_module
from app.api.routes import employee_config_module
from app.api.routes import employee_workflow_module
from app.api.routes import attendance_config_module
from app.api.routes import leave_config_module
from app.api.routes import payroll_config_module
from .base import router as base_router

router = APIRouter()

# Base / health routes
router.include_router(
    base_router,
    prefix="",
    tags=["base"],
)

# Web (admin) APIs
router.include_router(employee_module.router, prefix="/api/web/employees")
router.include_router(user_auth_module.router, prefix="/api/web/auth")
router.include_router(attendance_module.router, prefix="/api/web/attendance")
router.include_router(leave_module.router, prefix="/api/web/leaves")
router.include_router(advance_module.router, prefix="/api/web/advances")
router.include_router(payroll_module.router, prefix="/api/web")
router.include_router(expense_module.router, prefix="/api/web/expense")
router.include_router(asset_module.router, prefix="/api/web/asset")
router.include_router(document_module.router, prefix="/api/web/document")
router.include_router(policy_module.router, prefix="/api/web/policy")
router.include_router(announcement_module.router, prefix="/api/web/announcement")
router.include_router(celebration_module.router, prefix="/api/web/celebration")
router.include_router(holiday_module.router, prefix="/api/web/holiday")
router.include_router(
    onboarding_user_module.router,
    prefix="/api/web/onboarding",
    tags=["tenant-onboarding"],
)
router.include_router(employee_config_module.router, tags=["employee-config"])
router.include_router(employee_workflow_module.router, tags=["employee-workflow"])
router.include_router(attendance_config_module.router, tags=["attendance-config"])
router.include_router(leave_config_module.router, tags=["leave-config"])
router.include_router(payroll_config_module.router, tags=["payroll-config"])

# App/mobile APIs
router.include_router(app_user_auth_module.router, prefix="/api/app/auth")
router.include_router(app_dashboard_module.router, prefix="/api/app/dashboard")
router.include_router(app_attendance_module.router, prefix="/api/app/attendance")
router.include_router(app_request_module.router, prefix="/api/app/request")
router.include_router(app_sidebar_module.router, prefix="/api/app/sidebar")
router.include_router(app_ai_agent_module.router, prefix="/api/app/ai-agent")