from api.auth import router as auth_router
from api.dashboard import router as dashboard_router
from api.routes import router as api_router

__all__ = ["api_router", "auth_router", "dashboard_router"]

