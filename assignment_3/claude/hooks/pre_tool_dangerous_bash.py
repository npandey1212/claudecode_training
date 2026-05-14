#!/usr/bin/env python3
"""
PreToolUse hook — dangerous Bash command blocker.

Receives a JSON payload on stdin. Exits 2 (block) if the command matches a
dangerous pattern; exits 0 (allow) otherwise.

Verified: exit-code 2 blocks with stdout as the deny message (Claude Code docs).
Inferred: payload shape { "tool_name": str, "tool_input": { "command": str } }.
"""

import json
import re
import sys
from datetime import datetime, timezone

AUDIT_FILE = ".claude/audit/audit.jsonl"

# (pattern, human-readable label)
# Ordered from most specific to most general to reduce false positives.
DANGEROUS_PATTERNS = [
    # Filesystem destruction
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b", "rm -rf (recursive force delete)"),
    (r"\bsudo\s+rm\b",                                              "sudo rm"),
    (r"\bfind\b.+\s-delete\b",                                     "find -delete (bulk delete)"),
    # Git destructive ops  (settings.json deny list also covers these;
    # hook adds pattern-level logging that the static deny list cannot)
    (r"\bgit\s+push\s+(--force|-f)\b",                             "git push --force"),
    (r"\bgit\s+push\s+\S+\s+\S+\s+(--force|-f)\b",                "git push --force (with remote/branch)"),
    (r"\bgit\s+reset\s+--hard\b",                                  "git reset --hard"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f\b",                             "git clean -f (untracked file wipe)"),
    # Privilege / permissions
    (r"\bchmod\s+-R\s+777\b",                                      "chmod -R 777 (world-writable)"),
    (r"\bsudo\s+chmod\b",                                          "sudo chmod"),
    # Database wipe
    (r"\bDROP\s+TABLE\b",                                          "DROP TABLE"),
    (r"\bDROP\s+DATABASE\b",                                       "DROP DATABASE"),
    (r"\btruncate\s+table\b",                                      "TRUNCATE TABLE"),
    # Remote code execution via pipe
    (r"(curl|wget)\s+.+\|\s*(ba)?sh",                              "curl/wget piped to shell"),
    (r"(curl|wget)\s+.+\|\s*python",                               "curl/wget piped to python"),
    # Fork bomb
    (r":\s*\(\s*\)\s*\{\s*:\s*\|",                                 "fork bomb"),
    # Block heroku prod commands (project-specific; also in deny list)
    (r"\bheroku\s+run\b",                                          "heroku run (prod execution)"),
    (r"\bgit\s+push\s+heroku\b",                                   "git push heroku (prod deploy)"),
]


def _append_audit(entry: dict) -> None:
    """Best-effort append to audit log; never raises."""
    try:
        import os
        os.makedirs(".claude/audit", exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # Unparseable payload — allow and move on

    command = (payload.get("tool_input") or {}).get("command", "")

    for pattern, label in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            message = (
                f"BLOCKED — dangerous Bash command detected\n"
                f"Pattern matched : {label}\n"
                f"Command (first 300 chars): {command[:300]}\n"
                f"\n"
                f"If this action is intentional, run it manually in a terminal\n"
                f"outside Claude Code where you can review the full command first."
            )
            _append_audit({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "PreToolUse",
                "tool": "Bash",
                "identifier": command[:300],
                "status": "blocked",
                "reason": label,
            })
            print(message)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
