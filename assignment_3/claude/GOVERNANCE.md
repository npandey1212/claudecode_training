# Claude Code Governance — Conduit (flask-realworld-example-app)

This document explains the safety and audit layer configured under `.claude/`
for this repository. It covers what each hook does, why it exists, the
settings hierarchy, and clearly distinguishes verified Claude Code behaviour
from inferred implementation details.

---

## Evidence key

| Symbol | Meaning |
|--------|---------|
| ✅ | Verified — stated in Claude Code documentation or observed in practice |
| ⚠️ | Inferred — reasonable assumption; exact behaviour may differ across versions |

---

## File structure

```
.claude/
├── CLAUDE.md                      ✅ Architecture + coding conventions reference
├── GOVERNANCE.md                  ✅ This file
├── settings.json                  ✅ Project-level permissions + hook registration
├── settings.local.json            ✅ Machine-local overrides (not committed to shared config)
├── commands/                      ✅ Custom slash commands (/review, /commit, etc.)
│   ├── commit.md
│   ├── onboard.md
│   ├── review.md
│   ├── ship.md
│   └── test-gen.md
├── hooks/                         ✅ Hook scripts (Python; receive JSON on stdin)
│   ├── pre_tool_dangerous_bash.py      PreToolUse — blocks destructive shell commands
│   ├── pre_tool_secret_scan.py         PreToolUse — blocks credential writes
│   ├── pre_tool_file_scope.py          PreToolUse — enforces allowed edit paths
│   ├── post_tool_audit_logger.py       PostToolUse — appends every tool call to audit.jsonl
│   ├── user_prompt_logger.py           UserPromptSubmit — appends every prompt to prompts.jsonl
│   └── stop_session_summary.py         Stop — writes session-summary-latest.md
└── audit/                         ✅ Append-only log files (created at runtime)
    ├── .gitkeep                        Ensures directory is tracked by git
    ├── audit.jsonl                     One JSON line per tool call (blocked + completed)
    ├── prompts.jsonl                   One JSON line per submitted prompt
    └── session-summary-latest.md       Human-readable summary; overwritten each session
```

---

## Hook scripts

### 1. `pre_tool_dangerous_bash.py`

**Event:** `PreToolUse` — `Bash` tool only

**What it does:**
Scans the `command` string against a list of regex patterns for destructive or
irreversible shell operations before the command is executed. On a match, it
exits with code 2 and prints a human-readable block message. It also appends a
`status: blocked` entry to `audit.jsonl` before exiting.

**Patterns blocked:**

| Pattern | Label |
|---------|-------|
| `rm -rf` / `rm -fr` | Recursive force delete |
| `sudo rm` | Privileged remove |
| `find … -delete` | Bulk find-and-delete |
| `git push --force` / `-f` | Destructive force-push |
| `git reset --hard` | Hard reset (destroys local changes) |
| `git clean -f` | Untracked file wipe |
| `chmod -R 777` | World-writable permissions |
| `DROP TABLE` / `DROP DATABASE` / `TRUNCATE TABLE` | SQL table/database wipe |
| `curl … \| sh` / `wget … \| sh` | Remote code execution via pipe |
| `heroku run` / `git push heroku` | Production execution (project-specific) |
| fork bomb `:(){ :|:& };:` | Process explosion |

**Why it exists:**
The static `deny` list in `settings.json` catches exact strings. This hook
adds regex-level pattern matching (handles flag reordering, spacing variations,
and compound commands) and produces a logged, human-readable block message
rather than a silent deny. It also overlaps intentionally with the static deny
list as defence in depth.

**Note:** The hook does not gate on whether a command is inside the allow list.
A command can pass the static allow list and still be blocked here if it matches
a dangerous pattern (e.g. a `flask` command that also pipes to `sh`).

---

### 2. `pre_tool_secret_scan.py`

**Event:** `PreToolUse` — `Edit`, `Write`, `MultiEdit` tools

**What it does:**
Extracts the *new content* being written from the tool payload and scans it
against conservative regex patterns for credentials. Exits 2 with a redacted
block message if a likely secret is found. Known safe values from this project's
test fixtures and config templates are excluded from blocking.

**Patterns detected:**

| Pattern | Label |
|---------|-------|
| `-----BEGIN PRIVATE KEY-----` etc. | PEM private key block |
| `AKIA[0-9A-Z]{16}` | AWS access key ID |
| `aws_secret_access_key = <40 chars>` | AWS secret access key |
| `api_key = <24+ chars>` | API key assignment |
| `secret_key = <16+ chars>` | Secret key assignment |
| `Bearer <30+ chars>` | Bearer token literal |
| `eyJ…` three-part JWT | JWT token |
| `password = '<8+ chars>'` | Password literal (excluding known fixtures) |
| `token = <30+ chars>` | Long token literal |

**Known safe values excluded from blocking** (false-positive suppression):
`secret-key` (CONDUIT_SECRET default), `myprecious` (test fixture password),
`localdev` (dev CONDUIT_SECRET), `changeme`, `example`, `placeholder`, `your_…`

**Why it exists:**
This repo uses environment variables for secrets (`CONDUIT_SECRET`,
`DATABASE_URL`), but the default `CONDUIT_SECRET = 'secret-key'` fallback in
`settings.py` is a known footgun. This hook prevents a real secret from
accidentally replacing that fallback in source code. It is not a substitute for
a secrets manager — it is a last-resort check before a file write.

---

### 3. `pre_tool_file_scope.py`

**Event:** `PreToolUse` — `Edit`, `Write`, `MultiEdit` tools

**What it does:**
Resolves the target file path to a path relative to the project root and
checks it against `ALLOWED_PREFIXES` and `ALLOWED_FILES`. Exits 2 if the path
is outside the approved scope or matches `DENIED_PREFIXES`.

**Allowed scope (default):**

| Path | Category |
|------|----------|
| `.claude/` | Governance layer (primary assignment deliverable) |
| `doc/`, `docs/` | Documentation |
| `tests/` | Test files and factories |
| `.github/` | CI/CD configuration |
| `conduit/` | Application source (standard Flask development) |
| `migrations/` | Alembic migration scripts |
| `requirements/` | Dependency files |
| Root files: `autoapp.py`, `setup.cfg`, `Pipfile`, `.gitignore` | Config files |

**Explicitly denied regardless of allow list:** `.env`, `secrets/`, `.ssh/`

**Why it exists:**
For an assignment context, the scope of Claude Code edits should be bounded.
This hook surfaces any edit that strays outside expected paths and forces a
conscious decision (either adjust `ALLOWED_PREFIXES` in the script, or run
the command manually). It also prevents accidental overwrites of system or
credential files.

**How to adjust:**
Edit `ALLOWED_PREFIXES` or `ALLOWED_FILES` in
`.claude/hooks/pre_tool_file_scope.py`. The lists are documented inline.

---

### 4. `post_tool_audit_logger.py`

**Event:** `PostToolUse` — all tools (`matcher: ".*"`)

**What it does:**
Appends one JSON object to `.claude/audit/audit.jsonl` for every tool call
that completes. The entry includes timestamp, event name, tool name, a
one-line identifier (command or file path), session ID if available, and
`status: completed`.

**Combined with the blocked entries written by PreToolUse hooks,**
`audit.jsonl` is a complete record of both attempted-and-blocked and
completed tool calls.

**Exit behaviour:** Always exits 0. A logging failure is silently swallowed
and must never surface to the user.

**Why it exists:**
Provides a durable, inspectable record of what Claude Code did during a session.
Useful for assignment review, debugging unexpected changes, and demonstrating
that the governance layer is functioning.

---

### 5. `user_prompt_logger.py`

**Event:** `UserPromptSubmit`

**What it does:**
Appends one JSON object to `.claude/audit/prompts.jsonl` for every prompt the
user submits. The entry includes timestamp, session ID if available, and the
prompt text.

**Exit behaviour:** Always exits 0.

**Why it exists:**
Provides a chronological record of the instructions given during a session.
Combined with `audit.jsonl`, this gives a full picture of intent (prompts) and
action (tool calls) for any session.

---

### 6. `stop_session_summary.py`

**Event:** `Stop`

**What it does:**
Reads `audit.jsonl` and `prompts.jsonl`, then writes a Markdown summary to
`.claude/audit/session-summary-latest.md`. The summary includes:
- Timestamp and session ID (if available)
- Tool call counts grouped by tool name
- Files touched (Edit/Write/Read calls)
- Bash commands run (capped at 20 for readability)
- Blocked actions with reason
- Last 5 prompts (truncated to 120 characters each)

**Limitation:** Because `audit.jsonl` is append-only without a per-session
boundary marker, the summary covers the full log history, not just the current
session. Filter by `session_id` in the JSONL files for a single-session view.

**Exit behaviour:** Always exits 0.

---

## Settings hierarchy

Claude Code merges settings from four sources in this order (lowest to highest
priority):

| Level | File | Scope |
|-------|------|-------|
| 1. Enterprise policy | Managed by IT; not present in this repo | Organisation-wide; overrides everything |
| 2. User settings | `~/.claude/settings.json` | Personal preferences on this machine |
| 3. **Project settings** | `.claude/settings.json` ← **this file** | Shared with the team via git |
| 4. Local project overrides | `.claude/settings.local.json` | Machine-specific; gitignored |

Higher-priority levels override lower-priority levels for the same key.
Hook registration in project settings applies to everyone who works in
this repository.

`.claude/settings.local.json` in this repo contains the corporate proxy
workaround (`pip install … --trusted-host …`) that is specific to the
current machine and should not be committed to shared config.

---

## Permission mode rationale

This project uses **project-level settings** (`settings.json`) without
`dangerouslySkipPermissions`. The chosen approach:

1. **Static deny list** in `permissions.deny` — instantly blocks known-exact
   dangerous commands without user confirmation prompts. This is the fastest
   gate and requires no script execution.

2. **PreToolUse hooks** — add regex-level pattern matching, logging, and
   human-readable block messages for cases the static list cannot catch.

3. **Allowlist** in `permissions.allow` — explicitly pre-approves safe,
   expected commands (`flask test`, `flask lint`, `git diff`, etc.) so routine
   work does not trigger constant permission prompts.

4. **No `dangerouslySkipPermissions`** — this flag bypasses all human
   confirmation for tool calls that are not explicitly allowed or denied. For
   an assignment repository, the overhead of occasional prompts is acceptable
   and the safety benefit is material.

5. **Project-local scope** — hooks and permissions live in `.claude/` and are
   version-controlled. Any engineer who clones this repo and uses Claude Code
   gets the same governance layer automatically.

---

## Verified vs inferred

The following table distinguishes what is confirmed in Claude Code documentation
from what this governance layer assumes about runtime behaviour.

| Claim | Status |
|-------|--------|
| Hook events: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop` | ✅ Verified |
| Exit code 2 from PreToolUse blocks with stdout as the deny message | ✅ Verified |
| Exit code 0 allows the tool call to proceed | ✅ Verified |
| Hook script receives JSON payload on stdin | ✅ Verified |
| `settings.json` `hooks` key structure with event → matchers → command | ✅ Verified |
| PostToolUse hook must exit 0 (non-zero may surface as error) | ✅ Verified |
| `tool_input.command` contains the Bash command string | ⚠️ Inferred from documented tool schema |
| `tool_input.file_path` contains the target path for Edit/Write | ⚠️ Inferred from documented tool schema |
| `tool_input.new_string` contains the replacement content for Edit | ⚠️ Inferred from documented tool schema |
| `payload.session_id` is present and stable within a session | ⚠️ Inferred — may not always be populated |
| `UserPromptSubmit` payload contains `prompt` as the field name | ⚠️ Inferred — field name may differ |
| `Stop` event fires once at end of each response turn | ⚠️ Inferred — exact trigger semantics uncertain |
| `matcher: ".*"` in PostToolUse matches all tools | ⚠️ Inferred — regex support in matcher unconfirmed |
| Hook commands run from the project root directory | ✅ Verified (working directory is project root) |

If a hook fails silently (wrong payload field names), check the raw payload
by temporarily adding `import sys; print(json.dumps(payload), file=sys.stderr)`
before the main logic.

---

## Adjusting the governance layer

| Task | File to edit |
|------|-------------|
| Add a dangerous command pattern | `.claude/hooks/pre_tool_dangerous_bash.py` → `DANGEROUS_PATTERNS` |
| Add a secret regex | `.claude/hooks/pre_tool_secret_scan.py` → `SECRET_PATTERNS` |
| Add a false-positive exclusion | `.claude/hooks/pre_tool_secret_scan.py` → `SAFE_INDICATORS` |
| Expand the allowed edit scope | `.claude/hooks/pre_tool_file_scope.py` → `ALLOWED_PREFIXES` / `ALLOWED_FILES` |
| Allow a new Bash command without a prompt | `.claude/settings.json` → `permissions.allow` |
| Permanently deny a Bash command | `.claude/settings.json` → `permissions.deny` |
| Add a machine-local permission override | `.claude/settings.local.json` |
| Change the Python interpreter used by hooks | `.claude/settings.json` → each `"command"` value |
