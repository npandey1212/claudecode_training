# CLAUDE.md — Conduit (flask-realworld-example-app)

Project-specific rules for Claude Code working in this repo.

---

## Project overview

REST API backend for the [RealWorld](https://github.com/gothinkster/realworld) spec ("Conduit").
Implemented with Flask using an application-factory pattern, three modular blueprints, JWT auth,
and SQLAlchemy ORM. Deployed to Heroku via gunicorn.

---

## Repository layout

```
autoapp.py              # Entry point — picks DevConfig or ProdConfig via FLASK_DEBUG
conduit/
  app.py                # create_app() factory
  settings.py           # ProdConfig / DevConfig / TestConfig
  extensions.py         # Extension singletons + CRUDMixin on db.Model
  database.py           # SurrogatePK mixin, reference_col() helper
  exceptions.py         # InvalidUsage exception + named constructors
  utils.py              # JWT identity helpers (jwt_identity, identity_loader)
  commands.py           # Flask CLI: test, lint, clean, urls
  user/
    models.py           # User (table: users)
    views.py            # Blueprint: /api/users, /api/user
    serializers.py      # UserSchema (Marshmallow 3)
  profile/
    models.py           # UserProfile (table: userprofile), followers_assoc
    views.py            # Blueprint: /api/profiles/<username>
    serializers.py      # ProfileSchema
  articles/
    models.py           # Article, Tags, Comment; favoriter_assoc, tag_assoc
    views.py            # Blueprint: /api/articles, /api/tags
    serializers.py      # ArticleSchema, ArticleSchemas, CommentSchema, CommentsSchema
tests/
  conftest.py           # pytest fixtures: app, testapp, db, user
  factories.py          # UserFactory (factory-boy + SQLAlchemy)
  test_articles.py
  test_authentication.py
  test_config.py
  test_models.py
  test_profile.py
requirements/
  prod.txt              # Production deps (pinned SQLAlchemy==1.1.9, Flask-SQLAlchemy==2.2)
  dev.txt               # Extends prod.txt; adds pytest, WebTest, factory-boy, Faker
doc/
  dev-workflow.md       # Original Mermaid diagram + annotated workflow (ticket → deploy)
  workflow-map.md       # Refined flowchart + per-step scoring table (frequency / AI capability / ROI)
  impact-analysis.md    # Top 3 automation targets with before/after productivity estimates
  test-plan.md          # Test infrastructure reference, gap checklist, writing rules
  pr-check.md           # PR author + reviewer checklist and description template
.claude/
  CLAUDE.md             # This file
  settings.json         # Allowed / denied Claude Code shell commands for this repo
```

---

## Architecture

### Application factory

`create_app(config_object)` in `conduit/app.py` wires together:
1. Extensions (`bcrypt`, `cache`, `db`, `migrate`, `jwt`)
2. Three blueprints, each CORS-wrapped with the origin whitelist from config
3. A single error handler for `InvalidUsage`
4. Shell context (models available in `flask shell`)
5. CLI commands

`autoapp.py` calls `create_app(DevConfig)` when `FLASK_DEBUG=1`, `ProdConfig` otherwise.

### Blueprints

Each blueprint owns its own `models.py`, `views.py`, and `serializers.py`.

| Blueprint | URL prefix | Auth |
|-----------|-----------|------|
| `user` | `/api/users`, `/api/user` | JWT optional / required |
| `profile` | `/api/profiles` | JWT optional / required |
| `articles` | `/api/articles`, `/api/tags` | JWT optional / required |

### Model hierarchy

```
User (users)
 └─ UserProfile (userprofile)  1-to-1 via user_id FK
     ├─ follows  [M:M self-ref via followers_assoc]
     ├─ articles [backref from Article.author]
     ├─ favorites [backref from Article.favoriters]
     └─ comments [backref from Comment.author]

Article (article)
 ├─ author → UserProfile
 ├─ favoriters [M:M UserProfile via favoriter_assoc]
 ├─ tagList [M:M Tags via tag_assoc]
 └─ comments [1:M Comment]

Tags (tags)
Comment (comment)  → Article + UserProfile
```

Every model inherits **`CRUDMixin`** (from `extensions.py`) via `db = SQLAlchemy(model_class=CRUDMixin)`.
`CRUDMixin` supplies `.create()`, `.update()`, `.save()`, `.delete()`.

Models that need an integer PK also inherit **`SurrogatePK`** (from `database.py`),
which adds `id` and `.get_by_id()`.

`reference_col(tablename)` in `database.py` is the canonical way to declare FK columns.

### Serialization

All schemas use **Marshmallow 3** with `class Meta: strict = True`.

Every schema wraps/unwraps an envelope in `@pre_load` / `@post_dump`:
- Request JSON arrives as `{"user": {...}}`, `{"article": {...}}`, `{"comment": {...}}`, `{"profile": {...}}`
- Responses are re-wrapped in the same envelope
- `ArticleSchemas` / `CommentsSchema` override `@post_dump(pass_many=True)` to produce
  `{"articles": [...], "articlesCount": N}` / `{"comments": [...]}`

Schema instances at module level (`user_schema`, `article_schema`, etc.) are shared — do not
mutate them.

### Authentication

`Flask-JWT-Extended` with `JWT_HEADER_TYPE = 'Token'`.
- `create_access_token(identity=user)` stores `user.id` via `identity_loader`.
- `jwt_identity(payload)` reconstructs the `User` from the stored ID on every request.
- `current_user` (from flask-jwt-extended) is the `User` instance; access the profile via
  `current_user.profile`.

### Error handling

Raise `InvalidUsage` using its named constructors:

```python
raise InvalidUsage.user_not_found()       # 404
raise InvalidUsage.user_already_registered()  # 422
raise InvalidUsage.article_not_found()    # 404
raise InvalidUsage.comment_not_owned()    # 422
raise InvalidUsage.unknown_error()        # 500
```

Do not return raw error dicts from views; always raise `InvalidUsage`.

---

## Environment setup

### Required env vars

| Variable | Dev value | Notes |
|----------|-----------|-------|
| `FLASK_APP` | `autoapp.py` | Required for all `flask` CLI commands |
| `FLASK_DEBUG` | `1` | Selects `DevConfig`; omit or set `0` for prod |
| `CONDUIT_SECRET` | any string | Falls back to `'secret-key'` — change in prod |
| `DATABASE_URL` | _(not needed in dev)_ | PostgreSQL URI; used by `ProdConfig` only |

### Quick start (Pipenv)

```bash
export FLASK_APP=autoapp.py FLASK_DEBUG=1 CONDUIT_SECRET=localdev
pipenv install --dev
flask db upgrade
flask run
```

### Databases

| Environment | Engine | URI |
|-------------|--------|-----|
| Dev | SQLite | `dev.db` in project root |
| Test | SQLite | In-memory (`sqlite://`) |
| Prod | PostgreSQL | `$DATABASE_URL` |

**Important:** SQLite silently ignores some DDL (e.g. `ALTER COLUMN`). Always validate
migrations against a local PostgreSQL instance before merging to master.

---

## CLI commands

```bash
flask test                    # Run pytest (tests/ directory, verbose)
flask lint                    # flake8 (max-line-length 120)
flask lint --fix-imports      # isort -rc, then flake8
flask clean                   # Remove *.pyc / *.pyo files
flask urls                    # Print all registered routes
flask db migrate              # Auto-generate Alembic migration
flask db upgrade              # Apply pending migrations
flask shell                   # Python REPL with app context + model imports
```

---

## Coding rules

### General

- Follow the existing file-per-concern structure: `models.py`, `views.py`, `serializers.py`
  inside each blueprint package. Do not merge these.
- New blueprints must be registered in `conduit/app.py` (`register_blueprints`) and exposed in
  `register_shellcontext`.
- Do not use `db.session` directly in views. Use `CRUDMixin` methods (`.save()`, `.delete()`,
  `.update()`) or `db.session.rollback()` only in `except IntegrityError` blocks.

### Models

- Inherit `SurrogatePK, Model` for tables that need an integer PK.
- Use `reference_col('tablename')` for all FK columns — do not write raw `db.Column(db.ForeignKey(...))`.
- Keep business logic (follow/unfollow, favourite/unfavourite, is_following, etc.) on the model,
  not in views.
- The `User` model stores the bcrypt-hashed password as `db.Binary(128)`. Always call
  `user.set_password(plain)` — never write to `user.password` directly from a view.

### Views

- Decorate every view with `@use_kwargs(schema)` for deserialization and `@marshal_with(schema)`
  for serialization; do not manually call `schema.dump()` or `schema.load()` in view functions.
- Use `@jwt_required` for write endpoints, `@jwt_optional` for read endpoints that change output
  based on auth state.
- Keep views thin — no query logic beyond what is needed to retrieve the object; delegate to
  model methods.

### Serializers

- All schemas must set `class Meta: strict = True`.
- Maintain the envelope pattern (`@pre_load` unwraps, `@post_dump` re-wraps). New schemas must
  follow the same pattern.
- Fields that should never come back in responses: mark `load_only=True`.
  Fields that are read-only: mark `dump_only=True`.
- Instantiate schemas at module level as singletons. Do not instantiate schemas inside view
  functions.

### Linting

- Max line length: **120** characters (configured in `setup.cfg`).
- Run `flask lint` before every commit. There are no pre-commit hooks enforcing this.
- Run `flask lint --fix-imports` when adding or reordering imports.

---

## Testing rules

### Framework and fixtures

- Test runner: **pytest** via `flask test`.
- Use `TestConfig` (in-memory SQLite, `BCRYPT_LOG_ROUNDS=4`). Never test against dev or prod databases.
- All tests receive fixtures from `tests/conftest.py`:
  - `app` — function-scoped Flask test app
  - `db` — function-scoped in-memory DB (created + dropped each test)
  - `testapp` — WebTest `TestApp` wrapping the Flask app
  - `user` — a helper object; call `user.get()` to create and persist a `User` + `UserProfile`

### Writing tests

- Create model data via **factories** (`tests/factories.py`) or the `user` fixture, not by
  constructing models inline. Add new factories to `factories.py` when a new model is needed.
- HTTP tests use **WebTest** (`testapp.post_json`, `testapp.get`, etc.). Do not use
  `app.test_client()` — WebTest provides better response introspection.
- Assert on response `.json` dict structure, not on string content.
- Do not share state between tests — fixtures are function-scoped; each test gets a clean DB.

### Known baseline issue

One test is currently marked as failing / commented out (introduced in commit `4464881` during the
Marshmallow 3 migration). Before adding tests in the same area, run `flask test` to confirm the
existing baseline and do not suppress unrelated failures.

---

## Dependency notes

- `SQLAlchemy` is pinned to `1.1.9` and `Flask-SQLAlchemy` to `2.2` in `requirements/prod.txt`.
  Do not upgrade these without testing the `AppenderQuery` usage in `Article.favoriters` and
  `Article.comments` (both use `lazy='dynamic'` — a known breakage point from PR #27).
- `Marshmallow` is **version 3** (migrated in PR #26). Do not use the Marshmallow 2 API
  (`Schema(strict=True)` at instantiation, `@post_load` returning objects implicitly, etc.).
- `Flask-JWT-Extended` tokens use the header prefix `Token`, not `Bearer`. Any HTTP client or
  test must send `Authorization: Token <jwt>`.

---

## Deployment

Production runs on **Heroku** with gunicorn:

```
web: gunicorn autoapp:app -b 0.0.0.0:$PORT -w 3
```

After every deploy that includes schema changes, run migrations manually:

```bash
heroku run flask db upgrade
```

There is no automated post-deploy migration step. Skipping this will leave the production
database out of sync.
