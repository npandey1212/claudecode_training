#!/usr/bin/env python3
"""
PreToolUse hook — secret / credential leak scanner for Edit, Write, MultiEdit.

Receives a JSON payload on stdin. Scans the *new* content being written for
patterns that look like credentials. Exits 2 (block) if a match is found;
exits 0 (allow) otherwise.

Verified: exit-code 2 blocks with stdout as the deny message.
Inferred: payload shapes:
  Write     -> { "tool_input": { "file_path": str, "content": str } }
  Edit      -> { "tool_input": { "file_path": str, "new_string": str } }
  MultiEdit -> { "tool_input": { "file_path": str, "edits": [ { "new_string": str } ] } }
"""

import json
import re
import sys
from datetime import datetime, timezone

AUDIT_FILE = ".claude/audit/audit.jsonl"

# Each tuple: (compiled regex, human label)
# Patterns are intentionally conservative to minimise false positives.
SECRET_PATTERNS = [
    # Private key blocks
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
     "PEM private key block"),

    # AWS-style keys
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
     "AWS access key ID (AKIA prefix)"),
    (re.compile(r"(?i)\baws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9+/]{40}\b"),
     "AWS secret access key assignment"),

    # Generic high-entropy token assignments (≥24 chars of base64/hex after the = / :)
    (re.compile(r"(?i)\bapi[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9\-_]{24,}"),
     "API key assignment"),
    (re.compile(r"(?i)\bsecret[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9\-_!@#$%^&*]{16,}"),
     "secret_key assignment"),
    (re.compile(r"(?i)\bprivate[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9\-_]{24,}"),
     "private_key assignment"),

    # Bearer / JWT tokens in source code (long base64 blobs)
    (re.compile(r"\bBearer\s+[A-Za-z0-9\-_]{30,}\b"),
     "Bearer token literal"),
    (re.compile(r"eyJ[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{10,}"),
     "JWT token (eyJ… structure)"),

    # Password literals with a real-looking value (not 'secret-key' placeholder)
    (re.compile(r"(?i)\bpassword\s*[=:]\s*['\"](?!secret-key|myprecious|example|changeme|placeholder|<)[^'\"\s]{8,}['\"]"),
     "password literal assignment"),

    # Generic token= patterns with long values
    (re.compile(r"(?i)\btoken\s*[=:]\s*['\"]?[A-Za-z0-9\-_.]{30,}"),
     "token literal (long value)"),
]

# Strings that, if present anywhere in the matched text, indicate a false positive
# (test fixtures, documentation placeholders, config templates).
SAFE_INDICATORS = [
    "your_", "YOUR_", "<", ">", "example", "EXAMPLE",
    "placeholder", "changeme", "CHANGEME", "TODO", "test_",
    "fake_", "dummy_", "myprecious",           # this repo's test password fixture
    "secret-key",                              # this repo's default CONDUIT_SECRET
    "localdev",                                # this repo's dev CONDUIT_SECRET
]


def _is_safe(match_text: str) -> bool:
    return any(ind in match_text for ind in SAFE_INDICATORS)


def _extract_content(payload: dict) -> tuple[str, str]:
    """Return (content_to_scan, file_path)."""
    tool_name = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}

    if tool_name == "Write":
        return ti.get("content", ""), ti.get("file_path", "unknown")

    if tool_name == "Edit":
        return ti.get("new_string", ""), ti.get("file_path", "unknown")

    if tool_name == "MultiEdit":
        edits = ti.get("edits") or []
        combined = " ".join(e.get("new_string", "") for e in edits)
        return combined, ti.get("file_path", "unknown")

    return "", "unknown"


def _append_audit(entry: dict) -> None:
    try:
        import os
        os.makedirs(".claude/audit", exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _redact(text: str) -> str:
    """Show first 6 chars and last 4, redact the middle."""
    if len(text) <= 10:
        return text[:3] + "***"
    return text[:6] + "…" + text[-4:]


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    content, file_path = _extract_content(payload)
    if not content:
        sys.exit(0)

    for regex, label in SECRET_PATTERNS:
        match = regex.search(content)
        if match and not _is_safe(match.group(0)):
            redacted = _redact(match.group(0))
            message = (
                f"BLOCKED — possible credential detected in write to: {file_path}\n"
                f"Secret type : {label}\n"
                f"Match (redacted): {redacted}\n"
                f"\n"
                f"If this is a test fixture or placeholder, use a clearly fake value\n"
                f"(e.g. 'changeme', 'example_key') so the scanner can exclude it.\n"
                f"If it is a real credential, remove it from source and use an env var."
            )
            _append_audit({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "PreToolUse",
                "tool": payload.get("tool_name", "Edit/Write"),
                "identifier": file_path,
                "status": "blocked",
                "reason": f"secret scan: {label}",
            })
            print(message)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
