"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from loguru import logger

from app.api import (
    chat_router,
    auth_router,
    users_router,
    conversations_router,
    orders_router,
    health_router,
    chatbot_config_router,
    system_config_router,
    stats_router,
    customers_router,
    context_docs_router,
    scrape_router,
    assortment_router,
    logs_router,
)

# from app.api.test_router import router as test_router
# from app.api.chatbot_config_simple import router as chatbot_config_simple_router
from app.config import settings
from app.services.web_scraper_service import web_scraper
from app.utils.logging_config import logging_config, get_logger
from app.middleware.logging_middleware import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler."""
    # Setup logging first
    logging_config.setup_logging()
    app_logger = get_logger("app")
    app_logger.info("Starting Boxcatering Chatbot API...")
    # Start background web scraper
    try:
        await web_scraper.start()
        app_logger.info("Web scraper started successfully")
    except Exception as e:
        app_logger.warning(f"Failed to start web scraper: {e}")

    try:
        yield
    finally:
        # Stop background web scraper
        try:
            await web_scraper.stop()
            app_logger.info("Web scraper stopped successfully")
        except Exception as e:
            app_logger.warning(f"Failed to stop web scraper cleanly: {e}")
        app_logger.info("Shutting down Boxcatering Chatbot API...")


# Create FastAPI app
app = FastAPI(
    title="Boxcatering Chatbot API",
    description="AI-powered chatbot for boxcatering business with manager handover capabilities",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(conversations_router)
app.include_router(orders_router)
app.include_router(chatbot_config_router)
app.include_router(system_config_router)
app.include_router(stats_router)
app.include_router(customers_router)
app.include_router(context_docs_router)
app.include_router(scrape_router)
app.include_router(assortment_router)
app.include_router(logs_router)
# app.include_router(test_router)
# app.include_router(chatbot_config_simple_router)


@app.get("/static/auth.js")
async def auth_js() -> FileResponse:
    """Serve auth.js with no-store caching to ensure latest client auth logic."""
    resp = FileResponse("app/static/auth.js")
    # Prevent caching so updates take effect without cache-busting query params
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.get("/")
async def root():
    """Serve the login page."""
    return FileResponse("app/static/login.html")


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    """Serve the favicon to avoid 404s from browsers requesting /favicon.ico."""
    return FileResponse("app/static/favicon.ico")


@app.get("/login")
async def login_page():
    """Serve the login page."""
    return FileResponse("app/static/login.html")


@app.get("/dashboard")
async def dashboard_page():
    """Serve the dashboard page."""
    return FileResponse("app/static/dashboard.html")


@app.get("/chatbot-test")
async def chatbot_test_page():
    """Serve the chatbot testing page."""
    return FileResponse("app/static/chatbot-test.html")


@app.get("/chatbot-settings")
async def chatbot_settings_page():
    """Serve the chatbot configuration page."""
    return FileResponse("app/static/chatbot-settings.html")


@app.get("/order-history")
async def order_history_page():
    """Serve the order history page."""
    return FileResponse("app/static/order-history.html")


@app.get("/conversation-history")
async def conversation_history_page():
    """Serve the conversation history page."""
    return FileResponse("app/static/conversation-history.html")


@app.get("/user-management")
async def user_management_page():
    """Serve the user management page."""
    return FileResponse("app/static/user-management.html")


@app.get("/settings")
async def settings_page():
    """Serve the settings page."""
    return FileResponse("app/static/settings.html")


@app.get("/customers")
async def customers_page():
    """Serve the customers page."""
    return FileResponse("app/static/customers.html")


@app.get("/change-password")
async def change_password_page():
    """Serve the change password page."""
    return FileResponse("app/static/change-password.html")


@app.get("/assortment")
async def assortment_page():
    """Serve the assortment page."""
    return FileResponse("app/static/assortment.html")


@app.head("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_probe_head() -> Response:
    """Respond to Chrome DevTools discovery HEAD probe without 404 noise."""
    return Response(status_code=204)


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_probe_get() -> JSONResponse:
    """Respond to Chrome DevTools discovery GET probe with empty config."""
    return JSONResponse(content={})


if __name__ == "__main__":
    import uvicorn

    # # Configure loguru sinks
    # try:
    #     logger.add("logs/app.log", rotation="10 MB", retention="14 days", enqueue=True, backtrace=False, diagnose=False)
    #     logger.add("logs/prompt.log", rotation="10 MB", retention="14 days", enqueue=True, backtrace=False, diagnose=False)
    # except Exception:
    #     # Logging config should not block app start
    #     pass
    uvicorn.run(
        "app.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )
