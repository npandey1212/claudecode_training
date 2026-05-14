# =============================================================================
# Implements:
#   REQ-SHORT-001 (create short URL), REQ-SHORT-003 (persist fields)
#   REQ-SHORT-004 (return existing on duplicate), REQ-SHORT-005 (retry on collision)
#   REQ-ANALY-001 (increment click_count), REQ-ANALY-002 (last_accessed_at)
#   REQ-ANALY-003 (store referrer), NFR-SEC-004 (hash client IP)
# TASK-006: Database CRUD operations
# =============================================================================

import hashlib
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import URL, URLAccessLog
from app.utils.code_generator import MAX_RETRIES, generate_short_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_utc_naive(dt: datetime) -> datetime:
    """
    Normalise any datetime to UTC naive for consistent SQLite storage.
    SQLite has no timezone awareness — we always store UTC.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_url_by_code(db: Session, short_code: str) -> URL | None:
    """
    REQ-REDIR-001, REQ-REDIR-002: look up a URL record by its short code.
    Returns None if not found (caller raises 404).
    """
    return db.query(URL).filter(URL.short_code == short_code).first()


def get_url_by_original(db: Session, original_url: str) -> URL | None:
    """
    REQ-SHORT-004: check if this long URL has already been shortened.
    Only matches active records — a deleted URL can be re-shortened.
    """
    return (
        db.query(URL)
        .filter(URL.original_url == original_url, URL.is_active == True)
        .first()
    )


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def create_short_url(
    db: Session,
    original_url: str,
    expires_at: datetime | None = None,
) -> URL:
    """
    REQ-SHORT-001, REQ-SHORT-003: persist a new short URL record.
    REQ-SHORT-005: retry code generation on collision (max MAX_RETRIES).

    Raises RuntimeError if unique code cannot be generated within MAX_RETRIES.
    """
    # REQ-SHORT-005: collision-safe code generation
    # Fix FINDING-C3-001: wrap INSERT in try/except IntegrityError to handle
    # TOCTOU race conditions where two concurrent requests generate the same code.
    # The SELECT check is an optimisation (avoids wasted INSERTs on known collisions).
    # The IntegrityError catch is the safety net for races that slip through the check.
    normalised_expires = _to_utc_naive(expires_at) if expires_at else None

    for _ in range(MAX_RETRIES):
        candidate = generate_short_code()
        if db.query(URL).filter(URL.short_code == candidate).first() is not None:
            continue  # pre-detected collision — try a new candidate

        try:
            url_record = URL(
                short_code=candidate,
                original_url=original_url,
                expires_at=normalised_expires,
            )
            db.add(url_record)
            db.commit()
            db.refresh(url_record)
            return url_record
        except IntegrityError:
            # Race condition: another request inserted the same code between
            # our SELECT check and our INSERT. Roll back and try again.
            db.rollback()
            continue

    raise RuntimeError(
        f"Failed to generate a unique short code after {MAX_RETRIES} attempts"
    )


def record_access(
    db: Session,
    url: URL,
    referrer: str | None,
    client_ip: str | None,
) -> None:
    """
    REQ-ANALY-001: increment click_count.
    REQ-ANALY-002: update last_accessed_at.
    REQ-ANALY-003: store referrer in access log.
    NFR-SEC-004: hash client IP before storing — never plaintext.
    """
    now = datetime.utcnow()

    # REQ-ANALY-001 + REQ-ANALY-002: update denormalized fields on url row
    url.click_count += 1
    url.last_accessed_at = now

    # NFR-SEC-004: one-way SHA-256 hash — cannot recover original IP
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest() if client_ip else None

    # REQ-ANALY-003: append an immutable access log entry
    log = URLAccessLog(
        url_id=url.id,
        accessed_at=now,
        referrer=referrer,
        ip_hash=ip_hash,
    )
    db.add(log)
    db.commit()


def deactivate_url(db: Session, short_code: str) -> URL | None:
    """
    Soft-delete a URL by setting is_active=False.
    Row is retained so access log history is preserved.
    Returns None if short_code not found.
    """
    url = get_url_by_code(db, short_code)
    if url is None:
        return None
    url.is_active = False
    db.commit()
    db.refresh(url)
    return url
