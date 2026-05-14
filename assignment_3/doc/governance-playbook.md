# Governance Playbook — 6-Week Rollout Plan

This playbook outlines a practical 6-week rollout plan for introducing an AI-enabled developer workflow built on Claude Code, project slash commands, validation hooks, audit logging, and permission controls. The rollout approach is intentionally phased: start with a small pilot, prove value with measurements, then expand with stronger governance and training. That structure matches common engineering rollout guidance, which emphasizes expectations, metrics, risk controls, validation steps, communication, and rollback planning.[web:79][web:82]

## Rollout goals

The goal is not to “add AI everywhere.” The goal is to make routine engineering work faster, more consistent, and safer by combining workflow automation with governance. In this project, the highest-value areas were code impact analysis, test planning, PR preparation, and structured release preparation through commands such as `/review`, `/test-gen`, `/commit`, `/ship`, and `/onboard`.[web:47][web:61]

The rollout also needs to preserve trust. That means hooks must prevent unsafe actions, audit logs must capture what happened, and permission settings must keep the assistant within an appropriate operating boundary. Governance is not a separate track from adoption; it is part of what makes adoption acceptable to the team.[web:61][web:64][web:78]

## Success criteria

By the end of Week 6, the team should have:
- A working `.claude/` setup in the target repository.
- Five tested slash commands in `.claude/commands/`.
- PreToolUse, PostToolUse, UserPromptSubmit, and Stop hooks enabled and validated.
- Project-level permission controls in `.claude/settings.json`.
- A lightweight audit trail for prompts and tool usage.
- Baseline and assisted workflow measurements for at least one representative engineering task.
- A team guide for onboarding and safe usage.[web:47][web:61][web:79]

## Week 1 — Align on workflow and risk

The first week is about clarity, not automation. Start by mapping the current development workflow end-to-end: ticket pickup, codebase understanding, implementation, testing, review, merge, and deploy. Annotate each step with time spent, tools used, and the main pain points. This follows the principle that automation should begin with process understanding rather than tool enthusiasm.[web:79][web:80]

At the same time, define the governance boundary. Decide which parts of the repo the assistant should be allowed to edit, which commands are too risky to permit by default, what should be logged, and what level of autonomy is acceptable for the pilot. End the week with three outputs: workflow map, top 3 automation targets, and a one-page risk register covering shell commands, secrets, file scope, and audit requirements.[web:61][web:64]

**Week 1 deliverables**
- Current-state workflow map.
- Automation target shortlist.
- Risk and governance checklist.
- Named owner for rollout.

## Week 2 — Build the command layer

Week 2 is where the developer-facing workflow starts to take shape. Build the project-level `CLAUDE.md` and the five required slash commands under `.claude/commands/`: `/review`, `/test-gen`, `/commit`, `/ship`, and `/onboard`. Each command should be tied back to real workflow pain points rather than generic productivity language.[web:44][web:47]

Keep the first version narrow. The commands should be deterministic, repo-specific, and designed to reduce repetitive work, especially around review quality, test guidance, commit preparation, and onboarding. By the end of this week, the commands should run successfully in the target repository, even if they still need refinement.[web:47][web:48]

**Week 2 deliverables**
- Root `CLAUDE.md`.
- Five command files under `.claude/commands/`.
- Initial end-to-end manual validation notes for each command.

## Week 3 — Add safety hooks and permission controls

Once the command layer exists, Week 3 focuses on making it safe enough to trust. Add PreToolUse hooks to block dangerous bash commands, detect likely secrets in file edits, and enforce write scope restrictions. Add PostToolUse, UserPromptSubmit, and Stop hooks to create an audit trail and a session summary. Wire everything through `.claude/settings.json` with a conservative project-level permission mode.[web:61][web:64][web:67]

This is also the week to decide what should be denied by default. For a repo-governance assignment, that usually means allowing repo-local reading, editing, and controlled bash usage while blocking risky shell patterns and restricting writes to approved directories. The important thing is that the controls are understandable, testable, and documented in a short governance note.[web:64][web:78]

**Week 3 deliverables**
- `.claude/hooks/` scripts.
- `.claude/settings.json` with hook registration and permission rules.
- `.claude/GOVERNANCE.md` explaining controls and rationale.
- Manual blocked/allowed test cases for each hook.

## Week 4 — Pilot with a small developer group

Do not roll this out to everyone immediately. Week 4 should be a limited pilot with 2–5 developers or one small feature squad. That mirrors proven engineering-tool rollouts where early adopters are trained first, usage patterns are observed, and rough edges are fixed before broad launch.[web:82]

Have pilot users run a real workflow in the target repo using the new command suite. Ask them to perform at least one representative task manually and one comparable task using the AI workflow. Capture time, steps, friction, blocked actions, and whether outputs such as PR descriptions and test suggestions were actually useful. Keep a dedicated feedback channel during the pilot so issues are resolved quickly.[web:82][web:79]

**Week 4 deliverables**
- Pilot cohort.
- Feedback channel.
- Before/after measurement sheet.
- Top 5 issues and fixes list.

## Week 5 — Refine, train, and standardize

By Week 5, there should be enough pilot feedback to improve the workflow. Tighten prompts, simplify command outputs, reduce false positives in hooks, and clarify the rules in `CLAUDE.md` and governance docs. At this stage, the quality of the rollout depends heavily on developer education. Structured rollout experience shows that training, support channels, and examples have a big effect on adoption and satisfaction.[web:82]

Run a short enablement session for the broader team. Show the manual workflow versus the `/ship` workflow side by side. Demonstrate one blocked dangerous command, one generated PR summary, and one example of `/test-gen` producing a useful scaffold. Provide a quick-start page and one “golden path” example that new users can copy.

**Week 5 deliverables**
- Refined commands and hooks.
- Quick-start guide.
- Team training session or recorded walkthrough.
- Standard task checklist using `/review` → `/test-gen` → `/commit` → `/ship`.

## Week 6 — Expand rollout and lock in measurement

Week 6 is for broadening adoption and making the system sustainable. Move from pilot to team-wide usage, but keep the controls visible: audit logging enabled, hooks monitored, and settings version-controlled. Review the before/after measurements collected during the pilot and publish a short ROI summary for engineering leadership. A good rollout plan should always include both validation and rollback logic, so document what would trigger a pause or rollback as well.[web:79]

This is also the right time to define steady-state ownership. Decide who maintains the commands, who reviews hook changes, where audit logs are retained, and how new repos will adopt the same pattern. Without ownership, even a good governance setup will drift over time.

**Week 6 deliverables**
- Team-wide rollout announcement.
- ROI summary.
- Command and hook ownership model.
- Rollback / pause criteria.
- Backlog of next improvements.

## Team operating model

During the rollout, assign explicit owners:

| Role | Responsibility |
|---|---|
| Engineering manager or tech lead | Approves rollout scope, success metrics, and operating policy |
| Repo owner / senior engineer | Owns `CLAUDE.md`, command design, and workflow fit |
| Security or platform reviewer | Reviews dangerous-command blocks, secret detection, and audit policy |
| Pilot developers | Provide usability feedback and real workflow measurements |
| DevEx / tooling owner | Maintains commands, hooks, and settings over time |

This ownership model is important because AI workflow tooling sits across developer experience, engineering process, and governance, so it should not live as an orphaned experiment.[web:79][web:81]

## Metrics to track weekly

The rollout should be measured, not just announced. Track a small set of metrics every week:

- Number of developers actively using slash commands.
- Number of `/ship` runs completed.
- Average time to complete a comparable task before and after rollout.
- Number of blocked dangerous commands.
- Number of blocked secret-like edits.
- Review turnaround time.
- CI reruns caused by preventable issues.
- Qualitative feedback from developers on cognitive load and consistency.[web:79][web:82]

Keep the dashboard small. The point is to prove operational value, not build a giant reporting system during the first six weeks.

## Communication plan

Good rollout plans are also communication plans. Use a simple cadence:

- **Start of Week 1:** announce scope, goals, and repo selected for rollout.
- **End of Week 2:** share the first command suite and request feedback.
- **End of Week 4:** publish pilot findings and the top improvements made.
- **End of Week 6:** present ROI, quality gains, and next-step recommendation.[web:79][web:82]

The communication tone should stay practical. Developers adopt tools when they see that the tools remove annoying work and do not create hidden risk.

## Risks and mitigations

| Risk | Likely impact | Mitigation |
|---|---|---|
| Commands are too generic | Low adoption | Tie prompts to repo structure and real workflow pain points |
| Hooks block too aggressively | Developer frustration | Start conservative, test patterns, refine false positives |
| Logs exist but are not reviewed | Weak governance value | Assign clear log owner and weekly review rhythm |
| Team sees AI as extra process | Resistance | Demonstrate real time savings and fewer manual steps |
| No ownership after pilot | Tooling drift | Assign long-term owner by Week 6 |

This is where the rollout can fail quietly. The biggest risk is not technical failure; it is governance and automation becoming shelfware because no one owns the day-two experience.

## Rollback plan

If the rollout causes more friction than benefit, scale back in this order:
1. Keep `CLAUDE.md` and slash commands, but disable the most aggressive hooks.
2. Restrict governance to logging plus dangerous-command blocking only.
3. Move from default usage to pilot-only usage while prompts and hooks are refined.
4. Re-run one representative workflow and compare friction before relaunch.[web:79]

A rollback plan matters because safe adoption depends on credibility. If the controls are noisy or brittle, the team needs a graceful way to reduce scope without throwing away the whole workflow.

## End-state after 6 weeks

If the rollout goes well, the team should end Week 6 with a reusable pattern:
- workflow first,
- commands second,
- governance third,
- measurement throughout.

That is the real playbook. The slash commands make the workflow easier to use, the hooks make it safer, the logs make it observable, and the measurements make it defensible to leadership. That is what turns a classroom-style assignment into something a real engineering team could actually adopt.
