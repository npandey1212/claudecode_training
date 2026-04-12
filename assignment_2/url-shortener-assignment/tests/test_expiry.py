# =============================================================================
# Tests: URL expiry enforcement
# Scenarios: SCEN-007 (expired redirect → 410), SCEN-008 (past expiry on create → 422)
# Requirements: REQ-EXPRY-001, REQ-EXPRY-002, REQ-EXPRY-003, REQ-REDIR-003
# =============================================================================

from tests.test_data import VALID_URL, PAST_EXPIRY, FUTURE_EXPIRY, EXPIRED_SHORT_CODE


def test_redirect_expired_url_returns_410(client, expired_url):
    """
    Scenario: SCEN-007 Redirect to an expired URL returns 410 Gone
    Requirement: REQ-REDIR-003, REQ-EXPRY-002
    Type: edge_case
    """
    response = client.get(f"/{EXPIRED_SHORT_CODE}", follow_redirects=False)
    assert response.status_code == 410


def test_redirect_expired_url_error_body(client, expired_url):
    """
    Scenario: SCEN-007 410 response has correct error body
    Requirement: REQ-REDIR-003, REQ-API-001
    Type: edge_case
    """
    response = client.get(f"/{EXPIRED_SHORT_CODE}", follow_redirects=False)
    data = response.json()
    assert data["error"] == "url_expired"
    assert "message" in data


def test_redirect_expired_url_does_not_increment_click_count(client, expired_url):
    """
    Scenario: SCEN-007 Expired URL redirect attempt does not increment click_count
    Requirement: REQ-EXPRY-002
    Type: edge_case
    """
    # Attempt redirect — should 410
    client.get(f"/{EXPIRED_SHORT_CODE}", follow_redirects=False)

    # Stats should still show 0 clicks (no successful redirect occurred)
    stats = client.get(f"/api/v1/urls/{EXPIRED_SHORT_CODE}/stats")
    assert stats.status_code == 200
    assert stats.json()["click_count"] == 0


def test_create_url_with_past_expiry_returns_422(client):
    """
    Scenario: SCEN-008 Reject creation of a URL with a past expiry date
    Requirement: REQ-EXPRY-003
    Type: edge_case
    """
    response = client.post(
        "/api/v1/shorten",
        json={"url": VALID_URL, "expires_at": PAST_EXPIRY},
    )
    assert response.status_code == 422


def test_create_url_with_past_expiry_error_code(client):
    """
    Scenario: SCEN-008 Past expiry returns correct error code
    Requirement: REQ-EXPRY-003, REQ-API-002
    Type: edge_case
    """
    response = client.post(
        "/api/v1/shorten",
        json={"url": VALID_URL, "expires_at": PAST_EXPIRY},
    )
    data = response.json()
    assert data["error"] == "invalid_expiry"


def test_create_url_with_future_expiry_is_accepted(client):
    """
    Scenario: URL with a valid future expiry date is accepted
    Requirement: REQ-EXPRY-001
    Type: happy_path
    """
    response = client.post(
        "/api/v1/shorten",
        json={"url": VALID_URL, "expires_at": FUTURE_EXPIRY},
    )
    assert response.status_code == 201
    assert response.json()["expires_at"] is not None


def test_create_url_without_expiry_never_expires(client):
    """
    Scenario: URL without expires_at has null expiry (never expires)
    Requirement: REQ-EXPRY-001
    Type: happy_path
    """
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    assert response.status_code == 201
    assert response.json()["expires_at"] is None
