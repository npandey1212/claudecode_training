#!/usr/bin/env python3
"""
PreToolUse hook — file-scope enforcement for Edit, Write, MultiEdit.

Only allows writes to paths inside ALLOWED_PREFIXES. Explicitly denies
paths in DENIED_PREFIXES regardless of the allow list.

To expand the allowed scope, add entries to ALLOWED_PREFIXES below.

Verified: exit-code 2 blocks; exit-code 0 allows.
Inferred: file_path in tool_input may be absolute or relative.
          This script normalises both to a path relative to the project root.
"""

import json
import os
import sys
from datetime import datetime, timezone

AUDIT_FILE = ".claude/audit/audit.jsonl"

# Project root = two levels above this script (.claude/hooks/this_script.py)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))

# ── Scope configuration ────────────────────────────────────────────────────
# Paths are matched as prefixes after resolving to a path relative to
# PROJECT_ROOT. Use forward slashes; trailing slash is optional.
#
# Assignment-specific paths (primary deliverables):
ALLOWED_PREFIXES = [
    ".claude/",         # governance layer and slash commands
    "doc/",             # workflow docs and impact analysis
    "docs/",            # alternative docs directory name
    "tests/",           # test files and factories
    ".github/",         # CI/CD configuration
    # Standard development paths (needed for Flask feature work):
    "conduit/",         # application source (blueprints, models, views)
    "migrations/",      # Alembic migration scripts
    "requirements/",    # dependency files
]

# Individual root-level files that are safe to edit:
ALLOWED_FILES = {
    "autoapp.py",
    "setup.cfg",
    "Pipfile",
    "Pipfile.lock",
    ".gitignore",
    ".travis.yml",
}

# These are denied even if they would otherwise match an ALLOWED prefix.
DENIED_PREFIXES = [
    ".env",             # environment secrets
    "secrets/",
    ".ssh/",
]
# ── End configuration ───────────────────────────────────────────────────────


def _rel(file_path: str) -> str:
    """
    Return the path relative to PROJECT_ROOT, normalised to forward slashes.
    Falls back to the original path if it cannot be made relative.
    """
    try:
        abs_path = os.path.normpath(os.path.abspath(file_path))
        rel = os.path.relpath(abs_path, PROJECT_ROOT)
        return rel.replace("\\", "/")
    except ValueError:
        # os.path.relpath raises ValueError on Windows when drives differ
        return file_path.replace("\\", "/")


def _check(rel_path: str) -> tuple[bool, str]:
    """Return (is_allowed, reason_if_denied)."""
    # Denied list takes priority
    for denied in DENIED_PREFIXES:
        if rel_path == denied.rstrip("/") or rel_path.startswith(denied.rstrip("/") + "/"):
            return False, f"path is explicitly denied ({denied})"

    # Exact file match
    if rel_path in ALLOWED_FILES:
        return True, ""

    # Prefix match
    for prefix in ALLOWED_PREFIXES:
        norm = prefix.rstrip("/") + "/"
        if rel_path.startswith(norm) or rel_path == prefix.rstrip("/"):
            return True, ""

    return False, (
        f"path is outside the approved scope for this project.\n"
        f"Allowed prefixes : {', '.join(ALLOWED_PREFIXES)}\n"
        f"Allowed root files: {', '.join(sorted(ALLOWED_FILES))}\n"
        f"To expand the scope, add the path to ALLOWED_PREFIXES in\n"
        f"  .claude/hooks/pre_tool_file_scope.py"
    )


def _append_audit(entry: dict) -> None:
    try:
        os.makedirs(".claude/audit", exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        sys.exit(0)  # No path to check (e.g. some MultiEdit forms)

    rel = _rel(file_path)
    allowed, reason = _check(rel)

    if not allowed:
        _append_audit({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "PreToolUse",
            "tool": payload.get("tool_name", "Edit/Write"),
            "identifier": rel,
            "status": "blocked",
            "reason": "file scope enforcement",
        })
        print(
            f"BLOCKED — edit outside approved scope\n"
            f"File    : {rel}\n"
            f"Reason  : {reason}"
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
