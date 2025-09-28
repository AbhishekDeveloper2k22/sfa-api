from fastapi import APIRouter
from .base import router as base_router
from .web_user_auth_module import router as web_user_auth_module
from .web_skilled_worker_module import router as web_skilled_worker_module
from .web_coupon_module import router as web_coupon_module
from .web_master_module import router as web_master_module
from .web_redeem_request_module import router as web_redeem_request_module
from .app_user_auth_module import router as app_user_auth_module
from .app_coupon_module import router as app_coupon_module
from .app_master_module import router as app_master_module
from .app_redeem_module import router as app_redeem_module

#web


router = APIRouter()

router.include_router(
    base_router,
    prefix="",
    tags=["base"]
)

#app routes
router.include_router(app_user_auth_module, prefix="/api/app/auth")
router.include_router(app_coupon_module, prefix="/api/app/coupons")
router.include_router(app_master_module, prefix="/api/app/master")
router.include_router(app_redeem_module, prefix="/api/app/redeem")

#web routes
router.include_router(web_user_auth_module, prefix="/api/web/auth")
router.include_router(web_skilled_worker_module, prefix="/api/web/skilled_workers")
router.include_router(web_coupon_module, prefix="/api/web/coupons")
router.include_router(web_master_module, prefix="/api/web/master")
router.include_router(web_redeem_request_module, prefix="/api/web/redeem_requests")



