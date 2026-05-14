# =============================================================================
# Tests: URL Shortening core
# Scenarios: SCEN-001 (happy path shorten), SCEN-004 (duplicate URL)
# Requirements: REQ-SHORT-001, REQ-SHORT-002, REQ-SHORT-003, REQ-SHORT-004, REQ-SHORT-005
# =============================================================================

import re
from tests.test_data import VALID_URL, VALID_URL_2


def test_shorten_valid_url_returns_201(client):
    """
    Scenario: SCEN-001 Successfully shorten a valid URL
    Requirement: REQ-SHORT-001
    Type: happy_path
    """
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    assert response.status_code == 201


def test_shorten_response_contains_short_code(client):
    """
    Scenario: SCEN-001 Response includes a short_code field
    Requirement: REQ-SHORT-001, REQ-SHORT-002
    Type: happy_path
    """
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert "original_url" in data
    assert "created_at" in data


def test_shorten_short_code_is_6_alphanumeric_chars(client):
    """
    Scenario: SCEN-001 Short code matches the required format
    Requirement: REQ-SHORT-002
    Type: happy_path
    """
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    short_code = response.json()["short_code"]
    assert len(short_code) == 6
    assert re.match(r"^[a-zA-Z0-9]{6}$", short_code), f"Code '{short_code}' does not match ^[a-zA-Z0-9]{{6}}$"


def test_shorten_short_url_ends_with_code(client):
    """
    Scenario: SCEN-001 short_url is base_url + short_code
    Requirement: REQ-SHORT-001
    Type: happy_path
    """
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    data = response.json()
    assert data["short_url"].endswith(data["short_code"])


def test_shorten_original_url_preserved(client):
    """
    Scenario: SCEN-001 original_url in response matches submitted URL
    Requirement: REQ-SHORT-003
    Type: happy_path
    """
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    assert response.json()["original_url"] == VALID_URL


def test_shorten_created_at_is_present(client):
    """
    Scenario: SCEN-001 created_at field is set on creation
    Requirement: REQ-SHORT-003
    Type: happy_path
    """
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    assert response.json()["created_at"] is not None


def test_shorten_expires_at_null_when_not_provided(client):
    """
    Scenario: SCEN-001 expires_at is null when not submitted
    Requirement: REQ-EXPRY-001
    Type: happy_path
    """
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    assert response.json()["expires_at"] is None


def test_shorten_duplicate_url_returns_200(client):
    """
    Scenario: SCEN-004 Submitting the same URL twice returns 200 (not 201)
    Requirement: REQ-SHORT-004
    Type: happy_path
    """
    client.post("/api/v1/shorten", json={"url": VALID_URL})
    response = client.post("/api/v1/shorten", json={"url": VALID_URL})
    assert response.status_code == 200


def test_shorten_duplicate_url_returns_same_code(client):
    """
    Scenario: SCEN-004 Submitting the same URL twice returns the same short_code
    Requirement: REQ-SHORT-004
    Type: happy_path
    """
    r1 = client.post("/api/v1/shorten", json={"url": VALID_URL})
    r2 = client.post("/api/v1/shorten", json={"url": VALID_URL})
    assert r1.json()["short_code"] == r2.json()["short_code"]


def test_shorten_different_urls_get_different_codes(client):
    """
    Scenario: Two distinct URLs produce distinct short codes
    Requirement: REQ-SHORT-005
    Type: edge_case
    """
    r1 = client.post("/api/v1/shorten", json={"url": VALID_URL})
    r2 = client.post("/api/v1/shorten", json={"url": VALID_URL_2})
    assert r1.json()["short_code"] != r2.json()["short_code"]


def test_shorten_with_valid_future_expiry(client):
    """
    Scenario: URL with a future expiry date is accepted
    Requirement: REQ-EXPRY-001
    Type: happy_path
    """
    from tests.test_data import FUTURE_EXPIRY
    response = client.post("/api/v1/shorten", json={"url": VALID_URL, "expires_at": FUTURE_EXPIRY})
    assert response.status_code == 201
    assert response.json()["expires_at"] is not None
