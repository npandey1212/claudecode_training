Orchestrate a full release-prep pass for the current work: run a compressed review, surface test gaps, suggest a commit message, draft a ready-to-paste PR description, and produce a tiered shipping checklist. Collect all evidence once; synthesize findings across every section so each section builds on the last.

## Usage

```
/ship              # full pipeline — all five sections
/ship pr           # skip sections 1–3; output PR draft + checklist only
/ship checklist    # output the final checklist only, based on current state
```

Argument passed as: $ARGUMENTS

---

## Instructions

### Step 1 — Collect evidence (run all before writing any output)

Run these commands in order and hold all results in context:

1. `git diff HEAD` — all local changes, staged and unstaged combined
2. `git diff --cached` — staged-only diff (used for commit message in section 3)
3. `git diff --cached --stat` — per-file insertion/deletion counts
4. `git diff --cached --name-only` — file list for layer classification
5. `git status` — surface unstaged and untracked files
6. `git log --oneline -5` — recent commit style reference

Then read:

7. `.claude/CLAUDE.md` — conventions and architecture
8. `doc/pr-check.md` — PR template and blocking-item list

Do not produce any output until all eight steps are complete.

**If both `git diff HEAD` and `git diff --cached` are empty**, output only:

```
Nothing to ship. No staged or unstaged changes detected.
Make your changes, then run /ship again.
```

And stop.

**If $ARGUMENTS is `pr`:** skip directly to Section 4. Still run all eight collection steps first.
**If $ARGUMENTS is `checklist`:** skip directly to Section 5. Still run all eight collection steps first.

---

### Step 2 — Classify staged files by layer

Assign every file from `git diff --cached --name-only` to one tag. Carry these tags into all five sections.

| Tag | Matches |
|-----|---------|
| `[MODEL]` | `conduit/*/models.py` |
| `[VIEW]` | `conduit/*/views.py` |
| `[SERIAL]` | `conduit/*/serializers.py` |
| `[CONFIG]` | `conduit/settings.py`, `autoapp.py` |
| `[FACTORY]` | `conduit/app.py`, `conduit/extensions.py` |
| `[MIGRATION]` | `migrations/versions/*.py` |
| `[TEST]` | `tests/` |
| `[DEPS]` | `requirements/*.txt`, `Pipfile`, `Pipfile.lock` |
| `[CI]` | `.circleci/`, `.travis.yml` |
| `[INFRA]` | `Procfile`, `Vagrantfile` |
| `[DOCS]` | `*.md`, `*.rst` |

Derive four boolean flags from the layer set. Use these flags in sections 4 and 5 to suppress or include conditional items.

| Flag | True when |
|------|-----------|
| `MIGRATION_PRESENT` | one or more `[MIGRATION]` files are staged |
| `MODEL_CHANGED` | one or more `[MODEL]` files are staged |
| `AUTH_TOUCHED` | staged diff contains `@jwt_required`, `@jwt_optional`, `jwt_identity`, or `CONDUIT_SECRET` |
| `TESTS_STAGED` | one or more `[TEST]` files are staged |

Also note: `MIGRATION_MISMATCH = MODEL_CHANGED XOR MIGRATION_PRESENT` (one true but not the other — a blocking concern).

---

## Output format

Produce exactly these five sections in order. Keep each section tight; redirect to the dedicated command for full detail where noted.

---

### Section 1 — Review summary

**Purpose:** surface the top violations and concerns from the staged diff. Not a full /review — maximum 10 bullets total.

Apply the `/review` checklist silently (from `.claude/commands/review.md`) and report only findings at severity ❌ (violation) or ⚠️ (concern worth flagging). Skip ✅ (clean) findings unless every check passed, in which case write one line: `All checked items passed.`

Format:

```
## 1. Review summary
Layers touched: [LIST TAGS]   Blueprints: <list>   Auth touched: yes/no   Migration: yes/no

Findings (top issues only — run /review for full detail):
- ❌/⚠️  [TAG] <file or function> — <one-line description of the issue>
- ...

Blocking issues: <N>   Concerns: <N>
```

If `MIGRATION_MISMATCH` is true, always include as the first finding:
`❌ [MODEL]/[MIGRATION] mismatch — model changed without migration, or migration staged without model change`

---

### Section 2 — Test summary

**Purpose:** surface which endpoints and model methods lack test coverage. Not a full /test-gen — maximum 8 bullets, no scaffolds.

For each `[VIEW]` or `[MODEL]` file in the staged diff, check whether the corresponding test file covers: happy path, auth-missing, and not-found. Report only gaps.

Format:

```
## 2. Test summary
Test files staged: yes/no   Known failing baseline: tests/test_profile.py (commit 4464881, expected)

Coverage gaps (run /test-gen for scaffolds):
- ❌ <endpoint or model method> — missing: <happy-path | auth-missing | not-found | ownership>
- ...

Factory gap: <"ArticleFactory missing — needed for N new tests" | "None">
```

If `TESTS_STAGED` is false and `[VIEW]` or `[MODEL]` files are staged, prepend:
`⚠️  No test files staged alongside source changes.`

If no gaps found: `Coverage appears adequate for the staged changes. Verify by running: flask test`

---

### Section 3 — Commit suggestion

**Purpose:** produce two ready-to-use commit messages from the staged diff (`git diff --cached`). Apply the same rules as `/commit` (from `.claude/commands/commit.md`).

If `git diff --cached` is empty (nothing staged, but unstaged changes exist), output:
`⚠️  Nothing staged. Stage your files before committing. Commit suggestion is based on the full HEAD diff as a preview.`
Then proceed using `git diff HEAD` as a fallback.

Format:

```
## 3. Commit suggestion

Primary (conventional commit):
  <type>(<scope>): <subject — ≤72 chars>

Alternate (plain-language):
  <subject — ≤72 chars>

Body (include only if MIGRATION_PRESENT, AUTH_TOUCHED, or multi-layer commit):
  <bullet points — wrap at 72 chars>

Git command:
  git commit -m "<primary subject>"
```

Rules (abridged from `/commit`):
- Type: `feat` / `fix` / `test` / `refactor` / `chore` / `docs` / `style` / `migration`
- Scope: `user` / `profile` / `articles` / `auth` / `db` / `config` / `deps` / `ci` / `serializer`
- Subject: imperative, lowercase after colon, no period, ≤72 chars total
- If `MIGRATION_PRESENT`: subject must name the schema change, not just "update migration"
- Alternate must differ in verb and emphasis from primary, not just rephrase it

---

### Section 4 — PR draft

**Purpose:** produce a complete, pasteable GitHub PR description. Fill every field from what was learned in sections 1–3. Do not leave template placeholders — if a field cannot be inferred, write `_unknown — add before opening PR_` so the gap is visible rather than hidden.

The PR title is the same as the commit primary subject from section 3.

Build the body by applying these rules to each field:

**What changed:**
One sentence naming: (a) which blueprint(s) touched, (b) what was added/changed/removed, (c) the specific endpoint(s) or model method(s) if `[VIEW]` or `[MODEL]` is staged.

**Why:**
Scan `git log --oneline -5` for a ticket or issue reference (e.g. `#123`, `closes`, `fixes`). If found, include it. If not found, write: `_unknown — link ticket or add context before opening PR_`

**Migration included?**
If `MIGRATION_PRESENT` is true: Yes — describe what the migration does (read the migration file) and state whether `downgrade()` is non-trivial.
If `MIGRATION_MISMATCH` is true: flag this as a blocking gap inline.
Otherwise: No.

**Auth layer touched?**
If `AUTH_TOUCHED` is true: Yes — list each endpoint and which decorator was added/changed/removed.
Otherwise: No.

**Test coverage:**
If `TESTS_STAGED` is true: name the test file(s) staged and the scenarios they cover (from section 2).
If `TESTS_STAGED` is false and gaps exist from section 2: `No test files staged — see gaps in section 2 above.`
If no gaps: `No new endpoints; existing coverage unchanged.`

**Checklist:**
Pre-fill every item from `doc/pr-check.md` Author checklist using findings from sections 1–2:
- Mark `[x]` only for items that are positively verified from the diff or test files
- Mark `[ ]` for items that cannot be verified from the diff, or where a gap was found
- Never mark `[x]` for a `[BLOCK]` item unless it was explicitly confirmed clean

Output the entire section 4 inside a fenced markdown block so it can be copy-pasted directly:

````
## 4. PR draft

```markdown
## What changed
<filled>

## Why
<filled or _unknown_>

## Migration included?
<filled>

## Auth layer touched?
<filled>

## Test coverage
<filled>

## Checklist

### Code quality
- [x/] [BLOCK] `flask lint` passes ...
- [x/] [BLOCK] `flask lint --fix-imports` ...
- [x/] [BLOCK] `flask test` passes ...
- [ ] No `db.session` calls in views ...
- [ ] No raw `db.Column(db.ForeignKey(...))` ...
- [ ] No schema instantiation inside view functions ...

### Serializers / API contract
- [ ] New schemas set `class Meta: strict = True`
- [ ] Envelope pattern maintained
- [ ] `load_only` fields not in responses
- [ ] JWT header prefix is `Token` not `Bearer`

### Database
- [x/] [BLOCK] Migration present if model changed ...
- [x/] [BLOCK] No SQLite-incompatible DDL ...
- [ ] `downgrade()` is non-trivial

### Tests
- [x/] [BLOCK] New endpoints have happy-path, auth-missing, not-found tests ...
- [ ] New models have factory if used in >1 test
- [ ] Tests use `testapp`, not `app.test_client()`
- [ ] Tests assert on JSON envelope structure

### Auth & security
- [ ] `@jwt_required` on writes, `@jwt_optional` on auth-dependent reads
- [ ] Password only via `user.set_password()`
- [ ] `CONDUIT_SECRET` not hardcoded
```
````

---

### Section 5 — Final checklist

**Purpose:** tiered, conditional, actionable. BLOCK items must be resolved before merge. SHOULD items are strong recommendations. POST-MERGE items are required after merging — not optional.

Generate this checklist dynamically: include a conditional item only if the relevant flag is true or the relevant gap was found in sections 1–2. Do not pad with items that cannot possibly apply.

Format:

```
## 5. Final checklist

### BLOCK — resolve before opening PR
- [ ] `flask lint` exits 0                          [always]
- [ ] `flask test` exits 0 (1 known baseline failure in test_profile.py is acceptable)  [always]
- [ ] No [MODEL] change without [MIGRATION]         [if MIGRATION_MISMATCH]
- [ ] Migration `downgrade()` is not empty or pass  [if MIGRATION_PRESENT]
- [ ] No SQLite-incompatible DDL in migration       [if MIGRATION_PRESENT]
- [ ] New endpoints have happy-path + auth-missing + not-found tests  [if VIEW_GAP from section 2]
- [ ] `CONDUIT_SECRET` not hardcoded                [if AUTH_TOUCHED]

### SHOULD — complete before requesting review
- [ ] `flask lint --fix-imports` run if imports changed  [if [VIEW]/[SERIAL]/[MODEL] staged]
- [ ] PR description "Why" field has a ticket or context  [always]
- [ ] `lazy='dynamic'` relationship exercised in a test  [if new relationship added]
- [ ] ArticleFactory added to tests/factories.py    [if factory gap found in section 2]
- [ ] Marshmallow 3 API used throughout (no Schema(strict=True) at instantiation)  [if [SERIAL] staged]
- [ ] SQLAlchemy pinned versions unchanged (1.1.9 / Flask-SQLAlchemy 2.2)  [if [DEPS] staged]

### POST-MERGE — required after merge, not optional
- [ ] Monitor `heroku logs --tail` for 2 minutes after deploy  [always]
- [ ] `heroku run flask db upgrade` within 5 minutes of deploy  [if MIGRATION_PRESENT]
- [ ] Spot-check: GET /api/tags returns 200           [always]
- [ ] Spot-check: POST /api/users/login returns 200   [always]

---

STATUS: <one of the following>
  READY TO SHIP    — zero BLOCK items outstanding, no ❌ findings in sections 1–2
  BLOCKED (N)      — N BLOCK items require resolution; see list above
  REVIEW FIRST     — no hard blockers, but ⚠️ concerns in sections 1–2 warrant a closer look
```

Determine STATUS by counting unresolved BLOCK items (items where the evidence from sections 1–2 did not confirm the item clean):
- 0 unresolved BLOCK items and 0 ❌ findings → READY TO SHIP
- 1 or more unresolved BLOCK items → BLOCKED (N) where N is the count
- 0 unresolved BLOCK items but 1 or more ⚠️ concerns → REVIEW FIRST
