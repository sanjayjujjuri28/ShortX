from app.routers.auth import router as auth_router
from app.routers.urls import router as urls_router
from app.routers.analytics import router as analytics_router
from app.routers.redirect import router as redirect_router

__all__ = ["auth_router", "urls_router", "analytics_router", "redirect_router"]
