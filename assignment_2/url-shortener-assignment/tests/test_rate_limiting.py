# =============================================================================
# Tests: Rate limiting
# Scenarios: SCEN-010 (429 after rate limit exceeded)
# Requirements: REQ-API-003, NFR-SEC-001
# =============================================================================

from tests.test_data import VALID_URL_TEMPLATE


def test_requests_within_limit_succeed(client):
    """
    Scenario: Requests within the rate limit window all succeed
    Requirement: NFR-SEC-001
    Type: happy_path
    """
    for i in range(5):
        response = client.post(
            "/api/v1/shorten",
            json={"url": VALID_URL_TEMPLATE.format(n=i)},
        )
        assert response.status_code in (200, 201), f"Request {i+1} failed: {response.status_code}"


def test_rate_limit_exceeded_returns_429(client):
    """
    Scenario: SCEN-010 11th request in 60 seconds returns 429
    Requirement: REQ-API-003, NFR-SEC-001
    Type: error_case
    """
    # First 10 requests — all should succeed
    for i in range(10):
        r = client.post(
            "/api/v1/shorten",
            json={"url": VALID_URL_TEMPLATE.format(n=i)},
        )
        assert r.status_code in (200, 201), f"Request {i+1} unexpectedly failed: {r.status_code}"

    # 11th request — must be rate limited
    response = client.post(
        "/api/v1/shorten",
        json={"url": VALID_URL_TEMPLATE.format(n=99)},
    )
    assert response.status_code == 429


def test_rate_limit_response_has_correct_error_code(client):
    """
    Scenario: SCEN-010 Rate limit response contains machine-readable error code
    Requirement: REQ-API-003, REQ-API-001
    Type: error_case
    """
    for i in range(10):
        client.post("/api/v1/shorten", json={"url": VALID_URL_TEMPLATE.format(n=i)})

    response = client.post(
        "/api/v1/shorten",
        json={"url": VALID_URL_TEMPLATE.format(n=99)},
    )
    data = response.json()
    assert data["error"] == "rate_limit_exceeded"
    assert "message" in data


def test_rate_limit_response_includes_retry_after_header(client):
    """
    Scenario: SCEN-010 Rate limit 429 response includes Retry-After header
    Requirement: REQ-API-003
    Type: error_case
    """
    for i in range(10):
        client.post("/api/v1/shorten", json={"url": VALID_URL_TEMPLATE.format(n=i)})

    response = client.post(
        "/api/v1/shorten",
        json={"url": VALID_URL_TEMPLATE.format(n=99)},
    )
    assert response.status_code == 429
    # Header names are case-insensitive in HTTP
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    assert "retry-after" in headers_lower
    assert int(headers_lower["retry-after"]) > 0


def test_rate_limit_does_not_apply_to_redirect(client, existing_url):
    """
    Scenario: Rate limiting only applies to POST /shorten, not GET /{code}
    Requirement: NFR-SEC-001
    Type: edge_case
    """
    code = existing_url["short_code"]

    # Exhaust rate limit on shorten
    for i in range(10):
        client.post("/api/v1/shorten", json={"url": VALID_URL_TEMPLATE.format(n=i)})

    # Redirects should still work despite rate limit being exceeded
    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 302
