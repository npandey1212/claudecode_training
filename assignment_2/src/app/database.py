# =============================================================================
# Implements: REQ-SHORT-003 (persistent storage), NFR-SCAL-001 (state in DB)
# TASK-001: Project setup — database engine and session
# =============================================================================

from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

# SQLite file stored in project root — swap DATABASE_URL for PostgreSQL in prod
DATABASE_URL = "sqlite:///./url_shortener.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite with FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a DB session and guarantees cleanup.
    Used via Depends(get_db) in route handlers.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
