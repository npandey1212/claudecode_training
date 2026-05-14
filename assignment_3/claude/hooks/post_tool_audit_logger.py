#!/usr/bin/env python3
"""
PostToolUse hook — append-only audit logger.

Writes one JSON line to .claude/audit/audit.jsonl for every tool call that
completes (i.e. was not blocked by a PreToolUse hook).

This hook MUST exit 0. A non-zero exit from a PostToolUse hook may surface
as an error to the user; logging failure must never interfere with work.

Verified: PostToolUse fires after the tool completes; exit 0 is required.
Inferred: payload shape:
  {
    "hook_event_name": "PostToolUse",
    "tool_name": str,
    "tool_input": { ... },          # same shape as PreToolUse input
    "tool_response": { ... },       # inferred — may not always be present
    "session_id": str               # inferred — may not be present
  }
"""

import json
import os
import sys
from datetime import datetime, timezone

AUDIT_FILE = ".claude/audit/audit.jsonl"


def _identifier(tool_name: str, tool_input: dict) -> str | None:
    """Extract the most useful single-line identifier from tool_input."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return cmd[:300] if cmd else None
    if tool_name in ("Edit", "Write", "MultiEdit", "Read", "Glob"):
        return tool_input.get("file_path") or tool_input.get("pattern")
    if tool_name == "Grep":
        return tool_input.get("pattern")
    if tool_name in ("WebFetch", "WebSearch"):
        return tool_input.get("url") or tool_input.get("query")
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)

        tool_name = payload.get("tool_name", "unknown")
        tool_input = payload.get("tool_input") or {}

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": payload.get("hook_event_name", "PostToolUse"),
            "tool": tool_name,
            "identifier": _identifier(tool_name, tool_input),
            "session_id": payload.get("session_id"),
            "status": "completed",
        }

        os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception:
        pass  # Logging failure must never surface to the user

    sys.exit(0)  # Always allow


if __name__ == "__main__":
    main()
