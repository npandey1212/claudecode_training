#!/usr/bin/env python3
"""
Stop hook — session summary generator.

Reads .claude/audit/audit.jsonl and .claude/audit/prompts.jsonl, then writes
a human-readable Markdown summary to .claude/audit/session-summary-latest.md.

Because audit.jsonl is append-only across all sessions (no session-scope
boundary is written between sessions), this summary reflects the full log
contents, not just the current session. Filter by session_id in the JSONL
files for a session-scoped view.

Verified: Stop event fires when Claude Code finishes a response turn.
Inferred: payload may be empty or contain { "session_id": str }.
Exit 0 always.
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

AUDIT_FILE   = ".claude/audit/audit.jsonl"
PROMPTS_FILE = ".claude/audit/prompts.jsonl"
SUMMARY_FILE = ".claude/audit/session-summary-latest.md"

# Maximum entries to display in each list section to keep the summary readable
MAX_LIST_ITEMS = 20


def _read_jsonl(path: str) -> list[dict]:
    entries: list[dict] = []
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if raw:
                    try:
                        entries.append(json.loads(raw))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return entries


def _format_list(items: list[str], max_items: int = MAX_LIST_ITEMS) -> list[str]:
    lines = [f"- `{item}`" for item in items[:max_items]]
    if len(items) > max_items:
        lines.append(f"- … and {len(items) - max_items} more")
    return lines or ["- None recorded"]


def main() -> None:
    try:
        # Payload from Stop event (may be empty)
        try:
            payload = json.load(sys.stdin)
            session_id = payload.get("session_id")
        except Exception:
            session_id = None

        now = datetime.now(timezone.utc).isoformat()

        audit   = _read_jsonl(AUDIT_FILE)
        prompts = _read_jsonl(PROMPTS_FILE)

        # ── Tool usage ─────────────────────────────────────────────────────
        tool_counts: Counter = Counter(e.get("tool", "unknown") for e in audit)

        # ── Files touched (Edit/Write/Read/MultiEdit) ──────────────────────
        file_tools = {"Edit", "Write", "MultiEdit", "Read"}
        files_touched = sorted(set(
            e["identifier"]
            for e in audit
            if e.get("tool") in file_tools and e.get("identifier")
        ))

        # ── Bash commands run ──────────────────────────────────────────────
        commands = [
            e["identifier"]
            for e in audit
            if e.get("tool") == "Bash" and e.get("identifier")
        ]

        # ── Blocked actions ────────────────────────────────────────────────
        blocked = [
            e for e in audit if e.get("status") == "blocked"
        ]
        blocked_lines = [
            f"- `{e.get('tool','?')}` — {e.get('reason','unknown reason')} "
            f"({e.get('identifier','')[:80]})"
            for e in blocked[:MAX_LIST_ITEMS]
        ]

        # ── Build Markdown ─────────────────────────────────────────────────
        md: list[str] = [
            "# Session Summary — Conduit (flask-realworld-example-app)",
            "",
            f"**Generated :** {now}",
        ]
        if session_id:
            md.append(f"**Session ID :** `{session_id}`")
        md += [
            f"**Audit entries :** {len(audit)}",
            f"**Prompts logged:** {len(prompts)}",
            "",
            "> Note: audit.jsonl is append-only across all sessions.",
            "> This summary covers the full log. Filter by `session_id` for",
            "> a single-session view.",
            "",
            "---",
            "",
            "## Tools used",
            "",
        ]
        if tool_counts:
            for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
                status_tag = " *(includes blocked)*" if any(
                    e.get("tool") == tool and e.get("status") == "blocked"
                    for e in audit
                ) else ""
                md.append(f"| `{tool}` | {count} |{status_tag}")
        else:
            md.append("No tool calls recorded.")

        md += [
            "",
            "## Files touched (Edit / Write / Read)",
            "",
        ]
        md += _format_list(files_touched)

        md += [
            "",
            "## Bash commands run",
            "",
        ]
        md += _format_list(commands)

        md += [
            "",
            f"## Blocked actions ({len(blocked)})",
            "",
        ]
        md += blocked_lines if blocked_lines else ["- None"]

        md += [
            "",
            "## Prompts submitted",
            "",
            f"Total: {len(prompts)}",
            "",
        ]
        for p in prompts[-5:]:  # Show last 5 prompts (truncated)
            text = p.get("prompt", "")[:120]
            md.append(f'- `{p.get("timestamp","")[:19]}` — {text}…')

        md.append("")

        os.makedirs(os.path.dirname(SUMMARY_FILE), exist_ok=True)
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")

    except Exception:
        pass  # Summary failure must never interfere with session end

    sys.exit(0)


if __name__ == "__main__":
    main()
