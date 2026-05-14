Review the currently staged changes in this repository against the conventions in `.claude/CLAUDE.md` and the architecture of the Conduit Flask app.

## Usage

```
/review                  # full review of all staged changes
/review auth             # focus pass on auth-sensitive changes only
/review migration        # focus pass on DB migration changes only
```

Argument passed as: $ARGUMENTS

---

## Instructions

### Step 1 — Collect evidence (run all of these before writing any output)

Run these commands in order:

1. `git diff --cached --stat` — file-level summary of what is staged
2. `git diff --cached` — full staged diff
3. `git diff --cached --name-only` — plain file list (used to classify affected layers)
4. `git status` — catch untracked migration files or uncommitted schema changes
5. Read `.claude/CLAUDE.md` — authoritative conventions for this repo

Do not produce any output until all five steps are complete.

---

### Step 2 — Classify staged files by layer

Before writing findings, mentally sort each changed file into one or more of these layers.
Use the layer tags in your findings.

| Tag | Matches |
|-----|---------|
| `[MODEL]` | `conduit/*/models.py` |
| `[VIEW]` | `conduit/*/views.py` |
| `[SERIAL]` | `conduit/*/serializers.py` |
| `[FACTORY]` | `conduit/app.py`, `conduit/extensions.py` |
| `[CONFIG]` | `conduit/settings.py`, `autoapp.py` |
| `[MIGRATION]` | `migrations/versions/*.py` |
| `[TEST]` | `tests/` |
| `[DEPS]` | `requirements/*.txt`, `Pipfile`, `Pipfile.lock` |
| `[CI]` | `.circleci/`, `.travis.yml` |
| `[INFRA]` | `Procfile`, `Vagrantfile` |

---

### Step 3 — If $ARGUMENTS is "auth"

Narrow the review to only:
- Endpoints missing `@jwt_required` or `@jwt_optional`
- Any read of `current_user` without a `@jwt_required` / `@jwt_optional` guard
- Direct assignment to `user.password` (must use `user.set_password()`)
- JWT header prefix — must be `Token`, not `Bearer`, in tests or examples
- `CONDUIT_SECRET` appearing in any staged file as a literal string

Skip all other sections. Still produce the full 7-section output, but mark non-applicable sections as `N/A — auth focus`.

### Step 3 — If $ARGUMENTS is "migration"

Narrow the review to only:
- Whether a `migrations/versions/` file is staged
- Whether any `[MODEL]` change is staged without a corresponding migration file
- Whether the migration's `downgrade()` function is non-empty
- Whether any DDL in the migration is SQLite-incompatible (`ALTER COLUMN`, `ADD CONSTRAINT`, etc.)
- Whether the prod-migration step is called out in the PR description or commit message

Skip all other sections. Mark non-applicable sections as `N/A — migration focus`.

---

### Step 4 — Apply this checklist silently (do not print the checklist; use it to generate findings)

**Flask architecture**
- [ ] Each changed file is in the correct location: `models.py`, `views.py`, `serializers.py` inside its blueprint package
- [ ] Any new blueprint is registered in `conduit/app.py` `register_blueprints()` and `register_shellcontext()`
- [ ] No query logic has been added inside a view beyond retrieving the target object — business logic belongs on the model
- [ ] `db.session` is not called directly in views; only `CRUDMixin` methods (`.save()`, `.update()`, `.delete()`) or a narrow `except IntegrityError` rollback

**Models**
- [ ] New tables use `SurrogatePK, Model` for an integer PK
- [ ] FK columns use `reference_col('tablename')` from `conduit/database.py`, not raw `db.Column(db.ForeignKey(...))`
- [ ] Any new `lazy='dynamic'` relationship is exercised in a test (this pattern broke in PR #27)
- [ ] Password is never written to `user.password` directly — only via `user.set_password(plain)`

**Views / Auth**
- [ ] Write endpoints (`POST`, `PUT`, `DELETE`) carry `@jwt_required`
- [ ] Read endpoints whose output changes based on the caller carry `@jwt_optional`
- [ ] Every view that accepts a body is decorated `@use_kwargs(schema)` and returns via `@marshal_with(schema)` — no manual `schema.dump()` / `schema.load()` in the view body
- [ ] `current_user` access is only present in views decorated with `@jwt_required` or `@jwt_optional`

**Serializers**
- [ ] New or modified schemas declare `class Meta: strict = True`
- [ ] Envelope pattern is preserved: `@pre_load` unwraps, `@post_dump` re-wraps
- [ ] Write-only fields are marked `load_only=True`; computed / read-only fields are marked `dump_only=True`
- [ ] No schema is instantiated inside a view function — schemas are module-level singletons

**Tests**
- [ ] New endpoints have at minimum: happy-path test, auth-missing test, not-found test
- [ ] Tests use `testapp` (WebTest), not `app.test_client()`
- [ ] Model data is created via `UserFactory` or `user.get()`, not inline construction
- [ ] Auth headers in tests use `Authorization: Token <jwt>`, not `Bearer`
- [ ] No test relies on state from another test (fixtures are function-scoped)

**Migrations**
- [ ] If any `[MODEL]` file is staged, a corresponding `migrations/versions/` file is also staged
- [ ] `downgrade()` is not empty or `pass`
- [ ] Migration does not use DDL that silently no-ops on SQLite

**Config / Secrets**
- [ ] `CONDUIT_SECRET` is not hardcoded anywhere in staged changes
- [ ] No new env vars are introduced without a corresponding note in `.claude/CLAUDE.md`

**Dependencies**
- [ ] `SQLAlchemy` remains pinned to `1.1.9` and `Flask-SQLAlchemy` to `2.2` unless a tested upgrade PR is intended
- [ ] `marshmallow` is used as version 3 API — no `Schema(strict=True)` at instantiation, no implicit `@post_load` object return

---

### Step 5 — Produce the report

Use exactly this structure. Keep each section tight. Use bullet points, not prose paragraphs.
Prefix every finding with one of:
- `✅` — directly observed in the diff
- `⚠️` — inferred (cannot be verified from the diff alone; state the assumption)
- `❌` — clear violation of a convention in `.claude/CLAUDE.md`

---

## Output format

```
## Review — <short description of what is staged, e.g. "adds Comment delete endpoint">

### 1. Summary
- Files changed: <N> across layers: [LIST LAYER TAGS]
- Blueprints touched: <list>
- Auth layer touched: yes/no
- Migration included: yes/no
- Tests included: yes/no
- Overall risk: low / medium / high  (one word, followed by one-line reason)

---

### 2. Verified findings  (observed directly in the diff)
- ✅ ...
- ✅ ...

---

### 3. Inferred concerns  (cannot be verified from the diff alone)
- ⚠️ ...  [state the assumption and what to check]
- ⚠️ ...

If none: "None."

---

### 4. Convention violations  (clear breaches of .claude/CLAUDE.md rules)
- ❌ [LAYER] <file>:<line-or-function> — <rule broken> — <one-line fix>
- ❌ ...

If none: "None."

---

### 5. Missing tests
- ❌ <endpoint or behaviour> — no test for <happy-path / auth-missing / not-found>
- ...

If all cases are covered: "Coverage looks adequate for the staged changes."

---

### 6. Migration / config risks
- ✅/⚠️/❌ ...

Mandatory items to check:
- Is a migration staged if a model changed?
- Is `downgrade()` non-trivial?
- Does the migration contain SQLite-incompatible DDL?
- Is `CONDUIT_SECRET` or `DATABASE_URL` affected?
- Will `heroku run flask db upgrade` be required post-deploy?

If no model or config changes: "No migration or config risk in this diff."

---

### 7. Suggested next actions
Ordered by priority. Actionable commands or file edits, not vague advice.

1. [BLOCK if applicable] ...
2. ...
3. ...
```
