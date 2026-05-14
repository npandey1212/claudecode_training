Read the repository files listed in Step 1 and produce a concise onboarding brief for a new engineer. Every claim must be grounded in a file you actually read; label anything that cannot be directly verified with ⚠️.

## Usage

```
/onboard                  # full 8-section brief (recommended for day-one engineers)
/onboard auth             # section 4 only — deep-dive on the JWT auth flow
/onboard testing          # section 5 only — deep-dive on the test setup
/onboard migrations       # section 6 only — deep-dive on the migration workflow
/onboard conventions      # section 7 only — coding rules and known gotchas
```

Argument passed as: $ARGUMENTS

---

## Instructions

### Step 1 — Read these files before writing any output

Read all of the following. Do not produce any output until every file has been read.

| File | Why |
|------|-----|
| `autoapp.py` | Entry point — how the app is created |
| `conduit/app.py` | Application factory — full wiring |
| `conduit/settings.py` | Three config classes and their differences |
| `conduit/extensions.py` | CRUDMixin definition and extension singletons |
| `conduit/database.py` | SurrogatePK mixin and `reference_col` helper |
| `conduit/exceptions.py` | `InvalidUsage` and named constructors |
| `conduit/utils.py` | JWT identity wiring |
| `conduit/compat.py` | Python 2/3 shim (legacy; still imported by database.py) |
| `conduit/user/models.py` | `User` model — the identity anchor |
| `conduit/user/views.py` | User blueprint — shows the full request pattern |
| `conduit/user/serializers.py` | `UserSchema` — envelope pattern |
| `conduit/profile/models.py` | `UserProfile`, follow/unfollow, `followers_assoc` |
| `conduit/articles/models.py` | `Article`, `Tags`, `Comment`, M:M association tables |
| `tests/conftest.py` | Fixture hierarchy |
| `tests/factories.py` | `UserFactory` — only factory that exists |
| `tests/test_authentication.py` | Canonical HTTP test pattern |
| `.claude/CLAUDE.md` | Conventions reference |
| `requirements/prod.txt` | Pinned production dependencies |
| `Procfile` | Production server invocation |

---

### Step 2 — Handle focused arguments

**If $ARGUMENTS is `auth`:** produce a brief intro (3–4 lines from section 1 for context), then expand section 4 to double its normal depth. Omit sections 2, 3, 5, 6, 7, 8 and the Day 1 tasks.

**If $ARGUMENTS is `testing`:** produce a brief intro, then expand section 5. Include the full fixture reference table and a worked example of the login-then-call pattern. Omit other sections.

**If $ARGUMENTS is `migrations`:** produce a brief intro, then expand section 6. Include all five `flask db` commands and the prod-migration risk in full. Omit other sections.

**If $ARGUMENTS is `conventions`:** produce a brief intro, then expand section 7. List every coding rule and known gotcha from CLAUDE.md. Omit other sections.

**If $ARGUMENTS is empty:** produce all eight sections and the Day 1 tasks at normal depth.

---

### Step 3 — Synthesis rules (apply to all sections)

- Prefix every factual claim with ✅ (read directly from a file) or ⚠️ (inferred or not verifiable from the files above).
- Do not invent endpoint behaviour — state only what the view function explicitly does.
- Where a pattern has a known failure history, say so and cite the commit or PR.
- Keep each section scannable: use short bullets and inline code, not prose paragraphs.
- Do not repeat CLAUDE.md verbatim — synthesise it for a reader encountering the codebase for the first time.

---

## Output format

````
## Onboarding brief — Conduit (flask-realworld-example-app)
> Generated from repo files. ✅ = verified from source. ⚠️ = inferred.

---

### 1. Project purpose

- ✅ Backend REST API implementing the [RealWorld "Conduit" spec](https://github.com/gothinkster/realworld) — a Medium-style blogging platform used as a reference implementation across many frameworks.
- ✅ Exposes JSON endpoints for: user registration and login, profile follow/unfollow, article CRUD, article favouriting, article tags, and article comments.
- ✅ Deployed to **Heroku** via **gunicorn** (`Procfile`: `gunicorn autoapp:app -b 0.0.0.0:$PORT -w 3`).
- ✅ Python 3 app; `conduit/compat.py` is a legacy Python 2/3 shim still imported by `database.py` — do not remove it.

---

### 2. Key directories and files

Present this as an annotated tree. Use ✅/⚠️ per entry. Include only the files listed in Step 1 plus the `migrations/` and `doc/` directories. One line of explanation per entry. Example format:

```
flask-realworld-example-app/
├── autoapp.py              ✅ Entry point. Reads FLASK_DEBUG; passes DevConfig or ProdConfig to create_app()
├── conduit/
│   ├── app.py              ✅ Application factory. Registers extensions, blueprints, error handler, CLI
│   ├── settings.py         ✅ ProdConfig / DevConfig / TestConfig — three distinct DB URIs
│   ├── extensions.py       ✅ Extension singletons + CRUDMixin (inherited by every model via SQLAlchemy)
│   ├── database.py         ✅ SurrogatePK mixin (integer PK + get_by_id) and reference_col() FK helper
│   ├── exceptions.py       ✅ InvalidUsage exception with named constructors (user_not_found, etc.)
│   ├── utils.py            ✅ JWT identity callbacks wired to User.id
│   ├── compat.py           ✅ Python 2/3 shim — legacy; do not delete (imported by database.py)
│   ├── commands.py         ✅ Flask CLI: flask test, flask lint, flask clean, flask urls
│   ├── user/               ✅ User blueprint: register, login, get/update current user
│   ├── profile/            ✅ Profile blueprint: get profile, follow, unfollow
│   └── articles/           ✅ Articles blueprint: CRUD, favourite, feed, tags, comments
├── tests/
│   ├── conftest.py         ✅ Fixtures: app, testapp, db, user (all function-scoped)
│   ├── factories.py        ✅ UserFactory only — no Article/Tags/Comment factories exist yet
│   └── test_*.py           ✅ Five test files, one per concern
├── migrations/             ✅ Alembic migration scripts managed by Flask-Migrate
├── requirements/
│   ├── prod.txt            ✅ SQLAlchemy pinned to 1.1.9; Flask-SQLAlchemy pinned to 2.2
│   └── dev.txt             ✅ Extends prod.txt; adds pytest, WebTest, factory-boy, Faker
├── doc/                    ✅ Workflow docs, impact analysis, test plan, PR checklist
├── .claude/                ✅ CLAUDE.md conventions + slash commands
└── Procfile                ✅ Production: gunicorn autoapp:app -b 0.0.0.0:$PORT -w 3
```

---

### 3. Architecture summary

Describe the request lifecycle in four steps (adapt exact text from what you read in the files):

1. **Entry** — `autoapp.py` selects config, calls `create_app()`.
2. **Factory** — `conduit/app.py` initialises extensions in order (`bcrypt → cache → db → migrate → jwt`), registers each blueprint with its CORS origin whitelist, attaches `InvalidUsage` error handler, and adds CLI commands.
3. **Request path** — Incoming JSON → blueprint view function → `@use_kwargs(schema)` deserialises and unwraps the request envelope → view calls model methods via `CRUDMixin` → `@marshal_with(schema)` serialises and re-wraps the response envelope.
4. **Data layer** — Every model inherits `CRUDMixin` (`.save()`, `.update()`, `.delete()`, `.create()`) via `db = SQLAlchemy(model_class=CRUDMixin)`. Models needing a PK also inherit `SurrogatePK`. FK columns are declared with `reference_col('tablename')`.

Include a one-paragraph model relationship summary derived from the files (User → UserProfile 1:1, UserProfile → Article 1:M, etc.).

---

### 4. Auth flow

Cover these points with ✅/⚠️ labels:

- ✅ **Library:** `Flask-JWT-Extended`. Configured in `conduit/settings.py`: `JWT_HEADER_TYPE = 'Token'` and `JWT_AUTH_HEADER_PREFIX = 'Token'`.
- ✅ **Header format:** `Authorization: Token <jwt>` — NOT `Bearer`. This applies in tests, curl calls, and any client code.
- ✅ **Token issuance:** `create_access_token(identity=user)` → `identity_loader` in `utils.py` stores `user.id` as the identity.
- ✅ **Token verification:** On each request, `jwt_identity(payload)` in `utils.py` calls `User.get_by_id(payload)` to reconstruct the `User` object.
- ✅ **`current_user`:** Provided by `flask_jwt_extended`. It is the `User` model instance. Access the profile via `current_user.profile` (a SQLAlchemy backref on `UserProfile`).
- ✅ **Decorator rules:** `@jwt_required` on write endpoints (POST/PUT/DELETE that modify state); `@jwt_optional` on read endpoints whose response differs based on whether the caller is authenticated (e.g. `following` field on profiles).
- ✅ **Token in response:** The `token` field on `User` is a plain Python attribute (`token: str = ''`), not a DB column. It is set after login/register and serialised by `UserSchema` as `dump_only=True`.
- ⚠️ **Token expiry:** `DevConfig` sets `JWT_ACCESS_TOKEN_EXPIRES = timedelta(10 ** 6)` (≈ 11.5 days). `ProdConfig` inherits the Flask-JWT-Extended default (15 minutes unless overridden by env).

Walk through the register flow explicitly:
1. `POST /api/users` with `{"user": {"username": ..., "email": ..., "password": ...}}`
2. `@use_kwargs(user_schema)` unwraps and deserialises
3. `User(...).save()` then `UserProfile(user).save()` — both must succeed
4. `create_access_token(identity=user)` attached to `user.token`
5. `@marshal_with(user_schema)` re-wraps as `{"user": {..., "token": "..."}}`

---

### 5. Testing workflow

Cover these points:

**Running tests:**
```bash
export FLASK_APP=autoapp.py FLASK_DEBUG=1
flask test                    # full suite via pytest, verbose
# or target a single file:
.venv/Scripts/python.exe -m pytest tests/test_articles.py -v
```

**Fixture hierarchy** (from `tests/conftest.py`) — present as a table:

| Fixture | Scope | Provides |
|---------|-------|---------|
| `app` | function | Flask app with `TestConfig`; in-memory SQLite; pushes request context |
| `db` | function | `db.create_all()` before, `db.drop_all()` after — clean state per test |
| `testapp` | function | `WebTest.TestApp(app)` — the only HTTP client to use |
| `user` | function | Helper; call `user.get()` to create a `User` + `UserProfile` with password `'myprecious'` |

**Key call patterns** (from `tests/test_authentication.py` and `tests/test_articles.py`):
- HTTP requests via `testapp.post_json(url_for(...), {...}, headers={...})`
- Status code: `resp.status_int` — not `resp.status_code`
- Non-2xx tests: must pass `expect_errors=True` or WebTest raises
- URL resolution: always `url_for('blueprint.endpoint_name')` — never hardcoded strings
- Error body assertion: `resp.json == USER_NOT_FOUND['message']` (import the constant from `conduit/exceptions.py`)

**Known baseline issue:**
✅ One test in `tests/test_profile.py` is commented out / known-failing as of commit `4464881` (Marshmallow 3 migration side-effect). A red result there is expected noise. Run `flask test` before making any changes to establish your personal baseline.

**SQLite vs PostgreSQL:**
✅ Tests use in-memory SQLite (`TestConfig`). Production uses PostgreSQL. SQLite silently ignores some DDL (`ALTER COLUMN`, constraints). Write tests that will catch this: don't rely on SQLite-specific permissiveness.

---

### 6. Migration workflow

**Development (one-time setup):**
```bash
flask db init        # only needed if the migrations/ directory doesn't exist yet
flask db migrate     # auto-generate a migration script from model changes
flask db upgrade     # apply pending migrations to dev.db (SQLite)
```

**Everyday flow** (when you change a model):
```bash
# 1. edit conduit/*/models.py
flask db migrate -m "short description of the change"
# 2. REVIEW the generated file in migrations/versions/ before applying
flask db upgrade
```

**What Alembic cannot detect automatically** (always review the generated script):
- Renaming a column or table
- Changing a column's server default
- Removing a constraint
- Changes inside `__table_args__`

**Production (after every merge that changes a model):**
```bash
heroku run flask db upgrade
```
✅ This step is **manual and undocumented** in the Procfile — there is no post-deploy hook. If you skip it, the production database schema is out of sync with the running code.
⚠️ The one-off dyno has a 30-second default timeout. Migrations touching large tables may time out — plan accordingly.

---

### 7. Important conventions

Summarise the rules from `.claude/CLAUDE.md` as a new-engineer-oriented list. Group into: **must-know rules** and **known gotchas**.

**Must-know rules:**
- ✅ Every model inherits `CRUDMixin`. Use `.save()`, `.update()`, `.delete()` — do not call `db.session` directly in views (only allowed in `except IntegrityError` rollbacks).
- ✅ FK columns: always `reference_col('tablename')` from `conduit/database.py`. Never raw `db.Column(db.ForeignKey(...))`.
- ✅ Views stay thin. Business logic (follow/unfollow, favourite, tag management) lives on the model, not the view.
- ✅ All serializer schemas: `class Meta: strict = True`. `@pre_load` unwraps the request envelope; `@post_dump` re-wraps the response. Do not break this pattern.
- ✅ Schema instances are module-level singletons. Never instantiate a schema inside a view function.
- ✅ New blueprints require two registration calls in `conduit/app.py`: `register_blueprints()` and `register_shellcontext()`.

**Known gotchas — things that will waste your time if you don't know them:**
- ✅ **JWT header is `Token`, not `Bearer`.** Every test, every curl call, every client. This has silently broken things before.
- ✅ **SQLAlchemy is pinned to `1.1.9` and Flask-SQLAlchemy to `2.2`** in `requirements/prod.txt`. Do not upgrade — the `lazy='dynamic'` relationship pattern on `Article.favoriters` and `Article.comments` breaks with newer versions (PR #27).
- ✅ **Marshmallow is version 3.** The codebase was migrated from v2 in PR #26. The v2 API (`Schema(strict=True)` at instantiation, implicit `@post_load` object return) does not work here.
- ✅ **`conduit/compat.py` is a Python 2 shim.** `database.py` imports `basestring` from it. Do not delete it even though Python 2 is gone.
- ✅ **One test is permanently failing.** `tests/test_profile.py` has a commented-out assertion from the Marshmallow 3 migration. This is expected noise in `flask test` output.
- ✅ **No pre-commit hooks exist.** `flask lint` is entirely manual. You will push unlinted code to CI if you forget to run it.
- ⚠️ **CircleCI uses `python:3.6.0`** but `Pipfile` targets Python 3.7. Tests pass on both, but do not use any Python 3.7+ syntax (dataclasses, `datetime.fromisoformat()`, etc.) in source files.

---

### 8. First files to read

Present as an ordered reading path with a time estimate for each file and one sentence on what to understand before moving on.

| Order | File | Time | What to take away |
|-------|------|------|------------------|
| 1 | `autoapp.py` | 2 min | ✅ Config is selected by `FLASK_DEBUG`. This is the entry point gunicorn uses. |
| 2 | `conduit/settings.py` | 5 min | ✅ Three configs, three DB URIs. `TestConfig` is SQLite in-memory. `ProdConfig` reads `DATABASE_URL` from env. |
| 3 | `conduit/app.py` | 5 min | ✅ The factory order matters: extensions first, then blueprints, then error handler. Understand `register_blueprints` before touching CORS. |
| 4 | `conduit/extensions.py` | 5 min | ✅ `CRUDMixin` is the base of every model. Read `.save()`, `.update()`, `.delete()`. Then read the JWT wiring at the bottom. |
| 5 | `conduit/user/models.py` → `views.py` → `serializers.py` | 15 min | ✅ One complete blueprint end-to-end. The envelope pattern, `@use_kwargs`, `@marshal_with`, `set_password`, and `InvalidUsage` all appear here. |
| 6 | `conduit/exceptions.py` | 3 min | ✅ How errors are raised. Named constructors only — never construct `InvalidUsage` directly from a view. |
| 7 | `tests/conftest.py` + `tests/test_authentication.py` | 10 min | ✅ Fixture hierarchy and the canonical HTTP test pattern. Understand `user.get()`, `url_for()`, and `expect_errors=True` before writing any test. |
| 8 | `.claude/CLAUDE.md` | 15 min | ✅ Full conventions reference. Read once; return to it when you're unsure about a pattern. |

---

### Day 1 tasks

Concrete steps to get oriented and productive:

```bash
# 1. Set env vars
export FLASK_APP=autoapp.py FLASK_DEBUG=1 CONDUIT_SECRET=localdev

# 2. Install dependencies
pip install -r requirements/dev.txt
# If behind a corporate proxy with SSL inspection:
# pip install -r requirements/dev.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org

# 3. Apply migrations
flask db upgrade

# 4. Start the dev server
flask run

# 5. Verify the API is running
curl http://localhost:5000/api/tags

# 6. Run the test suite and record your baseline
flask test
# Note which test is already failing (expected: one in test_profile.py)

# 7. List all registered routes
flask urls
```

After these steps: read the files in order from the table above. You should be productive within half a day.
````
