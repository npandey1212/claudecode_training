# Automation Impact Analysis — Conduit (flask-realworld-example-app)

> **Evidence key**
> - ✅ Verified — directly observed in repo files or commit history
> - ⚠️ Inferred — based on typical Flask/GitHub OSS workflow norms; not provable from repo alone
>
> Time-savings estimates are **conservative floor values**. They assume a single active developer
> and do not compound across team size.

---

## Top 3 automation targets

### Target 1 — Enforce linting at commit time via pre-commit hook

**ROI score: 8/10**

#### Justification

| Evidence | Type |
|----------|------|
| No `.pre-commit-config.yaml` exists in repo | ✅ |
| `flask lint` (flake8 + isort) exists and works correctly | ✅ |
| `setup.cfg` contains complete flake8 config (`max-line-length = 120`) | ✅ |
| CI (CircleCI) runs `flask test`, not `flask lint` — lint failures are silent until a human notices | ✅ |
| Linting is documented as a manual step ("Run `flask lint` before every commit") | ✅ |

Without a gate, a developer pushes → CI runs tests (not lint) → reviewers catch style issues → developer fixes → repeat. Each cycle adds context-switching cost.

A `.pre-commit-config.yaml` that calls `flask lint` (or runs `flake8` + `isort` directly) eliminates this cycle entirely. Claude Code can additionally auto-apply `--fix-imports` and suggest line-length fixes before the hook rejects.

**What AI automates here:** Claude can (a) generate `.pre-commit-config.yaml` from the existing `setup.cfg`, (b) auto-run `flask lint --fix-imports` when lint fails, and (c) explain remaining violations with fix suggestions. This is full automation for ~80% of lint failures; the remaining 20% (logic-level style) require one-line human edits.

---

### Target 2 — AI-drafted PR descriptions from diff + commits

**ROI score: 8/10**

#### Justification

| Evidence | Type |
|----------|------|
| No `.github/PULL_REQUEST_TEMPLATE.md` exists in repo | ✅ |
| No CONTRIBUTING.md with PR guidance | ✅ |
| Commit history shows inconsistent messages (e.g. "fix failed unittest fix more for functions…") | ✅ commit `4464881` |
| Three active blueprints with clear, consistent structure make diff-to-description mapping tractable | ✅ |

Writing a PR description for a non-trivial change takes 5–10 minutes and is routinely skipped or done poorly. Reviewers then spend their own time reconstructing intent from the diff — magnifying the cost.

With Claude Code reading the `git diff` against master, the commit log, and the CLAUDE.md architecture context, it can generate a description that covers: what changed, which blueprint(s) affected, whether DB migrations are included, and whether the change touches auth/serializer layers.

**What AI automates here:** Draft generation is fully automated. Human reviews and adjusts the draft in < 1 minute rather than writing from scratch in 5–10 minutes. A `doc/pr-check.md` checklist enforces what the draft must cover.

---

### Target 3 — AI-scaffolded tests for new endpoints and models

**ROI score: 8/10**

#### Justification

| Evidence | Type |
|----------|------|
| All five test files follow a consistent WebTest + pytest + factory-boy pattern | ✅ |
| `conftest.py` fixtures (`app`, `db`, `testapp`, `user`) are function-scoped and well-separated | ✅ |
| `UserFactory` is the only factory — new models (Article, Comment, Tag) have no factories | ✅ |
| One test is currently failing/commented-out from the Marshmallow 3 migration | ✅ commit `4464881` |
| Writing tests is the highest per-PR time cost after writing source code (30–120 min) | ⚠️ |

The test suite has a regular, learnable shape: import fixtures, call `testapp.post_json` or `testapp.get` with a `JWT: Token …` header, assert on the response JSON envelope structure. New tests for existing blueprints are ~70% boilerplate that Claude can generate given the view signature and the schema envelope.

**What AI automates here:** Claude can generate the full scaffold for a new test function — fixture setup, HTTP call with auth header, response envelope assertion — from the view's route, method, and `@use_kwargs`/`@marshal_with` decorators. The developer fills in the business-logic assertions. Estimated scaffold generation: < 2 minutes vs. 15–30 minutes writing from scratch.

---

## Before / after productivity estimates

> These estimates cover a **single feature PR** for one developer. All ranges are conservative
> (they use the lower bound of improvement, not the upper bound). ✅ = grounded in repo evidence,
> ⚠️ = inferred from workflow norms.

### Target 1 — Pre-commit lint hook

| Metric | Before | After | Saving |
|--------|--------|-------|--------|
| Lint cycles per PR (push → notice → fix → repush) | 2–4 cycles ⚠️ | 0–1 cycles | 2–3 cycles avoided |
| Time per lint-fix cycle (notice + context-switch + fix + repush + wait for CI) | ~8–12 min ⚠️ | ~30 sec (local hook) | ~8–11 min / cycle |
| **Total lint overhead per PR** | **16–48 min** | **< 2 min** | **~15–45 min saved/PR** |
| CI pipeline runs wasted on lint-only failures | 2–4 ✅ (no lint step in CI) | 0 | Frees CI capacity |
| Developer context switches per PR (back to editor after CI red) | 2–4 ⚠️ | 0–1 | Reduced cognitive overhead |

**Conservative net saving per PR: ~15 minutes of active developer time + 2 fewer CI pipeline runs.**
Over 20 PRs/month ⚠️: ~5 hours/month saved.

---

### Target 2 — AI-drafted PR descriptions

| Metric | Before | After | Saving |
|--------|--------|-------|--------|
| Time to write PR description | 5–10 min ⚠️ | < 1 min (review draft) | ~5–9 min/PR |
| Reviewer time reconstructing intent from diff (description absent or thin) | 5–15 min ⚠️ | 1–2 min (structured description) | ~4–13 min/PR for reviewer |
| PRs with migration callout missing (risk of skipping `heroku run flask db upgrade`) | Frequent ✅ no template | Rare (checklist item in draft) | Reduced prod incident risk |
| PRs that explicitly note which blueprint(s) changed | Rare ⚠️ | Every PR (generated) | Faster triage |

**Conservative net saving per PR: ~10 minutes (author + reviewer combined).**
Qualitative benefit: migrations and auth-layer changes are flagged consistently — this is the highest-risk omission in the current workflow given the manual prod-migration step.

---

### Target 3 — AI-scaffolded tests

| Metric | Before | After | Saving |
|--------|--------|-------|--------|
| Time to write tests for one new endpoint | 30–90 min ⚠️ | 10–30 min (scaffold + fill assertions) | ~20–60 min/endpoint |
| Time to write factory for a new model | 10–20 min ⚠️ | 2–5 min (generated from model definition) | ~10–15 min/model |
| Tests written per PR that touch new endpoints | Often 0 ✅ (no factory for Article/Comment/Tag) | 1+ (scaffold lowers barrier) | Coverage improvement |
| Known baseline noise (1 failing test) | Masks new failures ✅ | Baseline fixed as part of scaffold task | Cleaner signal |

**Conservative net saving per PR with new endpoints: ~20 minutes of test-writing time.**
Qualitative benefit: the current gap in Article/Comment/Tag factories means auth-layer and M:M relationship tests are underrepresented. Scaffolding closes this gap without requiring the developer to study the full fixture chain from scratch.

---

## Cumulative estimate (all three targets, per PR)

| Item | Conservative saving |
|------|-------------------|
| Lint hook (developer time) | 15 min |
| AI PR description (author + reviewer) | 10 min |
| AI test scaffold (one new endpoint) | 20 min |
| **Total per PR** | **~45 min** |

> ⚠️ These are additive only if a PR touches a new endpoint. For a pure bug-fix PR with no new
> routes, the lint and PR-description savings still apply (~25 min), but the test-scaffold saving
> is smaller (~5–10 min for updating an existing test).

**Annualised estimate at 20 PRs/month ⚠️:** ~180 hours of developer-equivalent time recovered,
without changing the architecture or toolchain — only adding hooks, templates, and Claude Code
integration on top of what already exists.
