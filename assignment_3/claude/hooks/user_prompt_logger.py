#!/usr/bin/env python3
"""
UserPromptSubmit hook — prompt logger.

Appends one JSON line to .claude/audit/prompts.jsonl for every prompt the
user submits. Prioritises reliability: any exception is silently swallowed
so that logging never blocks a prompt.

Verified: UserPromptSubmit fires before Claude processes the prompt.
Inferred: payload shape:
  {
    "hook_event_name": "UserPromptSubmit",
    "session_id": str,      # inferred — may not be present
    "prompt": str           # inferred — field name uncertain; also try "user_prompt"
  }

Exit 0 always (logging hooks must not block user interaction).
"""

import json
import os
import sys
from datetime import datetime, timezone

PROMPTS_FILE = ".claude/audit/prompts.jsonl"


def _extract_prompt(payload: dict) -> str:
    """
    Try several field names in case the exact key differs across versions.
    Returns an empty string if none found.
    """
    for key in ("prompt", "user_prompt", "message", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def main() -> None:
    try:
        payload = json.load(sys.stdin)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": payload.get("session_id"),
            "prompt": _extract_prompt(payload),
        }

        os.makedirs(os.path.dirname(PROMPTS_FILE), exist_ok=True)
        with open(PROMPTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception:
        pass  # Logging failure must never block prompt submission

    sys.exit(0)


if __name__ == "__main__":
    main()
