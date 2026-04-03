# Pydantic v2 — End-to-End Execution Trace

## Example Code

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

user = User(name="Alice", age=30)
print(user.model_dump())
# Output: {'name': 'Alice', 'age': 30}
```

---

## Overview: Four Phases

| Phase | Trigger | Happens |
|-------|---------|---------|
| **1. Import** | `from pydantic import BaseModel` | Once per interpreter session |
| **2. Class definition** | `class User(BaseModel): ...` | Once per class, at import time |
| **3. Instantiation / Validation** | `User(name="Alice", age=30)` | Every call |
| **4. Serialization** | `user.model_dump()` | Every call |

---

## Phase 1 — Import (`from pydantic import BaseModel`)

### File: `pydantic/__init__.py`

**Line 249** — The `_dynamic_imports` dict declares lazy mappings for every public symbol:

```python
_dynamic_imports: 'dict[str, tuple[str, str]]' = {
    ...
    'BaseModel': (__spec__.parent, '.main'),   # line 292
    ...
}
```

Nothing is imported at module load time. The mapping just records *where* each name lives.

**Lines 425–452** — `__getattr__` implements the lazy-load protocol:

```python
def __getattr__(attr_name: str) -> object:      # line 425
    dynamic_attr = _dynamic_imports.get(attr_name)  # line 435
    if dynamic_attr is None:
        return _getattr_migration(attr_name)

    package, module_name = dynamic_attr
    module = import_module(module_name, package=package)  # line 446  → imports pydantic.main
    result = getattr(module, attr_name)                   # line 447  → grabs BaseModel class
    # cache all siblings from the same module in globals() (line 449-451)
    ...
    return result
```

**State after Phase 1:**
- `pydantic.main` module is now loaded.
- `BaseModel` class object is cached in `pydantic.__dict__` for subsequent imports.

---

## Phase 2 — Class Definition (`class User(BaseModel): name: str; age: int`)

Python's class machinery calls `ModelMetaclass.__new__` because `BaseModel`'s metaclass is `ModelMetaclass`.

### Step 2A — `ModelMetaclass.__new__`
**File:** `pydantic/_internal/_model_construction.py`
**Lines 84–262**

```
ModelMetaclass.__new__(mcs, "User", (BaseModel,), namespace)
```

Key actions in order:

| Line | Action |
|------|--------|
| 127 | `raw_annotations = namespace.get('__annotations__', {})` → `{'name': str, 'age': int}` |
| 129 | `mcs._collect_bases_data(bases)` — gather inherited field names, class vars, private attrs |
| 131 | `config_wrapper = ConfigWrapper.for_model(bases, namespace, raw_annotations, kwargs)` |
| 133–135 | `inspect_namespace(...)` — scan for `PrivateAttr` declarations |
| 156 | `cls = super().__new__(mcs, "User", (BaseModel,), namespace)` — **actual class object created** |
| 169 | `cls.__pydantic_custom_init__ = False` (User doesn't override `__init__`) |
| 174 | `cls.__pydantic_setattr_handlers__ = {}` |
| 176 | `cls.__pydantic_decorators__ = DecoratorInfos.build(cls, ...)` — collect `@field_validator` etc. |
| 228 | `cls.__pydantic_complete__ = False` — marks build in progress |
| 241 | `ns_resolver = NsResolver(parent_namespace=...)` — for resolving forward references |
| 243 | `set_model_fields(cls, config_wrapper, ns_resolver)` — **→ Step 2B** |
| 256–262 | `complete_model_class(cls, config_wrapper, ns_resolver, raise_errors=False)` — **→ Step 2C** |

---

### Step 2B — `set_model_fields`
**File:** `pydantic/_internal/_model_construction.py`
**Lines 566–598**

```python
def set_model_fields(cls, config_wrapper, ns_resolver):   # line 566
    typevars_map = get_model_typevars_map(cls)
    fields, pydantic_extra_info, class_vars = collect_model_fields(  # line 579  → Step 2C
        cls, config_wrapper, ns_resolver, typevars_map=typevars_map
    )
    cls.__pydantic_fields__ = fields          # line 583  ← key assignment
    cls.__pydantic_extra_info__ = pydantic_extra_info
    cls.__class_vars__.update(class_vars)
```

---

### Step 2C — `collect_model_fields`
**File:** `pydantic/_internal/_fields.py`
**Lines 224–382** (relevant excerpt)

```python
def collect_model_fields(cls, config_wrapper, ns_resolver, *, typevars_map=None):  # line 224

    type_hints = _typing_extra.get_model_type_hints(cls, ns_resolver=ns_resolver)  # line 265
    # → {'name': (str, True), 'age': (int, True)}

    fields: dict[str, FieldInfo] = {}      # line 270

    for ann_name, (ann_type, evaluated) in type_hints.items():   # line 273
        # e.g. ann_name='name', ann_type=str

        assigned_value = getattr(cls, ann_name, PydanticUndefined)   # line 291
        # → PydanticUndefined (no default given)

        if assigned_value is PydanticUndefined:      # line 342
            field_info = FieldInfo_.from_annotation(ann_type, _source=AnnotationSource.CLASS)
            # line 349  → Step 2D
            field_info._original_annotation = ann_type   # line 350
```

Loop runs twice: once for `name: str`, once for `age: int`.

---

### Step 2D — `FieldInfo.from_annotation`
**File:** `pydantic/fields.py`
**Lines 319–373**

```python
@staticmethod
def from_annotation(annotation, *, _source=AnnotationSource.ANY):   # line 319

    inspected_ann = inspect_annotation(           # line 353
        annotation,
        annotation_source=_source,
        unpack_type_aliases='skip',
    )
    # For `str`: inspected_ann.type=str, inspected_ann.metadata=[], inspected_ann.qualifiers=set()

    type_expr = inspected_ann.type               # line 366  → str
    final = 'final' in inspected_ann.qualifiers   # line 367  → False
    metadata = inspected_ann.metadata             # line 368  → []

    field_info = FieldInfo._construct(metadata, annotation=type_expr)  # line 373
    # → FieldInfo(annotation=str, default=PydanticUndefined, metadata=[], is_required=True)
```

**Objects created:**
```
User.__pydantic_fields__ = {
    'name': FieldInfo(annotation=str,  default=PydanticUndefined, is_required=True),
    'age':  FieldInfo(annotation=int,  default=PydanticUndefined, is_required=True),
}
```

---

### Step 2E — `complete_model_class`
**File:** `pydantic/_internal/_model_construction.py`
**Lines 600–721**

```python
def complete_model_class(cls, config_wrapper, ns_resolver, ...):   # line 600

    gen_schema = GenerateSchema(          # line 660
        config_wrapper,
        ns_resolver,
        typevars_map,
    )

    schema = gen_schema.generate_schema(cls)   # line 667  → Step 2F

    core_config = config_wrapper.core_config(title=cls.__name__)   # line 674

    schema = gen_schema.clean_schema(schema)   # line 677

    cls.__pydantic_core_schema__ = schema      # line 688  ← stored on class

    cls.__pydantic_validator__ = create_schema_validator(   # line 690
        schema, cls, cls.__module__, cls.__qualname__,
        'BaseModel', core_config, config_wrapper.plugin_settings,
        _use_prebuilt=True,
    )
    # → SchemaValidator (Rust object)

    cls.__pydantic_serializer__ = SchemaSerializer(    # line 700
        schema, core_config, _use_prebuilt=True
    )
    # → SchemaSerializer (Rust object)

    cls.__pydantic_complete__ = True     # line 716
```

---

### Step 2F — `GenerateSchema.generate_schema` + `_model_schema`
**File:** `pydantic/_internal/_generate_schema.py`

#### `generate_schema` — Lines 717–754

```python
def generate_schema(self, obj):          # line 717
    schema = self._generate_schema_from_get_schema_method(obj, obj)   # line 741
    # → None for plain BaseModel subclass (no custom __get_pydantic_core_schema__)

    if schema is None:
        schema = self._generate_schema_inner(obj)   # line 744
        # → dispatches to _model_schema(cls) because obj is a BaseModel subclass
    ...
    return schema
```

#### `_model_schema` — Lines 756–883

```python
def _model_schema(self, cls):     # line 756

    fields = getattr(cls, '__pydantic_fields__', {})   # line 780
    # → {'name': FieldInfo(str), 'age': FieldInfo(int)}

    # For each field, build a field-level CoreSchema (line 857–866):
    fields_schema = core_schema.model_fields_schema(
        {
          'name': self._generate_md_field_schema('name', field_info_name, decorators),
          # → core_schema.model_field(core_schema.str_schema(), required=True)
          'age':  self._generate_md_field_schema('age',  field_info_age,  decorators),
          # → core_schema.model_field(core_schema.int_schema(), required=True)
        },
        ...
        model_name='User',
    )                              # line 857–866

    model_schema = core_schema.model_schema(   # line 870
        cls,
        fields_schema,
        custom_init=False,
        root_model=False,
        post_init=None,
        config=core_config,
        ref=model_ref,
    )
    # → CoreSchema dict: {'type': 'model', 'cls': User, 'schema': fields_schema, ...}
```

**State after Phase 2 — class attributes set on `User`:**

| Attribute | Type | Value |
|-----------|------|-------|
| `User.__pydantic_fields__` | `dict[str, FieldInfo]` | `{'name': FieldInfo(str), 'age': FieldInfo(int)}` |
| `User.__pydantic_core_schema__` | `CoreSchema` (dict) | `{'type': 'model', 'cls': User, ...}` |
| `User.__pydantic_validator__` | `SchemaValidator` (Rust) | compiled validator tree |
| `User.__pydantic_serializer__` | `SchemaSerializer` (Rust) | compiled serializer tree |
| `User.__pydantic_complete__` | `bool` | `True` |
| `User.__pydantic_custom_init__` | `bool` | `False` |
| `User.__pydantic_decorators__` | `DecoratorInfos` | empty (no validators declared) |

---

## Phase 3 — Instantiation / Validation (`user = User(name="Alice", age=30)`)

### `BaseModel.__init__`
**File:** `pydantic/main.py`
**Lines 253–273**

```python
def __init__(self, /, **data: Any) -> None:   # line 253
    # data = {'name': 'Alice', 'age': 30}

    __tracebackhide__ = True    # line 262  (hides this frame from pytest tracebacks)

    validated_self = self.__pydantic_validator__.validate_python(   # line 263
        data,
        self_instance=self,
    )
    # self.__pydantic_validator__  →  SchemaValidator compiled from User's CoreSchema
    # .validate_python()           →  pydantic-core Rust call (no Python source)
```

### Inside `SchemaValidator.validate_python` (Rust, `pydantic-core`)

This is compiled Rust code (not in this repo). Conceptually it executes the validator tree built from the CoreSchema:

```
model_schema(User)
  └── model_fields_schema
        ├── field 'name' → str_schema
        │     input: 'Alice' (str) → passes → 'Alice'
        └── field 'age'  → int_schema
              input: 30 (int)   → passes → 30
```

With `self_instance=self`, the validator writes directly into the instance's `__dict__` and sets `__pydantic_fields_set__` without creating an intermediate dict object.

**State after Phase 3 — instance attributes set on `user`:**

| Attribute | Value |
|-----------|-------|
| `user.__dict__` | `{'name': 'Alice', 'age': 30}` |
| `user.__pydantic_fields_set__` | `{'name', 'age'}` |
| `user.__pydantic_extra__` | `None` |
| `user.__pydantic_private__` | `None` |

---

## Phase 4 — Serialization (`user.model_dump()`)

### `BaseModel.model_dump`
**File:** `pydantic/main.py`
**Lines 427–491**

```python
def model_dump(                          # line 427
    self,
    *,
    mode: Literal['json', 'python'] | str = 'python',
    include: IncEx | None = None,
    exclude: IncEx | None = None,
    context: Any | None = None,
    by_alias: bool | None = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
    exclude_computed_fields: bool = False,
    round_trip: bool = False,
    warnings: bool | ... = True,
    fallback: Callable | None = None,
    serialize_as_any: bool = False,
    polymorphic_serialization: bool | None = None,
) -> dict[str, Any]:

    return self.__pydantic_serializer__.to_python(   # line 475
        self,
        mode=mode,                          # 'python'
        by_alias=by_alias,                  # None
        include=include,                    # None → all fields
        exclude=exclude,                    # None → nothing excluded
        context=context,                    # None
        exclude_unset=exclude_unset,        # False
        exclude_defaults=exclude_defaults,  # False
        exclude_none=exclude_none,          # False
        exclude_computed_fields=exclude_computed_fields,  # False
        round_trip=round_trip,              # False
        warnings=warnings,                  # True
        fallback=fallback,                  # None
        serialize_as_any=serialize_as_any,  # False
        polymorphic_serialization=polymorphic_serialization,  # None
    )                                       # line 491
```

### Inside `SchemaSerializer.to_python` (Rust, `pydantic-core`)

Iterates over the compiled serializer tree (mirror of the validator):

```
model_schema(User)
  └── model_fields_schema
        ├── field 'name' → str → 'Alice'
        └── field 'age'  → int → 30
```

Returns: `{'name': 'Alice', 'age': 30}`

---

## Complete Call Stack Summary

```
from pydantic import BaseModel
│
└── pydantic/__init__.py:425  __getattr__('BaseModel')
    └── pydantic/__init__.py:446  import_module('.main', 'pydantic')
        └── returns BaseModel class


class User(BaseModel): name: str; age: int
│
└── pydantic/_internal/_model_construction.py:84   ModelMetaclass.__new__
    ├── :127  read raw_annotations = {'name': str, 'age': int}
    ├── :129  _collect_bases_data(bases)
    ├── :131  ConfigWrapper.for_model(...)
    ├── :156  super().__new__()  ← User class object created
    ├── :176  DecoratorInfos.build(cls)
    ├── :228  cls.__pydantic_complete__ = False
    ├── :243  set_model_fields(cls, ...)
    │   └── pydantic/_internal/_model_construction.py:566  set_model_fields
    │       └── pydantic/_internal/_fields.py:224  collect_model_fields
    │           ├── :265  get_model_type_hints → {'name': str, 'age': int}
    │           ├── :273  loop over type hints
    │           │   ├── 'name': :349  FieldInfo.from_annotation(str)
    │           │   │   └── pydantic/fields.py:319  from_annotation
    │           │   │       ├── :353  inspect_annotation(str)
    │           │   │       ├── :366  type_expr = str
    │           │   │       └── :373  FieldInfo._construct([], annotation=str)
    │           │   └── 'age':  :349  FieldInfo.from_annotation(int)
    │           │       └── pydantic/fields.py:319  (same path, int)
    │           └── returns {'name': FieldInfo(str), 'age': FieldInfo(int)}
    │       └── :583  cls.__pydantic_fields__ = fields
    └── :256  complete_model_class(cls, ...)
        └── pydantic/_internal/_model_construction.py:600  complete_model_class
            ├── :660  GenerateSchema(config_wrapper, ns_resolver, ...)
            ├── :667  gen_schema.generate_schema(User)
            │   └── pydantic/_internal/_generate_schema.py:717  generate_schema
            │       ├── :741  _generate_schema_from_get_schema_method → None
            │       └── :744  _generate_schema_inner(User)
            │           └── :756  _model_schema(User)
            │               ├── :780  fields = cls.__pydantic_fields__
            │               ├── :857  model_fields_schema({'name': str_schema, 'age': int_schema})
            │               └── :870  core_schema.model_schema(User, fields_schema, ...)
            ├── :674  core_config = config_wrapper.core_config(title='User')
            ├── :677  gen_schema.clean_schema(schema)
            ├── :688  cls.__pydantic_core_schema__ = schema
            ├── :690  cls.__pydantic_validator__ = SchemaValidator(schema, ...)   ← Rust
            ├── :700  cls.__pydantic_serializer__ = SchemaSerializer(schema, ...) ← Rust
            └── :716  cls.__pydantic_complete__ = True


user = User(name="Alice", age=30)
│
└── pydantic/main.py:253  BaseModel.__init__(self, **{'name': 'Alice', 'age': 30})
    └── :263  self.__pydantic_validator__.validate_python(data, self_instance=self)
        └── pydantic-core (Rust) SchemaValidator.validate_python
            ├── field 'name': str_validator('Alice') → 'Alice'  ✓
            ├── field 'age':  int_validator(30)       → 30      ✓
            └── writes {'name': 'Alice', 'age': 30} into self.__dict__
                sets self.__pydantic_fields_set__ = {'name', 'age'}


user.model_dump()
│
└── pydantic/main.py:427  BaseModel.model_dump(self, mode='python', ...)
    └── :475  self.__pydantic_serializer__.to_python(self, mode='python', ...)
        └── pydantic-core (Rust) SchemaSerializer.to_python
            ├── field 'name': 'Alice' (str) → 'Alice'
            ├── field 'age':  30 (int)      → 30
            └── returns {'name': 'Alice', 'age': 30}
```

---

## Key File Reference Table

| File | Lines | Role in trace |
|------|-------|---------------|
| `pydantic/__init__.py` | 249, 292, 425–452 | Lazy import facade; `__getattr__` → `_dynamic_imports` |
| `pydantic/main.py` | 119 | `BaseModel` class declaration (metaclass=ModelMetaclass) |
| `pydantic/main.py` | 253–273 | `BaseModel.__init__` → `validate_python` |
| `pydantic/main.py` | 427–491 | `BaseModel.model_dump` → `to_python` |
| `pydantic/_internal/_model_construction.py` | 84–262 | `ModelMetaclass.__new__` — orchestrates class creation |
| `pydantic/_internal/_model_construction.py` | 566–598 | `set_model_fields` → sets `__pydantic_fields__` |
| `pydantic/_internal/_model_construction.py` | 600–721 | `complete_model_class` → creates validator & serializer |
| `pydantic/_internal/_fields.py` | 224–382 | `collect_model_fields` — iterates annotations → FieldInfo |
| `pydantic/fields.py` | 319–373 | `FieldInfo.from_annotation` — builds FieldInfo from bare type |
| `pydantic/_internal/_generate_schema.py` | 717–754 | `generate_schema` — dispatch to type-specific schema builder |
| `pydantic/_internal/_generate_schema.py` | 756–883 | `_model_schema` — builds CoreSchema from fields |
| `pydantic-core` (Rust) | N/A | `SchemaValidator.validate_python`, `SchemaSerializer.to_python` |
