# Sequence Diagrams — URL Shortener Service

---

## 1. URL Shortening Flow (POST /api/v1/shorten)

Covers: REQ-SHORT-001, REQ-SHORT-002, REQ-SHORT-003, REQ-SHORT-004, REQ-SHORT-005, REQ-VALID-001 to REQ-VALID-004

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant VAL as Validator
    participant DB as Database (SQLite)
    participant GEN as Code Generator

    User->>API: POST /api/v1/shorten<br/>{ url, expires_at? }

    API->>VAL: validate(url, expires_at)

    alt URL scheme is not http/https
        VAL-->>API: ValidationError (REQ-VALID-001)
        API-->>User: 422 { error: "invalid_url" }
    else URL is malformed
        VAL-->>API: ValidationError (REQ-VALID-002)
        API-->>User: 422 { error: "invalid_url" }
    else Domain is blocklisted
        VAL-->>API: ValidationError (REQ-VALID-003)
        API-->>User: 422 { error: "domain_blocked" }
    else URL length > 2048
        VAL-->>API: ValidationError (REQ-VALID-004)
        API-->>User: 422 { error: "invalid_url" }
    else expires_at is in the past
        VAL-->>API: ValidationError (REQ-EXPRY-003)
        API-->>User: 422 { error: "invalid_expiry" }
    else Validation passed
        VAL-->>API: OK

        API->>DB: SELECT * FROM urls WHERE original_url = ?
        DB-->>API: result

        alt URL already exists (REQ-SHORT-004)
            API-->>User: 200 { short_code, short_url, original_url, created_at }
        else URL is new
            API->>GEN: generate_short_code()
            GEN-->>API: candidate_code (6 alphanumeric chars)

            API->>DB: SELECT id FROM urls WHERE short_code = ?
            DB-->>API: result

            alt Collision detected (REQ-SHORT-005)
                GEN-->>API: retry (max 5 attempts)
            else Code is unique
                API->>DB: INSERT INTO urls (short_code, original_url, ...)
                DB-->>API: saved (REQ-SHORT-003)
                API-->>User: 201 { short_code, short_url, original_url, created_at }
            end
        end
    end
```

---

## 2. URL Redirect Flow (GET /{code})

Covers: REQ-REDIR-001, REQ-REDIR-002, REQ-REDIR-003, REQ-ANALY-001, REQ-ANALY-002, REQ-ANALY-003, REQ-EXPRY-002

```mermaid
sequenceDiagram
    actor Visitor
    participant API as FastAPI Router
    participant DB as Database (SQLite)
    participant LOG as Access Logger

    Visitor->>API: GET /{code}<br/>Headers: Referer?

    API->>DB: SELECT * FROM urls WHERE short_code = ?
    DB-->>API: result

    alt Short code not found (REQ-REDIR-002)
        API-->>Visitor: 404 { error: "not_found" }
    else URL is expired (REQ-REDIR-003 + REQ-EXPRY-002)
        API-->>Visitor: 410 { error: "url_expired" }
    else URL is active (REQ-REDIR-001)
        API->>DB: UPDATE urls SET click_count+1, last_accessed_at=now() (REQ-ANALY-001, REQ-ANALY-002)
        API->>LOG: INSERT url_access_logs (url_id, accessed_at, referrer, ip_hash) (REQ-ANALY-003)
        LOG-->>API: logged
        API-->>Visitor: 302 Location: {original_url}
    end
```

---

## 3. Analytics Retrieval (GET /api/v1/urls/{code}/stats)

Covers: REQ-ANALY-004

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant DB as Database (SQLite)

    User->>API: GET /api/v1/urls/{code}/stats

    API->>DB: SELECT * FROM urls WHERE short_code = ?
    DB-->>API: result

    alt Short code not found
        API-->>User: 404 { error: "not_found" }
    else Found
        API-->>User: 200 {<br/>  short_code,<br/>  original_url,<br/>  click_count,<br/>  created_at,<br/>  last_accessed_at,<br/>  expires_at,<br/>  is_active<br/>}
    end
```
