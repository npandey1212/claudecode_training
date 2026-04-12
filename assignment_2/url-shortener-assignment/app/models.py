# =============================================================================
# Implements:
#   REQ-SHORT-002 (short_code length), REQ-SHORT-003 (stored fields)
#   REQ-EXPRY-001 (optional expires_at), REQ-ANALY-001 (click_count)
#   REQ-ANALY-002 (last_accessed_at), REQ-ANALY-003 (referrer log)
#   NFR-SEC-004 (IP stored as hash, never plaintext)
# TASK-002: SQLAlchemy ORM models
# =============================================================================

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.orm import relationship
from app.database import Base


class URL(Base):
    """
    Core table — one row per shortened URL.
    REQ-SHORT-003: stores original_url, short_code, created_at.
    """
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # REQ-SHORT-002: exactly 6 alphanumeric chars — enforced in code_generator
    short_code = Column(String(10), unique=True, nullable=False, index=True)

    # REQ-SHORT-003: the original long URL — indexed for duplicate detection
    original_url = Column(Text, nullable=False, index=True)

    # REQ-SHORT-003: creation timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # REQ-EXPRY-001: NULL means URL never expires
    expires_at = Column(DateTime, nullable=True)

    # Soft-delete flag — False means 404 on redirect (not a hard delete)
    is_active = Column(Boolean, nullable=False, default=True)

    # REQ-ANALY-001: denormalized click counter for O(1) stats reads
    click_count = Column(Integer, nullable=False, default=0)

    # REQ-ANALY-002: timestamp of most recent redirect
    last_accessed_at = Column(DateTime, nullable=True)

    access_logs = relationship("URLAccessLog", back_populates="url")


class URLAccessLog(Base):
    """
    Append-only event log — one row per redirect event.
    REQ-ANALY-003: captures referrer per click.
    NFR-SEC-004: IP stored as SHA-256 hash, never plaintext.
    """
    __tablename__ = "url_access_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK to urls — indexed for fast per-URL log lookups
    url_id = Column(Integer, ForeignKey("urls.id"), nullable=False, index=True)

    accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # REQ-ANALY-003: HTTP Referer header captured at redirect time
    referrer = Column(Text, nullable=True)

    # NFR-SEC-004: SHA-256 hash of client IP — never store plaintext IP
    ip_hash = Column(String(64), nullable=True)

    url = relationship("URL", back_populates="access_logs")
