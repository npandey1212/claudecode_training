# ER Diagram — URL Shortener Data Model

Covers: REQ-SHORT-003, REQ-ANALY-001, REQ-ANALY-002, REQ-ANALY-003, REQ-EXPRY-001, NFR-SEC-004

---

```mermaid
erDiagram

    urls {
        INTEGER id PK "AUTO INCREMENT"
        VARCHAR short_code UK "6 chars, alphanumeric, INDEXED"
        TEXT original_url "NOT NULL, INDEXED for duplicate check"
        DATETIME created_at "NOT NULL DEFAULT now()"
        DATETIME expires_at "NULLABLE — null means never expires"
        BOOLEAN is_active "DEFAULT true — false = soft deleted"
        INTEGER click_count "DEFAULT 0"
        DATETIME last_accessed_at "NULLABLE — updated on each redirect"
    }

    url_access_logs {
        INTEGER id PK "AUTO INCREMENT"
        INTEGER url_id FK "REFERENCES urls(id)"
        DATETIME accessed_at "NOT NULL DEFAULT now()"
        TEXT referrer "NULLABLE — HTTP Referer header value"
        VARCHAR ip_hash "NULLABLE — SHA-256 of client IP (NFR-SEC-004)"
    }

    urls ||--o{ url_access_logs : "has many"
```

---

## Field-Level Notes

| Table | Field | Why it exists |
|---|---|---|
| `urls` | `short_code` | The lookup key on every redirect — must be UNIQUE + INDEXED |
| `urls` | `original_url` | Indexed to detect duplicates on POST (REQ-SHORT-004) |
| `urls` | `expires_at` | Nullable — if null, URL lives forever (REQ-EXPRY-001) |
| `urls` | `is_active` | Soft delete flag — allows DELETE without losing analytics history |
| `urls` | `click_count` | Denormalized counter for fast stats reads (REQ-ANALY-001) |
| `urls` | `last_accessed_at` | Updated on every redirect for recency tracking (REQ-ANALY-002) |
| `url_access_logs` | `referrer` | Raw referrer per click event (REQ-ANALY-003) |
| `url_access_logs` | `ip_hash` | Hashed IP — never plaintext per NFR-SEC-004 |

---

## Design Decisions

- **Two-table design**: `urls` holds current state, `url_access_logs` holds history.
  This lets us compute `click_count` from the log table if needed, but we keep
  a denormalized counter in `urls` for O(1) reads on the stats endpoint.

- **Soft delete via `is_active`**: When a URL is "deleted", we set `is_active=false`
  rather than removing the row. This preserves the access log history and prevents
  short code reuse for deleted URLs.

- **SQLite for development**: Simple file-based database. SQLAlchemy ORM means
  we can swap to PostgreSQL in production with no code changes.
