## Product Requirement Document

# Vectorized Expression Compiler — Build, Compile, and Evaluate Columnar Expressions

## Project Goal

Build a library that lets developers describe row-wise computations over columnar data as composable **expression trees**, compile each tree once into an efficient kernel, and then evaluate it across whole batches of columns at a time. Developers get SQL-like projection, filtering, conditionals, arithmetic, comparison, membership, and pattern-matching over typed columns without hand-writing per-row loops or per-type branching.

---

## Background & Problem

Without this library, developers processing columnar data are forced to write bespoke loops that walk every row, branch on the column's element type, handle missing values by hand, and re-implement comparison, arithmetic, boolean, and pattern-matching logic for each new query. This leads to repetitive, error-prone boilerplate that is hard to optimize and hard to reuse.

With this library, a developer assembles a small, typed expression tree from primitive nodes (column references, typed constants, named functions, conditionals, boolean combinators, membership tests), compiles it once, and applies it to any number of record batches. Two evaluation modes are offered: a **projection** that turns an expression into one or more output columns, and a **filter** that turns a boolean condition into a selection vector of surviving row positions. The two modes compose into a filter-then-project pipeline.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (type system, expression-tree construction/validation, projection engine, filter engine, value rendering, and a separate execution adapter). It MUST NOT be a single "god file". Provide a clear multi-file tree (e.g. core engine modules plus a thin execution adapter) reflecting a production-grade repository. Do not over-engineer, but do not collapse distinct responsibilities into one module.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, not the internal data model of the engine. The core compiler/evaluation logic MUST be decoupled from stdin/stdout and JSON parsing. The execution adapter alone translates a JSON request into idiomatic calls on the core engine and renders results back to the stdout contract.

3. **Adherence to SOLID Design Principles:** Separate type resolution, tree building/validation, projection, filtering, and output formatting into distinct units. The expression-node abstraction must be open for extension (new node kinds / functions) but closed for modification. Keep node and engine interfaces small and cohesive; high-level engine code depends on the node abstraction, not on I/O details.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide compilation internals. Invalid trees (e.g. a required child node is missing, or a constant's value is incompatible with its declared type) MUST be rejected through proper error modeling rather than producing malformed trees or generic faults. Missing (null) data values in input columns MUST propagate to outputs as missing values.

---

## Core Features

### Feature 1: Conditional Projection (if / then / else over a comparison)

**As a developer**, I want to project a record batch through a conditional expression that chooses between two columns per row based on a comparison, so I can compute things like an element-wise maximum in one compiled pass.

**Expected Behavior / Usage:**

The schema declares two columns of the same signed-integer type. The expression is an if/then/else whose condition is a strict greater-than comparison of the first column against the second; when the condition holds the row takes the first column's value, otherwise the second column's value. Projection produces one output column of the declared result type. The adapter reports the operation name, the result type, the output row count, and the projected column as an ordered value list.

**Test Cases:** `rcb_tests/public_test_cases/feature1_conditional_projection.json`

```json
{
    "description": "Project a record batch through a compiled conditional expression. The schema has two equally-typed signed-integer columns. The expression compares the two columns element-wise and, for each row, selects the value from the first column when it is strictly greater than the second, otherwise the value from the second column (an if/then/else over a greater-than comparison). The adapter reports the operation, the declared result type, the number of output rows, and the resulting projected column as an ordered value list.",
    "cases": [
        {
            "input": {
                "operation": "project",
                "schema": [{"name": "a", "type": "int32"}, {"name": "b", "type": "int32"}],
                "columns": {"a": [10, 12, -20, 5], "b": [5, 15, 15, 17]},
                "expression": {
                    "node": "if",
                    "cond": {"node": "function", "name": "greater_than", "args": [{"node": "field", "name": "a"}, {"node": "field", "name": "b"}], "return": "bool"},
                    "then": {"node": "field", "name": "a"},
                    "else": {"node": "field", "name": "b"},
                    "type": "int32"
                },
                "result_type": "int32"
            },
            "expected_output": "op=project\nresult_type=int32\nlength=4\nvalues=[10, 15, 15, 17]\n"
        }
    ]
}
```

---

### Feature 2: Arithmetic Projection

**As a developer**, I want to project a record batch through an arithmetic expression that combines two columns, so I can derive a computed column in one compiled pass.

**Expected Behavior / Usage:**

The schema declares two double-precision floating-point columns. The expression adds the two columns element-wise to produce a new double-precision column. The adapter reports the operation name, the result type, the output row count, and the projected column as an ordered value list.

**Test Cases:** `rcb_tests/public_test_cases/feature2_arithmetic_projection.json`

```json
{
    "description": "Project a record batch through a compiled arithmetic expression. The schema has two double-precision floating-point columns. The expression adds the two columns element-wise to produce a new double-precision column. The adapter reports the operation, the declared result type, the number of output rows, and the resulting projected column as an ordered value list.",
    "cases": [
        {
            "input": {
                "operation": "project",
                "schema": [{"name": "a", "type": "float64"}, {"name": "b", "type": "float64"}],
                "columns": {"a": [1.0, 2.0], "b": [3.0, 4.0]},
                "expression": {"node": "function", "name": "add", "args": [{"node": "field", "name": "a"}, {"node": "field", "name": "b"}], "return": "float64"},
                "result_type": "float64"
            },
            "expected_output": "op=project\nresult_type=float64\nlength=2\nvalues=[4.0, 6.0]\n"
        }
    ]
}
```

---

### Feature 3: Comparison Filter (column vs. constant)

**As a developer**, I want to filter a record batch by comparing a column against a constant, so I can keep only the rows that satisfy a threshold.

**Expected Behavior / Usage:**

The schema declares one double-precision column. The condition keeps rows whose value is strictly less than a fixed numeric constant. Filtering produces a **selection vector**: an unsigned 32-bit list of the zero-based positions of the surviving rows, in ascending order. The adapter reports the operation name, the selection index element type, the number of surviving rows, and the selected positions as an ordered index list.

**Test Cases:** `rcb_tests/public_test_cases/feature3_comparison_filter.json`

```json
{
    "description": "Filter a record batch with a compiled boolean condition that compares a column against a constant. The schema has one double-precision column. The condition keeps rows whose value is strictly less than a fixed numeric literal. Filtering yields a selection vector of zero-based row positions (an unsigned 32-bit index list) identifying the surviving rows in ascending order. The adapter reports the operation, the selection index element type, the number of surviving rows, and the selected positions as an ordered index list.",
    "cases": [
        {
            "input": {
                "operation": "filter",
                "schema": [{"name": "a", "type": "float64"}],
                "columns": {"a": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]},
                "condition": {"node": "function", "name": "less_than", "args": [{"node": "field", "name": "a"}, {"node": "literal", "type": "float64", "value": 5.0}], "return": "bool"}
            },
            "expected_output": "op=filter\nselection_type=uint32\nlength=5\nindices=[0, 1, 2, 3, 4]\n"
        }
    ]
}
```

---

### Feature 4: Membership Filter (IN-set test)

**As a developer**, I want to filter a record batch by testing whether a column's value belongs to a fixed set of candidate constants, so I can express SQL-style `IN (...)` queries over textual or integer columns.

**Expected Behavior / Usage:**

The schema declares one column that is either textual or signed-integer. The condition keeps rows whose value is a member of a fixed candidate set carried in the expression and typed to match the column. Filtering produces a selection vector: an unsigned 32-bit list of the zero-based positions of matching rows in ascending order. The same behavior applies across text, 32-bit integer, and 64-bit integer columns. The adapter reports the operation name, the selection index element type, the number of matching rows, and the matching positions as an ordered index list.

**Test Cases:** `rcb_tests/public_test_cases/feature4_membership_filter.json`

```json
{
    "description": "Filter a record batch with a compiled membership condition that keeps rows whose value belongs to a fixed set of candidate constants (an IN-set test). The single column may be textual or signed integer; the candidate set is supplied as part of the expression and is typed to match the column. Filtering yields a selection vector of zero-based positions (an unsigned 32-bit index list) of the matching rows in ascending order. The adapter reports the operation, the selection index element type, the number of matching rows, and the matching positions as an ordered index list.",
    "cases": [
        {
            "input": {
                "operation": "filter",
                "schema": [{"name": "a", "type": "string"}],
                "columns": {"a": ["ga", "an", "nd", "di", "iv", "va"]},
                "condition": {"node": "in", "expr": {"node": "field", "name": "a"}, "values": ["an", "nd"], "type": "string"}
            },
            "expected_output": "op=filter\nselection_type=uint32\nlength=2\nindices=[1, 2]\n"
        }
    ]
}
```

---

### Feature 5: Boolean-Composition Filter (AND / OR of comparisons)

**As a developer**, I want to filter a record batch with a condition built by combining several comparisons with boolean conjunction and disjunction, so I can express compound predicates in one compiled pass.

**Expected Behavior / Usage:**

The schema declares two double-precision columns. The condition keeps a row when EITHER (the first column is below one constant AND the first column exceeds the second column) OR (the second column is below another constant). Filtering produces a selection vector: an unsigned 32-bit list of the zero-based positions of surviving rows in ascending order. The adapter reports the operation name, the selection index element type, the surviving-row count, and the positions as an ordered index list.

**Test Cases:** `rcb_tests/public_test_cases/feature5_boolean_composition_filter.json`

```json
{
    "description": "Filter a record batch with a compiled boolean condition built from several elementary comparisons combined with boolean conjunction and disjunction. The schema has two double-precision columns. The condition keeps a row when EITHER (the first column is below a constant AND the first column exceeds the second column) OR (the second column is below another constant). Filtering yields a selection vector of zero-based positions (an unsigned 32-bit index list) of surviving rows in ascending order. The adapter reports the operation, the selection index element type, the number of surviving rows, and the positions as an ordered index list.",
    "cases": [
        {
            "input": {
                "operation": "filter",
                "schema": [{"name": "a", "type": "float64"}, {"name": "b", "type": "float64"}],
                "columns": {"a": [1.0, 31.0, 46.0, 3.0, 57.0, 44.0, 22.0], "b": [5.0, 45.0, 36.0, 73.0, 83.0, 23.0, 76.0]},
                "condition": {
                    "node": "or",
                    "args": [
                        {"node": "and", "args": [
                            {"node": "function", "name": "less_than", "args": [{"node": "field", "name": "a"}, {"node": "literal", "type": "float64", "value": 50.0}], "return": "bool"},
                            {"node": "function", "name": "greater_than", "args": [{"node": "field", "name": "a"}, {"node": "field", "name": "b"}], "return": "bool"}
                        ]},
                        {"node": "function", "name": "less_than", "args": [{"node": "field", "name": "b"}, {"node": "literal", "type": "float64", "value": 11.0}], "return": "bool"}
                    ]
                }
            },
            "expected_output": "op=filter\nselection_type=uint32\nlength=3\nindices=[0, 2, 5]\n"
        }
    ]
}
```

---

### Feature 6: Pattern-Match Projection (SQL LIKE)

**As a developer**, I want to project a textual column through a SQL-style pattern match, so I can derive a boolean column marking the rows whose text matches a wildcard pattern.

**Expected Behavior / Usage:**

The schema declares one textual column. The expression applies a LIKE match against a pattern constant, where the percent sign is a wildcard matching any (possibly empty) run of characters. Projection produces a boolean column that is true exactly for the rows whose text matches the pattern. The adapter reports the operation name, the result type, the output row count, and the boolean column as an ordered value list of lowercase truth values (`true` / `false`).

**Test Cases:** `rcb_tests/public_test_cases/feature6_pattern_match_projection.json`

```json
{
    "description": "Project a record batch through a compiled SQL-style pattern-matching expression. The schema has one textual column. The expression applies a LIKE match against a pattern literal, where the percent sign is a wildcard matching any (possibly empty) run of characters, producing a boolean column that is true exactly for the rows whose text matches the pattern. The adapter reports the operation, the declared result type, the number of output rows, and the resulting boolean column as an ordered value list of lowercase truth values.",
    "cases": [
        {
            "input": {
                "operation": "project",
                "schema": [{"name": "a", "type": "string"}],
                "columns": {"a": ["park", "sparkle", "bright spark and fire", "spark"]},
                "expression": {"node": "function", "name": "like", "args": [{"node": "field", "name": "a"}, {"node": "literal", "type": "string", "value": "%spark%"}], "return": "bool"},
                "result_type": "bool"
            },
            "expected_output": "op=project\nresult_type=bool\nlength=4\nvalues=[false, true, true, true]\n"
        }
    ]
}
```

---

### Feature 7: Filter-then-Project Pipeline (with null propagation)

**As a developer**, I want to evaluate a projection only over the rows that survive a filter, so I can compute a derived column for a selected subset in one pipeline, with missing values handled correctly.

**Expected Behavior / Usage:**

The schema declares three signed-integer columns. A filter condition first selects the rows where the first column exceeds the second, producing a selection vector. A projection expression is then evaluated only over those selected rows: for each surviving row it selects the second column when that column is below the third column, otherwise the third column (an if/then/else over a less-than comparison). The third column may contain a missing value; a missing value propagates through the comparison and projection as a missing output. The adapter reports the operation name, the result type, the projected-row count, and the projected values as an ordered list with missing entries rendered as a `null` marker.

**Test Cases:** `rcb_tests/public_test_cases/feature7_filter_then_project.json`

```json
{
    "description": "Run a two-stage filter-then-project pipeline over a single record batch. The schema has three signed-integer columns. A filter condition first selects the rows where the first column exceeds the second column, producing a selection vector. A separate projection expression is then evaluated only over those selected rows: for each surviving row it selects the second column when that column is below the third column, otherwise the third column (an if/then/else over a less-than comparison). The third column may contain a missing value, which propagates through the comparison and projection as a missing output. The adapter reports the operation, the declared result type, the number of projected rows, and the projected values as an ordered list with missing entries rendered as a null marker.",
    "cases": [
        {
            "input": {
                "operation": "filter_project",
                "schema": [{"name": "a", "type": "int32"}, {"name": "b", "type": "int32"}, {"name": "c", "type": "int32"}],
                "columns": {"a": [10, 12, -20, 5, 21, 29], "b": [5, 15, 15, 17, 12, 3], "c": [1, 25, 11, 30, -21, null]},
                "condition": {"node": "function", "name": "greater_than", "args": [{"node": "field", "name": "a"}, {"node": "field", "name": "b"}], "return": "bool"},
                "expression": {
                    "node": "if",
                    "cond": {"node": "function", "name": "less_than", "args": [{"node": "field", "name": "b"}, {"node": "field", "name": "c"}], "return": "bool"},
                    "then": {"node": "field", "name": "b"},
                    "else": {"node": "field", "name": "c"},
                    "type": "int32"
                },
                "result_type": "int32",
                "selection_mode": "UINT32"
            },
            "expected_output": "op=filter_project\nresult_type=int32\nlength=3\nvalues=[1, -21, null]\n"
        }
    ]
}
```

---

### Feature 8: Typed Literal Construction & Validation

**As a developer**, I want to build constant nodes of any supported scalar type and have the system validate value/type compatibility, so I can embed well-typed constants in expressions and get a clear rejection when a value does not fit its declared type.

**Expected Behavior / Usage:**

A constant is described by a target type and a value. The target type may be supplied either as a structured type object or by its canonical type name; both spellings must be accepted and behave identically. Supported scalar types include the boolean, the unsigned integers (8/16/32/64-bit), the signed integers (8/16/32/64-bit), single- and double-precision floats, text, and binary. A constant whose value is compatible with its declared type is accepted; a constant whose value does not match its declared type, or whose declared type is missing, is rejected with a normalized `type_mismatch` error category. The adapter reports, for each requested constant in order, the type label, which type-spelling form was used, and whether construction succeeded (`status=ok`) or failed (`status=error error=type_mismatch`).

**Test Cases:** `rcb_tests/public_test_cases/feature8_typed_literals.json`

```json
{
    "description": "Construct constant (literal) nodes of every supported scalar type and validate type/value compatibility. Each literal is described by a target type and a value; the target type may be given either as a structured type object or by its canonical type name (both forms must be accepted). A literal whose value is compatible with the declared type is accepted; a literal whose value does not match the declared type, or whose declared type is missing, is rejected. The adapter reports, for each requested literal in order, the type label, which type-spelling form was used, and whether construction succeeded or failed, with failures carrying a normalized error category.",
    "cases": [
        {
            "input": {
                "operation": "literal_check",
                "literals": [
                    {"type": "int32", "value": 6, "form": "datatype"},
                    {"type": "float64", "value": 9.0, "form": "datatype"},
                    {"type": "string", "value": "hello", "form": "datatype"},
                    {"type": "int64", "value": 7, "form": "name"},
                    {"type": "int64", "value": "hello", "form": "datatype"},
                    {"type": null, "value": true, "form": "datatype"}
                ]
            },
            "expected_output": "op=literal_check\ntype=int32 form=datatype status=ok\ntype=float64 form=datatype status=ok\ntype=string form=datatype status=ok\ntype=int64 form=name status=ok\ntype=int64 form=datatype status=error error=type_mismatch\ntype=none form=datatype status=error error=type_mismatch\n"
        }
    ]
}
```

---

### Feature 9: Null-Node Rejection (malformed-tree validation)

**As a developer**, I want the builder to refuse any expression-tree construction in which a required child node is missing, so I never end up evaluating a malformed tree.

**Expected Behavior / Usage:**

Whenever a node position that demands a sub-expression is supplied with a null instead of a real node, the construction is refused and the adapter emits a single normalized `[a specific null rejection error code — verify against null handling logic]` error category (no result is produced). This rejection applies uniformly across every position that takes a node: a field reference, the branches of an if/then/else, the operands of a boolean conjunction or disjunction, the subject of a membership test, an operand of a comparison function, the root expression of a projection, and the condition of a filter.

**Test Cases:** `rcb_tests/public_test_cases/feature9_[a specific null rejection error code — verify against null handling logic]_rejection.json`

```json
{
    "description": "Reject expression-tree constructions in which a required child node is missing (supplied as a null). Whenever a node position that demands a sub-expression is given a null, the construction is refused rather than producing a malformed tree. This is checked across every position that takes a node: a field reference, the branches of an if/then/else, the operands of a boolean conjunction or disjunction, the subject of a membership test, an operand of a comparison function, the root expression of a projection, and the condition of a filter. The adapter reports a single normalized error category for each such construction.",
    "cases": [
        {
            "input": {"operation": "project", "schema": [{"name": "x", "type": "int32"}], "columns": {"x": [1]}, "expression": null, "result_type": "int32"},
            "expected_output": "error=[a specific null rejection error code — verify against null handling logic]\n"
        },
        {
            "input": {"operation": "filter", "schema": [{"name": "x", "type": "int32"}], "columns": {"x": [1]}, "condition": null},
            "expected_output": "error=[a specific null rejection error code — verify against null handling logic]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing a typed expression-node model, an expression-tree builder with validation, and projection / filter evaluation engines over batches of typed columns. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core engine. It reads one JSON request object from stdin, builds the schema, input columns, and expression tree, invokes the appropriate engine operation (`project`, `filter`, `filter_project`, or `literal_check`), and prints the result to stdout exactly matching the per-feature contracts above. Native errors are normalized here into language-neutral `error=<category>` lines (`[a specific null rejection error code — verify against null handling logic]`, `type_mismatch`); the core engine is never modified by the adapter. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing only the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the default list sorting behavior
- use the null projection outcome from the filter feature
