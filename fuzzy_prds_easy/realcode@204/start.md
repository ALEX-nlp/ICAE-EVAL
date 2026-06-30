## Product Requirement Document

# Lightweight Relational Record Mapper - Query, Projection, and Relationship Loading Contracts

## Project Goal

Build a relational record-mapping library that allows developers to fetch compact, read-oriented records with selected fields, relationship data, batching, scalar projection, and stable error reporting without hand-writing repetitive row mapping, relationship stitching, and value conversion code.

---

## Background & Problem

Without this library/tool, developers are forced to choose between heavyweight full-model loading and manual SQL/result processing. This leads to repetitive code, accidental N+1 reads, inconsistent relationship handling, and fragile error behavior when a selected result does not contain a field or relationship.

With this library/tool, developers can describe the records and relationships they need, then consume lightweight result objects, scalar projections, or batches with deterministic stdout behavior through the execution adapter.

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
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Relational Query Results

**As a developer**, I want to run relational queries that return compact records, selected fields, first matches, or a normalized not-found result, so I can read database-backed data without writing repetitive row-mapping code.

**Expected Behavior / Usage:**

A request names a relational read scenario. The adapter prints a single JSON line. Ordered list requests print a `records` array. Selected-field requests print a `rows` array with only requested scalar fields. First-match requests print the matching row and the SQL signal used to enforce single-row retrieval; if a required row is absent, stdout is a language-neutral `not_found` error.

**Test Cases:** `rcb_tests/public_test_cases/feature1_relational_queries.json`

```json
{
    "description": "Relational queries return ordered lightweight records, selected fields, first matching records, and normalized not-found errors.",
    "cases": [
        {
            "input": {
                "request": "ordered_groups"
            },
            "expected_output": "{\"records\":[\"Bar\",\"Foo\"]}\n"
        },
        {
            "input": {
                "request": "selected_transaction_fields"
            },
            "expected_output": "{\"rows\":[{\"amount\":56.72,\"id\":834596859,\"date\":\"2017-02-28\",\"customer_id\":42}]}\n"
        },
        {
            "input": {
                "request": "first_account_by_login",
                "username": "bob",
                "required": false
            },
            "expected_output": "{\"username\":\"bob\",\"sql\":[\"root: SELECT users.* FROM users WHERE users.username = 'bob' LIMIT 1\"]}\n"
        },
        {
            "input": {
                "request": "first_account_by_login",
                "username": "nobody",
                "required": true
            },
            "expected_output": "{\"error\":\"not_found\"}\n"
        }
    ]
}
```

---

### Feature 2: Parameterized SQL Reads

**As a developer**, I want to send SQL-shaped reads with scalar and list parameters, so I can use explicit SQL while still receiving mapped records.

**Expected Behavior / Usage:**

A request selects a supported placeholder style. The adapter executes the SQL-shaped read through the record-mapping layer, binds scalar and array values, and prints the matching item names in deterministic order. Percent-style, named-style, and question-mark positional placeholders must all bind array values correctly.

**Test Cases:** `rcb_tests/public_test_cases/feature2_raw_sql_parameters.json`

```json
{
    "description": "SQL text inputs with supported placeholder styles bind scalar and list parameters before returning records.",
    "cases": [
        {
            "input": {
                "request": "sql_items_by_group"
            },
            "expected_output": "{\"records\":[\"Widget A\",\"Widget B\",\"Widget C\"]}\n"
        },
        {
            "input": {
                "request": "sql_items_all_groups"
            },
            "expected_output": "{\"records\":[\"Widget A\",\"Widget B\",\"Widget C\",\"Widget D\",\"Widget E\",\"Widget F\",\"Widget G\"]}\n"
        },
        {
            "input": {
                "request": "sql_items_percent_placeholders"
            },
            "expected_output": "{\"records\":[\"Widget A\",\"Widget B\"]}\n"
        },
        {
            "input": {
                "request": "sql_items_named_placeholders"
            },
            "expected_output": "{\"records\":[\"Widget A\",\"Widget B\"]}\n"
        },
        {
            "input": {
                "request": "sql_items_question_placeholders"
            },
            "expected_output": "{\"records\":[\"Widget A\",\"Widget B\"]}\n"
        }
    ]
}
```

---

### Feature 3: Scalar Projection

**As a developer**, I want to project one or more columns from mapped or SQL-backed queries, so I can obtain compact scalar arrays instead of full record objects.

**Expected Behavior / Usage:**

A projection request prints a JSON object with `values`. Single-column projections produce a flat array. Multi-column projections produce an array of row arrays. Computed expressions such as item-name length are returned as scalar values and preserve row order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_scalar_projection.json`

```json
{
    "description": "Column projections return scalar arrays or row arrays instead of record objects.",
    "cases": [
        {
            "input": {
                "request": "project_item_names"
            },
            "expected_output": "{\"values\":[\"Widget A\",\"Widget B\",\"Widget C\",\"Widget D\",\"Widget E\",\"Widget F\",\"Widget G\"]}\n"
        },
        {
            "input": {
                "request": "project_item_name_lengths"
            },
            "expected_output": "{\"values\":[8,8,8,8,8,8,8]}\n"
        },
        {
            "input": {
                "request": "project_item_names_and_lengths"
            },
            "expected_output": "{\"values\":[[\"Widget A\",8],[\"Widget B\",8],[\"Widget C\",8],[\"Widget D\",8],[\"Widget E\",8],[\"Widget F\",8],[\"Widget G\",8]]}\n"
        },
        {
            "input": {
                "request": "sql_project_names_and_lengths"
            },
            "expected_output": "{\"values\":[[\"Widget A\",8],[\"Widget B\",8],[\"Widget C\",8],[\"Widget D\",8],[\"Widget E\",8],[\"Widget F\",8],[\"Widget G\",8]]}\n"
        }
    ]
}
```

---

### Feature 4: Batched Iteration

**As a developer**, I want to consume query results in batches, so I can process large result sets while preserving ordering and relationship data.

**Expected Behavior / Usage:**

Batch requests print either explicit `batches` plus a flattened sequence, or a `records` sequence after offset/limit constraints. A relationship-aware batch request must include fields from the base row and already-loaded related rows, proving that batching does not discard relationship data.

**Test Cases:** `rcb_tests/public_test_cases/feature4_batched_iteration.json`

```json
{
    "description": "Large result sets can be consumed in fixed-size batches while preserving ordering, offsets, limits, and loaded relationships.",
    "cases": [
        {
            "input": {
                "request": "batch_items",
                "batch_size": 3
            },
            "expected_output": "{\"batch_count\":3,\"batches\":[[\"Widget A\",\"Widget B\",\"Widget C\"],[\"Widget D\",\"Widget E\",\"Widget F\"],[\"Widget G\"]],\"flattened\":[\"Widget A\",\"Widget B\",\"Widget C\",\"Widget D\",\"Widget E\",\"Widget F\",\"Widget G\"]}\n"
        },
        {
            "input": {
                "request": "batch_items_offset_limit",
                "offset": 3,
                "batch_size": 2
            },
            "expected_output": "{\"records\":[\"Widget D\",\"Widget E\",\"Widget F\",\"Widget G\"]}\n"
        },
        {
            "input": {
                "request": "batch_items_offset_limit",
                "limit": 3,
                "batch_size": 2
            },
            "expected_output": "{\"records\":[\"Widget A\",\"Widget B\",\"Widget C\"]}\n"
        },
        {
            "input": {
                "request": "batch_items_with_relationships"
            },
            "expected_output": "{\"records\":[{\"name\":\"Widget B\",\"category\":\"Foo\",\"detail\":\"All about Widget B\",\"line_items\":[]},{\"name\":\"Widget C\",\"category\":\"Foo\",\"detail\":\"All about Widget C\",\"line_items\":[{\"amount\":200,\"order_total\":520}]},{\"name\":\"Widget D\",\"category\":\"Bar\",\"detail\":\"All about Widget D\",\"line_items\":[{\"amount\":[test transactional_chord_integration]0,\"order_total\":520}]}]}\n"
        }
    ]
}
```

---

### Feature 5: Direct Relationship Loading

**As a developer**, I want to include directly related records in mapped query results, so I can avoid per-row follow-up lookups for common relationship shapes.

**Expected Behavior / Usage:**

A direct relationship request returns base records with related data already present. It covers many-to-one group lookup, one-to-one detail lookup, one-to-many child amounts, and join-table locations. The output must include relationship values, not just base-row identifiers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_direct_relationship_loading.json`

```json
{
    "description": "Records can include directly related one-to-one, one-to-many, many-to-one, and join-table collections.",
    "cases": [
        {
            "input": {
                "request": "load_parent_group"
            },
            "expected_output": "{\"records\":[{\"widget\":\"Widget A\",\"category\":\"Foo\"},{\"widget\":\"Widget B\",\"category\":\"Foo\"},{\"widget\":\"Widget C\",\"category\":\"Foo\"},{\"widget\":\"Widget D\",\"category\":\"Bar\"},{\"widget\":\"Widget E\",\"category\":\"Bar\"},{\"widget\":\"Widget F\",\"category\":\"Bar\"},{\"widget\":\"Widget G\",\"category\":\"Bar\"}]}\n"
        },
        {
            "input": {
                "request": "load_single_detail"
            },
            "expected_output": "{\"records\":[{\"widget\":\"Widget A\",\"detail\":\"All about Widget A\"},{\"widget\":\"Widget B\",\"detail\":\"All about Widget B\"},{\"widget\":\"Widget C\",\"detail\":\"All about Widget C\"},{\"widget\":\"Widget D\",\"detail\":\"All about Widget D\"},{\"widget\":\"Widget E\",\"detail\":\"All about Widget E\"},{\"widget\":\"Widget F\",\"detail\":\"All about Widget F\"},{\"widget\":\"Widget G\",\"detail\":\"All about Widget G\"}]}\n"
        },
        {
            "input": {
                "request": "load_child_amounts"
            },
            "expected_output": "{\"records\":[{\"order_amount\":100,\"line_item_amounts\":[[test transactional_chord_integration],[test transactional_chord_integration]]},{\"order_amount\":520,\"line_item_amounts\":[20,200,[test transactional_chord_integration]0]}]}\n"
        },
        {
            "input": {
                "request": "load_joined_locations"
            },
            "expected_output": "{\"records\":[{\"user\":\"bob\",\"offices\":[\"Bar\",\"Foo\"]},{\"user\":\"craig\",\"offices\":[\"Foo\"]},{\"user\":\"sue\",\"offices\":[\"Bar\",\"Zorp\"]}]}\n"
        }
    ]
}
```

---

### Feature 6: Indirect Relationship Loading

**As a developer**, I want to include records reached through intermediate relationships, so I can traverse multi-hop data paths without manual join assembly.

**Expected Behavior / Usage:**

Indirect loading requests return customers and groups reached through intermediate records. The output includes both final related values and SQL trace lines that show the observable query path. A full traversal plan may load all columns from intermediate records, while a select traversal plan may load only intermediate keys; both must produce the same final related values. A filtered request returns only matching final related groups.

**Test Cases:** `rcb_tests/public_test_cases/feature6_indirect_relationship_loading.json`

```json
{
    "description": "Records can include relationships reached through intermediate records, with optional optimized intermediate projections and filters.",
    "cases": [
        {
            "input": {
                "request": "load_indirect_groups",
                "traversal_plan": "none"
            },
            "expected_output": "{\"records\":[{\"customer\":\"Jane\",\"categories\":[\"Bar\",\"Foo\"]},{\"customer\":\"Jon\",\"categories\":[\"Foo\"]}],\"sql\":[\"root: SELECT customers.* FROM customers ORDER BY customers.name ASC\",\"root.through(orders): SELECT orders.* FROM orders WHERE orders.customer_id IN (846114006, 980204181)\",\"root.through(orders).through(line_items): SELECT line_items.* FROM line_items WHERE line_items.order_id IN (683130438, 834596858)\",\"root.through(orders).through(line_items).categories: SELECT categories.* FROM categories WHERE categories.id IN (208889123, 922717355)\"]}\n"
        },
        {
            "input": {
                "request": "load_indirect_groups",
                "traversal_plan": "select"
            },
            "expected_output": "{\"records\":[{\"customer\":\"Jane\",\"categories\":[\"Bar\",\"Foo\"]},{\"customer\":\"Jon\",\"categories\":[\"Foo\"]}],\"sql\":[\"root: SELECT customers.* FROM customers ORDER BY customers.name ASC\",\"root.through(orders): SELECT id, customer_id FROM orders WHERE orders.customer_id IN (846114006, 980204181)\",\"root.through(orders).through(line_items): SELECT id, order_id, category_id FROM line_items WHERE line_items.order_id IN (683130438, 834596858)\",\"root.through(orders).through(line_items).categories: SELECT categories.* FROM categories WHERE categories.id IN (208889123, 922717355)\"]}\n"
        },
        {
            "input": {
                "request": "load_filtered_indirect_groups"
            },
            "expected_output": "{\"records\":[{\"customer\":\"Jane\",\"categories\":[\"Foo\"]},{\"customer\":\"Jon\",\"categories\":[\"Foo\"]}]}\n"
        }
    ]
}
```

---

### Feature 7: Typed Target Loading

**As a developer**, I want to resolve a related target whose concrete source varies per row, so I can represent heterogeneous relationship targets through one field.

**Expected Behavior / Usage:**

The request loads rows whose target item may come from different source types. Stdout lists each amount with the resolved target name in amount order, demonstrating that each row uses its own target type rather than one fixed table.

**Test Cases:** `rcb_tests/public_test_cases/feature7_polymorphic_relationship_loading.json`

```json
{
    "description": "A related record slot whose target table varies per row resolves each row to the correct target record.",
    "cases": [
        {
            "input": {
                "request": "load_typed_targets"
            },
            "expected_output": "{\"records\":[{\"amount\":20,\"item\":\"Spline C\"},{\"amount\":30,\"item\":\"Widget A\"},{\"amount\":[test transactional_chord_integration],\"item\":\"Spline A\"},{\"amount\":200,\"item\":\"Widget C\"},{\"amount\":300,\"item\":\"Widget D\"}]}\n"
        }
    ]
}
```

---

### Feature 8: Normalized Missing Data Errors

**As a developer**, I want to receive stable errors when accessing unavailable data, so I can handle absent relationship and field data without runtime-specific exception text.

**Expected Behavior / Usage:**

Error requests intentionally access data that was not loaded, not selected, or not defined on a related record. Stdout must contain only language-neutral categories and structured fields: affected relationship or column, record label, member name, and trace path. It must not include host-language exception class names or runtime-formatted messages.

**Test Cases:** `rcb_tests/public_test_cases/feature8_missing_data_errors.json`

```json
{
    "description": "Accessing unloaded relationships, unselected fields, or undefined related members reports normalized black-box errors with the affected path.",
    "cases": [
        {
            "input": {
                "request": "unloaded_relationship_error"
            },
            "expected_output": "{\"error\":\"association_not_loaded\",\"association\":\"category\",\"record\":\"Widget\",\"trace\":\"root\"}\n"
        },
        {
            "input": {
                "request": "unselected_field_error"
            },
            "expected_output": "{\"error\":\"column_not_selected\",\"column\":\"name\",\"record\":\"Widget\",\"trace\":\"root\"}\n"
        },
        {
            "input": {
                "request": "nested_unselected_field_error"
            },
            "expected_output": "{\"error\":\"column_not_selected\",\"column\":\"amount\",\"record\":\"LineItem\",\"trace\":\"root.orders.line_items\"}\n"
        },
        {
            "input": {
                "request": "undefined_related_member_error"
            },
            "expected_output": "{\"error\":\"undefined_member\",\"member\":\"foo\",\"trace\":\"root.category\"}\n"
        }
    ]
}
```

---

### Feature 9: Value Casting

**As a developer**, I want to read boolean, coded, and timestamp values in application-friendly form, so I can avoid manual post-processing of common database value types.

**Expected Behavior / Usage:**

Casting requests print boolean status values, coded status labels, and a timestamp converted to the configured local offset. Boolean `nil` values exposed through the predicate form print as `false`; unknown coded status values print as `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_value_casting.json`

```json
{
    "description": "Database values are exposed with query-layer boolean status, coded status, and local-time representations.",
    "cases": [
        {
            "input": {
                "request": "boolean_status_values"
            },
            "expected_output": "{\"records\":[{\"office\":\"Bar\",\"active\":true},{\"office\":\"Foo\",\"active\":false},{\"office\":\"Zorp\",\"active\":false}]}\n"
        },
        {
            "input": {
                "request": "coded_status_values"
            },
            "expected_output": "{\"values\":[[1,\"pending\"],[2,\"active\"],[3,null]]}\n"
        },
        {
            "input": {
                "request": "localized_timestamp"
            },
            "expected_output": "{\"username\":\"bob\",\"created_at\":\"2017-12-29T10:00:37-05:00\"}\n"
        }
    ]
}
```

---

### Feature 10: Record Object Behavior

**As a developer**, I want to use returned records through key-based access and identity equality, so I can treat query results as useful lightweight record objects.

**Expected Behavior / Usage:**

Record-object requests verify that fields and loaded relationship fields are addressable by key-like access and that equality compares represented row identity. The output includes values retrieved through both key forms and equality results for same-row versus different-row records.

**Test Cases:** `rcb_tests/public_test_cases/feature10_record_object_behavior.json`

```json
{
    "description": "Returned records support key-based field access and equality based on the represented row.",
    "cases": [
        {
            "input": {
                "request": "keyed_field_access"
            },
            "expected_output": "{\"name_by_string\":\"Widget A\",\"name_by_key\":\"Widget A\",\"category_by_string\":\"Foo\",\"category_by_key\":\"Foo\"}\n"
        },
        {
            "input": {
                "request": "record_identity_equality"
            },
            "expected_output": "{\"same_record_equal\":true,\"different_record_equal\":false}\n"
        }
    ]
}
```

---

### Feature 11: Delegated Record Behavior

**As a developer**, I want to invoke model-defined behavior from a returned record, so I can reuse domain behavior while preserving lightweight query results.

**Expected Behavior / Usage:**

Delegation requests call a domain behavior exposed through a returned record. The adapter prints the composed value. Optional argument and callback-like input values must be incorporated in order, proving that delegation preserves caller-supplied values.

**Test Cases:** `rcb_tests/public_test_cases/feature11_delegated_record_behavior.json`

```json
{
    "description": "A returned record can delegate model-defined behavior and preserve argument and callback values.",
    "cases": [
        {
            "input": {
                "request": "delegate_record_behavior"
            },
            "expected_output": "{\"value\":\"Foo - All about Widget A\"}\n"
        },
        {
            "input": {
                "request": "delegate_record_behavior",
                "argument": "foo"
            },
            "expected_output": "{\"value\":\"Foo - All about Widget A - foo\"}\n"
        },
        {
            "input": {
                "request": "delegate_record_behavior",
                "argument": "foo",
                "block_value": "bar"
            },
            "expected_output": "{\"value\":\"Foo - All about Widget A - foo - bar\"}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
