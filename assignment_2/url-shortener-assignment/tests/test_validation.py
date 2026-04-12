# =============================================================================
# Tests: URL validation rules
# Scenarios: SCEN-005 (invalid scheme), SCEN-009 (blocked domain)
# Requirements: REQ-VALID-001, REQ-VALID-002, REQ-VALID-003, REQ-VALID-004
#               REQ-API-001, REQ-API-002
# =============================================================================

from tests.test_data import (
    INVALID_URL_JS,
    INVALID_URL_FTP,
    INVALID_URL_DATA,
    INVALID_URL_MALFORMED,
    INVALID_URL_NO_DOMAIN,
    BLOCKED_DOMAIN_URL,
    TOO_LONG_URL,
)


def test_reject_javascript_scheme_returns_422(client):
    """
    Scenario: SCEN-005 Reject a non-HTTP/HTTPS URL scheme (javascript:)
    Requirement: REQ-VALID-001
    Type: error_case
    """
    response = client.post("/api/v1/shorten", json={"url": INVALID_URL_JS})
    assert response.status_code == 422


def test_reject_javascript_scheme_error_code(client):
    """
    Scenario: SCEN-005 Error body contains machine-readable error code
    Requirement: REQ-VALID-001, REQ-API-001
    Type: error_case
    """
    response = client.post("/api/v1/shorten", json={"url": INVALID_URL_JS})
    data = response.json()
    assert data["error"] == "invalid_url"
    assert "message" in data


def test_reject_ftp_scheme_returns_422(client):
    """
    Scenario: Reject ftp:// URL scheme
    Requirement: REQ-VALID-001
    Type: error_case
    """
    response = client.post("/api/v1/shorten", json={"url": INVALID_URL_FTP})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_url"


def test_reject_data_uri_scheme_returns_422(client):
    """
    Scenario: Reject data: URI scheme
    Requirement: REQ-VALID-001
    Type: error_case
    """
    response = client.post("/api/v1/shorten", json={"url": INVALID_URL_DATA})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_url"


def test_reject_malformed_url_returns_422(client):
    """
    Scenario: Reject a string that is not a URL
    Requirement: REQ-VALID-002
    Type: error_case
    """
    response = client.post("/api/v1/shorten", json={"url": INVALID_URL_MALFORMED})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_url"


def test_reject_url_with_no_domain_returns_422(client):
    """
    Scenario: Reject a URL with no host/domain part
    Requirement: REQ-VALID-002
    Type: edge_case
    """
    response = client.post("/api/v1/shorten", json={"url": INVALID_URL_NO_DOMAIN})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_url"


def test_reject_blocked_domain_returns_422(client):
    """
    Scenario: SCEN-009 Reject a URL with a blocklisted domain
    Requirement: REQ-VALID-003
    Type: edge_case
    """
    response = client.post("/api/v1/shorten", json={"url": BLOCKED_DOMAIN_URL})
    assert response.status_code == 422


def test_reject_blocked_domain_error_code(client):
    """
    Scenario: SCEN-009 Blocklisted domain returns specific error code
    Requirement: REQ-VALID-003, REQ-API-001
    Type: edge_case
    """
    response = client.post("/api/v1/shorten", json={"url": BLOCKED_DOMAIN_URL})
    data = response.json()
    assert data["error"] == "domain_blocked"
    assert "message" in data


def test_reject_url_exceeding_max_length(client):
    """
    Scenario: Reject a URL longer than 2048 characters
    Requirement: REQ-VALID-004
    Type: edge_case
    """
    response = client.post("/api/v1/shorten", json={"url": TOO_LONG_URL})
    assert response.status_code == 422
    assert response.json()["error"] == "url_too_long"


def test_validation_error_contains_field_detail(client):
    """
    Scenario: 422 responses include field-level detail array
    Requirement: REQ-API-002
    Type: error_case
    """
    response = client.post("/api/v1/shorten", json={"url": INVALID_URL_JS})
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0
    assert "field" in data["detail"][0]
    assert "issue" in data["detail"][0]
