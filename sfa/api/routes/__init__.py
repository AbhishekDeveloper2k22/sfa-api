from fastapi import APIRouter
from .base import router as base_router
from sfa.api.routes import employee_module
from sfa.api.routes import user_auth_module
from sfa.api.routes import app_user_auth_module
from sfa.api.routes import app_dashboard_module
from sfa.api.routes import app_attendance_module
from sfa.api.routes import app_request_module
from sfa.api.routes import app_sidebar_module
from sfa.api.routes import attendance_module
from sfa.api.routes import app_ai_agent_module

#web
from sfa.api.routes import web_user_module
from sfa.api.routes import web_category_module

router = APIRouter()

router.include_router(
    base_router,
    prefix="",
    tags=["base"]
)

router.include_router(employee_module.router, prefix="/api/employees")
router.include_router(user_auth_module.router,prefix="/api/auth")
router.include_router(app_user_auth_module.router, prefix="/api/app/auth")
router.include_router(app_dashboard_module.router, prefix="/api/app/dashboard")
router.include_router(app_attendance_module.router, prefix="/api/app/attendance")
router.include_router(app_request_module.router, prefix="/api/app/request")
router.include_router(app_sidebar_module.router, prefix="/api/app/sidebar")
router.include_router(attendance_module.router, prefix="/api/attendance")
router.include_router(app_ai_agent_module.router, prefix="/api/app/ai-agent")

#web routes
router.include_router(web_user_module.router, prefix="/api/web")
router.include_router(web_category_module.router, prefix="/api/web")
