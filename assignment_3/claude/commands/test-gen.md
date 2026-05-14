Inspect the target area, identify missing test coverage, and generate test scaffolds that match the existing pytest + WebTest + factory-boy patterns used in this repository.

## Usage

```
/test-gen                                   # inspect all staged/unstaged changes
/test-gen conduit/articles/views.py         # target a specific source file
/test-gen articles                          # target an entire blueprint (user|profile|articles)
/test-gen GET /api/articles/<slug>          # target a specific route
/test-gen tests/test_articles.py            # audit an existing test file for gaps
```

Argument passed as: $ARGUMENTS

---

## Instructions

### Step 1 — Determine the target

**If $ARGUMENTS is empty:**
Run `git diff HEAD --name-only` then `git diff --cached --name-only` and union the results.
Use every changed `.py` file under `conduit/` as the target set.
If nothing is staged or modified, report: "No changed files detected. Pass a file path or blueprint name as an argument." and stop.

**If $ARGUMENTS is a file path** (contains `/` or ends in `.py`):
Read that file directly.

**If $ARGUMENTS is a blueprint name** (`user`, `profile`, or `articles`):
Read all three files: `conduit/<blueprint>/models.py`, `conduit/<blueprint>/views.py`, `conduit/<blueprint>/serializers.py`.

**If $ARGUMENTS starts with an HTTP verb** (`GET`, `POST`, `PUT`, `DELETE`):
Parse the verb and path. Find the matching view function in `conduit/*/views.py` by scanning for the route decorator. Read that view function and its containing blueprint file.

**If $ARGUMENTS is a path inside `tests/`:**
Read that test file and its corresponding source files (infer the blueprint from the test file name).

---

### Step 2 — Read supporting context (do all of these before producing output)

1. Read `tests/conftest.py` — fixture signatures and scopes
2. Read `tests/factories.py` — available factories and their defaults
3. Read the test file(s) that correspond to the target blueprint:
   - `tests/test_authentication.py` for the `user` blueprint
   - `tests/test_profile.py` for the `profile` blueprint
   - `tests/test_articles.py` for the `articles` blueprint
   - `tests/test_models.py` for model-level behaviour
4. Read `.claude/CLAUDE.md` — testing rules section
5. If the target is a view file, read its serializer file to understand envelope structure

---

### Step 3 — Internalize repo test conventions (apply silently; do not print this section)

**WebTest call patterns — use exactly these forms in scaffolds:**

```python
# GET — no body
resp = testapp.get(url_for('blueprint.endpoint_name'))
resp = testapp.get(url_for('blueprint.endpoint_name', param=value))

# GET with auth
resp = testapp.get(url_for('blueprint.endpoint_name'),
                   headers={'Authorization': 'Token {}'.format(token)})

# POST with JSON body (use url_for, never hardcoded path strings)
resp = testapp.post_json(url_for('blueprint.endpoint_name'),
                         {'envelope_key': { ... }},
                         headers={'Authorization': 'Token {}'.format(token)})

# POST with no body (e.g. favorite, follow)
resp = testapp.post(url_for('blueprint.endpoint_name', slug=slug),
                    headers={'Authorization': 'Token {}'.format(token)})

# PUT with JSON body
resp = testapp.put_json(url_for('blueprint.endpoint_name'),
                        {'envelope_key': { ... }},
                        headers={'Authorization': 'Token {}'.format(token)})

# DELETE
resp = testapp.delete(url_for('blueprint.endpoint_name', slug=slug),
                      headers={'Authorization': 'Token {}'.format(token)})

# Expecting a non-2xx response — MUST pass expect_errors=True
resp = testapp.get(url_for('blueprint.endpoint_name'),
                   expect_errors=True)
assert resp.status_int == 404
```

**Status and body access:**
```python
resp.status_int          # integer HTTP status — NOT resp.status_code
resp.json                # parsed response body
resp.json['article']     # envelope key
resp.json['user']['token']
resp.json['profile']['following']
```

**Error body assertions — compare against the constant, not a hand-written dict:**
```python
from conduit.exceptions import USER_NOT_FOUND, ARTICLE_NOT_FOUND, USER_ALREADY_REGISTERED
assert resp.json == USER_NOT_FOUND['message']
assert resp.json == ARTICLE_NOT_FOUND['message']
```

**Token acquisition pattern — replicate this exactly:**
```python
def _login(testapp, email, password='myprecious'):
    resp = testapp.post_json(url_for('user.login_user'),
                             {'user': {'email': email, 'password': password}})
    return str(resp.json['user']['token'])
```

**User + profile creation:**
```python
# via fixture (preferred for single-user tests)
muser = user.get()          # creates User + UserProfile; password is 'myprecious'
token = _login(testapp, muser.email)

# via _register_user helper (preferred when you need the token immediately)
resp = _register_user(testapp)
token = str(resp.json['user']['token'])
```

**Model-level tests (no HTTP):**
```python
@pytest.mark.usefixtures('db')
class TestSomething:
    def test_behaviour(self, user):
        muser = user.get()
        # construct models directly — no factory needed for simple cases
        article = Article(muser.profile, 'title', 'body', description='desc')
        article.save()
        assert article.author == muser.profile
```

**Factories — only `UserFactory` exists. For Article/Tags/Comment, construct inline:**
```python
# UserFactory — creates User only; profile must be created separately
u = UserFactory(password='secret')
profile = UserProfile(u)
profile.save()
db.session.commit()

# Article — inline until an ArticleFactory is added to tests/factories.py
article = Article(profile, 'My Title', 'Body text', description='A description')
article.save()
```

**Python version constraint:** All test code must be compatible with Python 3.6
(CI uses `python:3.6.0`). No walrus operator, no f-strings unless already present in
the file being extended, no `datetime.fromisoformat()`.

---

### Step 4 — Identify coverage gaps using this checklist

For each endpoint in the target view file, check whether all of the following scenarios
exist in the corresponding test file. Mark each as present (✅) or missing (❌).

| Scenario category | What to look for |
|-------------------|-----------------|
| **Happy path** | 2xx response, correct envelope key, correct field values |
| **Auth missing** | `@jwt_required` endpoint called without `Authorization` header; expect 401/422 |
| **Auth wrong token** | Garbage token value; expect 401/422 |
| **Not found** | Resource slug/id that does not exist; expect 404 + correct error body |
| **Duplicate / conflict** | e.g. same slug, same email; expect 422 |
| **Ownership enforcement** | Action on another user's resource; expect 422 |
| **Pagination** | `limit` and `offset` params on list endpoints |
| **Filter params** | `tag`, `author`, `favorited` on `GET /api/articles` |
| **Empty list** | Query that returns zero results; expect `[]` not an error |
| **Model method coverage** | Methods on the model (e.g. `is_favourite`, `favorited`, `following`) exercised via HTTP |

For `lazy='dynamic'` relationships (`Article.favoriters`, `Article.comments`,
`UserProfile.follows`), flag explicitly if there is no test that calls `.all()` or
filters on the relationship — this is the pattern that broke in PR #27.

---

### Step 5 — Produce the report

Use exactly this structure. Prefix every finding with:
- `✅` — observed directly in existing source or test files
- `⚠️` — inferred; state the assumption
- `❌` — gap or violation

---

## Output format

```
## Test generation — <short description of target, e.g. "articles blueprint views">

### 1. Changed area summary
- Target: <file(s) or blueprint(s) inspected>
- Blueprint: <user | profile | articles | multiple>
- Endpoints / model methods in scope: <list with HTTP verb and path>
- Serializer envelope keys: <e.g. `article`, `articles`, `comment`, `comments`>
- Auth decorators present: <list of @jwt_required / @jwt_optional per endpoint>
- lazy='dynamic' relationships touched: yes/no — <list if yes>

---

### 2. Existing related tests
List every test function that already covers something in the target area.
Format: `✅ <test file>::<class>::<test_name> — <what it covers>`
If a test file for this blueprint does not exist: `❌ No test file found for <blueprint> blueprint.`

---

### 3. Missing test scenarios
For each gap found in Step 4, one line per missing scenario.
Format: `❌ <endpoint or method> — <scenario category> — <one sentence on what to assert>`

Group by endpoint. If a scenario cannot be verified from the source alone, prefix with ⚠️
and state the assumption.

If no gaps found: "No missing scenarios identified for the target area."

---

### 4. Suggested test scaffolds

Provide one complete, runnable test function or class per missing scenario group (group
related scenarios for the same endpoint into one class). Use only patterns from Step 3.

Rules for scaffolds:
- Use `url_for('blueprint.endpoint_name')` — never hardcoded URL strings
- Include the `_login` helper if the file does not already have one
- Add a factory to `tests/factories.py` if the scaffold needs Article/Tags/Comment
  and that factory does not exist — show the factory code separately before the test
- Mark any assertion that depends on behaviour not visible in the source with a
  comment: `# ⚠️ inferred — verify against actual response shape`
- Python 3.6 compatible — use `.format()` not f-strings unless the target file already
  uses f-strings

Show scaffolds as fenced Python code blocks. Label each block with the destination file,
e.g.:

**`tests/test_articles.py`** — add inside `class TestArticleViews`

```python
# scaffold code here
```

**`tests/factories.py`** — add after `UserFactory` (only if a new factory is needed)

```python
# factory code here
```

---

### 5. Commands to run

Exact shell commands, in order. No explanation prose.

```bash
export FLASK_APP=autoapp.py FLASK_DEBUG=1

# run only the relevant test file
.venv/Scripts/python.exe -m pytest tests/<test_file>.py -v

# run a single test by name
.venv/Scripts/python.exe -m pytest tests/<test_file>.py::<ClassName>::<test_name> -v

# run the full suite to check for regressions
flask test

# lint after adding new test code
flask lint
```

Note: one test in `tests/test_profile.py` is known-failing as of commit `4464881`
(Marshmallow 3 migration). A red result there is expected baseline noise, not a
regression introduced by new scaffolds.

---

### 6. Coverage / risk notes

Conservative observations only. Do not claim specific line-coverage percentages
(no coverage tool is configured in this repo).

- ⚠️/✅ for each note.
- Flag any scenario that behaves differently on SQLite (test DB) vs PostgreSQL (prod).
  Specifically: `ALTER COLUMN` in migrations, `ILIKE` queries, JSON column types.
- Flag any `lazy='dynamic'` relationship that is exercised only at the model level
  (unit test) but not via the HTTP layer — the serializer layer may expose different
  behaviour.
- Flag if new factories are needed before the scaffolds can run.
- End with a one-line risk summary:
  `Risk: low | medium | high — <one sentence reason>`
```
