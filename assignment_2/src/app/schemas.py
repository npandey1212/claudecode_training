# =============================================================================
# Implements: REQ-API-001 (error response shape), REQ-API-002 (422 details)
#             REQ-EXPRY-001 (optional expires_at in request)
# TASK-003: Pydantic request/response schemas
# =============================================================================

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ShortenRequest(BaseModel):
    """
    REQ-SHORT-001: accepts url (required) and optional expires_at.
    url is typed as str (not HttpUrl) so our validator returns
    domain-specific error codes instead of Pydantic's generic messages.
    """
    url: str
    expires_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ShortenResponse(BaseModel):
    """
    Returned on 201 (new URL) or 200 (duplicate URL).
    REQ-SHORT-001, REQ-SHORT-003.
    """
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class URLStatsResponse(BaseModel):
    """
    REQ-ANALY-004: analytics response for GET /api/v1/urls/{code}/stats.
    """
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    last_accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool


class DeleteResponse(BaseModel):
    """Response body for DELETE /api/v1/urls/{code}."""
    message: str


class ErrorResponse(BaseModel):
    """
    REQ-API-001: every error response MUST have these two fields.
    Used in OpenAPI docs via responses={} declarations.
    """
    error: str
    message: str
