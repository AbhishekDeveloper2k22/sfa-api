from fastapi import APIRouter
from .base import router as base_router
from .web_user_auth_module import router as web_user_auth_module
from .web_skilled_worker_module import router as web_skilled_worker_module
from .web_coupon_module import router as web_coupon_module
from .app_user_auth_module import router as app_user_auth_module
from .app_coupon_module import router as app_coupon_module

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

#web routes
router.include_router(web_user_auth_module, prefix="/api/web/auth")
router.include_router(web_skilled_worker_module, prefix="/api/web/skilled_workers")
router.include_router(web_coupon_module, prefix="/api/web/coupons")



