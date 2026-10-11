import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.auth_router import router as auth_router
from app.api.metrics_router import router as metrics_router
from app.api.system_router import router as system_router
from app.api.logs_router import router as logs_router
from app.api.editor_router import router as editor_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    logger.info("Initializing database schema...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    # Shutdown
    logger.info("Application shutting down.")

app = FastAPI(
    title="Ubuntu-LS Monitor",
    description="High-security system resource and operations dashboard for Ubuntu home server.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Global safe error handler (prevents stack trace leakage)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the administrator."}
    )

# Include API routers
app.include_router(auth_router)
app.include_router(metrics_router)
app.include_router(system_router)
app.include_router(logs_router)
app.include_router(editor_router)

# Healthcheck
@app.get("/api/health")
def healthcheck():
    return {"status": "ok", "app": "ubuntu-ls-monitor"}

# Serve frontend build if present
frontend_dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist_dir.exists() and frontend_dist_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Do not intercept API routes
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        file_path = frontend_dist_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        index_file = frontend_dist_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        return JSONResponse(status_code=404, content={"detail": "Frontend assets not found"})
