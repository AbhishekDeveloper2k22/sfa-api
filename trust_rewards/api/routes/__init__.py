from fastapi import APIRouter
from .base import router as base_router
from .web_user_auth_module import router as web_user_auth_module
from .web_skilled_worker_module import router as web_skilled_worker_module
from .web_coupon_module import router as web_coupon_module

#web


router = APIRouter()

router.include_router(
    base_router,
    prefix="",
    tags=["base"]
)

# router.include_router(app_user_auth_module.router, prefix="/api/app/auth")

#web routes
router.include_router(web_user_auth_module, prefix="/api/web/auth")
router.include_router(web_skilled_worker_module, prefix="/api/web/skilled_workers")
router.include_router(web_coupon_module, prefix="/api/web/coupons")



