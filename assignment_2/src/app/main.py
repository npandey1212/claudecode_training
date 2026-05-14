# =============================================================================
# Implements:
#   REQ-API-001 (uniform error response shape for all 4xx/5xx)
#   REQ-API-003 (rate limiting with 429 + Retry-After)
#   NFR-SEC-001 (10 req/min per IP on shorten endpoint)
#   NFR-SEC-002 (no internal error details in responses)
# TASK-010, TASK-011: Rate limiting middleware and app wiring
# =============================================================================

import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.routers import urls

# Create all tables on startup (idempotent — safe to call repeatedly)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener Service",
    version="1.0.0",
    description="Spec-driven URL shortener — assignment project",
)


# ---------------------------------------------------------------------------
# Rate limiting middleware
# NFR-SEC-001, REQ-API-003: 10 POST /shorten requests per IP per 60 seconds
# ---------------------------------------------------------------------------

# In-memory store: { ip_address: [timestamp, ...] }
# Limitation: resets on restart; production should use Redis with TTL keys.
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

RATE_LIMIT_MAX = 10      # max requests
RATE_LIMIT_WINDOW = 60   # seconds


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    NFR-SEC-001: enforce rate limit on POST /api/v1/shorten only.
    Sliding window algorithm — counts requests in the last 60 seconds.
    """
    if request.method == "POST" and request.url.path == "/api/v1/shorten":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # Evict timestamps outside the current window
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip] if t > window_start
        ]

        if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX:
            oldest = _rate_limit_store[client_ip][0]
            retry_after = max(1, int(RATE_LIMIT_WINDOW - (now - oldest)))
            # REQ-API-003: include Retry-After header
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please wait before trying again.",
                },
                headers={"Retry-After": str(retry_after)},
            )

        _rate_limit_store[client_ip].append(now)

    return await call_next(request)


# ---------------------------------------------------------------------------
# Exception handlers
# REQ-API-001: all errors return { "error": str, "message": str }
# NFR-SEC-002: no stack traces or internal details exposed
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    REQ-API-001: normalise HTTPException to { error, message } shape.
    Route handlers raise HTTPException with detail as a dict for full control.
    """
    if isinstance(exc.detail, dict):
        # Route handler provided a structured dict — use it directly
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    # Fallback for any unstructured HTTPException
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    REQ-API-002: Pydantic validation errors return 422 with field-level detail.
    Converts Pydantic's error format to our { error, message, detail } shape.
    """
    field_errors = [
        {"field": e["loc"][-1] if e["loc"] else "body", "issue": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Input validation failed",
            "detail": field_errors,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    NFR-SEC-002: catch-all handler — never expose internal error details.
    Logs internally (in production, send to observability platform).
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred. Please try again.",
        },
    )


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

app.include_router(urls.router)
