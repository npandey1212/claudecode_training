# =============================================================================
# Test fixtures — generated using prompts/test-generator.yaml
# Role applied: QA Engineer
# Covers: all Gherkin scenarios SCEN-001 through SCEN-010
# =============================================================================

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import models at module level so SQLAlchemy Base has all tables registered
# BEFORE any fixture calls Base.metadata.create_all().
# Without this, the first test that runs `db_tables` before `client`
# creates an empty schema (models not yet imported), causing a 500 on first POST.
import app.models  # noqa: F401

# ---------------------------------------------------------------------------
# In-memory SQLite test engine
# StaticPool: all connections share the same underlying connection so that
# test setup (direct DB inserts) and TestClient requests see the same data.
# ---------------------------------------------------------------------------
SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_tables():
    """
    Create all tables before the test and drop them after.
    Both `client` and `db_session` depend on this so pytest creates it once.
    """
    from app.database import Base
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_tables):
    """
    FastAPI TestClient with:
    - Clean in-memory SQLite database per test (via db_tables)
    - DB dependency overridden to use test engine
    - Rate limiter state reset before and after each test
    """
    from app.main import app, _rate_limit_store
    from app.database import get_db

    _rate_limit_store.clear()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
    _rate_limit_store.clear()


@pytest.fixture
def db_session(db_tables):
    """
    Direct SQLAlchemy session for test setup that bypasses the HTTP layer.
    Used to insert records that can't be created via the API
    (e.g., URLs with past expiry dates for SCEN-007).
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Data fixtures — pre-built states used across multiple test files
# ---------------------------------------------------------------------------

@pytest.fixture
def existing_url(client):
    """
    Creates a valid short URL via the API.
    Returns the full response JSON with short_code, short_url, original_url.
    Used by redirect, analytics, expiry, and delete tests.
    """
    from tests.test_data import VALID_URL
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    assert response.status_code == 201, f"Setup failed: {response.json()}"
    return response.json()


@pytest.fixture
def expired_url(client, db_session):
    """
    Inserts a URL directly into the DB with an expiry date in the past.
    Cannot be created via the API (REQ-EXPRY-003 would reject it).
    Used by SCEN-007: redirect to expired URL returns 410.
    """
    from datetime import datetime, timedelta
    from app.models import URL

    url = URL(
        short_code="exprd1",
        original_url="https://example.com/expired-page",
        expires_at=datetime.utcnow() - timedelta(hours=1),
        is_active=True,
        click_count=0,
    )
    db_session.add(url)
    db_session.commit()
    db_session.refresh(url)
    return url
