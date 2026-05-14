# =============================================================================
# Tests: Analytics endpoint
# Scenarios: SCEN-003 (retrieve analytics after clicks)
# Requirements: REQ-ANALY-004, REQ-ANALY-001, REQ-ANALY-002
# =============================================================================

from tests.test_data import VALID_URL, NONEXISTENT_CODE


def test_stats_returns_200_for_existing_url(client, existing_url):
    """
    Scenario: SCEN-003 Stats endpoint returns 200 for a valid short code
    Requirement: REQ-ANALY-004
    Type: happy_path
    """
    code = existing_url["short_code"]
    response = client.get(f"/api/v1/urls/{code}/stats")
    assert response.status_code == 200


def test_stats_response_has_all_required_fields(client, existing_url):
    """
    Scenario: SCEN-003 Stats response contains all mandatory fields
    Requirement: REQ-ANALY-004
    Type: happy_path
    """
    code = existing_url["short_code"]
    data = client.get(f"/api/v1/urls/{code}/stats").json()

    assert "short_code" in data
    assert "original_url" in data
    assert "click_count" in data
    assert "created_at" in data
    assert "last_accessed_at" in data
    assert "expires_at" in data
    assert "is_active" in data


def test_stats_initial_click_count_is_zero(client, existing_url):
    """
    Scenario: SCEN-003 click_count starts at 0 before any redirects
    Requirement: REQ-ANALY-001
    Type: happy_path
    """
    code = existing_url["short_code"]
    data = client.get(f"/api/v1/urls/{code}/stats").json()
    assert data["click_count"] == 0


def test_stats_click_count_reflects_redirect_count(client, existing_url):
    """
    Scenario: SCEN-003 click_count equals the number of redirects made
    Requirement: REQ-ANALY-001, REQ-ANALY-004
    Type: happy_path
    """
    code = existing_url["short_code"]

    # Make exactly 5 redirects
    for _ in range(5):
        client.get(f"/{code}", follow_redirects=False)

    data = client.get(f"/api/v1/urls/{code}/stats").json()
    assert data["click_count"] == 5


def test_stats_last_accessed_at_null_before_first_redirect(client, existing_url):
    """
    Scenario: SCEN-003 last_accessed_at is null before any redirect
    Requirement: REQ-ANALY-002
    Type: happy_path
    """
    code = existing_url["short_code"]
    data = client.get(f"/api/v1/urls/{code}/stats").json()
    assert data["last_accessed_at"] is None


def test_stats_last_accessed_at_set_after_redirect(client, existing_url):
    """
    Scenario: SCEN-003 last_accessed_at is populated after first redirect
    Requirement: REQ-ANALY-002
    Type: happy_path
    """
    code = existing_url["short_code"]
    client.get(f"/{code}", follow_redirects=False)

    data = client.get(f"/api/v1/urls/{code}/stats").json()
    assert data["last_accessed_at"] is not None


def test_stats_original_url_matches(client, existing_url):
    """
    Scenario: SCEN-003 Stats original_url matches what was submitted
    Requirement: REQ-ANALY-004
    Type: happy_path
    """
    code = existing_url["short_code"]
    data = client.get(f"/api/v1/urls/{code}/stats").json()
    assert data["original_url"] == VALID_URL


def test_stats_nonexistent_code_returns_404(client):
    """
    Scenario: Stats for a non-existent short code returns 404
    Requirement: REQ-ANALY-004, REQ-API-001
    Type: error_case
    """
    response = client.get(f"/api/v1/urls/{NONEXISTENT_CODE}/stats")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
