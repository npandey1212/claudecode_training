# Test Plan — Conduit (flask-realworld-example-app)

> All items below are grounded in the actual test infrastructure present in this repo.
> Where a gap is noted it is an observed absence, not an assumption.

---

## Test environment

| Property | Value | Source |
|----------|-------|--------|
| Runner | pytest (via `flask test`) | `conduit/commands.py` |
| HTTP layer | WebTest `TestApp` | `tests/conftest.py` |
| Database | In-memory SQLite (`sqlite://`) | `conduit/settings.py` `TestConfig` |
| Password hashing | bcrypt log-rounds = 4 (fast) | `conduit/settings.py` `TestConfig` |
| Fixture scope | Function — each test gets a clean DB | `tests/conftest.py` |
| Auth header format | `Authorization: Token <jwt>` | `conduit/settings.py` `JWT_HEADER_TYPE` |

### Running tests

```bash
export FLASK_APP=autoapp.py FLASK_DEBUG=1
flask test                # full suite, verbose
```

To run a single file:

```bash
pipenv run pytest tests/test_articles.py -v
```

---

## Fixture reference

All fixtures live in `tests/conftest.py`.

| Fixture | Scope | What it provides |
|---------|-------|-----------------|
| `app` | function | Flask app created with `TestConfig`; pushes a request context |
| `db` | function | `db.create_all()` before test, `db.drop_all()` after |
| `testapp` | function | `WebTest.TestApp(app)` — use for all HTTP-level tests |
| `user` | function | Helper object; call `user.get()` to create a persisted `User` + `UserProfile` |

### Factory reference (`tests/factories.py`)

| Factory | Model | Auto-generates |
|---------|-------|---------------|
| `UserFactory` | `User` | sequential `username`, `email`; bcrypt-hashes password `'example'` |

**Gap:** No factories exist for `Article`, `Tags`, or `Comment`. Tests that need these models
must construct them inline. Adding factories here is a high-value low-effort improvement.

---

## Existing test coverage

| File | What it covers |
|------|---------------|
| `test_authentication.py` | POST `/api/users` (register), POST `/api/users/login` |
| `test_profile.py` | GET `/api/profiles/<username>`, follow/unfollow |
| `test_articles.py` | Article CRUD, favouriting, tag filtering |
| `test_models.py` | `User.set_password`, `User.check_password`, model repr |
| `test_config.py` | Config class selection via `FLASK_DEBUG` |

**Known baseline issue:** One test in `test_profile.py` is commented out / known-failing as of
commit `4464881` (Marshmallow 3 migration). Run `flask test` before any new work to establish the
current baseline; do not treat a red baseline as a new failure.

---

## Test writing rules

### Structure

1. Use the `testapp` fixture for all HTTP-level tests. Do not use `app.test_client()`.
2. Use the `db` fixture whenever you need to persist models; it guarantees a clean DB per test.
3. Obtain a user via `user.get()` (which also creates the `UserProfile`). Do not construct
   `User` instances inline — the `UserProfile` creation step is easy to forget and causes FK errors.
4. Assert on the response JSON envelope structure, not on string content.
   ```python
   res = testapp.post_json('/api/users/login', {'user': {...}})
   assert res.json['user']['email'] == 'user@example.com'
   ```
5. For auth-required endpoints, obtain a token from the login response, then pass it:
   ```python
   token = testapp.post_json('/api/users/login', {'user': {...}}).json['user']['token']
   headers = {'Authorization': f'Token {token}'}
   res = testapp.get('/api/user', headers=headers)
   ```

### What to test for each new endpoint

For every new view function, write at minimum:

- [ ] **Happy path** — correct input, expected response envelope and status code
- [ ] **Auth missing** — omit `Authorization` header on `@jwt_required` endpoints; expect 401/422
- [ ] **Not found** — resource does not exist; expect the `InvalidUsage` error envelope
- [ ] **Duplicate / conflict** — e.g. registering an existing email; expect 422 with error body
- [ ] **Input validation** — missing required field; expect 422

### What NOT to test

- Do not test SQLAlchemy internals (e.g. that `.save()` calls `db.session.add()`).
- Do not test Flask extension behaviour (e.g. that bcrypt hashes look a certain way).
- Do not write tests that depend on sequence order across test functions — fixtures are
  function-scoped and state is not shared.

---

## Gap checklist

The following test cases are absent from the current suite and represent the highest-risk coverage gaps:

- [ ] `DELETE /api/articles/<slug>` — happy path and not-found
- [ ] `DELETE /api/articles/<slug>/comments/<cid>` — happy path and not-owned
- [ ] `POST /api/articles/<slug>/favorite` + `DELETE` — happy path
- [ ] `GET /api/articles/feed` — requires follow relationship setup
- [ ] `GET /api/tags` — trivial but absent
- [ ] Concurrent-user tests for follow/unfollow M:M relationship
- [ ] Migration smoke test against PostgreSQL (currently only tested via SQLite)
- [ ] `Article.is_favourite` / `Article.favorited` property — currently untested against the
  `lazy='dynamic'` query behaviour that was broken in PR #27

---

## CI integration

CI runs `flask test` via CircleCI (`python:3.6.0` image). It does **not** run `flask lint`.
The Python version in CI (3.6) differs from the `Pipfile` target (3.7). Tests pass on both
but f-strings in tests will fail on 3.5; any walrus operator (`:=`) will fail on < 3.8.

Keep tests compatible with Python 3.6 until the CI image is updated.
