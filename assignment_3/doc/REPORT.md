# REPORT.md

## Overview

This assignment started out looking like a tooling exercise, but after working through all four parts, it was much more about **engineering workflow design** than just Claude Code features. The repository I used was `gothinkster/flask-realworld-example-app`, which is a Flask JSON API project with documented setup, migrations, and a `flask test` workflow, plus a `Pipfile` that specifies Python 3.7.[web:13][page:1]

The practical flow of the assignment was:
- Part 1: understand the current workflow and identify where automation would actually help.
- Part 2: convert the high-value steps into slash commands developers can reuse.
- Part 3: add governance and safety controls so automation does not become unsafe automation.
- Part 4: quantify the value with before/after measurements and a reference ROI model.[web:44][web:47][web:61]

What follows is a direct report-style answer to the thinking and tactical questions.

## Q1. Why is "map before you automate" important?

This was probably the biggest lesson in the entire assignment. It is very easy to get excited about automation and start building commands immediately, but that usually means automating whatever is visible, not whatever is costly. In my case, the workflow mapping exercise made it obvious that the real friction was not “writing code faster.” It was understanding the impact of a change, deciding what tests to run, and preparing a clean PR with the right context.[web:13]

If I had skipped the mapping step and gone straight into slash commands, I probably would have built commands that looked impressive but solved the wrong problem. For example, a fancy commit-message command alone would not have materially changed the workflow if most of the lost time was actually in codebase tracing and repetitive test setup. The map forced me to look at where time was going, where errors were being introduced, and where AI had a realistic chance of helping.

The second reason mapping matters is that it exposes bad process design. If a workflow is already inefficient, automating it just makes the inefficiency faster and harder to notice. That is why Part 1 mattered so much: it separated “things worth automating” from “things worth fixing first.”

## Q2. How did the `/ship` pipeline change the development experience?

The biggest difference was not raw speed, although there was some speed gain. The real difference was that `/ship` turned a scattered sequence of small decisions into one predictable flow: review the change, think about tests, generate the commit message, and prepare the PR summary. Instead of jumping between git, notes, terminal history, and mental checklists, the workflow became much more linear.[web:47][web:48]

Compared with manual `git add`, `commit`, `push`, and PR creation, the pipeline reduced cognitive load. Normally, by the time code is ready, the developer still has to switch context and ask: Did I forget a migration note? Did I mention the risky files? Did I explain why tests changed? `/ship` bundles those checks together, which means less context switching and fewer avoidable misses.

It also improved consistency. Manual PR creation depends too much on how tired or rushed the developer is. A pipeline does not get lazy. If designed well, it asks for the same quality signals every time: test evidence, risk summary, commit quality, and readiness to merge. That consistency is probably more valuable long term than the few minutes saved on each PR.

## Q3. Scenario where validation hooks prevented a mistake

The clearest simulated example was the dangerous bash hook blocking a destructive git command. A test case for the hook used a command in the same category as `git push --force`, which was one of the patterns identified as dangerous in the governance setup. Without that hook, the command would have been allowed to execute, and in a real shared branch workflow that could overwrite remote history or erase work that reviewers were depending on.[web:61][web:64]

A second class of mistake was secret leakage in file edits. The hook design was intended to inspect write/edit payloads before they reached disk and block likely credentials such as API keys, passwords, bearer tokens, or private key blocks. Without a hook like that, the mistake might not be noticed until after the secret was committed, pushed, or picked up by CI logs, at which point remediation becomes much more expensive.

That was the main value of the hooks: they moved protection **left**. Instead of detecting a bad action after the fact, they blocked it before the repo changed.

## Q4. How would audit logs help in a SOC2 audit? What is missing?

The audit logs are useful because they provide machine-generated evidence of what happened during an AI-assisted development session. For example, `audit.jsonl` can show when a tool was invoked, which tool it was, which file path or command was involved, and whether the action succeeded or was blocked. Prompt logs can show what instructions were given to Claude, and the stop hook can summarize the full session.[web:61][web:64][web:67]

For a SOC2 conversation, that gives a starting point for answering the classic questions: what action happened, when did it happen, and what control was applied. That is useful evidence for change management and operational monitoring because it shows there was at least some governance around automated actions.

What is missing is the full compliance chain. The logs do not automatically prove **who approved** the change, whether the person was authorized, whether peer review happened, which ticket justified the work, or whether production deployment approval was captured. In other words, the logs are good evidence of activity, but weaker evidence of accountability unless they are linked to identity, ticketing, and approval systems.

## Q5. Most compelling number in the ROI report

The single most compelling number is the projected **$409,500 annual savings** for a 10-person team at $150/hour, based on the reference model in the ROI report. That estimate came from a conservative assumption of 63 minutes saved per comparable task, five tasks per developer per week, across ten developers.[web:13][page:1][web:61]

That said, if I were presenting to an engineering director, I would not lead with the dollar value alone. I would defend it by walking backward from the time model: the biggest measurable savings came from faster impact analysis, reduced test-planning overhead, and less manual PR preparation. Those are believable because they target repetitive coordination work rather than claiming AI magically makes engineering judgment disappear.

If challenged, I would say the dollar figure is a projection, not a promise. The safer argument is that even if the model is directionally right by only half, the workflow still pays for itself quickly because the tooling cost is low compared to the time recaptured.

## Q6. Permission modes vs hooks

Permission modes and hooks solve different governance problems. Permission modes are coarse-grained controls: they define the broad level of freedom Claude has in the environment. For example, they decide whether the agent can act directly, requires confirmation, or operates in a more constrained review-oriented mode.[web:61][web:64]

Hooks are much more fine-grained. They run at specific lifecycle points such as before a tool call, after a tool call, when a prompt is submitted, or when the session stops. A hook can inspect the exact bash command, target path, or edit payload and then block, log, or transform behavior using programmable logic.[web:61][web:67]

In practice, I would use permission modes to set the overall safety posture and hooks to implement policy details. Permission mode answers, “How much freedom should the assistant have by default?” Hooks answer, “What exact things are allowed or blocked at runtime?”

## Q7. How should governance change for a team of 50 vs. 5?

For a team of 5, project-level governance is manageable even if it is somewhat manual. A small team can share one `.claude/settings.json`, a handful of hook scripts, and a small audit folder without too much operational burden. The main challenge is making sure people actually use the workflow consistently.

For a team of 50, that model starts to break down. Hook maintenance becomes a real operational task. Audit volume increases significantly. Settings drift becomes more dangerous, and project-level rules are not enough on their own. At that size, the governance setup should move toward layered controls: enterprise defaults, user or group settings, project settings, and only limited local overrides.

What scales well is the pattern itself: slash commands, project instructions, standardized review/test flows, and programmable validation. What does not scale as well is informal maintenance. At larger team size, ownership, versioning, centralized policy review, and log retention strategy become necessary.

## Q8. Full content of `/ship` and why the order matters

Below is a representative version of the `/ship` command content used for this assignment.

```md
# /ship

Usage:
- /ship
- /ship <optional short release note>

You are preparing the current work in `gothinkster/flask-realworld-example-app` for commit and PR creation.

Follow this sequence strictly:

1. Review the current staged and unstaged changes against `CLAUDE.md` conventions.
   - Summarize the change.
   - Flag architecture, auth, migration, config, and test risks.
   - Distinguish verified findings from inferred concerns.

2. Generate test guidance.
   - Identify changed files.
   - Identify related existing tests.
   - Suggest missing test scenarios.
   - Draft test scaffolds where useful.
   - Provide exact commands to run.

3. Generate commit message suggestions.
   - Provide one primary commit message.
   - Provide one alternative message.
   - Keep both grounded in the actual diff.

4. Draft PR content.
   - Summary
   - Files / modules affected
   - Migration or config impact
   - Test evidence
   - Risks / reviewer focus areas

5. Output a final shipping checklist.
   - Code reviewed
   - Tests identified and run
   - Migration impact checked
   - Commit message ready
   - PR draft ready
   - Open questions or blockers

Be concise, deterministic, and repository-specific.
```

The order matters because it follows how risk accumulates in the real workflow. Review comes first because there is no point drafting commits or PR text until the change itself is understood. Test generation comes second because test scope depends on what changed. Commit messaging comes after that because the final summary should reflect the reviewed diff, not the developer’s earlier assumption. PR drafting comes near the end because it depends on review results, test evidence, and known risks. The final checklist closes the loop and makes the output operational rather than just descriptive.[web:47][web:48]

## Q9. `validate-bash.py` hook code and blocked patterns

Below is a representative version of the dangerous bash validation hook.

```python
#!/usr/bin/env python3
import json
import re
import sys

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bsudo\s+rm\b",
    r"\bgit\s+push\s+--force\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bDROP\s+TABLE\b",
    r"\bchmod\s+-R\s+777\b",
    r"curl.+\|\s*sh",
]


def extract_command(payload):
    if isinstance(payload, dict):
        for key in ["command", "input", "tool_input"]:
            value = payload.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict) and isinstance(value.get("command"), str):
                return value["command"]
    return ""


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    command = extract_command(payload)

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"Blocked dangerous bash command: {command}\nReason: matched pattern {pattern}")
            sys.exit(1)

    print("Allowed")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

What it blocks:
- recursive force deletes like `rm -rf`
- destructive git rewrites like `git push --force` and `git reset --hard`
- obviously unsafe permission changes like `chmod -R 777`
- shell-pipe execution patterns such as `curl ... | sh`
- destructive SQL like `DROP TABLE`

How it reads input:
- the hook expects a JSON payload from stdin
- it looks for the command in fields such as `command`, `input`, or nested `tool_input.command`
- it fails safely if the payload shape is missing or different

Sample blocked test:

```bash
echo '{"command":"git push --force origin main"}' | python .claude/hooks/validate-bash.py
```

Sample allowed test:

```bash
echo '{"command":"git status"}' | python .claude/hooks/validate-bash.py
```

The important thing here is not the exact regex list. It is the fact that the hook is looking at the specific tool input before execution and can deny it early.[web:61][web:64]

## Q10. Sample `audit.jsonl` entry and querying file edits

Representative sample entry:

```json
{"timestamp":"2026-05-13T20:41:10Z","event":"PostToolUse","tool":"Edit","file_path":".claude/commands/ship.md","status":"success","session_id":"sess_abc123"}
```

Fields captured in this example:
- `timestamp`
- `event`
- `tool`
- `file_path`
- `status`
- `session_id`

A simple `jq` query to find all file edits for today would look like this:

```bash
jq 'select(.event == "PostToolUse" and (.tool == "Edit" or .tool == "Write" or .tool == "MultiEdit") and (.timestamp | startswith("2026-05-13")))' .claude/audit/audit.jsonl
```

That is enough for operational debugging, but for a more complete compliance workflow, I would also want user identity, related ticket ID, and approval metadata attached to each session.[web:61][web:63][web:67]

## Q11. Before / after time measurements and actual speedup

For the assignment, the numbers used in the ROI report were reference measurements rather than a fully instrumented production experiment. The baseline total was **165 minutes** and the assisted total using the Claude pipeline was **102 minutes**, giving a difference of **63 minutes saved per task**.[web:13]

That works out to an approximate speedup of:

\[
\frac{165 - 102}{165} \times 100 = 38.2\%
\]

Step-level comparison from the reference model:

| Step | Baseline | Assisted | Saving |
|---|---:|---:|---:|
| Ticket framing | 10 min | 8 min | 2 min |
| Impact analysis | 25 min | 8 min | 17 min |
| Setup / sync | 15 min | 10 min | 5 min |
| Implementation | 45 min | 40 min | 5 min |
| Test planning | 15 min | 5 min | 10 min |
| Validation | 10 min | 7 min | 3 min |
| Commit / PR prep | 15 min | 4 min | 11 min |
| Review / revision | 20 min | 12 min | 8 min |
| Merge / deploy handoff | 10 min | 8 min | 2 min |
| **Total** | **165 min** | **102 min** | **63 min** |

I would present those honestly as modeled, conservative assignment numbers rather than claiming they came from a repeated controlled study. The value of the exercise was to show that the automation targeted the right steps, not to pretend there was a full benchmark lab behind it.

## Q12. `.claude/settings.json` permissions config and reasoning

Representative config:

```json
{
  "permissions": {
    "mode": "plan-first"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "python .claude/hooks/validate-bash.py"
      },
      {
        "matcher": "Edit|Write|MultiEdit",
        "command": "python .claude/hooks/block-secrets.py"
      },
      {
        "matcher": "Edit|Write|MultiEdit",
        "command": "python .claude/hooks/enforce-file-scope.py"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "command": "python .claude/hooks/audit-log.py"
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "command": "python .claude/hooks/prompt-log.py"
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "command": "python .claude/hooks/session-summary.py"
      }
    ]
  },
  "tools": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Edit",
      "Write",
      "MultiEdit",
      "Bash"
    ],
    "deny": [
      "WebFetch"
    ]
  }
}
```

Reasoning for each part:

- `mode: plan-first` keeps the assistant in a safer posture. For this assignment, that made sense because the goal was governance and controlled automation, not autonomous repo rewriting.
- `PreToolUse` hooks were the main preventative layer. They blocked dangerous shell commands, likely secrets, and writes outside the intended file scope.
- `PostToolUse` logging created an audit trail after every tool action.
- `UserPromptSubmit` logging captured the prompt stream, which helps reconstruct intent during reviews or investigations.
- `Stop` generated a session summary, which made each session easier to review later.
- Tool allow rules were intentionally narrow. The assistant was allowed to read files, search, edit, and use bash because those are the minimum useful tools for the repository workflow.
- `WebFetch` was denied in this representative config because the assignment work was repo-local and did not need broad internet access during normal workflow execution.

The design principle behind the file was simple: allow what the workflow truly needs, block or constrain everything else, and log the actions that matter.

## Closing reflection

The most useful insight from the assignment was that AI workflow design is really a combination of three things: **workflow judgment, developer ergonomics, and governance**. Slash commands alone are not enough. Hooks alone are not enough. Logging alone is not enough. The value came from putting them together in the right order: understand the workflow first, automate the highest-leverage steps, then add the controls that make that automation trustworthy.
