"""API routes for web UI."""

from swecli.web.routes.chat import router as chat_router
from swecli.web.routes.sessions import router as sessions_router
from swecli.web.routes.config import router as config_router

__all__ = ["chat_router", "sessions_router", "config_router"]
