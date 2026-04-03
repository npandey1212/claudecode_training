# Exploration Log — Pydantic Codebase Session
**Date:** 2026-04-03  
**Model:** claude-sonnet-4-6  
**Branch:** main · HEAD `46dea9288`  
**Working Directory:** `C:\self-study\ai\build\claude_training\repos\pydantic`  
**Session Duration:** Single continuous session (5 prompts)

---

## Session Overview

| # | Time Marker | Prompt | Primary Tool | Artifact |
|---|-------------|--------|--------------|----------|
| 1 | T+00 | How to add XMLDatatype with custom validation | Agent (Explore) | Inline code + explanation |
| 2 | T+01 | HTML visualization: Repo map, Validation flow, Validator order, Type gallery | Agent (Explore) + Write | `diagram/pydantic_viz.html` |
| 3 | T+02 | Top 5 Claude Code tools used across prompts | — (retrospective) | Inline table |
| 4 | T+03 | Create bug-audit.md | Agent (Explore) + Write | `bug-audit.md` |
| 5 | T+04 | Create exploration-log.md (this file) | Write | `exploration-log.md` |

---

## T+00 — XMLDatatype: Adding a Custom Type to Pydantic's Core System

### Prompt
> "How would I add a new XMLDatatype with custom validation to Pydantic's core type system"

### Exploration Performed
Launched **Explore subagent** targeting:
- `pydantic/networks.py` — how URL, Email, IP types implement `__get_pydantic_core_schema__`
- `pydantic/types.py` — Secret, UUID, Path, DateTime custom type patterns
- `pydantic/_internal/_generate_schema.py` — how GenerateSchema dispatches to custom types
- `pydantic/_internal/_schema_generation_shared.py` — CallbackGetCoreSchemaHandler

### Key Findings

| Finding | Location |
|---------|----------|
| All custom types hook in via `__get_pydantic_core_schema__(cls, source, handler)` | Convention across all types |
| `match_type()` dispatches to `_generate_schema_from_get_schema_method()` for non-primitive types | `_generate_schema.py:891, 1035` |
| `CallbackGetCoreSchemaHandler` wraps `_generate_schema_inner` to support nested type resolution | `_schema_generation_shared.py:65–126` |
| Best analogue for XMLDatatype: `IPvAnyAddress` — plain validator + string serializer | `networks.py:1174–1181` |
| `lax_or_strict_schema()` for accepting `str` in lax, rejecting it in strict | `types.py:1757–1794` (_SecretField pattern) |
| `to_string_ser_schema()` for serialising back via `__str__` | `networks.py:1180` |
| Pydantic catches `ValueError` and `AssertionError` in validators and converts to `ValidationError` | Convention |

### Three Core Schema Patterns Identified

```
Pattern A — Plain validator (IPvAnyAddress style):
  no_info_plain_validator_function() + to_string_ser_schema()

Pattern B — Wrap validator (URL types style):
  no_info_wrap_validator_function() + handler callback

Pattern C — Lax/strict split (SecretStr style):
  lax_or_strict_schema(lax=plain_validator, strict=is_instance_schema)
```

### Proposed XMLDatatype Schema
```python
@classmethod
def __get_pydantic_core_schema__(cls, source, handler):
    return core_schema.lax_or_strict_schema(
        lax_schema=core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.to_string_ser_schema(),
        ),
        strict_schema=core_schema.is_instance_schema(
            cls,
            serialization=core_schema.to_string_ser_schema(),
        ),
    )
```

### Design Gap Identified (later confirmed in bug-audit #5b, #5c)
- No JSON mode branch → `model_validate_json()` would fail
- `to_string_ser_schema()` calls `__str__()` on raw input string, not the parsed ET.Element → round-trip divergence risk

---

## T+01 — HTML Visualization: Four-Panel Architecture Reference

### Prompt
> "Create a HTML visualization that covers: Repo map, Validation flow, Validator order & Type system gallery."

### Exploration Performed
Launched **Explore subagent** with four parallel research goals:

**Repo Map research:**
- Top-level directory structure (8 dirs identified)
- `pydantic/` — 11 key files catalogued with purpose and line references
- `pydantic/_internal/` — 8 key files catalogued
- `pydantic-core/` — Rust src + Python bindings

**Validation Flow research:**
- Traced `MyModel(field=value)` → `BaseModel.__init__:253` → `SchemaValidator.validate_python` → Rust engine
- Located `__pydantic_validator__` creation: `_model_construction.py:690`
- Identified `PluggableSchemaValidator` wrapper: `plugin/_schema_validator.py:22–53`
- Confirmed `ValidationError` originates from Rust, re-exported from `pydantic_core`

**Validator Order research:**
- Located `_mode_to_validator` mapping: `_generate_schema.py:197–199`
- Traced field validator application: `_generate_schema.py:1277–1315`
- Found `apply_model_validators()` with 3-mode dispatch: `_generate_schema.py:2602–2646`
- Located `DecoratorInfos` class: `_decorators.py:416–486`

**Type System Gallery research:**
- Catalogued 28 built-in special types across 9 categories
- Mapped each to its `core_schema` builder and file:line

### Key Findings

**Call chain (validation):**
```
BaseModel.__init__ (main.py:253)
  → __pydantic_validator__.validate_python()
    → pydantic_core.SchemaValidator [Rust]
      → walks model_schema tree field-by-field
        → success: return validated instance
        → failure: raise ValidationError
```

**Schema generation happens once (at class definition), not per-call:**
```
ModelMetaclass.__new__
  → GenerateSchema.generate_schema()
    → _generate_schema_inner() (main dispatch, L1007)
      → match_type() (L1035) for primitives
      → _generate_schema_from_get_schema_method() (L891) for custom types
```

**Full validator order (field then model):**
```
1. @model_validator(mode='before')    ← raw dict, before any field
2. @field_validator(mode='before')    ← raw field value
3. @field_validator(mode='wrap')      ← wraps entire field pipeline
4. Type coercion / parsing (Rust)
5. @field_validator(mode='plain')     ← replaces inner schema
6. @field_validator(mode='after')     ← typed Python value
7. @model_validator(mode='wrap')      ← wraps entire model pipeline
8. @model_validator(mode='after')     ← fully-constructed model instance
```

**apply_model_validators() mode logic (`_generate_schema.py:2602`):**
```
mode='inner'  → only 'before' validators
mode='outer'  → all except 'before'
mode='all'    → all validators
```

### Artifact Produced
`diagram/pydantic_viz.html` — 4-tab dark-theme interactive page:
- **Repo Map** tab: top-level tree + 3 file-list cards with badges
- **Validation Flow** tab: 5 collapsible steps + success/error split panel
- **Validator Order** tab: two color-coded timelines + DecoratorInfos box
- **Type Gallery** tab: 28 filterable type cards (9 category filters)

**Technologies:** Vanilla HTML/CSS/JS, zero dependencies, ~1000 lines.

---

## T+02 — Retrospective: Tool Usage Analysis

### Prompt
> "Top 5 Claude Code Tools Used by across the prompts"

### Finding
Only 3 distinct tools were used across the first two prompts:

| Rank | Tool | Uses | Why |
|------|------|------|-----|
| 1 | Agent (Explore subagent) | 2 | Multi-file cross-referencing would have consumed main context |
| 2 | Bash | 2 | Filesystem ops: `ls` (check dir) + `mkdir` (create dir) |
| 3 | Write | 1 | Single large HTML artifact |

**Observation:** The session was Agent-heavy by design — both early prompts needed 20+ file reads across scattered modules. Delegating to Explore subagents preserved main context for synthesis and output generation.

---

## T+03 — Bug Audit: 4 Real Bugs + 3 Design Issues

### Prompt
> "create a bug-audit.md for the bug severity you worked on put all the details"

### Exploration Performed
Launched **Explore subagent** investigating 4 recent commits + 3 XMLDatatype design issues:
- `git log --oneline -20` to identify candidate commits
- Investigated `tuple.rs`, `union.rs` (Rust serializer), `_generate_schema.py`, `_fields.py`, `_model_construction.py`, `fields.py`

### Bugs Found and Documented

#### Bug #1 — Tuple under-fill warning missing
- **Commit:** `46dea9288` · **PR:** #13016
- **Severity:** 🟡 Medium
- **Location:** `pydantic-core/src/serializers/type_serializers/tuple.rs:214–220`
- **Root cause:** Non-variadic tuple loop exited without checking `n_items < self.serializers.len()`
- **Fix:** Added `PydanticSerializationUnexpectedValue` warning matching existing over-fill warning

#### Bug #2 — Private attribute factories can't see validated data
- **Commit:** `0a2cbb7c9` · **PR:** #13013
- **Severity:** 🟠 High
- **Locations:** `_fields.py:705–729`, `_model_construction.py:376–382`, `fields.py:1417–1486`
- **Root cause:** `ModelPrivateAttr.get_default()` called factory with 0 args always
- **Fix:** Added `resolve_default_value()` with signature introspection; passes `{**self.__dict__, **pydantic_private}` to factories that declare a `data` parameter

#### Bug #3 — Discriminated union serialization falls back to wrong variant
- **Commit:** `870ebe831` · **PR:** #12825
- **Severity:** 🔴 Critical
- **Location:** `pydantic-core/src/serializers/type_serializers/union.rs:261–313`
- **Root cause:** `tagged_union_serialize()` `skip` parameter allowed retrying all other union members after discriminator-selected variant failed — silent type confusion
- **Fix:** Refactored to enforce discriminator contract: only the selected variant is ever tried; nested unions propagate errors; top-level registers warning + returns `Ok(None)`

#### Bug #4 — MISSING sentinel inherits constraints from Annotated union
- **Commit:** `94dd544cc` · **PR:** #12908
- **Severity:** 🟡 Medium
- **Location:** `_generate_schema.py:2299–2339`
- **Root cause:** Constraint pushdown applied metadata to all union members including MISSING sentinel
- **Fix:** Added MISSING-aware constraint pushdown; separates MISSING before applying metadata, reconstructs union after

#### Design Issues #5a/5b/5c — XMLDatatype
- **#5a** ✅ None — `ET.ParseError` → `ValueError` chaining is safe; `SyntaxError` still inherits `BaseException`
- **#5b** 🟡 Medium — No JSON mode branch; needs `json_or_python_schema()` wrapper for `model_validate_json()`
- **#5c** 🔵 Low — `to_string_ser_schema()` calls `__str__()` on raw input; should use `ET.tostring(self._element)` for round-trip fidelity

### Artifact Produced
`bug-audit.md` — full severity table, root cause analysis, fix descriptions, and code snippets for all 7 items.

---

## Files Touched This Session

| File | Action | Purpose |
|------|--------|---------|
| `diagram/pydantic_viz.html` | Created | Interactive 4-tab architecture visualization |
| `bug-audit.md` | Created | Severity-graded bug documentation |
| `exploration-log.md` | Created | This file |

---

## Files Read / Explored (via Subagents)

| File | Key Lines Examined |
|------|--------------------|
| `pydantic/main.py` | 204, 253, 694 |
| `pydantic/networks.py` | 70–123, 110–123, 126–343, 313–332, 537+, 572, 663–693, 808–884, 977–1007, 1022–1090, ~1103–1268 |
| `pydantic/types.py` | 150, 237–242, 343–349, 673, 693, 752, 837, 920, 1046, 1183–1267, 1293–1310, 1577, 1752–1804, 1807, 1874, 1925, 2031, 2243, 2273–2354 |
| `pydantic/config.py` | Top-level ConfigDict |
| `pydantic/_internal/_generate_schema.py` | 65–126, 197–199, 891–933, 1007–1033, 1035–1155, 1277–1315, 2299–2339, 2602–2646 |
| `pydantic/_internal/_model_construction.py` | 376–382, 690 |
| `pydantic/_internal/_decorators.py` | 180, 416–486 |
| `pydantic/_internal/_fields.py` | 705–729 |
| `pydantic/_internal/_schema_generation_shared.py` | 65–126 |
| `pydantic/annotated_handlers.py` | 66–123 |
| `pydantic/fields.py` | 1417–1486 |
| `pydantic/plugin/_schema_validator.py` | 22–53 |
| `pydantic-core/python/pydantic_core/core_schema.py` | 605, 644, 706, 773, 889, 961, 1016, 1082, 1152, 1522, 1560, 1712, 1775, 1834, 1967, 2052–2453, 2516–2890, 3006, 3211, 3449, 3921, 3990 |
| `pydantic-core/src/serializers/type_serializers/tuple.rs` | 214–228 |
| `pydantic-core/src/serializers/type_serializers/union.rs` | 261–313 |

---

## Cross-Cutting Observations

### Architecture Insight
Schema generation (`GenerateSchema`) and validation execution (`SchemaValidator`) are deliberately decoupled — generation happens once at class-definition time in Python, execution happens at validation time in Rust. This is why Pydantic v2 is fast: the expensive Python work is amortised over the lifetime of the class.

### Pattern Consistency
Every special type follows one of exactly three patterns:
1. **Annotated alias** — `Annotated[primitive, constraint]` (PositiveInt, StrictStr, UUID variants)
2. **Class with `__get_pydantic_core_schema__`** — custom validator callable (EmailStr, IP types, SecretStr, URL types)
3. **Function returning Annotated** — `conint()`, `constr()`, `condecimal()` for backward compatibility

### Most Impactful Bug
Bug #3 (discriminated union fallback) is the highest severity finding — a **correctness violation** that produced wrong serialized output silently. The other bugs are either missing-warning issues (detectable) or feature limitations (visible at design time).
