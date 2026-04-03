# Bug Audit — Pydantic Codebase
**Session Date:** 2026-04-03  
**Auditor:** Claude Code (claude-sonnet-4-6)  
**Branch:** main  
**Head Commit:** 46dea9288  
**Scope:** Bugs surfaced and analyzed during codebase exploration + XMLDatatype design review

---

## Severity Legend

| Level | Meaning |
|-------|---------|
| 🔴 Critical | Incorrect output / silent data corruption / contract violation |
| 🟠 High | Feature broken for a real use-case; no workaround |
| 🟡 Medium | Silent failure or missing warning; observable but not crashing |
| 🔵 Low | Edge-case data fidelity concern; unlikely in practice |
| ✅ None | Investigated; no issue found |

---

## Bug #1 — Tuple Serialization Silently Drops Items

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Status** | Fixed |
| **Commit** | `46dea9288` |
| **PR** | [#13016](https://github.com/pydantic/pydantic/pull/13016) |
| **File** | `pydantic-core/src/serializers/type_serializers/tuple.rs` |
| **Lines** | 214–220 |

### Description
When serializing a **fixed-length tuple** that had **fewer items than expected**, the Rust serializer silently completed the loop without warning the caller. Data was dropped without any indication.

### Root Cause
The non-variadic tuple serialization path iterated through provided items and stopped early when items ran out. No check compared `n_items` against `self.serializers.len()` (the expected count). The symmetric warning for *extra* items (`"Unexpected extra items present in tuple"`) already existed (lines 224–228), but the *too-few-items* case had no equivalent.

### Fix Applied
```rust
// pydantic-core/src/serializers/type_serializers/tuple.rs : 214
if n_items < self.serializers.len() {
    state.warnings.register_warning(
        PydanticSerializationUnexpectedValue::new_from_msg(Some(
            "Unexpected too few items present in tuple".to_string(),
        ))
    );
}
```

### Impact
Non-crashing. Users serializing under-filled fixed tuples received no signal that data was missing. Now raises `PydanticSerializationUnexpectedValue` warning, consistent with the over-filled case.

---

## Bug #2 — Private Attribute Default Factories Cannot Access Validated Data

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Status** | Fixed |
| **Commit** | `0a2cbb7c9` |
| **PR** | [#13013](https://github.com/pydantic/pydantic/pull/13013) |
| **Files** | `pydantic/_internal/_fields.py` · `pydantic/_internal/_model_construction.py` · `pydantic/fields.py` |
| **Lines** | `_fields.py:705–729` · `_model_construction.py:376–382` · `fields.py:1417–1486` |

### Description
`PrivateAttr(default_factory=...)` factories could not receive validated model field data. The factory was always called with zero arguments, making it impossible to compute a private attribute value that depends on already-validated fields.

### Root Cause
`ModelPrivateAttr.get_default()` called factories unconditionally as `self.default_factory()` with no arguments. There was no signature inspection and no mechanism to pass the validated data dict.

```python
# Before fix — fields.py
def get_default(self):
    return smart_deepcopy(self.default) if self.default_factory is None \
        else self.default_factory()  # always 0 args — no access to model data
```

### Fix Applied
Three-part change:

1. **`_fields.py:705–729`** — New `resolve_default_value()` centralises factory dispatch, introspects factory signature via `takes_validated_data_argument()`, and either calls factory with `0` args or with the validated data dict.

2. **`_model_construction.py:376–382`** — `init_private_attributes()` now passes:
   ```python
   validated_data={**self.__dict__, **pydantic_private}
   ```
   This gives later factories visibility into both validated model fields *and* already-initialised private attributes (order-dependent).

3. **`fields.py:1417–1486`** — `ModelPrivateAttr` gains a `default_factory_takes_validated_data` property; `get_default()` delegates to `resolve_default_value()`.

### Example (now works)
```python
class Model(BaseModel):
    name: str
    _slug: str = PrivateAttr(default_factory=lambda data: data['name'].lower().replace(' ', '-'))
```

### Impact
Any model using `PrivateAttr(default_factory=...)` that needed computed values from field data was broken. No workaround existed short of post-init mutation.

---

## Bug #3 — Discriminated Union Serialization Falls Back to Wrong Variant

| Field | Value |
|-------|-------|
| **Severity** | 🔴 Critical |
| **Status** | Fixed |
| **Commit** | `870ebe831` |
| **PR** | [#12825](https://github.com/pydantic/pydantic/pull/12825) |
| **File** | `pydantic-core/src/serializers/type_serializers/union.rs` |
| **Lines** | 261–313 |

### Description
When using a **discriminated union**, if the discriminator correctly selected a variant but that variant's serializer failed, the old code silently fell back to trying **all remaining union members** left-to-right. This violated the discriminator contract and could serialize data as the completely wrong type without any warning.

### Root Cause
The `tagged_union_serialize()` function had a `skip` parameter path that, after a matched-variant failure, retried the entire union membership. The logic was:

1. Use discriminator → select variant N
2. Try variant N strict → fail
3. Try variant N lax → fail
4. **Silently try variant N+1, N+2, … until one succeeds** ← the bug

This "best effort" approach masked serializer bugs and produced incorrect JSON output where an unrelated union member happened to accept the data.

### Fix Applied
Full refactor of `tagged_union_serialize()` (lines 261–313). New invariant: **once a discriminator selects a variant, only that variant is tried.**

| Scenario | Old Behaviour | New Behaviour |
|----------|---------------|---------------|
| Discriminator match + strict success | Correct | Unchanged |
| Discriminator match + strict fail + lax success | Correct | Unchanged |
| Discriminator match + both fail (top-level) | Fallback to all variants 🐛 | Register warning, return `Ok(None)` — inference fallback only |
| Discriminator match + both fail (nested) | Fallback to all variants 🐛 | Propagate error upward |

### Impact
Critical: Users with a bug in one union variant's serializer would get silent type confusion — data serialized as an entirely different union member. The fix makes such failures visible (warning or error).

---

## Bug #4 — MISSING Sentinel Union Members Subject to Wrong Constraints

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Status** | Fixed |
| **Commit** | `94dd544cc` |
| **PR** | [#12908](https://github.com/pydantic/pydantic/pull/12908) |
| **File** | `pydantic/_internal/_generate_schema.py` |
| **Lines** | 2299–2339 |

### Description
Applying constraints (e.g., `Ge(1)`, `Lt(100)`) to a union that included the `MISSING` sentinel caused those constraints to be applied to the MISSING branch as well. This produced semantically invalid schemas and could cause validation errors when MISSING was the intended selected value.

### Root Cause
The constraint pushdown logic in `_generate_schema.py` distributed metadata annotations across all union members indiscriminately. `MISSING` is a sentinel meaning "no value provided" — a numeric minimum constraint on it is nonsensical.

```python
# Before fix — conceptual schema generated for:
# Annotated[Union[int, MISSING], Ge(1)]
{
  "type": "union",
  "choices": [
    {"type": "int", "ge": 1},   # correct
    {"type": "is-instance", "cls": MISSING, "ge": 1}  # wrong — MISSING has no numeric value
  ]
}
```

### Fix Applied
Constraint pushdown now separates MISSING from the union before applying metadata (lines 2299–2339):

- **2+ non-MISSING choices:** Apply constraint to sub-union, then reconstruct as `Annotated[non_missing_union, Constraint] | MISSING`
- **1 non-MISSING choice:** Apply constraint directly to that choice, preserve union structure

Also added `iter_union_choices()` utility in `core_schema.py` to safely iterate union choices (handling both bare schemas and labelled tuples), used consistently in `_schema_gather.py` and `json_schema.py`.

### Impact
Optional-with-sentinel patterns (common in partial-update models and PATCH endpoints) would fail validation incorrectly when constraints were present. No workaround without manual schema construction.

---

## Bug #5 — XMLDatatype Design Issues (Session Design Review)

> These were identified during the custom-type implementation guidance in this session.  
> Not bugs in the existing Pydantic codebase — issues in the proposed `XMLDatatype` design.

---

### #5a — ET.ParseError Exception Chaining

| Field | Value |
|-------|-------|
| **Severity** | ✅ None |
| **Status** | Not a bug — confirmed safe |
| **File** | Proposed `pydantic/xml_types.py` |

**Question:** Does `raise ValueError(...) from e` work correctly when `ET.ParseError` inherits from `SyntaxError`?

**Finding:** Safe. `ET.ParseError` → `SyntaxError` → `Exception` → `BaseException`. The `from e` clause uses `BaseException.__cause__`, available on all exceptions. Chain is preserved correctly. Pydantic catches `ValueError` and converts it to `ValidationError` as expected.

---

### #5b — Missing JSON Mode Support

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium (conditional) |
| **Status** | Design gap — fix if JSON round-trip is required |
| **File** | Proposed `pydantic/xml_types.py` |

**Problem:** The proposed schema uses `lax_or_strict_schema()` only. If the type is used in a model that is serialised/deserialised via JSON (e.g., `.model_dump_json()` / `.model_validate_json()`), there is no `json_schema` branch to handle JSON input as a string.

**Recommendation:** Wrap with `json_or_python_schema()` to add an explicit JSON input path:

```python
return core_schema.json_or_python_schema(
    json_schema=core_schema.no_info_plain_validator_function(
        cls._validate,
        serialization=core_schema.to_string_ser_schema(),
    ),
    python_schema=core_schema.lax_or_strict_schema(
        lax_schema=...,
        strict_schema=...,
    ),
)
```

Pattern reference: `_SecretField.__get_pydantic_core_schema__` — `pydantic/types.py:1757–1794`.

---

### #5c — to_string_ser_schema() Round-Trip Fidelity

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Status** | Design concern — verify against requirements |
| **File** | Proposed `pydantic/xml_types.py` |

**Problem:** `to_string_ser_schema()` calls `__str__()` on the object. For an `ET.Element`, the proposed `__str__` returns the raw input string stored at construction time. This is safe only if the input is stored verbatim. If `ET.fromstring()` normalises the XML (e.g., reorders attributes, strips comments, collapses whitespace), then the stored `_xml` field and the parsed `_element` may diverge.

**Potential data loss scenarios:**
- XML declaration attributes (`encoding`, `version`) stripped by `ET.fromstring()`
- Namespace prefix remapping
- Processing instructions / comments dropped
- Whitespace normalisation in text nodes

**Recommendation:** Derive the serialised form from the *parsed* element, not the raw input:

```python
def __str__(self) -> str:
    return ET.tostring(self._element, encoding='unicode')
```

This ensures the serialised form is always consistent with the parsed structure.

---

## Summary

| ID | PR / Source | File | Severity | Status |
|----|-------------|------|----------|--------|
| #1 | #13016 | `tuple.rs:214–220` | 🟡 Medium | Fixed in `46dea9288` |
| #2 | #13013 | `_fields.py:705–729`, `_model_construction.py:376–382`, `fields.py:1417–1486` | 🟠 High | Fixed in `0a2cbb7c9` |
| #3 | #12825 | `union.rs:261–313` | 🔴 Critical | Fixed in `870ebe831` |
| #4 | #12908 | `_generate_schema.py:2299–2339` | 🟡 Medium | Fixed in `94dd544cc` |
| #5a | Session design | Proposed `xml_types.py` | ✅ None | No action needed |
| #5b | Session design | Proposed `xml_types.py` | 🟡 Medium | Add `json_or_python_schema()` wrapper |
| #5c | Session design | Proposed `xml_types.py` | 🔵 Low | Use `ET.tostring()` in `__str__` |

---

## Notes
- Bugs #1–#4 are already fixed in the current `main` branch HEAD (`46dea9288`).
- Bugs #5b and #5c are design recommendations for the `XMLDatatype` custom type proposed during this session — not issues in existing Pydantic code.
- The most impactful historical fix in scope is **#3** (Critical) — silent discriminated-union serialization fallback was a correctness violation that could produce wrong JSON output with no observable error.
