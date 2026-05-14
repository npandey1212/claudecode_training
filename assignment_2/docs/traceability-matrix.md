# Traceability Matrix — URL Shortener Service

**Spec version**: specs/url-shortener.yaml v1.0.0
**Test run date**: 2026-04-12
**Result**: 49 passed, 0 failed (after 1 fix iteration)

---

## How to Read This Matrix

Each row maps one requirement to:
- The code file that implements it
- The test file(s) that verify it
- The specific test function(s)
- The Gherkin scenario covered (if applicable)
- Final pass/fail status

---

## Functional Requirements

### Domain: SHORTENING (REQ-SHORT)

| REQ ID | Statement | Code File | Test File | Test Function(s) | Scenario | Status |
|---|---|---|---|---|---|---|
| REQ-SHORT-001 | Accept valid URL, generate unique short code | `app/routers/urls.py` | `test_shorten.py` | `test_shorten_valid_url_returns_201` | SCEN-001 | ✅ PASS |
| REQ-SHORT-002 | Short code is exactly 6 alphanumeric chars | `app/utils/code_generator.py` | `test_shorten.py` | `test_shorten_short_code_is_6_alphanumeric_chars` | SCEN-001 | ✅ PASS |
| REQ-SHORT-003 | Store original_url, short_code, created_at, click_count=0 | `app/crud.py`, `app/models.py` | `test_shorten.py` | `test_shorten_original_url_preserved`, `test_shorten_created_at_is_present` | SCEN-001 | ✅ PASS |
| REQ-SHORT-004 | Return existing record on duplicate URL submission | `app/crud.py`, `app/routers/urls.py` | `test_shorten.py` | `test_shorten_duplicate_url_returns_200`, `test_shorten_duplicate_url_returns_same_code` | SCEN-004 | ✅ PASS |
| REQ-SHORT-005 | Retry code generation on collision (max 5) | `app/crud.py`, `app/utils/code_generator.py` | `test_shorten.py` | `test_shorten_different_urls_get_different_codes` | — | ✅ PASS |

### Domain: REDIRECT (REQ-REDIR)

| REQ ID | Statement | Code File | Test File | Test Function(s) | Scenario | Status |
|---|---|---|---|---|---|---|
| REQ-REDIR-001 | GET /{code} redirects to original URL via HTTP 302 | `app/routers/urls.py` | `test_redirect.py` | `test_redirect_active_url_returns_302`, `test_redirect_location_header_is_original_url` | SCEN-002 | ✅ PASS |
| REQ-REDIR-002 | Return 404 for unknown short code | `app/routers/urls.py` | `test_redirect.py` | `test_redirect_nonexistent_code_returns_404`, `test_redirect_404_has_correct_error_body` | SCEN-006 | ✅ PASS |
| REQ-REDIR-003 | Return 410 for expired short URL | `app/routers/urls.py` | `test_expiry.py` | `test_redirect_expired_url_returns_410`, `test_redirect_expired_url_error_body` | SCEN-007 | ✅ PASS |

### Domain: ANALYTICS (REQ-ANALY)

| REQ ID | Statement | Code File | Test File | Test Function(s) | Scenario | Status |
|---|---|---|---|---|---|---|
| REQ-ANALY-001 | Increment click_count on each redirect | `app/crud.py` | `test_redirect.py`, `test_analytics.py` | `test_redirect_increments_click_count`, `test_stats_click_count_reflects_redirect_count` | SCEN-002, SCEN-003 | ✅ PASS |
| REQ-ANALY-002 | Record last_accessed_at on each redirect | `app/crud.py` | `test_redirect.py`, `test_analytics.py` | `test_redirect_updates_last_accessed_at`, `test_stats_last_accessed_at_set_after_redirect` | SCEN-002, SCEN-003 | ✅ PASS |
| REQ-ANALY-003 | Capture Referer header per click event | `app/crud.py` | `test_redirect.py` | `test_redirect_captures_referrer_header` | SCEN-002 | ✅ PASS |
| REQ-ANALY-004 | GET /api/v1/urls/{code}/stats returns all analytics fields | `app/routers/urls.py` | `test_analytics.py` | `test_stats_returns_200_for_existing_url`, `test_stats_response_has_all_required_fields` | SCEN-003 | ✅ PASS |

### Domain: EXPIRY (REQ-EXPRY)

| REQ ID | Statement | Code File | Test File | Test Function(s) | Scenario | Status |
|---|---|---|---|---|---|---|
| REQ-EXPRY-001 | URLs MAY include optional expires_at | `app/models.py`, `app/routers/urls.py` | `test_shorten.py`, `test_expiry.py` | `test_shorten_expires_at_null_when_not_provided`, `test_create_url_with_future_expiry_is_accepted` | — | ✅ PASS |
| REQ-EXPRY-002 | Evaluate expiry on every redirect | `app/routers/urls.py` | `test_expiry.py` | `test_redirect_expired_url_returns_410`, `test_redirect_expired_url_does_not_increment_click_count` | SCEN-007 | ✅ PASS |
| REQ-EXPRY-003 | Reject creation with past expires_at | `app/routers/urls.py` | `test_expiry.py` | `test_create_url_with_past_expiry_returns_422`, `test_create_url_with_past_expiry_error_code` | SCEN-008 | ✅ PASS |

### Domain: VALIDATION (REQ-VALID)

| REQ ID | Statement | Code File | Test File | Test Function(s) | Scenario | Status |
|---|---|---|---|---|---|---|
| REQ-VALID-001 | Reject non-http/https URL schemes | `app/utils/validator.py` | `test_validation.py` | `test_reject_javascript_scheme_returns_422`, `test_reject_ftp_scheme_returns_422`, `test_reject_data_uri_scheme_returns_422` | SCEN-005 | ✅ PASS |
| REQ-VALID-002 | Reject malformed URLs | `app/utils/validator.py` | `test_validation.py` | `test_reject_malformed_url_returns_422`, `test_reject_url_with_no_domain_returns_422` | SCEN-005 | ✅ PASS |
| REQ-VALID-003 | Reject blocklisted domains | `app/utils/validator.py` | `test_validation.py` | `test_reject_blocked_domain_returns_422`, `test_reject_blocked_domain_error_code` | SCEN-009 | ✅ PASS |
| REQ-VALID-004 | Reject URLs longer than 2048 chars | `app/utils/validator.py` | `test_validation.py` | `test_reject_url_exceeding_max_length` | — | ✅ PASS |

### Domain: API (REQ-API)

| REQ ID | Statement | Code File | Test File | Test Function(s) | Scenario | Status |
|---|---|---|---|---|---|---|
| REQ-API-001 | All error responses have `error` + `message` fields | `app/main.py` (exception handlers) | `test_validation.py`, `test_redirect.py` | `test_reject_javascript_scheme_error_code`, `test_redirect_404_has_correct_error_body` | — | ✅ PASS |
| REQ-API-002 | 422 responses include field-level detail array | `app/main.py`, `app/routers/urls.py` | `test_validation.py` | `test_validation_error_contains_field_detail` | SCEN-005 | ✅ PASS |
| REQ-API-003 | 429 Too Many Requests with Retry-After header | `app/main.py` (rate limit middleware) | `test_rate_limiting.py` | `test_rate_limit_exceeded_returns_429`, `test_rate_limit_response_includes_retry_after_header` | SCEN-010 | ✅ PASS |

---

## Non-Functional Requirements

| NFR ID | Statement | Code File | Verified By | Status |
|---|---|---|---|---|
| NFR-SEC-001 | Rate limit: 10 POST /shorten per IP per 60 seconds | `app/main.py` | `test_rate_limiting.py` — all 5 rate limit tests | ✅ PASS |
| NFR-SEC-002 | No internal error details in responses | `app/main.py` (global exception handler) | 500 response returns only generic message — confirmed in test run | ✅ PASS |
| NFR-SEC-004 | IP stored as SHA-256 hash, never plaintext | `app/crud.py` (`record_access`) | Code review (no direct test — would require DB inspection) | ✅ VERIFIED (code review) |
| NFR-MAINT-001 | All source files include REQ-ID traceability comments | All `app/` files | Structural — visible in every source file | ✅ VERIFIED |
| NFR-SCAL-001 | All state in database, no app-memory state | `app/crud.py`, `app/database.py` | Architecture — confirmed in code review | ✅ VERIFIED |

---

## Gherkin Scenario Coverage

| Scenario ID | Title | Test Function | Status |
|---|---|---|---|
| SCEN-001 | Successfully shorten a valid URL | `test_shorten_valid_url_returns_201` + 4 supporting tests | ✅ PASS |
| SCEN-002 | Successfully redirect a valid short URL | `test_redirect_active_url_returns_302` + 4 supporting tests | ✅ PASS |
| SCEN-003 | Retrieve analytics after multiple clicks | `test_stats_click_count_reflects_redirect_count` + 6 supporting tests | ✅ PASS |
| SCEN-004 | Duplicate URL returns existing short URL | `test_shorten_duplicate_url_returns_200` + 1 supporting test | ✅ PASS |
| SCEN-005 | Reject non-HTTP/HTTPS URL scheme | `test_reject_javascript_scheme_returns_422` + 3 supporting tests | ✅ PASS |
| SCEN-006 | Return 404 for non-existent short code | `test_redirect_nonexistent_code_returns_404` + 1 supporting test | ✅ PASS |
| SCEN-007 | Redirect to expired URL returns 410 | `test_redirect_expired_url_returns_410` + 2 supporting tests | ✅ PASS |
| SCEN-008 | Reject creation with past expiry date | `test_create_url_with_past_expiry_returns_422` + 1 supporting test | ✅ PASS |
| SCEN-009 | Reject URL with blocklisted domain | `test_reject_blocked_domain_returns_422` + 1 supporting test | ✅ PASS |
| SCEN-010 | Return 429 when rate limit exceeded | `test_rate_limit_exceeded_returns_429` + 3 supporting tests | ✅ PASS |

**Gherkin coverage: 10/10 scenarios (100%)**

---

## Fix Iteration Log

### Iteration 1 — Initial run: 48 passed, 1 error

**Failing test**: `test_stats_returns_200_for_existing_url`
**Root cause**: Cold-start import ordering bug. `db_tables` fixture called `Base.metadata.create_all()` before `app.models` was imported, so SQLAlchemy's `Base` had no tables registered. The first test saw an empty schema and got a 500 on POST /shorten.

**Fix applied**: Added `import app.models` at module level in `conftest.py` to ensure models are registered with `Base` before any fixture runs.

**Result after fix**: 49 passed, 0 failed.

---

## Summary

| Metric | Value |
|---|---|
| Total requirements | 20 functional + 5 NFR |
| Total Gherkin scenarios | 10 |
| Total test functions | 49 |
| Scenarios covered | 10 / 10 (100%) |
| Requirements with passing tests | 20 / 20 (100%) |
| Final test result | **49 passed, 0 failed** |
| Fix iterations needed | 1 |
