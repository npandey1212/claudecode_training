Analyze the staged diff and produce two ready-to-use commit messages — a conventional-commit primary and a plain-language alternate — plus an optional body. Ground every word in the actual changed files; do not produce generic summaries.

## Usage

```
/commit                  # generate message from staged changes (git diff --cached)
/commit wip              # same, but prefix output with WIP: and omit body
/commit squash           # generate a squash/fixup message for amending or rebasing
```

Argument passed as: $ARGUMENTS

---

## Instructions

### Step 1 — Collect evidence (run all before writing any output)

1. `git diff --cached --stat` — file-level summary; number of insertions/deletions per file
2. `git diff --cached` — full staged diff
3. `git diff --cached --name-only` — plain file list for layer classification
4. `git status` — flag any related unstaged changes that are NOT in the staged set
5. `git log --oneline -5` — read recent commit messages to match the repo's established tone

Do not produce any output until all five commands have completed.

If `git diff --cached` is empty (nothing staged), output only:

```
Nothing is staged. Stage your changes first:

  git add <files>        # stage specific files
  git add -p             # stage hunks interactively

Then run /commit again.
```

And stop.

---

### Step 2 — Classify the staged files by layer

Use these tags in the body bullet points. Assign every changed file to one tag.

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

---

### Step 3 — Determine the conventional-commit type and scope

**Type — choose exactly one:**

| Type | Use when |
|------|----------|
| `feat` | A new endpoint, model method, or user-visible behaviour is added |
| `fix` | A bug, incorrect behaviour, or broken test is corrected |
| `test` | Tests are added or updated; no source change |
| `refactor` | Code is restructured without changing behaviour |
| `chore` | Dependency updates, CI config, tooling, `.gitignore` |
| `docs` | Documentation only (`*.md`, `*.rst`, docstrings) |
| `style` | Lint, formatting, import order only (no logic change) |
| `migration` | A database migration is the primary change |

**Scope — choose exactly one (or omit if the change spans three or more):**

| Scope | Use when |
|-------|----------|
| `user` | Changes are isolated to `conduit/user/` or `tests/test_authentication.py` |
| `profile` | Changes are isolated to `conduit/profile/` or `tests/test_profile.py` |
| `articles` | Changes are isolated to `conduit/articles/` or `tests/test_articles.py` |
| `auth` | Changes touch JWT decorators, `utils.py`, or `extensions.py` JWT wiring |
| `db` | Changes touch `conduit/database.py`, `conduit/extensions.py` CRUDMixin, or migrations |
| `config` | Changes touch `conduit/settings.py` or `autoapp.py` only |
| `deps` | Changes touch `requirements/*.txt` or `Pipfile` only |
| `ci` | Changes touch `.circleci/` or `.travis.yml` only |
| `serializer` | Changes touch one or more `serializers.py` files, no model or view change |

**Subject line rules (apply strictly):**
- 72 characters maximum including `type(scope): `
- Lowercase after the colon; no trailing period
- Imperative mood: "add", "fix", "remove", "update" — not "added", "fixes", "removed"
- Name the specific thing changed, not the category: "add DELETE /api/articles/<slug>" not "add delete endpoint"
- If a `[MIGRATION]` file is staged, the subject must name the schema change: "add slug column to article" not "update migration"
- If an auth decorator changed, name it: "`@jwt_required` → `@jwt_optional` on get_article"

---

### Step 4 — Rules for the alternate message

The alternate must differ from the primary in at least two of these ways:
- Different opening verb (if primary uses "add", alternate uses "introduce", "expose", "extend")
- Different emphasis (primary names the endpoint; alternate names the behaviour or the guard)
- Plain-language style without the `type(scope):` prefix — match the free-form style visible in commits like `AppenderQuery error with newer versions` or `[Bug Fix] deal API changes for marshmallow from 2 to 3`
- Never just a rephrasing of the same subject — it must read as a genuinely different description

---

### Step 5 — Rules for the optional body

Write the body only if any of the following are true:
- A `[MIGRATION]` file is staged
- An auth decorator (`@jwt_required`, `@jwt_optional`) was added, removed, or changed
- A `[SERIAL]` file changed (envelope structure is non-obvious to reviewers)
- More than two layers are touched in a single commit
- The diff contains a workaround, a known limitation, or a SQLAlchemy version constraint

Body format — bullet points only, no prose paragraphs:
- Lead with changed endpoints or model methods, one per bullet
- If a migration is included: state whether `downgrade()` is non-trivial
- If an auth decorator changed: state which endpoints and in which direction
- If a serializer envelope changed: name the key and the direction (added/removed/renamed)
- End with `No migration required.` or `Migration required: run flask db upgrade.` as appropriate
- Hard-wrap at 72 characters per line

Do not write a body that only restates the subject in longer form.

---

### Step 6 — Handle the $ARGUMENTS flags

**`/commit wip`**
- Prefix both messages with `WIP: `
- Omit the body section entirely
- Add a note: `⚠️  WIP commit — do not merge without removing WIP: prefix`

**`/commit squash`**
- Generate a single `fixup!` or `squash!` message suitable for `git rebase -i`
- Format: `fixup! <subject of the commit being amended>` (run `git log --oneline -3` to find it)
- No alternate, no body
- Add the rebase command: `git rebase -i HEAD~<N>` with the correct N

---

## Output format

Produce exactly this structure. No prose outside the sections.

---

```
## Commit messages for: <one-line description of what is staged, e.g. "DELETE comment endpoint + ownership guard">

### Staged files
<output of git diff --cached --stat, verbatim, indented as a code block>

⚠️  Unstaged related changes: <list any relevant unstaged files from git status, or "none">

---

### Primary  (conventional commit)
```
<type>(<scope>): <subject — ≤ 72 chars total>
```

### Alternate  (plain-language)
```
<plain subject — ≤ 72 chars>
```

---

### Body  (optional — paste after a blank line below the subject)
```
<bullet points per Step 5 rules>
```
_Omit body section entirely if none of the Step 5 conditions are met._

---

### Git commands

**Commit with primary message only (no body):**
```bash
git commit -m "<primary subject>"
```

**Commit with primary message + body:**
```bash
git commit -m "<primary subject>

<body bullet points>"
```

**Commit with alternate message only:**
```bash
git commit -m "<alternate subject>"
```

---

### Notes
- <one-line note per file if anything is ambiguous, risky, or staged partially — or "None.">
- Flag if `[MIGRATION]` is staged without a corresponding `[MODEL]` change, or vice versa.
- Flag if `[TEST]` files are absent and the staged change touches `[VIEW]` or `[MODEL]`.
- Flag if the subject had to be truncated below 72 chars and meaning was lost.
```
