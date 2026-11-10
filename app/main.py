from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.core.exceptions import HRMSException
from app.routers import (
    auth,
    users,
    departments,
    attendance,
    leaves,
    reviews,
    reports,
    audit,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables are created
    init_db()
    yield
    # Shutdown logic if any


app = FastAPI(
    title=settings.APP_NAME,
    description="""
# Comprehensive Human Resources Management System (HRMS) API

A robust, secure, and scalable backend for modern enterprise HR operations.

### Key Capabilities:
- **Role-Based Access Control (RBAC):** Distinct permissions for `admin`, `manager`, and `employee`.
- **Employee Lifecycle Tracking:** Onboarding, offboarding, profile updates, and reporting lines.
- **Organization Hierarchy:** Department and manager association with team reporting.
- **Attendance Management:** Daily check-ins, check-outs, automatic half-day calculation, and geo/ip logging.
- **Leave Management:** Sick, Casual, Annual, and Unpaid leave workflows with automated balance checks and multi-tier approval.
- **Performance Appraisals:** Quantitative ratings (1-5) and qualitative quarterly/annual reviews.
- **Audit Logging & Analytics:** Immutable audit trails and real-time executive HR summary reports.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized Exception Handlers
@app.exception_handler(HRMSException)
async def hrms_exception_handler(request: Request, exc: HRMSException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Format pydantic validation errors nicely
    clean_errors = []
    for err in exc.errors():
        loc = " -> ".join([str(x) for x in err.get("loc", []) if x != "body"])
        clean_errors.append({
            "field": loc or "body",
            "message": err.get("msg"),
            "type": err.get("type"),
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed. Please check the supplied fields.",
                "details": clean_errors,
            },
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": None,
            },
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    details = traceback.format_exc() if settings.DEBUG else None
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request.",
                "details": details,
            },
        },
    )


# Health & Info Endpoints
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "api_version": "v1",
    }


@app.get("/", tags=["System"])
def root_info():
    return {
        "name": settings.APP_NAME,
        "docs": "/docs",
        "redoc": "/redoc",
        "api_v1_prefix": settings.API_V1_STR,
    }


# Include V1 Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(departments.router, prefix=settings.API_V1_STR)
app.include_router(attendance.router, prefix=settings.API_V1_STR)
app.include_router(leaves.router, prefix=settings.API_V1_STR)
app.include_router(reviews.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
