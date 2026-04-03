# 2.1 Break Prompts Intentionally

---

## 1) Why does model_schema function returns incorrect xml output?

**Claude Code:**
> There's no model_schema function in pydantic that produces XML output — pydantic has no XML support at all, natively.
>
> A few possibilities for what you might mean:
>
> 1. `model_json_schema()` (main.py) — generates JSON Schema (not XML). Is that what you're looking at?
> 2. A custom integration — are you using a third-party library (e.g. pydantic-xml, xsdata, lxml) on top of pydantic?
> 3. `__pydantic_core_schema__` — the internal CoreSchema dict — which is sometimes called "the schema" in pydantic internals, but it's a Python dict, not XML.
> 4. A specific test or file — did you see this in a particular file or test in the repo?
>
> Could you clarify:
> - Where did you see model_schema producing XML (file path, line, or error message)?
> - What XML output were you expecting vs. what you got?
>
> That will let me trace the actual bug or misunderstanding precisely.

**Explanation:**  
Returned a valid answer for the vague prompt — correctly identified that only JSON is supported.

---

## 2) Add support for new types

**Claude Code:**
> Too vague to act on. I need to know:
>
> 1. Which types? — e.g. IPv6Network, Decimal, pathlib.PurePath, a custom class, something else?
> 2. Where? — as a new pydantic built-in type in `pydantic/types.py`? In `pydantic/networks.py`? As a `__get_pydantic_core_schema__` on your own class?
> 3. What validation behavior? — what should pydantic accept, coerce, and reject for this type?
>
> Give me a concrete example and I can trace exactly what needs to change and where.

**Explanation:**  
Returned a valid response.

---

## 3) Fix the validation errors

**Claude Code:**
> No validation errors have been shared. I need something concrete to work with:
>
> 1. Paste the error — the full `ValidationError` output or stack trace  
> 2. Paste the code — the model definition and the input that triggered it  
> 3. Or point to a file — a test file, a script, a specific line in this repo  
>
> Without any of these I'm guessing at shadows. What exactly are you seeing?

**Explanation:**  
Returned a valid response.

---

## 4) Improve error messages

**Claude Code:**
> Still too vague. Please clarify:
>
> 1. Which error messages? — `ValidationError` output? Internal `PydanticUserError` messages? Something in `pydantic/errors.py`?
> 2. What's wrong with them? — unclear wording, missing context, wrong location (`loc`), something else?
> 3. Which scenario? — a specific field type, a specific validator mode, a specific edge case?
>
> Paste the current error message you're unhappy with and describe what it should say instead.

**Explanation:**  
Returned a valid response.