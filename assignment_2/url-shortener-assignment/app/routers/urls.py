# =============================================================================
# Implements:
#   REQ-SHORT-001, REQ-SHORT-004 (POST /api/v1/shorten)
#   REQ-REDIR-001, REQ-REDIR-002, REQ-REDIR-003 (GET /{code})
#   REQ-ANALY-001, REQ-ANALY-002, REQ-ANALY-003, REQ-ANALY-004 (analytics)
#   REQ-EXPRY-002, REQ-EXPRY-003 (expiry enforcement)
#   REQ-VALID-001..004 (input validation)
#   REQ-API-001, REQ-API-002 (error response shape)
# TASK-007, TASK-008, TASK-009: Route handlers
# =============================================================================

from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.crud import (
    create_short_url,
    deactivate_url,
    get_url_by_code,
    get_url_by_original,
    record_access,
)
from app.database import get_db
from app.schemas import DeleteResponse, ShortenRequest, URLStatsResponse
from app.utils.validator import validate_url

router = APIRouter()


def _base_url(request: Request) -> str:
    """Extract base URL (scheme + host) from the incoming request."""
    return str(request.base_url).rstrip("/")


def _url_to_dict(url, base_url: str) -> dict:
    """
    Serialise a URL ORM record to the ShortenResponse shape.
    Handles datetime → ISO string conversion for JSONResponse.
    """
    return {
        "short_code": url.short_code,
        "short_url": f"{base_url}/{url.short_code}",
        "original_url": url.original_url,
        "created_at": url.created_at.isoformat(),
        "expires_at": url.expires_at.isoformat() if url.expires_at else None,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/shorten — create a short URL
# REQ-SHORT-001, REQ-SHORT-004, REQ-EXPRY-003, REQ-VALID-001..004
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/shorten",
    status_code=201,
    responses={
        200: {"description": "URL already shortened — returns existing record"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
    },
)
def shorten_url(
    payload: ShortenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # REQ-VALID-001, REQ-VALID-002, REQ-VALID-003, REQ-VALID-004
    is_valid, error_code = validate_url(payload.url)
    if not is_valid:
        error_messages = {
            "invalid_url": "URL must use http or https scheme and be well-formed",
            "url_too_long": "URL must not exceed 2048 characters",
            "domain_blocked": "This domain is not permitted",
        }
        raise HTTPException(
            status_code=422,
            detail={
                "error": error_code,
                "message": error_messages.get(error_code, "Invalid URL"),
                "detail": [{"field": "url", "issue": error_code}],
            },
        )

    # REQ-EXPRY-003: reject if expiry date is already in the past
    if payload.expires_at:
        expires_naive = payload.expires_at.replace(tzinfo=None) if payload.expires_at.tzinfo else payload.expires_at
        if expires_naive <= datetime.utcnow():
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_expiry",
                    "message": "expires_at must be a future datetime",
                    "detail": [{"field": "expires_at", "issue": "invalid_expiry"}],
                },
            )

    base_url = _base_url(request)

    # REQ-SHORT-004: return existing short URL if this long URL was already shortened
    existing = get_url_by_original(db, payload.url)
    if existing:
        return JSONResponse(status_code=200, content=_url_to_dict(existing, base_url))

    # REQ-SHORT-001, REQ-SHORT-003: create and persist new short URL
    url_record = create_short_url(db, payload.url, payload.expires_at)
    return JSONResponse(status_code=201, content=_url_to_dict(url_record, base_url))


# ---------------------------------------------------------------------------
# GET /api/v1/urls/{code}/stats — analytics for a short URL
# REQ-ANALY-004
# NOTE: this route MUST be registered before GET /{code} so FastAPI
#       matches the more specific path first.
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/urls/{code}/stats",
    response_model=URLStatsResponse,
    responses={404: {"description": "Short code not found"}},
)
def get_stats(code: str, db: Session = Depends(get_db)):
    # REQ-ANALY-004: return analytics fields for an existing URL
    url = get_url_by_code(db, code)
    if url is None or not url.is_active:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Short URL not found"},
        )

    return URLStatsResponse(
        short_code=url.short_code,
        original_url=url.original_url,
        click_count=url.click_count,
        created_at=url.created_at,
        last_accessed_at=url.last_accessed_at,
        expires_at=url.expires_at,
        is_active=url.is_active,
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/urls/{code} — soft-delete a short URL
# ---------------------------------------------------------------------------

@router.delete(
    "/api/v1/urls/{code}",
    response_model=DeleteResponse,
    responses={404: {"description": "Short code not found"}},
)
def delete_url(code: str, db: Session = Depends(get_db)):
    url = deactivate_url(db, code)
    if url is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Short URL not found"},
        )
    return DeleteResponse(message="Short URL deactivated")


# ---------------------------------------------------------------------------
# GET /{code} — redirect to original URL
# REQ-REDIR-001, REQ-REDIR-002, REQ-REDIR-003, REQ-EXPRY-002
# REQ-ANALY-001, REQ-ANALY-002, REQ-ANALY-003
#
# IMPORTANT: registered LAST — single-segment catch-all.
# Does NOT conflict with /api/v1/... paths (different segment count).
# ---------------------------------------------------------------------------

@router.get(
    "/{code}",
    responses={
        302: {"description": "Redirect to original URL"},
        404: {"description": "Short code not found"},
        410: {"description": "Short URL has expired"},
    },
)
def redirect_url(code: str, request: Request, db: Session = Depends(get_db)):
    # REQ-REDIR-002: 404 if code does not exist or has been soft-deleted
    url = get_url_by_code(db, code)
    if url is None or not url.is_active:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Short URL not found"},
        )

    # REQ-REDIR-003, REQ-EXPRY-002: 410 if URL is past its expiry date
    if url.expires_at and url.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=410,
            detail={"error": "url_expired", "message": "This short URL has expired"},
        )

    # FINDING-001 fix: re-validate scheme at redirect time (defence-in-depth)
    # Protects against future blocklist bypass or DB-level URL tampering
    parsed = urlparse(url.original_url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Stored URL has invalid scheme"},
        )

    # REQ-ANALY-001, REQ-ANALY-002, REQ-ANALY-003: record this click
    # FINDING-002 fix: truncate referrer to prevent DB bloat via oversized header
    raw_referrer = request.headers.get("referer")
    referrer = raw_referrer[:2048] if raw_referrer else None
    client_ip = request.client.host if request.client else None
    record_access(db, url, referrer, client_ip)

    # REQ-REDIR-001: 302 redirect to original URL
    return RedirectResponse(url=url.original_url, status_code=302)
