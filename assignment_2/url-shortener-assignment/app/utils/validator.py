# =============================================================================
# Implements:
#   REQ-VALID-001 (reject non-http/https schemes)
#   REQ-VALID-002 (reject malformed URLs)
#   REQ-VALID-003 (reject blocklisted domains)
#   REQ-VALID-004 (reject URLs > 2048 chars)
# TASK-004: URL validation utility
# =============================================================================

from urllib.parse import urlparse

# REQ-VALID-001: only these two schemes are permitted
ALLOWED_SCHEMES = {"http", "https"}

# REQ-VALID-004: maximum URL length
MAX_URL_LENGTH = 2048

# REQ-VALID-003: known malicious or disallowed domains
# In production this would be loaded from a database or threat-feed API
BLOCKED_DOMAINS: set[str] = {
    "malware.example.com",
    "phishing.example.com",
    "evil.example.com",
}


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validate a URL against all REQ-VALID requirements.

    Returns:
        (True, "")               — URL is valid, proceed
        (False, error_code)      — URL is invalid, error_code explains why

    Error codes:
        "url_too_long"           — REQ-VALID-004
        "invalid_url"            — REQ-VALID-001 or REQ-VALID-002
        "domain_blocked"         — REQ-VALID-003
    """
    # REQ-VALID-004: length check before any parsing
    if len(url) > MAX_URL_LENGTH:
        return False, "url_too_long"

    # REQ-VALID-002: must be parseable as a URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "invalid_url"

    # REQ-VALID-001: only http and https schemes accepted
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, "invalid_url"

    # REQ-VALID-002: must have a non-empty host (netloc)
    if not parsed.netloc:
        return False, "invalid_url"

    # REQ-VALID-003: blocklist check — strip port before comparing
    domain = parsed.netloc.lower().split(":")[0]
    if domain in BLOCKED_DOMAINS:
        return False, "domain_blocked"

    return True, ""
