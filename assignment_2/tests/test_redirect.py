# =============================================================================
# Tests: URL Redirect behaviour
# Scenarios: SCEN-002 (successful redirect), SCEN-006 (404 for unknown code)
# Requirements: REQ-REDIR-001, REQ-REDIR-002, REQ-ANALY-001, REQ-ANALY-002, REQ-ANALY-003
# =============================================================================

from tests.test_data import VALID_URL, NONEXISTENT_CODE


def test_redirect_active_url_returns_302(client, existing_url):
    """
    Scenario: SCEN-002 Successfully redirect a valid short URL
    Requirement: REQ-REDIR-001
    Type: happy_path
    """
    code = existing_url["short_code"]
    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 302


def test_redirect_location_header_is_original_url(client, existing_url):
    """
    Scenario: SCEN-002 Location header points to the original URL
    Requirement: REQ-REDIR-001
    Type: happy_path
    """
    code = existing_url["short_code"]
    response = client.get(f"/{code}", follow_redirects=False)
    assert response.headers["location"] == VALID_URL


def test_redirect_increments_click_count(client, existing_url):
    """
    Scenario: SCEN-002 click_count incremented on each redirect
    Requirement: REQ-ANALY-001
    Type: happy_path
    """
    code = existing_url["short_code"]

    # 3 redirects
    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)

    stats = client.get(f"/api/v1/urls/{code}/stats").json()
    assert stats["click_count"] == 3


def test_redirect_updates_last_accessed_at(client, existing_url):
    """
    Scenario: SCEN-002 last_accessed_at is set after first redirect
    Requirement: REQ-ANALY-002
    Type: happy_path
    """
    code = existing_url["short_code"]

    # Before redirect — last_accessed_at should be null
    stats_before = client.get(f"/api/v1/urls/{code}/stats").json()
    assert stats_before["last_accessed_at"] is None

    # After redirect — last_accessed_at should be set
    client.get(f"/{code}", follow_redirects=False)
    stats_after = client.get(f"/api/v1/urls/{code}/stats").json()
    assert stats_after["last_accessed_at"] is not None


def test_redirect_captures_referrer_header(client, existing_url):
    """
    Scenario: SCEN-002 Referer header is captured in access log
    Requirement: REQ-ANALY-003
    Type: happy_path
    Note: We verify the redirect succeeds when Referer is sent.
          Direct log inspection would require a db_session fixture.
    """
    code = existing_url["short_code"]
    response = client.get(
        f"/{code}",
        follow_redirects=False,
        headers={"Referer": "https://www.google.com"},
    )
    # Redirect still succeeds with a Referer header
    assert response.status_code == 302


def test_redirect_nonexistent_code_returns_404(client):
    """
    Scenario: SCEN-006 Return 404 for a non-existent short code
    Requirement: REQ-REDIR-002
    Type: error_case
    """
    response = client.get(f"/{NONEXISTENT_CODE}", follow_redirects=False)
    assert response.status_code == 404


def test_redirect_404_has_correct_error_body(client):
    """
    Scenario: SCEN-006 404 response has structured error body
    Requirement: REQ-REDIR-002, REQ-API-001
    Type: error_case
    """
    response = client.get(f"/{NONEXISTENT_CODE}", follow_redirects=False)
    data = response.json()
    assert data["error"] == "not_found"
    assert "message" in data


def test_redirect_does_not_count_failed_attempts(client, existing_url):
    """
    Scenario: 404 redirects do not affect click_count of existing URLs
    Requirement: REQ-ANALY-001
    Type: edge_case
    """
    code = existing_url["short_code"]

    # Redirect to wrong code — should 404 and not affect existing URL
    client.get(f"/{NONEXISTENT_CODE}", follow_redirects=False)

    stats = client.get(f"/api/v1/urls/{code}/stats").json()
    assert stats["click_count"] == 0
