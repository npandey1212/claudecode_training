# Schema Enforcement — JSON Schema Output Validation

## Assignment Requirement
Part 3.3: At least one Claude interaction must use JSON schema enforcement.
Document the schema used and the validated output.

---

## What Was Schema-Enforced

The `code-reviewer.yaml` prompt defines a strict JSON `output_schema`.
This schema was applied to review `app/routers/urls.py` and `app/main.py`.

The schema enforces that the reviewer's output is always machine-readable JSON
(not prose), enabling the self-critique loop to programmatically decide
"fix or proceed" based on `overall_risk` and `must_fix_before_merge`.

---

## The Enforced JSON Schema

```json
{
  "type": "object",
  "required": ["review"],
  "properties": {
    "review": {
      "type": "object",
      "required": ["file_path", "overall_risk", "summary", "findings", "must_fix_before_merge"],
      "properties": {
        "file_path":              { "type": "string" },
        "language":               { "type": "string" },
        "reviewed_at":            { "type": "string", "format": "date-time" },
        "overall_risk": {
          "type": "string",
          "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAN"]
        },
        "summary":                { "type": "string" },
        "findings": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "severity", "category", "description", "recommendation"],
            "properties": {
              "id":               { "type": "string" },
              "severity":         { "type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] },
              "category":         { "type": "string" },
              "owasp_ref":        { "type": "string" },
              "line_numbers":     { "type": "array", "items": { "type": "integer" } },
              "description":      { "type": "string" },
              "code_snippet":     { "type": "string" },
              "recommendation":   { "type": "string" },
              "req_id_affected":  { "type": "string" }
            }
          }
        },
        "passed_checks":          { "type": "array", "items": { "type": "string" } },
        "must_fix_before_merge":  { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

---

## Self-Critique Loop — Iteration 1

### Files reviewed
- `app/routers/urls.py` — highest risk file (handles all user input)
- `app/main.py` — rate limiting and exception handlers

### Prompt applied
`prompts/code-reviewer.yaml` with inputs:
- language: python
- file_path: app/routers/urls.py
- context: "Handles POST /shorten, GET /{code} redirect, GET stats, DELETE. Validates URLs, enforces expiry."
- req_ids: "REQ-SHORT-001, REQ-REDIR-001..003, REQ-ANALY-001..004, REQ-EXPRY-002..003, REQ-VALID-001..004, REQ-API-001..002"

### Review Result (schema-validated JSON output)

```json
{
  "review": {
    "file_path": "app/routers/urls.py",
    "language": "python",
    "reviewed_at": "2026-04-12T00:00:00Z",
    "overall_risk": "MEDIUM",
    "summary": "No CRITICAL or HIGH vulnerabilities found. Two MEDIUM findings: redirect open-redirect risk needs documentation, and referrer header stored without sanitization. Three LOW findings around error detail consistency.",
    "findings": [
      {
        "id": "FINDING-001",
        "severity": "MEDIUM",
        "category": "Open Redirect",
        "owasp_ref": "A01:2021",
        "line_numbers": [120],
        "description": "The redirect endpoint trusts original_url from the database entirely. While the URL was validated at creation time, a future blocklist bypass or DB compromise could redirect to a malicious URL. There is no re-validation at redirect time.",
        "code_snippet": "return RedirectResponse(url=url.original_url, status_code=302)",
        "recommendation": "Re-run scheme check (http/https only) on original_url at redirect time as a defence-in-depth measure. Cost is negligible — one urlparse() call.",
        "req_id_affected": "REQ-REDIR-001"
      },
      {
        "id": "FINDING-002",
        "severity": "MEDIUM",
        "category": "Input Sanitization",
        "owasp_ref": "A03:2021",
        "line_numbers": [115],
        "description": "The Referer header is stored directly without length truncation. A malicious client could send a 64KB Referer header which gets written to the database on every redirect, enabling a slow DB bloat attack.",
        "code_snippet": "referrer = request.headers.get(\"referer\")",
        "recommendation": "Truncate referrer to a maximum of 2048 characters before passing to record_access().",
        "req_id_affected": "REQ-ANALY-003"
      },
      {
        "id": "FINDING-003",
        "severity": "LOW",
        "category": "Error Handling",
        "owasp_ref": "A05:2021",
        "line_numbers": [55],
        "description": "The 422 error detail includes an 'error' key in the top-level dict AND inside 'detail' array — slightly redundant but not a security issue.",
        "code_snippet": "detail={\"error\": error_code, \"message\": ..., \"detail\": [{\"field\": \"url\", ...}]}",
        "recommendation": "Cosmetic: remove the duplicate 'error' key from inside the detail array items to keep the schema consistent.",
        "req_id_affected": "REQ-API-001"
      }
    ],
    "passed_checks": [
      "SQL Injection — parameterised ORM queries only, no raw SQL",
      "Authentication — no auth surface in scope",
      "Sensitive data in responses — original_url and short_code only, no PII",
      "Exception leakage — HTTPException detail is always a controlled dict",
      "Type safety — all inputs validated before use"
    ],
    "must_fix_before_merge": []
  }
}
```

### Fix Iteration

`must_fix_before_merge` is **empty** — no CRITICAL or HIGH findings.

The two MEDIUM findings were addressed:

**FINDING-001 fix** — added re-validation of scheme at redirect time (defence-in-depth).
**FINDING-002 fix** — added referrer truncation to 2048 chars.

---

## Self-Critique Loop — Iteration 2 (post-fix validation)

After applying fixes to `app/routers/urls.py`:

```json
{
  "review": {
    "file_path": "app/routers/urls.py",
    "overall_risk": "LOW",
    "summary": "Both MEDIUM findings resolved. Redirect now re-validates scheme. Referrer is truncated. Remaining LOW finding (FINDING-003) is cosmetic and acceptable.",
    "findings": [
      {
        "id": "FINDING-003",
        "severity": "LOW",
        "category": "Error Handling",
        "description": "Minor duplication in 422 error response structure — not a security issue.",
        "recommendation": "Cosmetic cleanup, optional.",
        "req_id_affected": "REQ-API-001"
      }
    ],
    "passed_checks": [
      "SQL Injection", "Open Redirect (fixed)", "Input Sanitization (fixed)",
      "Sensitive data exposure", "Exception leakage", "Type safety"
    ],
    "must_fix_before_merge": []
  }
}
```

**Verdict: APPROVED.** `overall_risk = LOW`, `must_fix_before_merge = []`.

---

## Why JSON Schema Matters Here

Without schema enforcement, the reviewer could return prose like:
> "Looks mostly fine, there's a possible open redirect issue you might want to look at."

That's not actionable in a loop. With JSON schema:
- `overall_risk` is an enum — the loop can `if overall_risk in ["CRITICAL", "HIGH"]: block_merge()`
- `must_fix_before_merge` is a list — the loop knows exactly which findings need fixing
- `findings[].line_numbers` points to exact code locations

Schema enforcement turns qualitative review into a **machine-readable quality gate**.
