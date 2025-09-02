"""
FastAPI Main Application for Finance Tracker

This module creates the main FastAPI application with all routes,
middleware, and configuration for the Finance Tracker web interface.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog
import os
from pathlib import Path

from .routes import treasury_router, repo_router, scoring_router, dashboard_router
from .monitoring import monitoring_router
from ..utils.s3_helper import S3DataManager
from ..visualization.plotly_charts import PlotlyChartGenerator

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Finance Tracker",
    description="Event-driven finance data pipeline with interactive dashboards",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Setup templates and static files
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Create directories if they don't exist
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize services
s3_manager = S3DataManager()
chart_generator = PlotlyChartGenerator()

# Application state
app.state.s3_manager = s3_manager
app.state.chart_generator = chart_generator

# Include routers
app.include_router(treasury_router, prefix="/api/treasury", tags=["Treasury"])
app.include_router(repo_router, prefix="/api/repo", tags=["Repo"])
app.include_router(scoring_router, prefix="/api/scoring", tags=["Scoring"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(
        "Finance Tracker API starting up",
        version="1.0.0",
        templates_dir=str(TEMPLATES_DIR),
        static_dir=str(STATIC_DIR)
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Finance Tracker API shutting down")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirect to dashboard."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Finance Tracker",
            "description": "Event-driven finance data pipeline with interactive dashboards"
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": structlog.stdlib.get_logger().info("Health check performed"),
            "services": {
                "api": "healthy",
                "s3": "unknown",  # Could add actual S3 connectivity check
                "templates": "healthy" if TEMPLATES_DIR.exists() else "unhealthy"
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler."""
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "title": "Page Not Found"},
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Custom 500 handler."""
    logger.error(
        "Internal server error",
        path=request.url.path,
        method=request.method,
        error=str(exc)
    )
    
    return templates.TemplateResponse(
        "500.html",
        {"request": request, "title": "Internal Server Error"},
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
