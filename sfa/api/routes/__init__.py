from fastapi import APIRouter
from .base import router as base_router
from sfa.api.routes import employee_module
from sfa.api.routes import app_user_auth_module
from sfa.api.routes import app_dashboard_module
from sfa.api.routes import app_attendance_module
from sfa.api.routes import app_request_module
from sfa.api.routes import app_sidebar_module
from sfa.api.routes import attendance_module
from sfa.api.routes import app_ai_agent_module
from sfa.api.routes import app_beat_plan_module

#web
from sfa.api.routes import web_user_module
from sfa.api.routes import web_user_auth_module
from sfa.api.routes import web_category_module
from sfa.api.routes import web_product_module
from sfa.api.routes import web_lead_module
from sfa.api.routes import web_customer_module
from sfa.api.routes import web_attendance_module
from sfa.api.routes import web_location_module
from sfa.api.routes import web_beat_plan_module
from sfa.api.routes import web_followup_module
from sfa.api.routes import app_master_module
from sfa.api.routes import app_customer_module
from sfa.api.routes import app_order_module
from sfa.api.routes import app_otp_module

router = APIRouter()

router.include_router(
    base_router,
    prefix="",
    tags=["base"]
)

router.include_router(employee_module.router, prefix="/api/employees")
router.include_router(app_user_auth_module.router, prefix="/api/app/auth")
router.include_router(app_dashboard_module.router, prefix="/api/app/dashboard")
router.include_router(app_attendance_module.router, prefix="/api/app/attendance")
router.include_router(app_request_module.router, prefix="/api/app/request")
router.include_router(app_sidebar_module.router, prefix="/api/app/sidebar")
router.include_router(attendance_module.router, prefix="/api/attendance")
router.include_router(app_ai_agent_module.router, prefix="/api/app/ai_agent")
router.include_router(app_beat_plan_module.router, prefix="/api/app/beat_plan")
router.include_router(app_master_module.router, prefix="/api/app/master")
router.include_router(app_customer_module.router, prefix="/api/app/customer")
router.include_router(app_order_module.router, prefix="/api/app/order")
router.include_router(app_otp_module.router, prefix="/api/app/otp")

#web routes
router.include_router(web_user_module.router, prefix="/api/web/user")
router.include_router(web_user_auth_module.router, prefix="/api/web/auth")
router.include_router(web_category_module.router, prefix="/api/web/category")
router.include_router(web_product_module.router, prefix="/api/web/product")
router.include_router(web_lead_module.router, prefix="/api/web/lead")
router.include_router(web_customer_module.router, prefix="/api/web/customer")
router.include_router(web_attendance_module.router, prefix="/api/web/attendance")
router.include_router(web_location_module.router, prefix="/api/web/location")
router.include_router(web_beat_plan_module.router, prefix="/api/web/beat_plan")
router.include_router(web_followup_module.router, prefix="/api/web/followup")


