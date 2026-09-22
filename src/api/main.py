from __future__ import annotations
"""FastAPI application entry point for the unified SkillMatch service."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.security import verify_api_key
from src.api.v1.routers import api_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.core.redis import is_redis_available, redis_manager
from src.db.base import init_db
from src.middleware.rate_limit_middleware import RateLimitMiddleware
from src.schemas.cv import ExtractionErrorResponse

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize logging, persistence, and release shared resources on shutdown."""
    setup_logging()
    init_db()
    if is_redis_available():
        logger.info("Redis is available at %s", settings.REDIS_URL)
    else:
        logger.warning("Redis is unavailable; using local fallbacks where supported")
    yield
    redis_manager.close()


app = FastAPI(
    title="SkillMatch AI Services API",
    description=(
        "Production AI Services API for SkillMatch. The canonical AI-Serv5 CV "
        "extraction pipeline powers CV, matching, interview, and review features."
    ),
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Rate-limit feature endpoints centrally. The canonical CV router keeps its
# existing dependency-based limiter so its original contract remains intact.
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOWED_METHODS,
    allow_headers=settings.CORS_ALLOWED_HEADERS,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        detail = str(exc.detail.get("detail", exc.detail))
        error_code = str(exc.detail.get("error_code", "HTTP_ERROR"))
    else:
        detail = str(exc.detail)
        status_code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            413: "FILE_TOO_LARGE",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_SERVER_ERROR",
        }
        error_code = status_code_map.get(exc.status_code, "HTTP_ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content=ExtractionErrorResponse(detail=detail, error_code=error_code).model_dump(),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    detail = "; ".join(
        f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content=ExtractionErrorResponse(detail=detail, error_code="VALIDATION_ERROR").model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "error_code": "INTERNAL_SERVER_ERROR",
            "detail": "An unexpected internal server error occurred.",
        },
    )


# Mount aggregated API v1 router. All /api/v1 endpoints inherit API-key verification.
# CV extraction additionally enforces its route-level rate limiter dependency.
app.include_router(
    api_router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)],
)


# Ensure database-backed feature routes work for TestClient and standalone local
# invocations even when the FastAPI server lifespan is not explicitly entered.
init_db()


@app.get("/health", tags=["System Health"], summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "active_model": settings.llm.model_name,
        "redis": {
            "status": "connected" if is_redis_available() else "unavailable",
            "url": settings.REDIS_URL,
        },
        "features": {
            "cv_profile_extraction": "active",
            "skill_gap_analysis": "active",
            "interview_coach": "active",
            "review_queue": "active",
            "job_description_understanding": "active",
            "personalized_job_recommendations": "active",
        },
    }


@app.get("/", tags=["Root"], summary="API Root")
async def root():
    return {
        "message": "Welcome to SkillMatch AI Services API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "version": settings.VERSION,
    }


if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
