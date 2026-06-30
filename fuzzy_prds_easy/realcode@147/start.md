## Product Requirement Document

# API Output Builder — Transform & Serialize Domain Data into Wire-Ready Structures

## Project Goal

Build a reusable library that turns arbitrary application objects into clean, predictable API output structures, so developers can expose a stable public representation of their data — with optional nested relationships, metadata, and pagination — without hand-writing serialization code for every endpoint and every output convention.

---

## Background & Problem

When an application returns data over an API, the internal shape of its objects is rarely the shape clients should see. Fields need renaming or type-fixing, private fields must be hidden, related entities may or may not be embedded depending on what the caller asked for, and the whole thing must be wrapped in whatever envelope convention the API follows (a `data` wrapper, a flat object, or a compound document with side-loaded relationships). Pagination and metadata add further envelope concerns.

Without a shared library, every endpoint reinvents this glue: inconsistent envelopes, leaked internal fields, ad-hoc relationship embedding, and duplicated pagination formatting. This library separates three concerns cleanly: a *transformer* that maps one raw record to its public fields and declares which relationships are includable; a *resource* (a single item or a collection) that carries the data plus optional metadata, pagination cursor, or paginator; and a pluggable *serializer* that decides the final envelope. Callers also control which relationships are embedded through a compact include-directive syntax, and can read modifier parameters attached to those directives.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification. New envelope conventions must be addable as new serializers without touching existing ones.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Relationship Include Directives

**As a developer**, I want callers to declare which related resources to embed using a compact directive syntax, so the same endpoint can return lean or rich responses on demand.

**Expected Behavior / Usage:**

*1.1 Normalizing requested includes — parsing and ancestor expansion*

A request for includes may arrive either as a comma-separated string or as a list of strings. The library normalizes this into the canonical list of requested include paths. Duplicate entries are collapsed to a single occurrence. Every dotted (nested) path implicitly requests each of its ancestor paths as well, so requesting a deeply nested relationship also marks each parent on the way as requested. The order in which paths first appear is preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_parse_includes.json`

```json
{
    "description": "Normalize a set of requested relationship-include directives. The directives may be supplied as a comma-separated string or as a list of strings. The result is the normalized, de-duplicated list of requested include paths: repeated entries collapse to one, and any dotted (nested) path implicitly adds each of its ancestor paths so a request for a child also requests every parent leading to it. Order of first appearance is preserved.",
    "cases": [
        {"input": {"action": "parse_includes", "includes": "foo,bar"}, "expected_output": "[\"foo\",\"bar\"]\n"},
        {"input": {"action": "parse_includes", "includes": ["foo", "bar", "bar.baz"]}, "expected_output": "[\"foo\",\"bar\",\"bar.baz\"]\n"}
    ]
}
```

*1.2 Limiting include nesting depth*

To prevent runaway recursion, each dotted include path is trimmed to at most a configurable number of segments (defaulting to ten). Segments beyond the limit are discarded *before* ancestor expansion, so the resulting list never contains a path deeper than the limit.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_recursion_limit.json`

```json
{
    "description": "Limit how deeply nested include paths may go. Each dotted include path is trimmed to at most a configurable number of segments (default ten); any segments beyond the limit are discarded before the ancestor-expansion happens. The result is the normalized list of include paths after trimming.",
    "cases": [
        {"input": {"action": "parse_includes", "includes": "[a specific recursive depth limit defined in the system config].d.e.f.g.h.i.j.NEVER"}, "expected_output": "[\"a\",\"a.b\",\"[a specific recursive depth limit defined in the system config]\",\"[a specific recursive depth limit defined in the system config].d\",\"[a specific recursive depth limit defined in the system config].d.e\",\"[a specific recursive depth limit defined in the system config].d.e.f\",\"[a specific recursive depth limit defined in the system config].d.e.f.g\",\"[a specific recursive depth limit defined in the system config].d.e.f.g.h\",\"[a specific recursive depth limit defined in the system config].d.e.f.g.h.i\",\"[a specific recursive depth limit defined in the system config].d.e.f.g.h.i.j\"]\n"},
        {"input": {"action": "parse_includes", "recursion_limit": 3, "includes": "[a specific recursive depth limit defined in the system config].NEVER"}, "expected_output": "[\"a\",\"a.b\",\"[a specific recursive depth limit defined in the system config]\"]\n"}
    ]
}
```

*1.3 Include modifier parameters*

A directive may carry named modifiers using the syntax `name(values)` appended after a colon, and a directive may chain several such modifiers. Each modifier's values are pipe-delimited. After parsing, the parameters for a given include can be queried by modifier name, returning the ordered list of that modifier's values. Querying a modifier name that was not supplied returns null.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_include_params.json`

```json
{
    "description": "Parse modifier parameters attached to an include directive. A directive may carry one or more named modifiers using the syntax name(values) appended after a colon, and each modifier's values are pipe-delimited. After parsing, the parameters for a given include can be queried by modifier name, returning the list of that modifier's values; querying a modifier that was not supplied returns null.",
    "cases": [
        {"input": {"action": "include_params", "includes": "foo:limit(5|1):order(-something)", "include": "foo", "query": ["limit", "order", "totallymadeup"]}, "expected_output": "{\"limit\":[\"5\",\"1\"],\"order\":[\"-something\"],\"totallymadeup\":null}\n"}
    ]
}
```

*1.4 Rejecting an invalid include argument*

If the include argument is neither a string nor a list, parsing fails. The failure is reported as a neutral error category and no normalized list is produced.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_invalid_includes.json`

```json
{
    "description": "Reject an include argument that is neither a string nor a list. When the include argument has an unsupported type, parsing fails and a neutral error category is reported instead of any output.",
    "cases": [
        {"input": {"action": "parse_includes", "includes": null}, "expected_output": "error=invalid_includes_argument\n"},
        {"input": {"action": "parse_includes", "includes": 99}, "expected_output": "error=invalid_includes_argument\n"}
    ]
}
```

---

### Feature 2: Immutable Parameter Bag

**As a developer**, I want a read-only container for the modifier parameters of an include, so transformers can safely read them without any risk of accidental mutation.

**Expected Behavior / Usage:**

The bag is constructed from a map of parameter names to values (each value being a scalar or a list). Values can be fetched by key; fetching an absent key yields null, and an existence check reports whether a key is present. The bag is strictly immutable: any attempt to assign a value to a key or to remove a key is rejected with a neutral error category, and the bag's contents are never changed.

**Test Cases:** `rcb_tests/public_test_cases/feature2_param_bag.json`

```json
{
    "description": "Provide read-only access to a bag of parameters. Stored values (scalars or lists) can be fetched by key; fetching an absent key yields null and an existence check reports whether a key is present. The bag is immutable: any attempt to assign or remove a parameter is rejected with a neutral error category rather than mutating the bag.",
    "cases": [
        {"input": {"action": "param_bag", "op": "read", "params": {"one": "potato", "two": ["potato", "tomato"], "foo": "bar"}, "get": ["one", "two", "totallymadeup"], "has": ["foo", "totallymadeup"]}, "expected_output": "{\"get\":{\"one\":\"potato\",\"two\":[\"potato\",\"tomato\"],\"totallymadeup\":null},\"has\":{\"foo\":true,\"totallymadeup\":false}}\n"},
        {"input": {"action": "param_bag", "op": "mutate", "params": {"foo": "bar"}}, "expected_output": "error=immutable_parameters\n"}
    ]
}
```

---

### Feature 3: Data-Wrapped Serialization

**As a developer**, I want every response wrapped under a single top-level `data` key, so clients always find the payload in the same predictable place.

**Expected Behavior / Usage:**

Under this serialization strategy, a single record is emitted as an object under `data`, and a list of records is emitted as an array under `data`. Each record is transformed before serialization: in the sample data the `year` field is normalized to an integer, and any private field whose name begins with an underscore is dropped from the visible output. When a relationship is requested and present, the related resource is serialized with the *same* strategy — i.e. it is itself wrapped under its own `data` key — and placed beside the parent's fields under the relationship's name. Any metadata attached to the resource is emitted under a separate top-level `meta` key.

**Test Cases:** `rcb_tests/public_test_cases/feature3_data_serializer.json`

```json
{
    "description": "Serialize transformed resources under a fixed top-level data key. A single record is wrapped as an object under data; a list of records is wrapped as an array under data. Each record is transformed first (the year field is normalized to an integer and private underscore-prefixed fields are dropped). When a nested relationship is requested, the related resource is itself wrapped under its own data key and placed beside the parent's fields. Any attached metadata is emitted under a separate top-level meta key.",
    "cases": [
        {"input": {"action": "transform", "serializer": "data", "resource": "item", "data": {"foo": "bar"}}, "expected_output": "{\"data\":{\"foo\":\"bar\"}}\n"},
        {"input": {"action": "transform", "serializer": "data", "resource": "collection", "data": [{"foo": "bar"}]}, "expected_output": "{\"data\":[{\"foo\":\"bar\"}]}\n"}
    ]
}
```

---

### Feature 4: Flat Serialization

**As a developer**, I want an envelope-free representation where an item's fields sit at the top level, so simple responses stay compact.

**Expected Behavior / Usage:**

Under this strategy, a single record's fields appear directly at the top level with no wrapper. A list of records appears as an array under the supplied resource key, or under a default `data` key when no resource key is given. Included relationships are merged in flat — keyed by the relationship name, with the related data placed inline and not wrapped. Records are transformed first (the `year` field normalized to an integer; private underscore-prefixed fields dropped). A relationship that is declared as a *default* include is emitted even when the caller did not explicitly request it. Attached metadata is emitted under a separate top-level `meta` key.

**Test Cases:** `rcb_tests/public_test_cases/feature4_array_serializer.json`

```json
{
    "description": "Serialize transformed resources without a data wrapper. A single record's fields appear directly at the top level. A list of records appears as an array under the supplied resource key, or under a default data key when no resource key is given. Nested included relationships are merged in flat, keyed by the relationship name and not wrapped. Records are transformed first (year normalized to integer, private underscore-prefixed fields dropped). A relationship marked as a default include is emitted even when not explicitly requested. Attached metadata is emitted under a separate top-level meta key.",
    "cases": [
        {"input": {"action": "transform", "serializer": "array", "resource": "item", "resource_key": "book", "includes": "author", "data": {"title": "Foo", "year": "1991", "_author": {"name": "Dave"}}}, "expected_output": "{\"title\":\"Foo\",\"year\":1991,\"author\":{\"name\":\"Dave\"}}\n"},
        {"input": {"action": "transform", "serializer": "array", "resource": "item", "resource_key": "book", "includes": "author", "meta": {"foo": "bar"}, "data": {"title": "Foo", "year": "1991", "_author": {"name": "Dave"}}}, "expected_output": "{\"title\":\"Foo\",\"year\":1991,\"author\":{\"name\":\"Dave\"},\"meta\":{\"foo\":\"bar\"}}\n"}
    ]
}
```

---

### Feature 5: Compound-Document Serialization (Side-Loaded Relationships)

**As a developer**, I want related entities collected once into a separate top-level section rather than nested inline, so shared relationships are not duplicated across many records.

**Expected Behavior / Usage:**

Under this strategy the primary record(s) are placed as an array under the supplied resource key (or under a default `data` key when none is given); even a single record appears inside an array. Included relationships are *not* nested inline. Instead they are collected into a separate top-level `linked` section, grouped by relationship name. When the same related entity — identified by its `id` field — appears more than once across the primary records, it is listed only once in the `linked` section (de-duplication by id). Records are transformed first (the `year` field normalized to an integer; private underscore-prefixed fields dropped). Attached metadata is emitted under a separate top-level `meta` key.

**Test Cases:** `rcb_tests/public_test_cases/feature5_jsonapi_serializer.json`

```json
{
    "description": "Serialize transformed resources as a compound document with side-loaded relationships. The primary record(s) are placed as an array under the supplied resource key (or a default data key when none is given); a single record still appears inside an array. Included relationships are not nested inline but collected into a separate top-level linked section, grouped by relationship name. When the same related entity (identified by its id) appears more than once across the primary records, it is listed only once in the linked section. Records are transformed first (year normalized to integer, private underscore-prefixed fields dropped). Attached metadata is emitted under a separate top-level meta key.",
    "cases": [
        {"input": {"action": "transform", "serializer": "json_api", "resource": "item", "resource_key": "book", "includes": "author", "data": {"title": "Foo", "year": "1991", "_author": {"name": "Dave"}}}, "expected_output": "{\"book\":[{\"title\":\"Foo\",\"year\":1991}],\"linked\":{\"author\":[{\"name\":\"Dave\"}]}}\n"},
        {"input": {"action": "transform", "serializer": "json_api", "resource": "collection", "resource_key": "book", "includes": "author", "data": [{"title": "Foo", "year": "1991", "_author": {"name": "Dave"}}, {"title": "Bar", "year": "1997", "_author": {"name": "Bob"}}]}, "expected_output": "{\"book\":[{\"title\":\"Foo\",\"year\":1991},{\"title\":\"Bar\",\"year\":1997}],\"linked\":{\"author\":[{\"name\":\"Dave\"},{\"name\":\"Bob\"}]}}\n"}
    ]
}
```

---

### Feature 6: Pagination Metadata

**As a developer**, I want pagination information attached to a collection response in a consistent envelope, so clients can navigate large result sets.

**Expected Behavior / Usage:**

*6.1 Page-based pagination*

Given a paginator describing the current page, last page, per-page size, total item count, and the count on the current page, the serialized collection carries a `pagination` block under `meta`. That block reports the figures (with `total_pages` reflecting the last page) plus a `links` section. A `previous` link is present only when the current page is past the first page; a `next` link is present only when the current page precedes the last page. Each link is the page URL for the adjacent page.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_paginator_meta.json`

```json
{
    "description": "Attach page-based pagination metadata to a serialized collection. Given the current page, last page, per-page size, total item count, and count on the current page, the serialized output carries a pagination block under meta containing those figures (with total_pages reflecting the last page) plus a links section. A previous link is present only when the current page is past the first page, and a next link is present only when the current page precedes the last page; each link is the page URL for the adjacent page.",
    "cases": [
        {"input": {"action": "transform", "serializer": "data", "resource": "collection", "data": [{"foo": "bar", "baz": "ban"}], "paginator": {"total": 100, "count": 5, "per_page": 5, "current_page": 2, "last_page": 20, "base_url": "http://example.com/foo"}}, "expected_output": "{\"data\":[{\"foo\":\"bar\",\"baz\":\"ban\"}],\"meta\":{\"pagination\":{\"total\":100,\"count\":5,\"per_page\":5,\"current_page\":2,\"total_pages\":20,\"links\":{\"previous\":\"http:\\/\\/example.com\\/foo?page=1\",\"next\":\"http:\\/\\/example.com\\/foo?page=3\"}}}}\n"}
    ]
}
```

*6.2 Cursor-based pagination*

Given a cursor describing the current position, the previous and next cursor values, and the number of items in the current window, the serialized collection carries a `cursor` block under `meta` reporting those four values.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_cursor_meta.json`

```json
{
    "description": "Attach cursor pagination metadata to a serialized collection. Given the current cursor position, the previous and next cursor values, and the number of items in the current window, the serialized output carries a cursor block under meta reporting those four values.",
    "cases": [
        {"input": {"action": "transform", "serializer": "data", "resource": "collection", "data": [{"foo": "bar", "baz": "ban"}], "cursor": {"current": 0, "prev": "ban", "next": "ban", "count": 2}}, "expected_output": "{\"data\":[{\"foo\":\"bar\",\"baz\":\"ban\"}],\"meta\":{\"cursor\":{\"current\":0,\"prev\":\"ban\",\"next\":\"ban\",\"count\":2}}}\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — a manager that resolves include directives and recursion limits, an immutable parameter bag, item/collection resources carrying optional metadata, cursor, and paginator, a transformer abstraction that maps records and declares includable relationships, and a family of interchangeable serializers (data-wrapped, flat, and compound-document). The physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to the core system — logically and ideally physically separated from it. It reads a single JSON command from stdin and prints the resulting structure (or a neutral error line) to stdout, matching the per-feature contracts above. The command's `action` selects behavior: `parse_includes` normalizes include directives and prints the requested-include list; `include_params` parses directives and prints the queried modifier parameters; `param_bag` exercises the read-only parameter container; `transform` runs a record (or list of records) through the transformer and the chosen `serializer` (`data`, `array`, or `json_api`), honoring an optional `includes` string, `default_includes`, `resource_key`, `meta`, `paginator`, and `cursor`. Serialized structures are rendered as JSON. Errors are normalized to neutral `error=<category>` lines and never leak host-language exception identities.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same path normalization logic used for include parsing
- same key aliasing used for collection serialization
