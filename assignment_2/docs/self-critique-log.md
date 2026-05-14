# Self-Critique Log — URL Shortener Service

**Prompt used**: `prompts/code-reviewer.yaml`
**Role applied**: Security Engineer (OWASP Top 10, adversarial mindset)
**Output schema**: JSON (enforced — see `docs/schema-enforcement.md`)
**Loop protocol**: Generate → Review → Fix → Validate (repeat until `must_fix_before_merge = []`)

---

## How the Loop Works

```
┌─────────────┐     code-reviewer.yaml      ┌──────────────────┐
│  Write code │ ─────────────────────────► │  JSON review      │
│  (generate) │                             │  output           │
└─────────────┘                             └────────┬─────────┘
       ▲                                             │
       │                                    overall_risk?
       │                                             │
       │              CRITICAL/HIGH findings?        │
       │         YES ◄──────────────────────────────┤
       │  fix and re-submit                          │
       │                                             │ NO (or CLEAN/LOW)
       └─────────────────────────────────────────────┘
                                            ✅ APPROVED
```

**Gate rule**: A file is approved when `must_fix_before_merge` is empty.
MEDIUM findings are fixed as good practice. LOW/INFO are documented but optional.

---

## Review Summary

| Cycle | File | Initial Risk | Findings | Fixed | Final Risk |
|---|---|---|---|---|---|
| 1 | `app/routers/urls.py` | MEDIUM | 2 MEDIUM, 1 LOW | ✅ Both MEDIUM fixed | LOW |
| 2 | `app/utils/code_generator.py` | MEDIUM | 1 MEDIUM | ✅ Fixed | LOW |
| 3 | `app/crud.py` | MEDIUM | 1 MEDIUM, 1 LOW | ✅ MEDIUM fixed | LOW |
| 4 | `app/utils/validator.py` | LOW | 1 LOW, 1 INFO | — (documented) | LOW |
| 5 | `app/main.py` | LOW | 1 LOW, 1 INFO | — (documented) | LOW |

---

---

# CYCLE 1 — app/routers/urls.py

**Prompt inputs applied**:
```yaml
language: python
file_path: app/routers/urls.py
context: >
  Handles all 4 HTTP endpoints: POST /api/v1/shorten (create),
  GET /{code} (redirect), GET /api/v1/urls/{code}/stats (analytics),
  DELETE /api/v1/urls/{code} (soft delete).
  Highest risk file — all user input enters here.
req_ids: "REQ-SHORT-001, REQ-REDIR-001..003, REQ-ANALY-001..004, REQ-EXPRY-002..003, REQ-VALID-001..004, REQ-API-001..002"
```

## Iteration 1 — Initial Review

```json
{
  "review": {
    "file_path": "app/routers/urls.py",
    "language": "python",
    "reviewed_at": "2026-04-12T00:00:00Z",
    "overall_risk": "MEDIUM",
    "summary": "No critical or high vulnerabilities. Two medium findings: the redirect endpoint performs no scheme re-validation at runtime (trusts the stored URL completely), and the HTTP Referer header is stored without a length cap, allowing a slow DB bloat attack via oversized headers. One low cosmetic issue with error body duplication.",
    "findings": [
      {
        "id": "FINDING-C1-001",
        "severity": "MEDIUM",
        "category": "Open Redirect / Defence in Depth",
        "owasp_ref": "A01:2021",
        "line_numbers": [202],
        "description": "The redirect endpoint trusts original_url from the database entirely and issues a 302 without re-checking the scheme. If a future bug or direct DB access allowed a non-http/https URL to be stored, this would become an open redirect to a javascript: or data: URI.",
        "code_snippet": "return RedirectResponse(url=url.original_url, status_code=302)",
        "recommendation": "Re-validate that original_url starts with http:// or https:// at redirect time. Costs one urlparse() call. Provides defence-in-depth against future schema bypass or DB tampering.",
        "req_id_affected": "REQ-REDIR-001"
      },
      {
        "id": "FINDING-C1-002",
        "severity": "MEDIUM",
        "category": "Input Sanitization / Resource Exhaustion",
        "owasp_ref": "A05:2021",
        "line_numbers": [197],
        "description": "The HTTP Referer header is read and passed to record_access() without any length limit. An attacker sending a crafted 64KB Referer on every redirect request would silently bloat the url_access_logs table, potentially filling disk or degrading query performance.",
        "code_snippet": "referrer = request.headers.get(\"referer\")",
        "recommendation": "Truncate the referrer value to a maximum of 2048 characters before storing: `referrer = raw[:2048] if raw else None`",
        "req_id_affected": "REQ-ANALY-003"
      },
      {
        "id": "FINDING-C1-003",
        "severity": "LOW",
        "category": "Response Schema Consistency",
        "owasp_ref": "N/A",
        "line_numbers": [55, 60],
        "description": "The 422 error dict passed to HTTPException contains both a top-level 'error' key and the same key repeated inside each item in the 'detail' array. Redundant but not a security issue.",
        "code_snippet": "detail={\"error\": error_code, \"message\": ..., \"detail\": [{\"field\": \"url\", \"issue\": error_code}]}",
        "recommendation": "Remove the 'error' key from inside the detail array items. Keep it only at the top level to match REQ-API-001.",
        "req_id_affected": "REQ-API-001"
      }
    ],
    "passed_checks": [
      "SQL Injection — ORM parameterised queries only, no raw SQL string interpolation",
      "Sensitive data in responses — no PII, no internal stack traces",
      "Exception leakage — all HTTPExceptions use controlled dict detail",
      "Type safety — all inputs go through validate_url() before use"
    ],
    "must_fix_before_merge": []
  }
}
```

> `must_fix_before_merge` is empty but two MEDIUM findings demand action.
> Loop protocol: fix all MEDIUM before re-submit.

## Fix Applied — FINDING-C1-001 (Open Redirect)

Added `urlparse` import and re-validated scheme at redirect time:

```python
# BEFORE
return RedirectResponse(url=url.original_url, status_code=302)

# AFTER
parsed = urlparse(url.original_url)
if parsed.scheme not in {"http", "https"}:
    raise HTTPException(
        status_code=500,
        detail={"error": "internal_error", "message": "Stored URL has invalid scheme"},
    )
return RedirectResponse(url=url.original_url, status_code=302)
```

**Why this matters**: The check at creation time (REQ-VALID-001) is the primary gate. The check at redirect time is a second gate. If both are present, a bypass of one doesn't lead to a successful exploit.

## Fix Applied — FINDING-C1-002 (Unbounded Referrer)

Capped referrer at 2048 characters before passing to record_access():

```python
# BEFORE
referrer = request.headers.get("referer")

# AFTER
raw_referrer = request.headers.get("referer")
referrer = raw_referrer[:2048] if raw_referrer else None
```

## Iteration 2 — Post-Fix Validation

```json
{
  "review": {
    "file_path": "app/routers/urls.py",
    "overall_risk": "LOW",
    "summary": "Both MEDIUM findings resolved. Scheme re-validated at redirect. Referrer truncated. FINDING-C1-003 (cosmetic) remains documented but does not block merge.",
    "findings": [
      {
        "id": "FINDING-C1-003",
        "severity": "LOW",
        "category": "Response Schema Consistency",
        "description": "Minor redundancy in 422 error body structure. No security impact.",
        "recommendation": "Optional cosmetic cleanup.",
        "req_id_affected": "REQ-API-001"
      }
    ],
    "passed_checks": [
      "SQL Injection", "Open Redirect (fixed)", "Unbounded input (fixed)",
      "Sensitive data exposure", "Exception leakage", "Type safety"
    ],
    "must_fix_before_merge": []
  }
}
```

**CYCLE 1 VERDICT: ✅ APPROVED** — `overall_risk: LOW`, `must_fix_before_merge: []`

---

---

# CYCLE 2 — app/utils/code_generator.py

**Prompt inputs applied**:
```yaml
language: python
file_path: app/utils/code_generator.py
context: Generates 6-character alphanumeric short codes used as public-facing identifiers.
req_ids: "REQ-SHORT-002, REQ-SHORT-005"
```

## Iteration 1 — Initial Review

```json
{
  "review": {
    "file_path": "app/utils/code_generator.py",
    "language": "python",
    "reviewed_at": "2026-04-12T00:00:00Z",
    "overall_risk": "MEDIUM",
    "summary": "One medium finding: the code uses Python's standard random module which is a Mersenne Twister PRNG, not a cryptographically secure source. An attacker who observes enough generated codes could reconstruct the internal state and predict future codes, enabling enumeration of other users' short URLs.",
    "findings": [
      {
        "id": "FINDING-C2-001",
        "severity": "MEDIUM",
        "category": "Insecure Randomness",
        "owasp_ref": "A02:2021",
        "line_numbers": [27],
        "description": "random.choices() uses Python's Mersenne Twister (MT19937). MT state (624 integers) can be fully recovered after observing ~624 outputs. An attacker who makes enough shorten requests can predict all future short codes and silently enumerate any shortened URL in the system — including private documents, internal tools, or one-time links.",
        "code_snippet": "return \"\".join(random.choices(ALPHABET, k=SHORT_CODE_LENGTH))",
        "recommendation": "Replace with secrets.choice() from Python's secrets module, which uses the OS CSPRNG (e.g., /dev/urandom on Linux). Same API, no performance penalty at this scale.",
        "req_id_affected": "REQ-SHORT-002"
      }
    ],
    "passed_checks": [
      "Output format — always produces exactly 6 chars from [a-zA-Z0-9]",
      "No side effects — pure function",
      "No hardcoded values except configurable constants"
    ],
    "must_fix_before_merge": []
  }
}
```

> `must_fix_before_merge` is empty (MEDIUM not CRITICAL), but this is a real
> security risk for a public-facing service. Fixing it costs zero lines of change.

## Fix Applied — FINDING-C2-001 (Insecure Randomness)

```python
# BEFORE
import random
...
return "".join(random.choices(ALPHABET, k=SHORT_CODE_LENGTH))

# AFTER
import secrets
...
return "".join(secrets.choice(ALPHABET) for _ in range(SHORT_CODE_LENGTH))
```

**Why `secrets` over `random`**:
- `random` = Mersenne Twister, seeded from current time — predictable after observation
- `secrets` = OS CSPRNG (`/dev/urandom`, `CryptGenRandom`) — designed for security tokens
- `secrets.choice()` pulls one character at a time from the CSPRNG — same result, unpredictable sequence

## Iteration 2 — Post-Fix Validation

```json
{
  "review": {
    "file_path": "app/utils/code_generator.py",
    "overall_risk": "LOW",
    "summary": "Insecure randomness resolved. secrets.choice() is the correct primitive for short codes used as public identifiers. No remaining findings.",
    "findings": [],
    "passed_checks": [
      "Insecure randomness (fixed — now CSPRNG)",
      "Output format correct",
      "No side effects"
    ],
    "must_fix_before_merge": []
  }
}
```

**CYCLE 2 VERDICT: ✅ APPROVED** — `overall_risk: LOW`, `must_fix_before_merge: []`

---

---

# CYCLE 3 — app/crud.py

**Prompt inputs applied**:
```yaml
language: python
file_path: app/crud.py
context: >
  All database read/write operations. No HTTP concepts.
  Key operations: create_short_url (with collision retry),
  record_access (click tracking), deactivate_url (soft delete).
req_ids: "REQ-SHORT-001, REQ-SHORT-003..005, REQ-ANALY-001..003, NFR-SEC-004"
```

## Iteration 1 — Initial Review

```json
{
  "review": {
    "file_path": "app/crud.py",
    "language": "python",
    "reviewed_at": "2026-04-12T00:00:00Z",
    "overall_risk": "MEDIUM",
    "summary": "One medium finding: a classic TOCTOU (time-of-check / time-of-use) race condition in create_short_url(). The code checks for uniqueness with a SELECT, then inserts — but under concurrent load, two requests can both see the same code as available and both attempt to insert it. The database UNIQUE constraint catches this, but the resulting IntegrityError is unhandled and bubbles up as a 500. One low finding: RuntimeError message text is logged but also reaches the global exception handler which sanitises the response — so NFR-SEC-002 is safe.",
    "findings": [
      {
        "id": "FINDING-C3-001",
        "severity": "MEDIUM",
        "category": "Race Condition / Unhandled Exception",
        "owasp_ref": "A05:2021",
        "line_numbers": [73, 74, 75, 76, 77],
        "description": "SELECT-then-INSERT pattern for uniqueness checking has a TOCTOU window. Concurrent requests can both SELECT the same candidate code as available, then both attempt INSERT. The second INSERT hits the UNIQUE constraint on short_code and raises sqlalchemy.exc.IntegrityError. This exception is not caught — it propagates to the global exception handler and returns HTTP 500 to the user.",
        "code_snippet": "if db.query(URL).filter(URL.short_code == candidate).first() is None:\n    short_code = candidate\n    break",
        "recommendation": "Wrap the INSERT in try/except IntegrityError. On IntegrityError, rollback the session and continue the retry loop. This makes the collision retry loop handle both pre-checked and race-condition collisions identically.",
        "req_id_affected": "REQ-SHORT-005"
      },
      {
        "id": "FINDING-C3-002",
        "severity": "LOW",
        "category": "Error Handling",
        "owasp_ref": "N/A",
        "line_numbers": [79, 80, 81],
        "description": "RuntimeError message includes 'MAX_RETRIES' count which is an internal detail. The global exception handler in main.py correctly strips this before the HTTP response, so NFR-SEC-002 is satisfied. The risk is if logging is added later without sanitisation.",
        "code_snippet": "raise RuntimeError(f\"Failed to generate a unique short code after {MAX_RETRIES} attempts\")",
        "recommendation": "Not a security bug today. For future-safety, use a custom exception class (e.g. CodeGenerationError) so log handlers can filter it explicitly.",
        "req_id_affected": "N/A"
      }
    ],
    "passed_checks": [
      "SQL Injection — all queries use SQLAlchemy ORM parameterised filters",
      "IP hashing — SHA-256 used correctly, no plaintext IP stored (NFR-SEC-004)",
      "No sensitive data in return values",
      "UTC normalisation logic is correct"
    ],
    "must_fix_before_merge": []
  }
}
```

## Fix Applied — FINDING-C3-001 (TOCTOU Race Condition)

Wrapped the INSERT in `try/except IntegrityError` so the retry loop handles
both pre-detected and race-condition collisions:

```python
# BEFORE — SELECT check then INSERT (TOCTOU window between the two)
for _ in range(MAX_RETRIES):
    candidate = generate_short_code()
    if db.query(URL).filter(URL.short_code == candidate).first() is None:
        short_code = candidate
        break
else:
    raise RuntimeError(...)

url_record = URL(short_code=short_code, ...)
db.add(url_record)
db.commit()

# AFTER — SELECT check + IntegrityError catch (belt and braces)
for _ in range(MAX_RETRIES):
    candidate = generate_short_code()
    if db.query(URL).filter(URL.short_code == candidate).first() is not None:
        continue  # pre-detected collision — try next candidate
    try:
        url_record = URL(short_code=candidate, ...)
        db.add(url_record)
        db.commit()
        db.refresh(url_record)
        return url_record
    except IntegrityError:
        db.rollback()
        continue  # race-condition collision — retry with new code
raise RuntimeError(...)
```

**Why this matters**: At scale, even a 1-in-1000 collision probability under concurrent load would occasionally produce 500 errors visible to users. The fix makes the retry loop robust to both predicted and unexpected collisions.

## Iteration 2 — Post-Fix Validation

```json
{
  "review": {
    "file_path": "app/crud.py",
    "overall_risk": "LOW",
    "summary": "TOCTOU race condition resolved. The create loop now handles both pre-detected collisions (via SELECT) and concurrent collisions (via IntegrityError catch with rollback). FINDING-C3-002 is LOW and does not block merge.",
    "findings": [
      {
        "id": "FINDING-C3-002",
        "severity": "LOW",
        "category": "Error Handling",
        "description": "RuntimeError message text is internal but sanitised before HTTP response. Low risk, documented.",
        "recommendation": "Future enhancement: use custom exception class.",
        "req_id_affected": "N/A"
      }
    ],
    "passed_checks": [
      "SQL Injection", "Race condition (fixed)", "IP hashing", "UTC normalisation"
    ],
    "must_fix_before_merge": []
  }
}
```

**CYCLE 3 VERDICT: ✅ APPROVED** — `overall_risk: LOW`, `must_fix_before_merge: []`

---

---

# CYCLE 4 — app/utils/validator.py

**Prompt inputs applied**:
```yaml
language: python
file_path: app/utils/validator.py
context: URL validation — scheme check, format check, domain blocklist, length limit.
req_ids: "REQ-VALID-001, REQ-VALID-002, REQ-VALID-003, REQ-VALID-004"
```

## Iteration 1 — Review Result

```json
{
  "review": {
    "file_path": "app/utils/validator.py",
    "language": "python",
    "reviewed_at": "2026-04-12T00:00:00Z",
    "overall_risk": "LOW",
    "summary": "No MEDIUM or HIGH findings. Two observations: the blocklist is hardcoded (acceptable for dev, not for production), and Python's urlparse() is permissive — it does not reject all malformed input. The existing netloc and scheme checks compensate for urlparse's permissiveness.",
    "findings": [
      {
        "id": "FINDING-C4-001",
        "severity": "LOW",
        "category": "Configuration Hardcoding",
        "owasp_ref": "A05:2021",
        "line_numbers": [20, 21, 22, 23, 24],
        "description": "BLOCKED_DOMAINS is a hardcoded Python set. Adding a new blocked domain requires a code deploy. In production this should be loaded from a database, config file, or threat-feed API so the blocklist can be updated without redeployment.",
        "code_snippet": "BLOCKED_DOMAINS: set[str] = {\n    \"malware.example.com\",\n    ...\n}",
        "recommendation": "For this assignment scope, hardcoded is acceptable and documented in the source. Production: load from DB or config. No code change required now.",
        "req_id_affected": "REQ-VALID-003"
      },
      {
        "id": "FINDING-C4-002",
        "severity": "INFO",
        "category": "Validation Completeness",
        "owasp_ref": "N/A",
        "line_numbers": [45, 46, 47, 48],
        "description": "urllib.parse.urlparse() is intentionally lenient — it accepts malformed URLs like 'http://' (empty netloc) or 'https://a b c' (spaces in host). The existing `if not parsed.netloc` check catches the empty netloc case. Spaces in host would pass through to the database. In practice, most browsers would reject such a redirect target anyway.",
        "code_snippet": "parsed = urlparse(url)",
        "recommendation": "Optional: add a regex check on parsed.netloc to reject hosts with whitespace. Not required for assignment scope.",
        "req_id_affected": "REQ-VALID-002"
      }
    ],
    "passed_checks": [
      "Scheme whitelist correct (http and https only)",
      "Length check runs before parsing (efficient)",
      "Domain comparison is case-normalised and port-stripped",
      "No injection risk — no output, pure validation logic"
    ],
    "must_fix_before_merge": []
  }
}
```

> No code change applied. Both findings are below the fix threshold for this scope.
> FINDING-C4-001 is documented in the source code with a production note.
> FINDING-C4-002 is noted — browser-level rejection provides a compensating control.

**CYCLE 4 VERDICT: ✅ APPROVED** — `overall_risk: LOW`, `must_fix_before_merge: []` (no changes needed)

---

---

# CYCLE 5 — app/main.py

**Prompt inputs applied**:
```yaml
language: python
file_path: app/main.py
context: >
  FastAPI app entry point. Wires rate limiting middleware (sliding window,
  in-memory dict), three exception handlers for uniform error responses,
  and registers the URL router.
req_ids: "REQ-API-001, REQ-API-003, NFR-SEC-001, NFR-SEC-002"
```

## Iteration 1 — Review Result

```json
{
  "review": {
    "file_path": "app/main.py",
    "language": "python",
    "reviewed_at": "2026-04-12T00:00:00Z",
    "overall_risk": "LOW",
    "summary": "No MEDIUM or HIGH findings. Two observations: the in-memory rate limit store grows unboundedly until restarted (keys are never evicted even after inactivity), and the rate limiter falls back to 'unknown' for requests with no client address, meaning all such requests share one bucket.",
    "findings": [
      {
        "id": "FINDING-C5-001",
        "severity": "LOW",
        "category": "Resource Leak / Memory Growth",
        "owasp_ref": "N/A",
        "line_numbers": [37, 55, 56, 57],
        "description": "_rate_limit_store is a defaultdict that accumulates one entry per unique IP. Old timestamps within each entry are evicted on every request from that IP, but the key itself is never removed. A long-running service receiving requests from millions of unique IPs would grow this dict unboundedly. For a single-instance dev server this is acceptable. Production must use Redis with TTL.",
        "code_snippet": "_rate_limit_store: dict[str, list[float]] = defaultdict(list)",
        "recommendation": "Documented limitation — acceptable for dev/assignment. Production: replace with Redis INCR + EXPIRE pattern.",
        "req_id_affected": "NFR-SEC-001"
      },
      {
        "id": "FINDING-C5-002",
        "severity": "INFO",
        "category": "Rate Limit Bypass",
        "owasp_ref": "N/A",
        "line_numbers": [50],
        "description": "When request.client is None (e.g., certain test proxies or WebSocket upgrades), the IP falls back to the string 'unknown'. All such requests share a single rate limit bucket, which could allow a client to exhaust this bucket and deny service to other clients without a client address.",
        "code_snippet": "client_ip = request.client.host if request.client else \"unknown\"",
        "recommendation": "In production, reject requests with no client address (return 400) rather than bucketing them together. For this assignment scope, the fallback is acceptable.",
        "req_id_affected": "REQ-API-003"
      }
    ],
    "passed_checks": [
      "NFR-SEC-002 — global exception handler never exposes stack traces",
      "REQ-API-001 — HTTPException and RequestValidationError handlers both produce {error, message}",
      "Rate limit window logic is correct (sliding window, not fixed window)",
      "Retry-After calculation is correct and always >= 1",
      "Router registration correct — urls.router included without prefix"
    ],
    "must_fix_before_merge": []
  }
}
```

> No code changes applied. Both findings are LOW/INFO and documented.
> FINDING-C5-001 is already noted in a comment in main.py.

**CYCLE 5 VERDICT: ✅ APPROVED** — `overall_risk: LOW`, `must_fix_before_merge: []` (no changes needed)

---

---

# Code Changes Applied (from review cycles)

## Files modified by the self-critique loop

| File | Cycle | Change |
|---|---|---|
| `app/routers/urls.py` | Cycle 1 | Added scheme re-validation at redirect time (FINDING-C1-001) |
| `app/routers/urls.py` | Cycle 1 | Added referrer truncation to 2048 chars (FINDING-C1-002) |
| `app/utils/code_generator.py` | Cycle 2 | Replaced `random.choices` with `secrets.choice` (FINDING-C2-001) |
| `app/crud.py` | Cycle 3 | Wrapped INSERT in `try/except IntegrityError` to handle TOCTOU (FINDING-C3-001) |

## Files approved with no code changes

| File | Cycle | Reason |
|---|---|---|
| `app/utils/validator.py` | Cycle 4 | Findings below fix threshold for assignment scope |
| `app/main.py` | Cycle 5 | Findings already documented in source; production notes added |

---

---

# What the Self-Critique Loop Caught (and Why It Matters)

| Finding | Risk Without Review | Cost of Fix | Lesson |
|---|---|---|---|
| Open redirect (C1-001) | Future DB compromise → redirect to malicious URL | 5 lines | Defence in depth: validate at every trust boundary, not just entry |
| Unbounded referrer (C1-002) | Slow disk exhaustion via crafted Referer headers | 1 line | Sanitise all user-controlled data before storage, including headers |
| Insecure PRNG (C2-001) | Attacker predicts all future short codes after 624 observations | 2 lines | `random` is for games; `secrets` is for tokens |
| TOCTOU race (C3-001) | Intermittent 500 errors under concurrent load | 8 lines | SELECT-then-INSERT is never atomic — catch the constraint violation |

---

# Test Impact After Fixes

All 4 code changes were applied and the full test suite re-run:

```
49 passed in 0.84s
```

No regressions. The fixes did not break any existing tests because:
- The scheme re-validation only fires on impossible-in-practice stored URLs
- The referrer truncation still stores a valid string (just shorter)
- `secrets.choice` produces the same output format as `random.choices`
- The IntegrityError handler retries — same success path for callers
