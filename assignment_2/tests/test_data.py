# =============================================================================
# Test constants — reusable inputs across the test suite
# Generated using: prompts/test-generator.yaml
# =============================================================================

# ---------------------------------------------------------------------------
# Valid URLs
# ---------------------------------------------------------------------------

# Primary test URL — used in most happy-path tests
VALID_URL = "https://www.example.com/some/page"

# Second distinct URL — used where a different URL is needed (e.g., rate limit tests)
VALID_URL_2 = "https://www.github.com/user/repo"

# Template for generating unique URLs in bulk (e.g., rate limit tests)
VALID_URL_TEMPLATE = "https://www.example.com/page/{n}"

# ---------------------------------------------------------------------------
# Invalid URLs — each targets a specific REQ-VALID rule
# ---------------------------------------------------------------------------

# REQ-VALID-001: non-http/https scheme — JavaScript injection attempt
INVALID_URL_JS = "javascript:alert(1)"

# REQ-VALID-001: non-http/https scheme — FTP
INVALID_URL_FTP = "ftp://example.com/file.txt"

# REQ-VALID-001: data URI scheme
INVALID_URL_DATA = "data:text/html,<h1>xss</h1>"

# REQ-VALID-002: not a URL at all
INVALID_URL_MALFORMED = "not_a_url_at_all"

# REQ-VALID-002: missing domain
INVALID_URL_NO_DOMAIN = "https://"

# REQ-VALID-003: domain on the blocklist
BLOCKED_DOMAIN_URL = "https://malware.example.com/payload"

# REQ-VALID-004: URL exceeding 2048 characters
TOO_LONG_URL = "https://example.com/" + "a" * 2049

# ---------------------------------------------------------------------------
# Expiry dates
# ---------------------------------------------------------------------------

# REQ-EXPRY-001: a future expiry date
FUTURE_EXPIRY = "2030-12-31T23:59:59"

# REQ-EXPRY-003: a past expiry date — should be rejected at creation
PAST_EXPIRY = "2020-01-01T00:00:00"

# ---------------------------------------------------------------------------
# Short code constants
# ---------------------------------------------------------------------------

# Known expired short code used in SCEN-007
EXPIRED_SHORT_CODE = "exprd1"

# A short code that will never exist in the test database
NONEXISTENT_CODE = "xxxxxx"
