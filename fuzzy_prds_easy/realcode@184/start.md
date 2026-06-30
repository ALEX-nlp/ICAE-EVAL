## Product Requirement Document

# Declarative JSON Serialization Engine — Shape Records into Wire-Ready JSON Documents

## Project Goal

Build a declarative serialization engine that turns in-memory records into JSON documents according to a per-r[a list of predicates defined in the spec]uest specification, so developers can control exactly which fields are exposed, how keys are named, how related records are nested, and how a payload is wrapped — without hand-writing bespoke JSON-building code for every endpoint.

---

## Background & Problem

Application code constantly needs to convert domain objects into JSON for APIs. Doing this by hand leads to repetitive, error-prone code: every endpoint re-implements field selection, key casing, nesting of related objects, root-key wrapping, conditional inclusion and error handling. The rules end up scattered and inconsistent.

With this engine, a single declarative specification describes *what* the output should look like — the selected fields and their order, the casing applied to keys, the nested related records, the optional wrapping root key, conditional fields, metadata, and how missing or failing values are handled. The engine reads a record (or a list of records) plus that specification and produces the corresponding JSON document. The core is a pure transformation: data and specification in, JSON string out.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional r[a list of predicates defined in the spec]uirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## The R[a list of predicates defined in the spec]uest Contract (shared by all features)

The execution adapter reads ONE JSON object from stdin and prints the resulting JSON document (or a neutral error line) to stdout. The r[a list of predicates defined in the spec]uest object has the following top-level fields:

- `object` — the data to serialize: either a single record (a JSON object whose fields are the record's readable attributes), or a list of records (a JSON array of such objects), or `null`. Nested objects/arrays inside a record represent related records reachable from that record.
- `resource` — the serialization specification (described below).
- `root_key` *(optional)* — a string root key supplied at serialization time; it overrides any root key declared in `resource`.
- `params` *(optional)* — a map of r[a list of predicates defined in the spec]uest-scoped parameters available to conditional rules.
- `meta` *(optional)* — a map of metadata supplied at serialization time.

The `resource` specification supports these fields (all optional unless noted):

- `attributes` — an ordered list of fields to emit. Each entry is either a field name (string) or a conditional entry `{"name": <field>, "if": <condition>}`.
- `root_key` — how to wrap the payload: a string (wrap singular and collection alike under that key); or `{"key": <singular>, "collection": <plural>}`; or `{"collection": <plural>}` (wrap only collections).
- `transform_keys` — key casing: a style string, or `{"type": <style>, "root": <bool>, "cascade": <bool>}`.
- `collection_key` — a field name; serialize a list as a JSON object keyed by that field instead of as an array.
- `associations` — a list of nested related-record rules: `{"relation": "one"|"many", "name": <field>, "key": <output key, optional>, "if": <condition, optional>, "resource": <nested specification>}`.
- `nested` — a list of inline nested groups: `{"name": <group key>, "resource": {"attributes": [...]}}`.
- `on_nil` — a constant substituted for any attribute whose value is null.
- `on_error` — `"ignore"` | `"nullify"` (policy for an attribute that cannot be resolved).
- `meta` — declared metadata: `{"static": <map>, "count_key": <key>}`.

A **condition** is `{"subject": "value"|"object"|"params", "key": <params key>, "attr": <method to read on the subject, optional>, "predicate": "[a list of predicates defined in the spec]"|"[a list of predicates defined in the spec]"|"[a list of predicates defined in the spec]"|"[a list of predicates defined in the spec]"|"[a list of predicates defined in the spec]", "operand": <comparison operand>}`.

---

## Core Features

### Feature 1: Field Selection

**As a developer**, I want to choose exactly which fields are exposed and in what order, so I can publish a stable, intentional shape rather than dumping the whole object.

**Expected Behavior / Usage:**

The engine emits only the fields listed in `attributes`, in declaration order. A single record yields a JSON object; a list of records yields a JSON array of objects in input order. Fields present on the record but not selected do not appear.

**Test Cases:** `rcb_tests/public_test_cases/feature1_attribute_selection.json`

```json
{
    "description": "Serialize a record into a JSON object that contains only an explicitly selected set of fields, in the exact order they were declared. A single record produces a JSON object; a list of records produces a JSON array of objects. Fields present on the record but not selected are omitted.",
    "cases": [
        {"input": {"object": {"id": 1, "name": "test"}, "resource": {"attributes": ["id", "name"]}}, "expected_output": "{\"id\":1,\"name\":\"test\"}"},
        {"input": {"object": [{"id": 1, "name": "test"}, {"id": 2, "name": "test2"}], "resource": {"attributes": ["id", "name"]}}, "expected_output": "[{\"id\":1,\"name\":\"test\"},{\"id\":2,\"name\":\"test2\"}]"}
    ]
}
```

---

### Feature 2: Root-Key Wrapping

**As a developer**, I want to optionally wrap the payload under a named root key, so the document matches the envelope my API expects.

**Expected Behavior / Usage:**

*2.1 Declared root key (singular and collection) — wrap with distinct keys for one vs. many*

When the specification declares a singular root key and a separate collection root key, a single record is wrapped under the singular key and a list is wrapped under the collection key.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_explicit_root_key.json`

```json
{
    "description": "Wrap the serialized payload under a top-level root key. The resource declares a singular root key and a separate plural root key for collections; a single record is wrapped under the singular key while a list of records is wrapped under the collection key.",
    "cases": [
        {"input": {"object": {"id": 1, "name": "A"}, "resource": {"attributes": ["id", "name"], "root_key": {"key": "user", "collection": "users"}}}, "expected_output": "{\"user\":{\"id\":1,\"name\":\"A\"}}"},
        {"input": {"object": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}], "resource": {"attributes": ["id", "name"], "root_key": {"key": "user", "collection": "users"}}}, "expected_output": "{\"users\":[{\"id\":1,\"name\":\"A\"},{\"id\":2,\"name\":\"B\"}]}"}
    ]
}
```

*2.2 Serialization-time root key — override the declared key per r[a list of predicates defined in the spec]uest*

A `root_key` supplied at the top level of the r[a list of predicates defined in the spec]uest overrides whatever root key the specification declares; the payload is wrapped under the r[a list of predicates defined in the spec]uest-supplied key.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_runtime_root_key.json`

```json
{
    "description": "A root key supplied at serialization time overrides any root key declared on the resource. The payload is wrapped under the r[a list of predicates defined in the spec]uest-supplied key regardless of the resource's own root-key configuration.",
    "cases": [
        {"input": {"object": {"id": 1, "name": "A"}, "resource": {"attributes": ["id", "name"], "root_key": {"key": "user", "collection": "users"}}, "root_key": "foo"}, "expected_output": "{\"foo\":{\"id\":1,\"name\":\"A\"}}"}
    ]
}
```

*2.3 Collection-only root key — wrap lists only*

When the specification declares a root key that applies only to collections, a list of records is wrapped under that key.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_collection_root_key.json`

```json
{
    "description": "A resource may declare a root key that applies only when serializing a collection. When given a list of records, the output is wrapped under that collection key; each record contributes one object to the wrapped array.",
    "cases": [
        {"input": {"object": [{"id": 1, "name": "Masafumi OKURA"}, {"id": 2, "name": "heka1024"}], "resource": {"attributes": ["id", "name"], "root_key": {"collection": "users"}}}, "expected_output": "{\"users\":[{\"id\":1,\"name\":\"Masafumi OKURA\"},{\"id\":2,\"name\":\"heka1024\"}]}"}
    ]
}
```

---

### Feature 3: Collection Output Shapes

**As a developer**, I want control over how a list of records is rendered, so I can emit either a plain array or a lookup-friendly keyed object.

**Expected Behavior / Usage:**

*3.1 Plain array — render an unwrapped list*

A list of records serialized without any root key produces a bare JSON array of objects, one per record, in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_collection_array.json`

```json
{
    "description": "When a list of records is serialized without any root key, the result is a bare JSON array of objects, one per record, preserving input order.",
    "cases": [
        {"input": {"object": [{"id": 1}, {"id": 2}], "resource": {"attributes": ["id"]}}, "expected_output": "[{\"id\":1},{\"id\":2}]"}
    ]
}
```

*3.2 Keyed object — render a list keyed by a field*

When `collection_key` names a field, the list is emitted as a JSON object whose keys are the string form of each record's value for that field, mapping to that record's serialized object.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_collection_key.json`

```json
{
    "description": "A collection can be serialized as a JSON object keyed by a chosen field of each record instead of as an array. Each record becomes a value under the string form of that record's key field.",
    "cases": [
        {"input": {"object": [{"id": 1}, {"id": 2}], "resource": {"attributes": ["id"], "collection_key": "id"}}, "expected_output": "{\"1\":{\"id\":1},\"2\":{\"id\":2}}"}
    ]
}
```

---

### Feature 4: Nested Related Records

**As a developer**, I want to embed related records and inline groupings, so a single document can carry a whole object graph in the shape clients need.

**Expected Behavior / Usage:**

*4.1 Singular association — embed one related record*

A `one` association reads the named field of the record (a related record) and embeds it as a nested JSON object, serialized with its own specification.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_one_association.json`

```json
{
    "description": "A singular association embeds a related record as a nested JSON object under the association name. The nested object is itself serialized with its own selected fields.",
    "cases": [
        {"input": {"object": {"id": 1, "profile": {"email": "test@example.com", "first_name": "Masafumi"}}, "resource": {"attributes": ["id"], "associations": [{"relation": "one", "name": "profile", "resource": {"attributes": ["email"]}}]}}, "expected_output": "{\"id\":1,\"profile\":{\"email\":\"test@example.com\"}}"}
    ]
}
```

*4.2 Plural association — embed a list of related records*

A `many` association reads the named field (a list of related records) and embeds it as a nested JSON array, each element serialized with the association's specification, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_many_association.json`

```json
{
    "description": "A plural association embeds a list of related records as a nested JSON array under the association name. Each element is serialized with the association resource's selected fields, preserving order.",
    "cases": [
        {"input": {"object": {"id": 1, "articles": [{"title": "Hello World!", "body": "Hello World!!!"}, {"title": "Super nice", "body": "Really nice!"}]}, "resource": {"attributes": ["id"], "associations": [{"relation": "many", "name": "articles", "resource": {"attributes": ["title", "body"]}}]}}, "expected_output": "{\"id\":1,\"articles\":[{\"title\":\"Hello World!\",\"body\":\"Hello World!!!\"},{\"title\":\"Super nice\",\"body\":\"Really nice!\"}]}"}
    ]
}
```

*4.3 Association output key — rename the nested key*

When an association supplies an explicit output `key`, the nested payload appears under that key instead of the source field name.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_association_key.json`

```json
{
    "description": "An association can be rendered under an explicit output key that differs from the association name. The nested payload appears under the chosen key instead of the source field name.",
    "cases": [
        {"input": {"object": {"id": 1, "articles": [{"title": "Hello World!"}, {"title": "Super nice"}]}, "resource": {"attributes": ["id"], "associations": [{"relation": "many", "name": "articles", "key": "posts", "resource": {"attributes": ["title"]}}]}}, "expected_output": "{\"id\":1,\"posts\":[{\"title\":\"Hello World!\"},{\"title\":\"Super nice\"}]}"}
    ]
}
```

*4.4 Null association — emit null when absent*

When the source field backing an association is null, the association serializes to JSON null, for both singular and plural associations.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_nil_association.json`

```json
{
    "description": "When the source field backing an association is absent (null), the association serializes to JSON null, for both singular and plural associations.",
    "cases": [
        {"input": {"object": {"id": 1, "profile": null}, "resource": {"attributes": ["id"], "associations": [{"relation": "one", "name": "profile", "resource": {"attributes": ["email"]}}]}}, "expected_output": "{\"id\":1,\"profile\":null}"},
        {"input": {"object": {"id": 1, "articles": null}, "resource": {"attributes": ["id"], "associations": [{"relation": "many", "name": "articles", "resource": {"attributes": ["title"]}}]}}, "expected_output": "{\"id\":1,\"articles\":null}"}
    ]
}
```

*4.5 Inline nested group — introduce nesting not backed by a relation*

A `nested` group introduces an arbitrary nesting level whose fields are read from the *same* source record and placed under the group key as a nested object.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_nested_attribute.json`

```json
{
    "description": "A nested attribute group introduces an arbitrary nesting level in the output that is not backed by an association on the source record. Fields listed for the group are read from the same source record and placed under the group's key as a nested object.",
    "cases": [
        {"input": {"object": {"id": 1, "city": "Tokyo", "zipcode": "0000000"}, "resource": {"root_key": "user", "attributes": ["id"], "nested": [{"name": "address", "resource": {"attributes": ["city", "zipcode"]}}]}}, "expected_output": "{\"user\":{\"id\":1,\"address\":{\"city\":\"Tokyo\",\"zipcode\":\"0000000\"}}}"}
    ]
}
```

---

### Feature 5: Key Transformation

**As a developer**, I want to rewrite output key casing uniformly, so the document follows the naming convention my clients expect without renaming every field by hand.

**Expected Behavior / Usage:**

*5.1 Casing styles — transform every attribute key*

Every attribute key is rewritten according to the chosen style: `camel` (UpperCamelCase), `lower_camel` (lowerCamelCase), `dash` (kebab-case), `snake` (snake_case), or `none` (unchanged). Underscore-delimited source field names are the input to the transformation.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_key_transform.json`

```json
{
    "description": "Output keys can be rewritten according to a casing style applied uniformly to every attribute key. Supported styles are camel (UpperCamelCase), lower_camel (lowerCamelCase), dash (kebab-case), snake (snake_case) and none (unchanged). Underscore-delimited source field names are the input to the transformation.",
    "cases": [
        {"input": {"object": {"id": 1, "first_name": "Masafumi", "last_name": "Okura"}, "resource": {"attributes": ["id", "first_name", "last_name"], "transform_keys": "camel"}}, "expected_output": "{\"Id\":1,\"FirstName\":\"Masafumi\",\"LastName\":\"Okura\"}"},
        {"input": {"object": {"id": 1, "first_name": "Masafumi", "last_name": "Okura"}, "resource": {"attributes": ["id", "first_name", "last_name"], "transform_keys": "dash"}}, "expected_output": "{\"id\":1,\"first-name\":\"Masafumi\",\"last-name\":\"Okura\"}"}
    ]
}
```

*5.2 Root-key transformation — opt the wrapping key in or out*

When root transformation is enabled, the wrapping root key is transformed with the same style; when disabled, the root key is left untouched while inner keys are still transformed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_root_key_transform.json`

```json
{
    "description": "Key transformation can optionally be applied to the root key as well. When root transformation is enabled, the wrapping root key is transformed with the same style as the inner keys; when it is disabled, the root key is left untouched while inner keys are still transformed.",
    "cases": [
        {"input": {"object": {"account_number": 123456789}, "resource": {"root_key": "bank_account", "attributes": ["account_number"], "transform_keys": {"type": "dash", "root": true}}}, "expected_output": "{\"bank-account\":{\"account-number\":123456789}}"},
        {"input": {"object": {"account_number": 123456789}, "resource": {"root_key": "bank_account", "attributes": ["account_number"], "transform_keys": {"type": "dash", "root": false}}}, "expected_output": "{\"bank_account\":{\"account-number\":123456789}}"}
    ]
}
```

*5.3 Cascade into associations — confine or propagate transformation*

When cascade is enabled, nested association keys are transformed with the same style as the parent; when disabled, the parent's keys are transformed while the nested association keeps its original field names.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_cascade.json`

```json
{
    "description": "Key transformation can cascade into inline associations or be confined to the top level. With cascade enabled, nested association keys are transformed with the same style as the parent; with cascade disabled, the parent's keys are transformed while the nested association keeps its original field names.",
    "cases": [
        {"input": {"object": {"id": 1, "first_name": "Masafumi", "last_name": "Okura", "bank_account": {"account_number": 123456789}}, "resource": {"attributes": ["id", "first_name", "last_name"], "transform_keys": {"type": "lower_camel", "cascade": true}, "associations": [{"relation": "one", "name": "bank_account", "resource": {"attributes": ["account_number"]}}]}}, "expected_output": "{\"id\":1,\"firstName\":\"Masafumi\",\"lastName\":\"Okura\",\"bankAccount\":{\"accountNumber\":123456789}}"},
        {"input": {"object": {"id": 1, "first_name": "Masafumi", "last_name": "Okura", "bank_account": {"account_number": 123456789}}, "resource": {"attributes": ["id", "first_name", "last_name"], "transform_keys": {"type": "lower_camel", "cascade": false}, "associations": [{"relation": "one", "name": "bank_account", "resource": {"attributes": ["account_number"]}}]}}, "expected_output": "{\"id\":1,\"firstName\":\"Masafumi\",\"lastName\":\"Okura\",\"bankAccount\":{\"account_number\":123456789}}"}
    ]
}
```

---

### Feature 6: Conditional Inclusion

**As a developer**, I want fields and associations to appear only when a predicate holds, so the document adapts to data and r[a list of predicates defined in the spec]uest context.

**Expected Behavior / Usage:**

*6.1 Conditional field by value — include based on the field's own value*

An attribute carrying an `if` condition is included only when the predicate over the attribute's value holds (e.g. value length at least a threshold); otherwise it is omitted entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_conditional_attribute_value.json`

```json
{
    "description": "An attribute can be made conditional on a predicate evaluated against the attribute's own value. The attribute is included only when the predicate holds (here: the value's length is at least a threshold) and is otherwise omitted entirely from the output.",
    "cases": [
        {"input": {"object": {"id": 1, "name": "Masafumi OKURA"}, "resource": {"attributes": ["id", {"name": "name", "if": {"subject": "value", "attr": "size", "predicate": "[a list of predicates defined in the spec]", "operand": 5}}]}}, "expected_output": "{\"id\":1,\"name\":\"Masafumi OKURA\"}"},
        {"input": {"object": {"id": 2, "name": "Foo"}, "resource": {"attributes": ["id", {"name": "name", "if": {"subject": "value", "attr": "size", "predicate": "[a list of predicates defined in the spec]", "operand": 5}}]}}, "expected_output": "{\"id\":2}"}
    ]
}
```

*6.2 Conditional field by parameter — include based on r[a list of predicates defined in the spec]uest context*

An attribute can be gated on a named r[a list of predicates defined in the spec]uest parameter; it is included only when that parameter is [a list of predicates defined in the spec] and omitted when the parameter is falsey or absent.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_conditional_attribute_param.json`

```json
{
    "description": "An attribute can be made conditional on a r[a list of predicates defined in the spec]uest-supplied parameter rather than on record data. The attribute is included only when the named parameter is [a list of predicates defined in the spec]; when the parameter is falsey or absent, the attribute is omitted.",
    "cases": [
        {"input": {"object": {"id": 1, "name": "Masafumi OKURA"}, "params": {"should_have_name": true}, "resource": {"attributes": ["id", {"name": "name", "if": {"subject": "params", "key": "should_have_name", "predicate": "[a list of predicates defined in the spec]"}}]}}, "expected_output": "{\"id\":1,\"name\":\"Masafumi OKURA\"}"},
        {"input": {"object": {"id": 1, "name": "Masafumi OKURA"}, "params": {"should_have_name": false}, "resource": {"attributes": ["id", {"name": "name", "if": {"subject": "params", "key": "should_have_name", "predicate": "[a list of predicates defined in the spec]"}}]}}, "expected_output": "{\"id\":1}"}
    ]
}
```

*6.3 Conditional singular association — include based on the related record*

A `one` association carrying an `if` condition is embedded only when the predicate over the associated record holds (e.g. a field ends with a suffix); otherwise the association key is omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_conditional_one.json`

```json
{
    "description": "A singular association can be made conditional on a predicate evaluated against the associated record. The association is embedded only when the predicate holds (here: a field of the associated record ends with a given suffix); otherwise the association key is omitted entirely.",
    "cases": [
        {"input": {"object": {"id": 1, "profile": {"email": "test@example.com"}}, "resource": {"attributes": ["id"], "associations": [{"relation": "one", "name": "profile", "resource": {"attributes": ["email"]}, "if": {"subject": "value", "attr": "email", "predicate": "[a list of predicates defined in the spec]", "operand": "com"}}]}}, "expected_output": "{\"id\":1,\"profile\":{\"email\":\"test@example.com\"}}"},
        {"input": {"object": {"id": 2, "profile": {"email": "test@example.org"}}, "resource": {"attributes": ["id"], "associations": [{"relation": "one", "name": "profile", "resource": {"attributes": ["email"]}, "if": {"subject": "value", "attr": "email", "predicate": "[a list of predicates defined in the spec]", "operand": "com"}}]}}, "expected_output": "{\"id\":2}"}
    ]
}
```

*6.4 Conditional plural association — include based on the related collection*

A `many` association carrying an `if` condition is embedded only when the predicate over the associated collection holds (e.g. the collection is non-empty); otherwise the association key is omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_conditional_many.json`

```json
{
    "description": "A plural association can be made conditional on a predicate evaluated against the associated collection. The association is embedded only when the predicate holds (here: the collection is non-empty); when it does not hold, the association key is omitted entirely.",
    "cases": [
        {"input": {"object": {"id": 1, "articles": [{"title": "Hello World!"}]}, "resource": {"attributes": ["id"], "associations": [{"relation": "many", "name": "articles", "resource": {"attributes": ["title"]}, "if": {"subject": "value", "predicate": "[a list of predicates defined in the spec]"}}]}}, "expected_output": "{\"id\":1,\"articles\":[{\"title\":\"Hello World!\"}]}"},
        {"input": {"object": {"id": 2, "articles": []}, "resource": {"attributes": ["id"], "associations": [{"relation": "many", "name": "articles", "resource": {"attributes": ["title"]}, "if": {"subject": "value", "predicate": "[a list of predicates defined in the spec]"}}]}}, "expected_output": "{\"id\":2}"}
    ]
}
```

---

### Feature 7: Null & Failure Handling

**As a developer**, I want explicit policies for null values and unresolvable fields, so the output is predictable instead of crashing or leaking nulls.

**Expected Behavior / Usage:**

*7.1 Null substitution — replace null values with a constant*

When a nil-handling constant is configured, every attribute whose source value is null is emitted with that constant instead of null; non-null values pass through unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_on_nil.json`

```json
{
    "description": "A nil-handling policy can replace every null attribute value with a configured constant. Attributes whose source value is null are emitted with the replacement constant instead of null; non-null values pass through unchanged.",
    "cases": [
        {"input": {"object": {"id": 1, "name": null, "age": null}, "resource": {"attributes": ["id", "name", "age"], "on_nil": ""}}, "expected_output": "{\"id\":1,\"name\":\"\",\"age\":\"\"}"},
        {"input": {"object": {"id": 3, "name": "User3", "age": 19}, "resource": {"attributes": ["id", "name", "age"], "on_nil": ""}}, "expected_output": "{\"id\":3,\"name\":\"User3\",\"age\":19}"}
    ]
}
```

*7.2 Unresolvable-field policy — ignore, nullify, or fail*

When an attribute cannot be resolved (the source record does not provide it), the policy decides the outcome: `ignore` drops the field; `nullify` emits it as null; the default policy propagates the failure, which the adapter reports as the neutral error line `error=serialization_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_on_error.json`

```json
{
    "description": "When an attribute cannot be resolved (the source record does not provide it), an error-handling policy decides the outcome. The 'ignore' policy drops the offending attribute from the output; the 'nullify' policy emits it as null; the default policy propagates the failure, which the adapter reports as a neutral serialization error.",
    "cases": [
        {"input": {"object": {"id": 1, "name": "Masafumi OKURA"}, "resource": {"root_key": "user", "attributes": ["id", "name", "email"], "on_error": "ignore"}}, "expected_output": "{\"user\":{\"id\":1,\"name\":\"Masafumi OKURA\"}}"},
        {"input": {"object": {"id": 1, "name": "Masafumi OKURA"}, "resource": {"root_key": "user", "attributes": ["id", "name", "email"], "on_error": "nullify"}}, "expected_output": "{\"user\":{\"id\":1,\"name\":\"Masafumi OKURA\",\"email\":null}}"},
        {"input": {"object": {"id": 1, "name": "Masafumi OKURA"}, "resource": {"root_key": "user", "attributes": ["id", "name", "email"]}}, "expected_output": "error=serialization_failed"}
    ]
}
```

---

### Feature 8: Metadata Envelope

**As a developer**, I want to attach metadata to the document, so clients receive contextual information (counts, flags) alongside the payload.

**Expected Behavior / Usage:**

Declared metadata is attached under a top-level `meta` key, but only when the payload is wrapped under a root key. The metadata may be a static map for a single record and a derived value (such as the collection size, emitted under `count_key`) for a list. Metadata supplied at serialization time is merged into the declared metadata, overriding entries on key collisions.

**Test Cases:** `rcb_tests/public_test_cases/feature8_meta.json`

```json
{
    "description": "A resource may declare metadata that is attached under a top-level 'meta' key, but only when the payload itself is wrapped under a root key. The metadata may be a static map for a single record and a derived value (such as the collection size) for a list. Metadata supplied at serialization time is merged into the declared metadata, overriding entries on key collisions.",
    "cases": [
        {"input": {"object": {"id": 1, "name": "Masafumi OKURA"}, "resource": {"root_key": {"key": "user", "collection": "users"}, "attributes": ["id", "name"], "meta": {"static": {"foo": "bar"}, "count_key": "size"}}}, "expected_output": "{\"user\":{\"id\":1,\"name\":\"Masafumi OKURA\"},\"meta\":{\"foo\":\"bar\"}}"},
        {"input": {"object": [{"id": 1, "name": "Masafumi OKURA"}], "resource": {"root_key": {"key": "user", "collection": "users"}, "attributes": ["id", "name"], "meta": {"static": {"foo": "bar"}, "count_key": "size"}}}, "expected_output": "{\"users\":[{\"id\":1,\"name\":\"Masafumi OKURA\"}],\"meta\":{\"size\":1}}"},
        {"input": {"object": [{"id": 1, "name": "Masafumi OKURA"}], "resource": {"root_key": {"key": "user", "collection": "users"}, "attributes": ["id", "name"], "meta": {"static": {"foo": "bar"}, "count_key": "size"}}, "meta": {"class": "MetaTest"}}, "expected_output": "{\"users\":[{\"id\":1,\"name\":\"Masafumi OKURA\"}],\"meta\":{\"size\":1,\"class\":\"MetaTest\"}}"}
    ]
}
```

---

### Feature 9: Invalid Specification Rejection

**As a developer**, I want a malformed specification to fail fast with a clear, neutral error, so misconfiguration is caught instead of silently producing wrong output.

**Expected Behavior / Usage:**

R[a list of predicates defined in the spec]uesting an unsupported key-transformation style is rejected when the specification is built. The adapter prints a neutral error identifying the failure category on the first line (`error=unknown_transform_type`) and echoing the offending style value on a second line (`type=<value>`), and produces no serialized output.

**Test Cases:** `rcb_tests/public_test_cases/feature9_invalid_transform.json`

```json
{
    "description": "R[a list of predicates defined in the spec]uesting an unsupported key-transformation style is rejected when the resource definition is built. The adapter reports a neutral error identifying the failure category and echoing the offending style value, rather than producing any serialized output.",
    "cases": [
        {"input": {"object": {"id": 1}, "resource": {"attributes": ["id"], "transform_keys": "unknown"}}, "expected_output": "error=unknown_transform_type\ntype=unknown"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the serialization engine described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core transformation (record + specification → JSON) must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON r[a list of predicates defined in the spec]uest from stdin, builds the records and the serialization specification, invokes the core engine, and prints the resulting JSON document (or a neutral error line) to stdout, matching the per-feature contracts above. Native failures from the core must be translated into the language-neutral error lines specified (`error=serialization_failed`, `error=unknown_transform_type` with a `type=` line) — never leaking host-language runtime traces.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same casing pattern as the keys module
- apply the same transformation logic to the root key
