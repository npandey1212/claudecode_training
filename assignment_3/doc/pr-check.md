# PR Checklist — Conduit (flask-realworld-example-app)

Copy this checklist into every GitHub PR description.
Items marked **[BLOCK]** must be resolved before merge. Others are best-effort.

---

## Author checklist

### Code quality
- [ ] **[BLOCK]** `flask lint` passes with zero violations (`max-line-length = 120`)
- [ ] **[BLOCK]** `flask lint --fix-imports` run if any imports were added or reordered
- [ ] **[BLOCK]** `flask test` passes — no new test failures beyond the known baseline (commit `4464881`)
- [ ] No `db.session` calls in views — only `CRUDMixin` methods (`.save()`, `.update()`, `.delete()`)
- [ ] No raw `db.Column(db.ForeignKey(...))` — use `reference_col('tablename')` from `database.py`
- [ ] No schema instantiation inside view functions — schemas are module-level singletons

### Serializers / API contract
- [ ] New schemas set `class Meta: strict = True`
- [ ] `@pre_load` unwraps the envelope; `@post_dump` re-wraps it (consistent with existing schemas)
- [ ] New `load_only` fields are not accidentally serialised in responses
- [ ] JWT auth header prefix is `Token`, not `Bearer` — any test headers or curl examples use `Authorization: Token <jwt>`

### Database
- [ ] **[BLOCK]** If any model was added or changed: `flask db migrate` was run and the generated script reviewed for correctness
- [ ] **[BLOCK]** Migration script does not use DDL that SQLite silently ignores (`ALTER COLUMN`, etc.) — test against PostgreSQL locally if possible
- [ ] Migration is reversible (`downgrade()` function is not empty / `pass`)

### Tests
- [ ] **[BLOCK]** New endpoints have at minimum: happy path, auth-missing, not-found test cases
- [ ] New models have a corresponding factory in `tests/factories.py` if used in > 1 test
- [ ] Tests use `testapp` (WebTest), not `app.test_client()`
- [ ] Tests assert on the JSON envelope structure (e.g. `res.json['article']['slug']`), not on raw strings

### Auth & security
- [ ] Write endpoints are decorated `@jwt_required`; read endpoints with auth-dependent output use `@jwt_optional`
- [ ] Password is never written directly to `user.password` — only via `user.set_password(plain)`
- [ ] `CONDUIT_SECRET` is not hardcoded anywhere in new code

---

## PR description template

```
## What changed
<!-- One sentence: what does this PR do? Which blueprint(s) does it touch? -->

## Why
<!-- Link to ticket / issue, or one line of context -->

## Migration included?
<!-- Yes / No. If Yes: what does it change? Is it reversible? -->

## Auth layer touched?
<!-- Yes / No. If Yes: which endpoints and how? -->

## Test coverage
<!-- New tests added: yes / no. If no, explain why. -->

## Checklist
<!-- Paste the author checklist above here and tick each box -->
```

---

## Reviewer checklist

- [ ] PR description answers all five template questions above
- [ ] If a migration is included: the script was read, not just trusted from `flask db migrate`
- [ ] If auth layer is touched: `@jwt_required` / `@jwt_optional` decorators are appropriate
- [ ] Envelope pattern is maintained in any new/modified serializer
- [ ] No new model attributes are returned in responses without explicit `dump_only` or exclusion
- [ ] If `lazy='dynamic'` is used on a new relationship: the query is exercised in a test
  (this pattern broke in PR #27 with SQLAlchemy version changes)

---

## Post-merge deploy checklist

- [ ] Merge to `master` complete
- [ ] Heroku auto-deploy triggered **or** `git push heroku master` run manually
- [ ] **If migration included:** `heroku run flask db upgrade` run within 5 minutes of deploy
- [ ] Spot-check: `GET /api/tags` and `POST /api/users/login` return 200 from prod
- [ ] No error-rate spike in Heroku logs (`heroku logs --tail`) in the 2 minutes following deploy
