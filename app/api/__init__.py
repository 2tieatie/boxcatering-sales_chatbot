"""API package for FastAPI routes."""

from .chat import router as chat_router
from .auth import router as auth_router
from .users import router as users_router
from .conversations import router as conversations_router
from .orders import router as orders_router
from .health import router as health_router

from .chatbot_config import router as chatbot_config_router
from .system_config import router as system_config_router
from .stats import router as stats_router
from .customers import router as customers_router
from .context_docs import router as context_docs_router
from .scrape import router as scrape_router
from .assortment import router as assortment_router
from .logs import router as logs_router

__all__ = [
    "chat_router",
    "auth_router",
    "users_router", 
    "conversations_router",
    "orders_router",
    "health_router",
    "chatbot_config_router",
    "system_config_router",
    "stats_router",
    "customers_router",
    "context_docs_router",
    "scrape_router",
    "assortment_router",
    "logs_router",
]
