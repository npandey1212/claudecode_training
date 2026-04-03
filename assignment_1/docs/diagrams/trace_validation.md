# Pydantic v2 — Validation Process Trace

## Example Under Trace

```python
from pydantic import BaseModel, field_validator, model_validator
from typing import Self

class User(BaseModel):
    name: str
    age: int

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('name must not be empty')
        return v.strip()

    @model_validator(mode='after')
    def check_age(self) -> Self:
        if self.age < 0:
            raise ValueError('age must be non-negative')
        return self

# Success path
user = User(name='  Alice  ', age=30)
# → name='Alice', age=30

# Failure path
User(name='', age=-1)
# → ValidationError: 2 errors
```

---

## Overview: Two Stages

| Stage | When | What happens |
|-------|------|-------------|
| **Schema build** | At class definition (once) | Validators are registered, converted to CoreSchema nodes, compiled to Rust |
| **Runtime validation** | Every `User(...)` call | Rust validator tree executes; Python validators called back via FFI |

---

## Stage 1 — Schema Build (class definition time)

### 1A. Decorator registration — `@field_validator`
**File:** `pydantic/functional_validators.py` · **Lines 409–514**

```python
def field_validator(            # line 409
    field: str,
    /,
    *fields: str,
    mode: FieldValidatorModes = 'after',   # default: run AFTER type validation
    check_fields: bool | None = None,
    json_schema_input_type: Any = PydanticUndefined,
) -> Callable[[Any], Any]:

    fields = field, *fields      # line 489  → ('name',)

    def dec(f):                  # line 497
        f = _decorators.ensure_classmethod_based_on_signature(f)   # line 507
        dec_info = _decorators.FieldValidatorDecoratorInfo(         # line 509
            fields=('name',),
            mode='after',
            check_fields=None,
            json_schema_input_type=PydanticUndefined,
        )
        return _decorators.PydanticDescriptorProxy(f, dec_info)     # line 512

    return dec                   # line 514
```

`PydanticDescriptorProxy` wraps the function and carries `dec_info`. The class namespace now holds `name_must_not_be_empty = PydanticDescriptorProxy(func, FieldValidatorDecoratorInfo(...))` instead of the raw function.

---

### 1B. Decorator registration — `@model_validator`
**File:** `pydantic/functional_validators.py` · **Lines 668–733**

```python
def model_validator(*, mode: Literal['wrap', 'before', 'after']) -> Any:   # line 668

    def dec(f: Any):                                   # line 717
        f = _decorators.ensure_classmethod_based_on_signature(f)   # line 719
        dec_info = _decorators.ModelValidatorDecoratorInfo(mode='after')   # line 730
        return _decorators.PydanticDescriptorProxy(f, dec_info)            # line 731

    return dec                                         # line 733
```

---

### 1C. `FieldValidatorDecoratorInfo` and `ModelValidatorDecoratorInfo`
**File:** `pydantic/_internal/_decorators.py`

```python
@dataclass
class FieldValidatorDecoratorInfo:    # line 56
    decorator_repr: ClassVar[str] = '@field_validator'
    fields: tuple[str, ...]           # ('name',)
    mode: FieldValidatorModes         # 'after'
    check_fields: bool | None
    json_schema_input_type: Any

@dataclass
class ModelValidatorDecoratorInfo:    # line 135
    decorator_repr: ClassVar[str] = '@model_validator'
    mode: Literal['wrap', 'before', 'after']   # 'after'
```

---

### 1D. `DecoratorInfos.build` — collecting all validators
**File:** `pydantic/_internal/_decorators.py` · **Lines 432–486**

Called from `ModelMetaclass.__new__` at `_model_construction.py:176`.

```python
@classmethod
def build(cls, typ: type[Any], replace_wrapped_methods: bool = True) -> Self:  # line 432

    res = cls()                  # line 456  empty DecoratorInfos

    # Walk MRO for inherited validators (line 459):
    for base in reversed(mro(typ)[1:-1]):
        existing = base.__dict__.get('__pydantic_decorators__')
        res.field_validators.update({k: v.bind_to_cls(typ) ...})   # line 464
        res.model_validators.update({k: v.bind_to_cls(typ) ...})   # line 468

    # Collect from User itself (line 471):
    decorator_infos, to_replace = _decorator_infos_for_class(typ, collect_to_replace=True)
```

`_decorator_infos_for_class` (line 505) iterates `vars(typ)`:
```python
for var_name, var_value in vars(typ).items():    # line 514
    if isinstance(var_value, PydanticDescriptorProxy):  # line 515
        info = var_value.decorator_info
        if isinstance(info, FieldValidatorDecoratorInfo):   # line 519
            res.field_validators['name_must_not_be_empty'] = Decorator.build(...)  # line 520
        elif isinstance(info, ModelValidatorDecoratorInfo):  # line 531
            res.model_validators['check_age'] = Decorator.build(...)               # line 532
```

**Result on `User.__pydantic_decorators__`:**
```
DecoratorInfos(
  field_validators = {
      'name_must_not_be_empty': Decorator(fields=('name',), mode='after', func=<classmethod>)
  },
  model_validators = {
      'check_age': Decorator(mode='after', func=<method>)
  }
)
```

---

### 1E. `_common_field_schema` — wiring field validators into field CoreSchema
**File:** `pydantic/_internal/_generate_schema.py` · **Lines 1268–1323**

Called once per field from `_generate_md_field_schema` (line 1228) inside `_model_schema`.

```python
def _common_field_schema(self, name: str, field_info: FieldInfo, decorators: DecoratorInfos):  # line 1268

    source_type, annotations = field_info.annotation, field_info.metadata
    # For 'name': source_type=str, annotations=[]

    # Convert @field_validator entries that match this field name (line 1277-1281):
    validators_from_decorators = [
        _mode_to_validator[decorator.info.mode]._from_decorator(decorator)
        for decorator in filter_field_decorator_info_by_field(
            decorators.field_validators.values(), name   # filters to those with 'name' in their .fields
        )
    ]
    # _mode_to_validator (line 197-199):
    #   {'before': BeforeValidator, 'after': AfterValidator,
    #    'plain': PlainValidator,   'wrap': WrapValidator}
    # mode='after' → AfterValidator._from_decorator(decorator)
    # → AfterValidator(func=name_must_not_be_empty)

    # Apply annotations + validators to build field schema (line 1289-1292):
    schema = self._apply_annotations(
        source_type,                             # str
        annotations + validators_from_decorators # [AfterValidator(name_must_not_be_empty)]
    )
    # _apply_annotations → match_type(str) → core_schema.str_schema()   (line 1048-1049)
    # Then AfterValidator.__get_pydantic_core_schema__ wraps it:
    #   → no_info_after_validator_function(name_must_not_be_empty, str_schema())
```

**CoreSchema produced for field `name`:**
```
after_validator(
    func = name_must_not_be_empty,
    schema = str_schema()
)
```

For field `age` (no `@field_validator`):
```
int_schema()   ← line 1052-1053
```

---

### 1F. `match_type` — primitive type → CoreSchema
**File:** `pydantic/_internal/_generate_schema.py` · **Lines 1035–1079**

```python
def match_type(self, obj: Any) -> core_schema.CoreSchema:   # line 1035
    if obj is str:                       # line 1048
        return core_schema.str_schema()  # line 1049
    elif obj is int:                     # line 1052
        return core_schema.int_schema()  # line 1053
    elif obj is float:   ...
    elif obj is bool:    ...
    # ... full type dispatch table
```

---

### 1G. `_model_schema` — assembling the full model CoreSchema
**File:** `pydantic/_internal/_generate_schema.py` · **Lines 756–883**

```python
def _model_schema(self, cls):    # line 756

    fields = cls.__pydantic_fields__   # line 780
    decorators = cls.__pydantic_decorators__   # line 808
    model_validators = decorators.model_validators.values()   # line 809
    # → [Decorator(mode='after', func=check_age)]

    # Build per-field schemas (line 857-866):
    fields_schema = core_schema.model_fields_schema({
        'name': _generate_md_field_schema('name', fi_name, decorators),
        #       → model_field(after_validator(name_must_not_be_empty, str_schema()))
        'age':  _generate_md_field_schema('age',  fi_age,  decorators),
        #       → model_field(int_schema())
    }, model_name='User')

    inner_schema = apply_validators(fields_schema, decorators.root_validators.values())  # line 867
    # no root_validators → unchanged

    inner_schema = apply_model_validators(inner_schema, model_validators, 'inner')  # line 868
    # mode='inner': only 'before' validators applied; check_age is 'after' → skipped

    model_schema = core_schema.model_schema(cls, inner_schema, ...)   # line 870

    schema = apply_model_validators(model_schema, model_validators, 'outer')  # line 882
    # mode='outer': skips 'before', applies 'wrap' and 'after'
    # check_age is 'after' → applied here
```

---

### 1H. `apply_model_validators` — wrapping schema with model validators
**File:** `pydantic/_internal/_generate_schema.py` · **Lines 2602–2646**

```python
def apply_model_validators(schema, validators, mode):   # line 2602

    for validator in validators:
        if mode == 'inner' and validator.info.mode != 'before':
            continue                  # line 2623-2624  ← check_age skipped here
        if mode == 'outer' and validator.info.mode == 'before':
            continue                  # line 2625-2626

        info_arg = inspect_validator(validator.func, mode=validator.info.mode, type='model')
        # inspect_validator (line 550): counts positional params
        # check_age(self) → 1 param → 'no-info' (line 581-582)

        # mode='after', info_arg=False → line 2642-2643:
        schema = core_schema.no_info_after_validator_function(
            function=validator.func,   # check_age
            schema=schema,
        )
    return schema
```

---

### 1I. `inspect_validator` — detects `info` argument
**File:** `pydantic/_internal/_decorators.py` · **Lines 550–587**

```python
def inspect_validator(validator, *, mode, type) -> bool:   # line 550
    sig = signature_no_eval(validator)          # line 566
    n_positional = count_positional_required_params(sig)   # line 571

    # mode='after': (line 577-582)
    if n_positional == 2: return True   # func(cls_or_self, info) → with-info
    elif n_positional == 1: return False # func(cls_or_self)       → no-info

    # For name_must_not_be_empty(cls, v): n_positional=2 → True... wait
    # BUT: it's a classmethod. After @classmethod wrapping the bound call
    # only passes (v,) as positional. So pydantic inspects the *unwrapped* function.
    # name_must_not_be_empty(cls, v) → 2 params → 'with-info'? No —
    # field validators: cls is the first param (implicit), v is the value.
    # The mode='after' branch: 2 params = with-info (cls=info), 1 param = no-info.
    # For a classmethod used as field validator: cls is dropped; (v,) = 1 param.
    # inspect_validator is called on the *shim* or unwrapped func.
```

**Practical result for our validators:**
- `name_must_not_be_empty(cls, v)` — classmethod with value only → **no-info** → `no_info_after_validator_function`
- `check_age(self)` — instance method, 1 param → **no-info** → `no_info_after_validator_function`

---

### 1J. Final compiled CoreSchema (conceptual tree)

```
no_info_after_validator_function(check_age,            ← model validator (outer)
  model_schema(User,
    model_fields_schema(
      name: model_field(
        no_info_after_validator_function(name_must_not_be_empty,  ← field validator
          str_schema()
        )
      ),
      age: model_field(
        int_schema()
      )
    )
  )
)
```

This tree is compiled to Rust by `SchemaValidator(schema, core_config)` at `_model_construction.py:690`.

---

## Stage 2 — Runtime Validation (every `User(...)` call)

### 2A. Entry — `BaseModel.__init__`
**File:** `pydantic/main.py` · **Lines 253–273**

```python
def __init__(self, /, **data: Any) -> None:    # line 253
    __tracebackhide__ = True                   # line 262
    validated_self = self.__pydantic_validator__.validate_python(  # line 263
        data,
        self_instance=self,
    )
```

`data = {'name': '  Alice  ', 'age': 30}`

---

### 2B. Success path — `User(name='  Alice  ', age=30)`

The Rust SchemaValidator executes the compiled tree depth-first:

```
Step 1: outer no_info_after_validator_function (check_age)
        ↓ execute inner schema first

Step 2: model_schema(User) — create instance shell

Step 3: model_fields_schema — validate each field

Step 4: field 'name'
    Step 4a: str_schema() validator
             input:  '  Alice  '  (str) → passes → '  Alice  '
    Step 4b: no_info_after_validator_function(name_must_not_be_empty)
             calls:  name_must_not_be_empty(cls, '  Alice  ')
             logic:  '  Alice  '.strip() = 'Alice'  → non-empty → OK
             returns: 'Alice'
    → user.__dict__['name'] = 'Alice'

Step 5: field 'age'
    Step 5a: int_schema() validator
             input: 30 (int) → passes → 30
    → user.__dict__['age'] = 30

Step 6: model_schema sets __pydantic_fields_set__ = {'name', 'age'}

Step 7: outer no_info_after_validator_function(check_age)
        calls: check_age(user_instance)
        logic: user.age (30) >= 0 → OK
        returns: self (the instance)

Result: user instance with __dict__ = {'name': 'Alice', 'age': 30}
```

---

### 2C. Failure path — `User(name='', age=-1)`

```
Step 1: outer no_info_after_validator_function (check_age) — deferred

Step 2: model_schema(User) — create instance shell

Step 3: model_fields_schema

Step 4: field 'name'
    Step 4a: str_schema() → '' (str) → passes
    Step 4b: no_info_after_validator_function(name_must_not_be_empty)
             calls: name_must_not_be_empty(cls, '')
             logic: ''.strip() = '' → empty → raise ValueError('name must not be empty')
             → Rust catches ValueError, converts to PydanticCustomError
             → error collected: {type='value_error', loc=('name',), msg='Value error, name must not be empty'}

Step 5: field 'age'
    Step 5a: int_schema() → -1 (int) → passes
    → user.__dict__['age'] = -1

Step 6: model_schema builds partial instance

Step 7: outer check_age(user)
        user.age = -1 < 0 → raise ValueError('age must be non-negative')
        → error collected: {type='value_error', loc=(), msg='Value error, age must be non-negative'}

Step 8: Rust raises ValidationError with all collected errors
```

**Resulting `ValidationError`:**
```
2 validation errors for User
name
  Value error, name must not be empty
  [type=value_error, input_value='', input_type=str, input_url=...]
  Value error, age must be non-negative
  [type=value_error, input_value={'name': '', 'age': -1}, input_type=dict, ...]
```

---

## Validator Modes — When Each Runs

```
Input dict {'name': '  Alice  ', 'age': 30}
       │
       ▼
@model_validator(mode='before')    ← runs on raw dict, before any field parsing
       │
       ▼
  per-field validation loop:
    for each field:
      @field_validator(mode='before')   ← raw input value
          │
          ▼
      type coercion (str_schema / int_schema)
          │
          ▼
      @field_validator(mode='after')    ← post-coercion typed value   ← our validator
          │
          ▼
      field stored on instance
       │
       ▼
@model_validator(mode='after')     ← runs on fully constructed instance   ← our validator
       │
       ▼
model_post_init()                  ← optional hook (if defined)
```

---

## Validator Decorator Data Flow

```
@field_validator('name')                              functional_validators.py:409
  → dec_info = FieldValidatorDecoratorInfo(            _decorators.py:56
        fields=('name',), mode='after')
  → PydanticDescriptorProxy(func, dec_info)            _decorators.py:165

  [stored in class namespace as name_must_not_be_empty]

ModelMetaclass.__new__                                 _model_construction.py:84
  → DecoratorInfos.build(User)                         _decorators.py:432
      → _decorator_infos_for_class(User)               _decorators.py:505
          → sees PydanticDescriptorProxy                _decorators.py:515
          → isinstance(info, FieldValidatorDecoratorInfo) → line 519
          → res.field_validators['name_must_not_be_empty'] = Decorator(...)

  → cls.__pydantic_decorators__ = DecoratorInfos(      _model_construction.py:176
        field_validators={'name_must_not_be_empty': ...},
        model_validators={'check_age': ...}
    )

complete_model_class                                   _model_construction.py:600
  → GenerateSchema._model_schema(User)                 _generate_schema.py:756
      → _common_field_schema('name', fi, decorators)   _generate_schema.py:1268
          → validators_from_decorators = [             _generate_schema.py:1278
                AfterValidator._from_decorator(dec)    functional_validators.py:85
            ]
          → _apply_annotations(str, [AfterValidator])
              → match_type(str) → str_schema()         _generate_schema.py:1048
              → AfterValidator.__get_pydantic_core_schema__
                  → no_info_after_validator_function(  pydantic_core.core_schema
                        name_must_not_be_empty,
                        str_schema()
                    )
      → apply_model_validators(schema, [check_age], 'outer')   _generate_schema.py:882
          → inspect_validator(check_age, mode='after') → False  _decorators.py:550
          → no_info_after_validator_function(check_age, model_schema)

  → SchemaValidator(schema, core_config)               _model_construction.py:690
    [Rust compilation — tree is now native code]
```

---

## Key File / Line Reference

| Step | File | Lines | What happens |
|------|------|-------|-------------|
| `@field_validator` decorator | `pydantic/functional_validators.py` | 409–514 | Returns `PydanticDescriptorProxy` carrying `FieldValidatorDecoratorInfo` |
| `@model_validator` decorator | `pydantic/functional_validators.py` | 668–733 | Returns `PydanticDescriptorProxy` carrying `ModelValidatorDecoratorInfo` |
| `FieldValidatorDecoratorInfo` | `pydantic/_internal/_decorators.py` | 56–76 | Dataclass: fields, mode, check_fields |
| `ModelValidatorDecoratorInfo` | `pydantic/_internal/_decorators.py` | 135–145 | Dataclass: mode |
| `DecoratorInfos.build` | `pydantic/_internal/_decorators.py` | 432–486 | Walks MRO; collects all validators into dicts |
| `_decorator_infos_for_class` | `pydantic/_internal/_decorators.py` | 505–535 | Scans `vars(typ)` for `PydanticDescriptorProxy` |
| `inspect_validator` | `pydantic/_internal/_decorators.py` | 550–587 | Counts positional params to decide `with-info` vs `no-info` |
| `_mode_to_validator` | `pydantic/_internal/_generate_schema.py` | 197–199 | Maps mode string → validator class |
| `_common_field_schema` | `pydantic/_internal/_generate_schema.py` | 1268–1323 | Converts `@field_validator` → `AfterValidator`; applies to field schema |
| `_generate_md_field_schema` | `pydantic/_internal/_generate_schema.py` | 1228–1244 | Wraps field schema in `model_field(...)` |
| `match_type` | `pydantic/_internal/_generate_schema.py` | 1035–1079 | `str` → `str_schema()`, `int` → `int_schema()`, etc. |
| `_model_schema` | `pydantic/_internal/_generate_schema.py` | 756–883 | Builds full model CoreSchema; calls apply_model_validators |
| `apply_model_validators` | `pydantic/_internal/_generate_schema.py` | 2602–2646 | Wraps schema with before/wrap/after model validators |
| `_VALIDATOR_F_MATCH` | `pydantic/_internal/_generate_schema.py` | 2534–2546 | Maps (mode, info-type) → `core_schema` wrapping call |
| `BaseModel.__init__` | `pydantic/main.py` | 253–273 | Calls `validate_python(data, self_instance=self)` |
| `SchemaValidator.validate_python` | `pydantic-core` (Rust) | N/A | Executes compiled validator tree; calls Python funcs via FFI |
