# URL Shortener Assignment — Project Guide

## What This Project Is

A spec-driven URL shortener service built as an assignment to practice:
- YAML prompt library design
- Formal specification writing (SHALL/MUST language, Gherkin, OpenAPI)
- Spec-to-code generation with traceability
- Self-critique loops (generate → review → fix → validate)
- Auto-generated tests with full traceability matrix

The deliverable is **the process and artifacts**, not just working code.

---

## Tech Stack

- **Language/Framework**: Python + FastAPI
- **Database**: SQLite (via SQLAlchemy) — simple, no Docker dependency for dev
- **Testing**: pytest
- **Validation**: Pydantic (built into FastAPI)
- **Scaffold reference**: tiangolo/full-stack-fastapi-template (ideas only, do NOT copy)

---

## Delivery Plan

### Part A — Prompt Library + Specification
Maps to Assignment Parts 1 & 2.

1. Create `prompts/` directory with 4 YAML templates:
   - `prompts/spec-writer.yaml` — product analyst role
   - `prompts/architect.yaml` — senior architect role
   - `prompts/code-reviewer.yaml` — security reviewer role
   - `prompts/test-generator.yaml` — QA engineer role
2. Use `spec-writer.yaml` to generate `specs/url-shortener.yaml`
   - SHALL/MUST normative language
   - Minimum 6 Gherkin scenarios
   - OpenAPI contract for all endpoints
   - Non-functional requirements (perf, security, rate limiting)
3. Generate Mermaid diagrams in `specs/diagrams/`
   - Sequence diagram: URL shortening flow
   - ER diagram: data model
   - State diagram: URL lifecycle (active → expired → deleted)

### Part B — Implementation
Maps to Assignment Part 3.

1. Use `architect.yaml` to produce a technical plan referencing requirement IDs
2. Implement features task-by-task with traceability comments in code (`# REQ-SHORT-001`)
3. Self-critique loop: Generate → Review (via `code-reviewer.yaml`) → Fix → Validate
4. At least one interaction uses JSON schema enforcement (document it in `docs/schema-enforcement.md`)

### Part C — Tests + Traceability
Maps to Assignment Part 4.

1. Use `test-generator.yaml` to generate tests covering all Gherkin scenarios
2. Run tests, document pass/fail
3. Produce `docs/traceability-matrix.md`: requirement ID → code file → test file → pass/fail
4. Fix failures and re-run (document iterations)

---

## Directory Structure

```
url-shortener-assignment/
├── CLAUDE.md                        ← this file
├── prompts/
│   ├── spec-writer.yaml
│   ├── architect.yaml
│   ├── code-reviewer.yaml
│   └── test-generator.yaml
├── specs/
│   ├── url-shortener.yaml           ← formal spec
│   └── diagrams/
│       ├── sequence.md
│       ├── er-diagram.md
│       └── state-lifecycle.md
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── routers/
│   │   └── urls.py
│   └── database.py
├── tests/
│   ├── test_shorten.py
│   ├── test_redirect.py
│   ├── test_analytics.py
│   └── test_expiry.py
├── docs/
│   ├── traceability-matrix.md
│   └── schema-enforcement.md
├── requirements.txt
└── README.md
```

---

## Requirement ID Conventions

All requirement IDs follow this pattern: `REQ-[DOMAIN]-[NNN]`

| Domain | Meaning |
|--------|---------|
| `SHORT` | URL shortening core |
| `REDIR` | Redirect behavior |
| `ANALY` | Analytics tracking |
| `EXPRY` | Expiry handling |
| `VALID` | Validation rules |
| `API`   | API contract / error responses |
| `NFR`   | Non-functional requirements |

Example usage in code:
```python
# REQ-SHORT-001: Generate unique 6-character alphanumeric short code
def generate_short_code() -> str:
    ...
```

---

## YAML Prompt Template Schema

Every prompt template in `prompts/` must include these fields:

```yaml
name: string
version: string          # semver e.g. "1.0.0"
role: string             # persona Claude should adopt
task: string             # what Claude must do
input_variables:         # list of {{ variable }} placeholders used
  - name: string
    description: string
output_schema:           # shape of the expected output
  type: object | string | array
  fields: ...
tags:                    # searchable labels
  - string
```

---

## Self-Critique Loop Protocol

When running the generate → review → fix cycle:

1. **Generate**: Produce code for a feature
2. **Review**: Feed it to `code-reviewer.yaml` prompt; get back JSON with severity scores
3. **Fix**: Address all HIGH and CRITICAL findings
4. **Validate**: Re-run review; confirm no HIGH/CRITICAL remain
5. **Document**: Note any interesting findings in a comment or in `docs/`

---

## Key Conventions

- Each source file must have a module-level comment listing which REQ IDs it implements
- Tests must reference the Gherkin scenario they cover in a docstring
- No feature implementation before its requirement exists in the spec
- All diagrams use Mermaid syntax (renders in GitHub)

---

## Assignment Constraints (do not violate)

- Do NOT copy code from reference implementations (YOURLS, kutt, tiny-url)
- Code must be generated FROM the spec, not written independently then spec written after
- The process artifacts (prompts, spec, diagrams, traceability matrix) matter as much as the code
