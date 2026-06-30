## Product Requirement Document

# Document-Store Data Mapper — Pure Transformation Layer

## Project Goal

Build a data-modeling library for a key-addressed document store that allows developers to declare a typed record shape once — a primary key, an attribute type map, optional secondary indexes, and optional automatic timestamps — and then obtain deterministic, well-defined transformations between application records and the store's wire form, plus helpers that assemble the parameter objects for read and write requests, without hand-writing fragile attribute-by-attribute conversion code.

---

## Background & Problem

Without this library, developers integrating with a key-addressed document store are forced to manually translate every record between their application's natural shape and the store's verbose wire encoding: tagging each value with a storage type code, flattening typed sets into and out of plain lists, formatting dates as ISO-8601 instants, base64-encoding binaries, dropping null attributes, and stitching together the placeholder-laden condition and update expression strings the store's query protocol demands. This leads to repetitive, error-prone boilerplate scattered across the codebase, subtle inconsistencies between read and write paths, and brittle string concatenation for query/filter/update expressions.

With this library, the developer declares the model's shape once and calls small, composable transformations and fluent request builders. The library derives the storage type map from the declared schema, serializes and deserializes records consistently, builds lookup keys, assembles mutation action maps and update-expression bundles, and renders partition-scoped and full-table read parameters — each as a pure function of its inputs with no clock, randomness, network, or external state.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility library (schema/metadata derivation, validation, forward/reverse serialization, key construction, mutation and update-expression assembly, expression text parse/render, and two distinct request-parameter builders). It MUST NOT be a single "god file": output a clear, multi-file directory tree separating these concerns. Do not over-engineer, but do reflect the real feature surface in the layout.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core transformation logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. A thin execution adapter is solely responsible for decoding a JSON request, invoking the appropriate core transformation, and rendering the canonical output. The tagged input wrappers and the canonical output shape described below are adapter-level concerns, not core-model concerns.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core transformation, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** Adding a new attribute type or a new condition operator should not require modifying unrelated transformation code.
   - **Liskov Substitution Principle (LSP):** The condition operators usable on a read builder must be substitutable wherever a condition is accepted.
   - **Interface Segregation Principle (ISP):** Keep the builder interfaces small and cohesive (key conditions, filters, projection, paging are separable concerns).
   - **Dependency Inversion Principle (DIP):** Core transformations depend on the abstract schema/type map, not on any concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface (schema declaration, the serialize/deserialize helpers, and the fluent read builders) must be elegant and idiomatic to the target language, hiding the wire-format complexity.
   - **Resilience:** Edge cases must be handled gracefully — null records, numeric zero, empty strings, absent optional keys, and nested structures. Invalid configurations and invalid options must be modeled as proper errors rather than silent corruption.

---

## Core Features

### Feature 1: Schema Declaration & Metadata Derivation

**As a developer**, I want to declare a model's primary key, attribute types, secondary indexes, and timestamp policy once and read back the derived metadata, so I can rely on a single source of truth for how my records map onto the store.

**Expected Behavior / Usage:**

A model is configured with a primary key (a mandatory partition attribute and an optional sort attribute), an optional explicit table-name designation, an attribute type map, an optional timestamp policy, and an optional list of secondary indexes. From this configuration the model exposes several reports. The *keys* report returns the resolved partition and sort attribute names and the table-name designation (a literal name, a dynamic designation, or none). The *datatypes* report returns a map from each declared attribute name to a short storage type code — `S` (string), `N` (number), `BOOL` (boolean), `B` (binary), `DATE` (date), `L` (list), and the typed-set codes `SS`/`NS`/`BS` (string/number/binary set) — recursing into nested object attributes so their value is itself a type map. The *indexes* report classifies declared secondary indexes into a *global* group and a *local* group, each keyed by name. When the timestamp policy is enabled, created/updated date attributes are injected into the type map under default or caller-supplied names, and each may be independently suppressed. The input selects one report via a `report` field; output is a single canonical JSON line for structured reports, or `key=value` lines for the keys report.

**Test Cases:** `rcb_tests/public_test_cases/feature1_schema_metadata.json`

```json
{
  "description": "Schema declaration and metadata derivation. A model is configured with a primary key (a mandatory partition attribute and an optional sort attribute), an optional explicit table name, an optional attribute type map, optional automatic timestamp attributes, and an optional list of secondary indexes. From this configuration the model exposes: the resolved primary key attribute names and table-name designation; a derived wire-type map that assigns each declared attribute a storage type code (scalar string/number/boolean/binary, date, list, and the typed-set codes for string/number/binary sets), recursing into nested object attributes; the classification of declared secondary indexes into global versus local groupings by name; and, when timestamps are enabled, the injection of created/updated date attributes (under default or caller-supplied names, each independently suppressible) into the type map. Each case drives one of these reports.",
  "cases": [
    {
      "input": {
        "op": "schema_setup",
        "report": "datatypes",
        "config": {
          "hashKey": "id",
          "timestamps": true,
          "schema": {
            "id": "string"
          }
        }
      },
      "expected_output": "{\"createdAt\":\"DATE\",\"id\":\"S\",\"updatedAt\":\"DATE\"}\n"
    }
  ]
}
```

---

### Feature 2: Validation & Default Application

**As a developer**, I want arbitrary input records validated against the declared schema and static defaults applied, so I can reject malformed data and fill in omitted attributes before persisting.

**Expected Behavior / Usage:**

Given a model schema, an arbitrary input record is checked and the result reports a neutral validation-outcome category — a success marker when the record conforms, or a generic validation-failure marker otherwise — together with the coerced value the validator produced. Schema constraints such as a required attribute or a format-constrained string (for example an email-shaped string) participate in the outcome. Separately, supplying a record to the default-application path fills in any attribute that declares a static default while leaving provided attributes untouched. A configuration that omits the mandatory partition-key attribute is itself rejected at construction time and surfaces as a neutral schema-configuration error category. Errors are emitted as a single neutral line `error=<category>` and never leak any host-language exception identity.

**Test Cases:** `rcb_tests/public_test_cases/feature2_validation_defaults.json`

```json
{
  "description": "Validation and default application against a declared schema. Given a model schema, an arbitrary input record is checked: the result reports a neutral validation-outcome category (success versus a generic validation failure) together with the coerced value the validator produced. Constraints such as a required attribute or a format-constrained string participate in the outcome. Separately, supplying a record to the default-application path fills in any attributes that declare a static default while leaving provided attributes untouched. A configuration that omits the mandatory partition key attribute is itself rejected at construction time and surfaces as a neutral schema-configuration error category.",
  "cases": [
    {
      "input": {
        "op": "schema_setup",
        "report": "validate",
        "config": {
          "hashKey": "email",
          "schema": {
            "email": {
              "type": "string",
              "email": true,
              "required": true
            }
          }
        },
        "data": {
          "email": "foo@bar.com"
        }
      },
      "expected_output": "{\"error\":null,\"value\":{\"email\":\"foo@bar.com\"}}\n"
    }
  ]
}
```

---

### Feature 3: Record Serialization (Application → Wire)

**As a developer**, I want an application record converted into the store's attribute-value wire form according to the declared types, so I never have to hand-encode each attribute.

**Expected Behavior / Usage:**

A record is serialized into the storage attribute-value form, driven by the schema's derived type map. Scalars pass through, and numeric zero is preserved (not dropped or treated as absent). Boolean-typed attributes are coerced from loose inputs to a true/false value. Date-typed attributes render as an ISO-8601 instant. Binary-typed attributes render as an opaque byte payload (base64 under a `B` tag). Typed-set attributes (string/number/binary) render as set-tagged value collections under the `SS`/`NS`/`BS` tags, accepting either a single element or a collection. Nested object attributes are serialized recursively. An optional expectation mode wraps each produced attribute in a value envelope while passing through any caller-provided existence guard unchanged. Attributes whose value is null are omitted from the output, and serializing a null record yields a null result.

**Test Cases:** `rcb_tests/public_test_cases/feature3_item_serialization.json`

```json
{
  "description": "Forward serialization of an application record into the storage attribute-value form, driven by the schema's derived type map. Scalars pass through; numeric zero is preserved. Boolean-typed attributes are coerced from loose inputs to a true/false value. Date-typed attributes render as an ISO-8601 instant. Binary-typed attributes render as an opaque byte payload. Typed-set attributes (string/number/binary) render as set-tagged value collections, accepting either a single element or a collection. Nested object attributes are serialized recursively. An optional expectation mode wraps each produced attribute in a value envelope, while passing through any caller-provided existence guard unchanged. Attributes whose value is null are omitted from the output, and serializing a null record yields a null result.",
  "cases": [
    {
      "input": {
        "op": "serialize_item",
        "config": {
          "hashKey": "foo",
          "schema": {
            "foo": "string",
            "names": {
              "set": "string"
            }
          }
        },
        "item": {
          "names": [
            "Tim",
            "Steve",
            "Bob"
          ]
        }
      },
      "expected_output": "{\"names\":{\"SS\":[\"Tim\",\"Steve\",\"Bob\"]}}\n"
    }
  ]
}
```

---

### Feature 4: Lookup-Key Construction

**As a developer**, I want the library to extract just the key-bearing attributes that address a single record, so I can issue point reads and writes without manually picking out partition, sort, and index keys.

**Expected Behavior / Usage:**

The lookup key that addresses a single item may be built from a bare partition value (optionally accompanied by a sort value) or from a record object that already carries the relevant key attributes. The builder extracts only the attributes that serve as keys: the partition attribute, the sort attribute when one is declared, and the partition/sort attributes contributed by any declared secondary indexes (both global and local). Extracted values pass through the same type-driven serialization as item attributes, so a date-typed key renders as an ISO-8601 instant and a boolean index key is preserved as a boolean. Attributes that are not part of any key are dropped from the result.

**Test Cases:** `rcb_tests/public_test_cases/feature4_key_construction.json`

```json
{
  "description": "Construction of the lookup key record used to address a single item. A key may be built from a bare partition value (optionally accompanied by a sort value) or from a record object that already carries the relevant key attributes. The builder extracts only the attributes that serve as keys: the partition attribute, the sort attribute when one is declared, and the partition/sort attributes contributed by any declared secondary indexes (global and local). Extracted values pass through the same type-driven serialization as item attributes, so for example a date-typed key renders as an ISO-8601 instant and a boolean index key is preserved as a boolean. Attributes that are not part of any key are dropped.",
  "cases": [
    {
      "input": {
        "op": "build_key",
        "config": {
          "hashKey": "email",
          "rangeKey": "age",
          "schema": {
            "email": "string",
            "age": "number",
            "name": "string"
          },
          "indexes": [
            {
              "hashKey": "email",
              "rangeKey": "name",
              "type": "local",
              "name": "NameIndex"
            }
          ]
        },
        "hashKey": {
          "email": "test@example.com",
          "age": 22,
          "name": "Foo Bar"
        }
      },
      "expected_output": "{\"age\":22,\"email\":\"test@example.com\",\"name\":\"Foo Bar\"}\n"
    }
  ]
}
```

---

### Feature 5: Mutation Action-Map Serialization

**As a developer**, I want a record turned into a per-attribute action map describing how each attribute changes, so I can express in-place writes, removals, and set additions/subtractions declaratively.

**Expected Behavior / Usage:**

A record is serialized into the per-attribute action map consumed by an item-mutation request. Each non-key attribute becomes an entry carrying an action verb and, where relevant, a serialized value. A plain value produces a write action (`PUT`) with the type-serialized value. A null value produces a remove action (`DELETE`) with no value. An attribute wrapped as an additive operation produces an add action (`ADD`); an attribute wrapped as a subtractive operation produces a remove-from-set action (`DELETE`); in both cases the operand is type-serialized, so numbers stay numbers and set operands render as set-tagged collections. The partition-key attribute (and the sort attribute when declared) is never emitted, since keys are addressed separately.

**Test Cases:** `rcb_tests/public_test_cases/feature5_update_item_serialization.json`

```json
{
  "description": "Serialization of an application record into the per-attribute action map consumed by an item-mutation request. Each non-key attribute becomes an entry carrying an action verb and, where relevant, a serialized value. A plain value produces a write action with the type-serialized value. A null value produces a remove action with no value. An attribute wrapped as an additive operation produces an add action; an attribute wrapped as a subtractive operation produces a remove-from-set action; in both cases the operand is type-serialized (numbers stay numbers, set operands render as set-tagged collections). The primary key attribute (and the sort attribute when declared) is never emitted, since keys are addressed separately.",
  "cases": [
    {
      "input": {
        "op": "serialize_update_item",
        "action": "PUT",
        "config": {
          "hashKey": "email",
          "schema": {
            "email": "string",
            "age": "number",
            "names": {
              "set": "string"
            }
          }
        },
        "item": {
          "email": "test@test.com",
          "age": {
            "$add": 1
          },
          "names": {
            "$add": [
              "foo",
              "bar"
            ]
          }
        }
      },
      "expected_output": "{\"age\":{\"Action\":\"ADD\",\"Value\":1},\"names\":{\"Action\":\"ADD\",\"Value\":{\"SS\":[\"foo\",\"bar\"]}}}\n"
    }
  ]
}
```

---

### Feature 6: Update-Expression Bundle Assembly

**As a developer**, I want a record turned into a complete update-expression bundle — the four action-clause groups together with the name and value placeholder bindings — so I can submit a parameterized update without hand-building placeholder strings.

**Expected Behavior / Usage:**

From a record the builder assembles an update bundle. For each non-key attribute it emits a placeholder name binding and, where a value is involved, a placeholder value binding holding the type-serialized value, then assigns the attribute to one of four ordered action groups: a plain value joins the assignment group (`SET`) as a name-equals-value clause; an additive-wrapped value joins the add group (`ADD`); a subtractive-wrapped value joins the remove-from-set group (`DELETE`) with its operand rendered as a set-tagged collection; and a null or empty-string value joins the remove group (`REMOVE`) with no value binding. The result exposes the four ordered action-clause groups, the accumulated name bindings, and the accumulated value bindings. Key attributes are excluded; an empty or null record yields four empty groups and empty bindings.

**Test Cases:** `rcb_tests/public_test_cases/feature6_update_expression.json`

```json
{
  "description": "Building an update-expression bundle from an application record. For each non-key attribute the builder emits a placeholder name binding and, where a value is involved, a placeholder value binding holding the type-serialized value, and assigns the attribute to one of four action groups: a plain value joins the assignment group as a name-equals-value clause; an additive-wrapped value joins the add group; a subtractive-wrapped value joins the remove-from-set group with its operand rendered as a set-tagged collection; and a null or empty-string value joins the remove group with no value binding. The result exposes the four ordered action-clause groups, the accumulated name bindings, and the accumulated value bindings. Key attributes are excluded; an empty or null record yields four empty groups and empty bindings.",
  "cases": [
    {
      "input": {
        "op": "expr_serialize_update",
        "config": {
          "hashKey": "id",
          "schema": {
            "id": "string",
            "email": "string",
            "age": "number",
            "names": {
              "set": "string"
            }
          }
        },
        "item": {
          "id": "foobar",
          "email": "test@test.com"
        }
      },
      "expected_output": "{\"attributeNames\":{\"#email\":\"email\"},\"expressions\":{\"ADD\":[],\"DELETE\":[],\"REMOVE\":[],\"SET\":[\"#email = :email\"]},\"values\":{\":email\":\"test@test.com\"}}\n"
    }
  ]
}
```

---

### Feature 7: Update-Expression Text (Parse / Render)

**As a developer**, I want to convert between an update-expression string and its structured action groups in both directions, so I can inspect, compose, or rewrite expressions programmatically.

**Expected Behavior / Usage:**

This is a single bidirectional text-handling point covering both directions. *Parsing* splits an expression string into its four action groups: for each verb (`SET`, `ADD`, `DELETE`, `REMOVE`) it returns the ordered list of operand clauses that follow that verb, correctly handling nested parentheses inside operands, or a null marker when that verb is absent; a null or empty input yields all four markers null. *Rendering* is the inverse: given a mapping of action verbs to clause lists (or a single clause string per verb), it produces the canonical multi-clause expression, joining sibling clauses within a verb with commas and separating distinct action groups by spaces, while skipping empty or null groups; an empty or null mapping renders the empty string. The input's `op` field selects the direction (`expr_parse` versus `expr_stringify`).

**Test Cases:** `rcb_tests/public_test_cases/feature7_expression_text.json`

```json
{
  "description": "Bidirectional text handling for update expressions. Parsing splits an expression string into its four action groups, returning, for each verb, the ordered list of operand clauses that follow it (handling nested parentheses in operands) or a null marker when that verb is absent; a null or empty input yields all four markers null. Stringifying performs the inverse: given a mapping of action verbs to clause lists (or a single clause string), it renders the canonical multi-clause expression, joining sibling clauses with commas and separating action groups by spaces, while skipping empty or null groups; an empty or null mapping renders the empty string.",
  "cases": [
    {
      "input": {
        "op": "expr_parse",
        "expression": "ADD num :y SET name = :n"
      },
      "expected_output": "{\"ADD\":[\"num :y\"],\"DELETE\":null,\"REMOVE\":null,\"SET\":[\"name = :n\"]}\n"
    }
  ]
}
```

---

### Feature 8: Record Deserialization (Wire → Application)

**As a developer**, I want a stored item transformed back into a plain application record, so reads return natural shapes instead of the store's wire encoding.

**Expected Behavior / Usage:**

A stored item is transformed back into a plain record. Scalar attributes pass through unchanged. Any attribute stored as a typed set is flattened to a plain list of its member values. The transformation recurses through nested objects and through lists of objects, flattening sets wherever they appear at any depth. A null item yields a null result.

**Test Cases:** `rcb_tests/public_test_cases/feature8_item_deserialization.json`

```json
{
  "description": "Reverse transformation of a stored item back into a plain application record. Scalar attributes pass through unchanged. Any attribute stored as a typed set is flattened to a plain list of its member values. The transformation recurses through nested objects and through lists of objects, flattening sets wherever they appear at any depth. A null item yields a null result.",
  "cases": [
    {
      "input": {
        "op": "deserialize_item",
        "item": {
          "names": {
            "__set__": [
              "a",
              "b",
              "c"
            ]
          }
        }
      },
      "expected_output": "{\"names\":[\"a\",\"b\",\"c\"]}\n"
    }
  ]
}
```

---

### Feature 9: Partition-Scoped Read Request Parameters

**As a developer**, I want a fluent builder that accumulates the parameters of a partition-scoped read — key conditions, filters, projection, paging, and index selection — so I can compose a query without assembling placeholder strings by hand.

**Expected Behavior / Usage:**

Through a fluent builder the parameters of a partition-scoped read are accumulated and rendered together with the target table designation. Key conditions on the partition and sort attributes (equality, ordered comparisons, prefix match, and range) contribute a key-condition expression with their associated name and value placeholder bindings; when the read is finalized the partition equality is appended automatically, and selecting a secondary index switches the partition condition to that index's partition attribute. Non-key filter conditions (equality, existence/absence, range, set membership, and nested document paths) contribute a separate filter expression. Placeholder value names are de-duplicated across clauses (a second use of the same attribute gets a suffixed placeholder). Builder options such as a projected attribute list, an index selection, a result limit, and consistent-read selection are reflected in the parameters; a non-positive limit is rejected as a neutral error category (`error=invalid_limit`).

**Test Cases:** `rcb_tests/public_test_cases/feature9_query_params.json`

```json
{
  "description": "Assembly of the request parameters for a partition-scoped read, accumulated through a fluent builder and rendered together with the target table designation. Key conditions on the partition and sort attributes (equality, ordered comparisons, prefix match, and range) contribute a key-condition expression with their associated name and value placeholder bindings; when the read is finalized the partition equality is appended automatically, and selecting a secondary index switches the partition condition to that index's partition attribute. Non-key filter conditions (equality, existence/absence, range, set membership, and nested document paths) contribute a separate filter expression. Placeholder value names are de-duplicated across clauses. Builder options such as a projected attribute list, an index selection, a result limit, and consistent-read selection are reflected in the parameters; a non-positive limit is rejected as a neutral error category.",
  "cases": [
    {
      "input": {
        "op": "query_build",
        "tableName": "accounts",
        "config": {
          "hashKey": "name",
          "rangeKey": "email",
          "schema": {
            "name": "string",
            "email": "string"
          }
        },
        "hashKey": "tim",
        "ops": [
          [
            "where",
            "email"
          ],
          [
            "equals",
            "foo@example.com"
          ]
        ],
        "execKey": true
      },
      "expected_output": "{\"ExpressionAttributeNames\":{\"#email\":\"email\",\"#name\":\"name\"},\"ExpressionAttributeValues\":{\":email\":\"foo@example.com\",\":name\":\"tim\"},\"KeyConditionExpression\":\"(#email = :email) AND (#name = :name)\",\"TableName\":\"accounts\"}\n"
    }
  ]
}
```

---

### Feature 10: Full-Scan Read Request Parameters

**As a developer**, I want a fluent builder that accumulates the parameters of a full-table read — arbitrary filters, projection, and parallel-segment assignment — so I can compose a scan without assembling placeholder strings by hand.

**Expected Behavior / Usage:**

Through a fluent builder the parameters of a full-table read are accumulated and rendered with the target table designation. Filter conditions on any attribute contribute a filter expression with associated name and value placeholder bindings, supporting equality and inequality, ordered comparisons, prefix match, range, set membership, substring containment and its negation, and attribute presence/absence. Successive conditions are conjoined, and placeholder value names are de-duplicated across clauses. Date-valued operands are rendered as ISO-8601 instants. Nested document paths expand into segmented name placeholders. Builder options including a projected attribute list and a parallel-scan segment assignment are reflected in the parameters.

**Test Cases:** `rcb_tests/public_test_cases/feature10_scan_params.json`

```json
{
  "description": "Assembly of the request parameters for a full-table read, accumulated through a fluent builder and rendered with the target table designation. Filter conditions on any attribute contribute a filter expression with associated name and value placeholder bindings: equality and inequality, ordered comparisons, prefix match, range, set membership, substring containment and its negation, and attribute presence/absence. Successive conditions are conjoined and placeholder value names are de-duplicated across clauses. Date-valued operands are rendered as ISO-8601 instants. Nested document paths expand into segmented name placeholders. Builder options including a projected attribute list and a parallel-scan segment assignment are reflected in the parameters.",
  "cases": [
    {
      "input": {
        "op": "scan_build",
        "tableName": "accounts",
        "config": {
          "hashKey": "name",
          "rangeKey": "email",
          "schema": {
            "name": "string",
            "email": "string"
          }
        },
        "ops": [
          [
            "where",
            "email"
          ],
          [
            "in",
            [
              "foo@example.com",
              "test@example.com"
            ]
          ]
        ]
      },
      "expected_output": "{\"ExpressionAttributeNames\":{\"#email\":\"email\"},\"ExpressionAttributeValues\":{\":email\":\"foo@example.com\",\":email_2\":\"test@example.com\"},\"FilterExpression\":\"(#email IN (:email,:email_2))\",\"TableName\":\"accounts\"}\n"
    }
  ]
}
```

---

## Adapter I/O Protocol

Each behavior is exercised by feeding **one JSON request object** on standard input to a thin execution adapter and reading its **raw standard output**. The request always carries an `op` field selecting the behavior; the remaining fields are operands. Because some runtime values have no direct JSON form, operand values may use tagged wrappers in the input: `{"__date__": "<iso-8601>"}` for a date/time instant, `{"__buffer__": "<base64>"}` for a binary payload, and `{"__set__": [ ... ]}` for a typed-set value. Schema attribute types are described in `config.schema` using compact type tags: the strings `"string"`, `"number"`, `"boolean"`, `"binary"`, `"date"`, `"object"`, `"array"`; `{"set":"string"|"number"|"binary"}` for typed sets; `{"object":{...}}` for a nested record; and an object form `{"type":..., "default":..., "required":true, "email":true}` for constrained scalars; a list attribute with an explicit storage code uses `{"type":"array","dynamoType":"SS"|"NS"|"BS"}`.

Output is canonicalized for determinism: object keys are emitted in sorted order; sets render as `{"SS"|"NS"|"BS": [ ... ]}`; binaries render as `{"B": "<base64>"}`; dates render as ISO-8601 strings. A structured result is a single JSON line; a simple report is `key=value` lines; a recognized failure is a single neutral line `error=<category>` (for example `error=invalid_schema_config`, `error=invalid_limit`, `error=unknown_op`). No host-language exception class name, runtime message suffix, or language-specific object rendering ever appears in the output.

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the ten features above — schema/metadata derivation, validation and defaults, forward and reverse record serialization, lookup-key construction, mutation action-map serialization, update-expression bundle assembly, expression text parse/render, and the partition-scoped and full-table read-parameter builders. The physical structure MUST align with the "Scale-Driven Code Organization" constraint, keeping these responsibilities in separate logical units.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core system. It reads one JSON command from stdin, decodes the tagged wrappers and schema tags, invokes the appropriate core transformation, and prints the canonical result to stdout, strictly matching the per-feature contracts above. Native errors raised by the core are translated **here** into neutral `error=<category>` lines. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_schema_metadata.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_schema_metadata@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`. The full hidden suite in `rcb_tests/test_cases/` and the public subset in `rcb_tests/public_test_cases/` must both report zero failures.


---
**Implementation notes:**
- SS/NS/BS codes defined in the mime type configuration module
