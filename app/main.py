import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, engine
from app.redis import get_redis_client
from app.routers import auth_router, urls_router, analytics_router, redirect_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("shortx.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database tables and test Redis
    logger.info("Initializing ShortX database schema...")
    init_db()
    logger.info("Database schema initialized.")

    try:
        r = get_redis_client()
        r.ping()
        logger.info("Redis cache ready.")
    except Exception as e:
        logger.warning("Redis initialization check warning: %s", str(e))

    yield
    # Shutdown logic if needed
    logger.info("ShortX shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="High-performance URL shortener with FastAPI, PostgreSQL, Redis caching, and rate limiting.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files setup
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.api_route("/health", methods=["GET", "HEAD"], tags=["System"])
def health_check():
    """Health check for API, Database, and Redis cache."""
    from sqlalchemy import text
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    redis_ok = True
    try:
        r = get_redis_client()
        redis_ok = bool(r.ping())
    except Exception:
        redis_ok = False

    return {
        "status": "healthy" if db_ok and redis_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "redis": "connected" if redis_ok else "unreachable"
    }


# Include API Routers
app.include_router(auth_router)
app.include_router(urls_router)
app.include_router(analytics_router)


# Root route serves the single page application
@app.api_route("/", methods=["GET", "HEAD"], response_class=FileResponse, tags=["Web"])
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>ShortX URL Shortener API</h1><p>Visit /docs for OpenAPI documentation.</p>")


# Mount redirect router LAST so short codes don't shadow fixed API endpoints
app.include_router(redirect_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
