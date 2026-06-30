## Product Requirement Document

# SQL Query Builder - Structured SQL Rendering and Execution Adapter

## Project Goal

Build a SQL query construction library that allows developers to compose SELECT, INSERT, UPDATE, DELETE, predicate, conditional, placeholder, and execution-helper behavior through structured inputs without hand-concatenating SQL strings and bind argument lists.

---

## Background & Problem

Without this library/tool, developers are forced to manually concatenate SQL clauses, count placeholders, preserve bind argument order, and duplicate boilerplate for database execution. This leads to repetitive code, off-by-one placeholder bugs, inconsistent handling of nulls and lists, and fragile statement assembly.

With this library/tool, developers describe query parts and execution intent as structured data, and the system renders deterministic SQL text, argument arrays, normalized validation errors, and database-runner integration signals.

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

### Feature 1: Predicate Expressions

**As a developer**, I want to describe field comparisons, null checks, set membership, and range comparisons, so I can generate SQL predicate fragments plus the ordered bind values without hand-writing every placeholder.

**Expected Behavior / Usage:**

Input is a JSON command describing one predicate: the comparison kind, target field, and value. Scalar equality renders `field = ?` with one argument, list equality renders `field IN (...)` with one placeholder per element, negative equality uses `<>` or `NOT IN`, null equality uses `IS NULL`, negative null equality uses `IS NOT NULL`, and range comparisons render `<`, `<=`, `>`, or `>=`. Empty list equality is invalid and must render the neutral error category `[a specific error code for empty list predicates – check the error mapping table]`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_predicate_expressions.json`

```json
{
    "description": "Render standalone predicate expressions into SQL fragments and bound argument arrays.",
    "cases": [
        {
            "input": {
                "operation": "predicate",
                "predicate": {
                    "comparison": "equals",
                    "field": "id",
                    "value": 1
                }
            },
            "expected_output": "sql=id = ?\nargs=[1]\n"
        },
        {
            "input": {
                "operation": "predicate",
                "predicate": {
                    "comparison": "equals",
                    "field": "id",
                    "value": [
                        1,
                        2,
                        3
                    ]
                }
            },
            "expected_output": "sql=id IN (?,?,?)\nargs=[1,2,3]\n"
        }
    ]
}
```

---

### Feature 2: Placeholder Formatting

**As a developer**, I want to choose a bind marker style for SQL text, so I can target engines that require either question marks or [the exact string literal used for numeric operands in case expressions]ed placeholders.

**Expected Behavior / Usage:**

Input is a SQL template and a placeholder style. The question style leaves `?` markers unchanged. The [the exact string literal used for numeric operands in case expressions]ed style rewrites each placeholder in encounter order as `$1`, `$2`, and so on. A doubled question mark is an escape for a literal single question mark and is not itself counted as a bind marker. A separate placeholder-list command returns a comma-separated run of question marks for a requested count.

**Test Cases:** `rcb_tests/public_test_cases/feature2_placeholder_formats.json`

```json
{
    "description": "Convert question-mark placeholders to the requested bind marker style while preserving escaped literal question marks.",
    "cases": [
        {
            "input": {
                "operation": "placeholders",
                "template": "x = ? AND y = ?",
                "format": "question"
            },
            "expected_output": "sql=x = ? AND y = ?\n"
        },
        {
            "input": {
                "operation": "placeholders",
                "template": "x = ? AND y = ?",
                "format": "[the exact string literal used for numeric operands in case expressions]ed"
            },
            "expected_output": "sql=x = $1 AND y = $2\n"
        }
    ]
}
```

---

### Feature 3: SELECT Statement Rendering

**As a developer**, I want to compose read queries from structured clauses, so I can produce deterministic SQL text and argument ordering for complex read statements.

**Expected Behavior / Usage:**

Input describes result columns, distinctness, source table, joins, predicates, grouping, having text, ordering, limit, offset, suffix text, and placeholder style. Output is the exact rendered SQL and the ordered argument array. Zero is a meaningful limit or offset and must be emitted as `LIMIT 0` or `OFFSET 0`. A read statement with no result columns is invalid and must render `[a specific error code for missing select columns – consult the error catalog]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_select_statements.json`

```json
{
    "description": "Build SELECT statements from externally supplied clauses, expressions, joins, filters, grouping, ordering, limits, offsets, suffixes, and placeholder style.",
    "cases": [
        {
            "input": {
                "operation": "select",
                "scenario": "full_select",
                "clauses": {
                    "columns": [
                        "a",
                        "b",
                        "c"
                    ],
                    "distinct": true,
                    "source": "e",
                    "joins": [
                        "CROSS JOIN j1",
                        "JOIN j2",
                        "LEFT JOIN j3",
                        "RIGHT JOIN j4"
                    ],
                    "filters": [
                        "f = ?",
                        "g = ?",
                        "h = ?",
                        "i IN",
                        "compound"
                    ],
                    "group_by": [
                        "l"
                    ],
                    "having": "m = n",
                    "order_by": [
                        "o ASC",
                        "p DESC"
                    ],
                    "limit": 12,
                    "offset": 13
                }
            },
            "expected_output": "sql=WITH prefix AS ? SELECT DISTINCT a, b, c, IF(d IN (?,?,?), 1, 0) as stat_column, a > ?, (b IN (?,?,?)) AS b_alias, (SELECT aa, bb FROM dd) AS subq FROM e CROSS JOIN j1 JOIN j2 LEFT JOIN j3 RIGHT JOIN j4 WHERE f = ? AND g = ? AND h = ? AND i IN (?,?,?) AND (j = ? OR (k = ? AND true)) GROUP BY l HAVING m = n ORDER BY o ASC, p DESC LIMIT 12 OFFSET 13 FETCH FIRST ? ROWS ONLY\nargs=[0,1,2,3,100,101,102,103,4,5,6,7,8,9,10,11,14]\n"
        },
        {
            "input": {
                "operation": "select",
                "scenario": "zero_limit_offset",
                "clauses": {
                    "columns": [
                        "a"
                    ],
                    "source": "b",
                    "limit": 0,
                    "offset": 0
                }
            },
            "expected_output": "sql=SELECT a FROM b LIMIT 0 OFFSET 0\nargs=[]\n"
        }
    ]
}
```

---

### Feature 4: INSERT Statement Rendering

**As a developer**, I want to compose insertion queries from targets, columns, rows, options, and expressions, so I can generate insertion SQL without manually aligning value placeholders and arguments.

**Expected Behavior / Usage:**

Input describes the insertion target, optional prefix, insertion options, column names, row values, raw value expressions, suffix text, map-style column values, and placeholder style. Output is the exact rendered SQL and ordered arguments. Missing target and missing values are invalid and must render `error=missing_insert_target` or `error=missing_insert_values`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_insert_statements.json`

```json
{
    "description": "Build INSERT statements from target tables, options, column lists, row values, value expressions, suffixes, map-style assignments, and placeholder style.",
    "cases": [
        {
            "input": {
                "operation": "insert",
                "scenario": "full_insert",
                "clauses": {
                    "target": "a",
                    "options": [
                        "DELAYED",
                        "IGNORE"
                    ],
                    "columns": [
                        "b",
                        "c"
                    ],
                    "rows": [
                        [
                            1,
                            2
                        ],
                        [
                            3,
                            {
                                "expression": "? + 1",
                                "args": [
                                    4
                                ]
                            }
                        ]
                    ],
                    "prefix": "WITH prefix AS ?",
                    "suffix": "RETURNING ?"
                }
            },
            "expected_output": "sql=WITH prefix AS ? INSERT DELAYED IGNORE INTO a (b,c) VALUES (?,?),(?,? + 1) RETURNING ?\nargs=[0,1,2,3,4,5]\n"
        },
        {
            "input": {
                "operation": "insert",
                "scenario": "missing_target",
                "clauses": {
                    "target": "",
                    "rows": [
                        [
                            1
                        ]
                    ]
                }
            },
            "expected_output": "error=missing_insert_target\n"
        }
    ]
}
```

---

### Feature 5: UPDATE Statement Rendering

**As a developer**, I want to compose update queries from a target, assignments, filters, ordering, and bounds, so I can generate update SQL with stable assignment order and argument order.

**Expected Behavior / Usage:**

Input describes the target table, assignments, raw assignment expressions, optional prefix, filter, ordering, limit, offset, suffix text, and placeholder style. Output is the exact rendered SQL and ordered arguments. Zero limit and zero offset must be emitted. Missing target and missing assignments are invalid and must render `error=missing_update_target` or `error=missing_update_assignments`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_update_statements.json`

```json
{
    "description": "Build UPDATE statements from a target table, assignments, raw value expressions, filters, ordering, limits, offsets, suffixes, and placeholder style.",
    "cases": [
        {
            "input": {
                "operation": "update",
                "scenario": "full_update",
                "clauses": {
                    "target": "a",
                    "assignments": {
                        "b": {
                            "expression": "? + 1",
                            "args": [
                                1
                            ]
                        },
                        "c": 2
                    },
                    "filter": "d = ?",
                    "order_by": [
                        "e"
                    ],
                    "limit": 4,
                    "offset": 5,
                    "prefix": "WITH prefix AS ?",
                    "suffix": "RETURNING ?"
                }
            },
            "expected_output": "sql=WITH prefix AS ? UPDATE a SET b = ? + 1, c = ? WHERE d = ? ORDER BY e LIMIT 4 OFFSET 5 RETURNING ?\nargs=[0,1,2,3,6]\n"
        },
        {
            "input": {
                "operation": "update",
                "scenario": "zero_limit_offset",
                "clauses": {
                    "target": "a",
                    "assignments": {
                        "b": true
                    },
                    "limit": 0,
                    "offset": 0
                }
            },
            "expected_output": "sql=UPDATE a SET b = ? LIMIT 0 OFFSET 0\nargs=[true]\n"
        }
    ]
}
```

---

### Feature 6: DELETE Statement Rendering

**As a developer**, I want to compose delete queries from targets, sources, joins, filters, ordering, and bounds, so I can support single-table and multi-table deletions through one rendering contract.

**Expected Behavior / Usage:**

Input describes deletion target names, source table, joins, filters, ordering, limit, offset, suffix text, and placeholder style. If an explicit source is supplied it is used after `FROM`; otherwise the target can serve as the source. Multiple deletion targets are rendered between `DELETE` and `FROM`. Zero limit and offset are emitted. A delete request without any usable target or source is invalid and must render `error=missing_delete_target`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_delete_statements.json`

```json
{
    "description": "Build DELETE statements from deletion targets, source tables, joins, filters, ordering, limits, offsets, suffixes, and placeholder style.",
    "cases": [
        {
            "input": {
                "operation": "delete",
                "scenario": "full_delete",
                "clauses": {
                    "source": "a",
                    "filter": "b = ?",
                    "order_by": [
                        "c"
                    ],
                    "limit": 2,
                    "offset": 3,
                    "prefix": "WITH prefix AS ?",
                    "suffix": "RETURNING ?"
                }
            },
            "expected_output": "sql=WITH prefix AS ? DELETE FROM a WHERE b = ? ORDER BY c LIMIT 2 OFFSET 3 RETURNING ?\nargs=[0,1,4]\n"
        },
        {
            "input": {
                "operation": "delete",
                "scenario": "explicit_source_over_target",
                "clauses": {
                    "target": "b",
                    "source": "a",
                    "filter": "b = ?"
                }
            },
            "expected_output": "sql=DELETE FROM a WHERE b = ?\nargs=[1]\n"
        }
    ]
}
```

---

### Feature 7: CASE Expression Rendering

**As a developer**, I want to compose SQL conditional expressions inside generated queries, so I can represent conditional projection logic while preserving bind argument order.

**Expected Behavior / Usage:**

Input describes a conditional SQL expression with an optional operand, one or more condition/result pairs, optional else expression, optional alias, and source table. Output is the enclosing SELECT statement plus the ordered arguments. Searched conditions may themselves be predicates or raw expressions. A conditional expression with no condition/result pair is invalid and must render `error=missing_case_when`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_case_expressions.json`

```json
{
    "description": "Build SQL CASE expressions, including simple case operands, searched cases, raw expressions, aliases, ELSE branches, and validation for missing WHEN clauses.",
    "cases": [
        {
            "input": {
                "operation": "case_expression",
                "scenario": "simple_value_case",
                "case": {
                    "operand": "[the exact string literal used for numeric operands in case expressions]",
                    "when_then": [
                        [
                            "1",
                            "one"
                        ],
                        [
                            "2",
                            "two"
                        ]
                    ],
                    "else": {
                        "expression": "?",
                        "args": [
                            "big [the exact string literal used for numeric operands in case expressions]"
                        ]
                    },
                    "source": "table"
                }
            },
            "expected_output": "sql=SELECT CASE [the exact string literal used for numeric operands in case expressions] WHEN 1 THEN one WHEN 2 THEN two ELSE ? END FROM table\nargs=[\"big [the exact string literal used for numeric operands in case expressions]\"]\n"
        },
        {
            "input": {
                "operation": "case_expression",
                "scenario": "complex_operand_alias",
                "case": {
                    "operand": {
                        "expression": "? > ?",
                        "args": [
                            10,
                            5
                        ]
                    },
                    "when_then": [
                        [
                            "true",
                            "'T'"
                        ]
                    ],
                    "alias": "complexCase",
                    "source": "table"
                }
            },
            "expected_output": "sql=SELECT (CASE ? > ? WHEN true THEN 'T' END) AS complexCase FROM table\nargs=[10,5]\n"
        }
    ]
}
```

---

### Feature 8: Runner Execution

**As a developer**, I want to send rendered statements to an injected executor or query interface, so I can verify the SQL string delivered to database-facing integrations without executing a real database.

**Expected Behavior / Usage:**

Input describes a statement and whether it should be exercised through execution, query, single-row query, or direct helper-style calls. Output reports the SQL string observed by the recording runner for each call. When no runner is configured, execution, query, and scan paths must render `runner_not_configured` as the neutral error category.

**Test Cases:** `rcb_tests/public_test_cases/feature8_runner_execution.json`

```json
{
    "description": "Execute rendered statements through an injected execution/query interface and report which SQL string the runner receives, including normalized errors when no runner is configured.",
    "cases": [
        {
            "input": {
                "operation": "runner",
                "scenario": "select_runner",
                "statement": {
                    "kind": "select",
                    "columns": [
                        "test"
                    ]
                }
            },
            "expected_output": "exec_sql=SELECT test\nquery_sql=SELECT test\nqueryrow_sql=SELECT test\nscan_error=none\n"
        },
        {
            "input": {
                "operation": "runner",
                "scenario": "insert_runner",
                "statement": {
                    "kind": "insert",
                    "target": "test",
                    "rows": [
                        [
                            1
                        ]
                    ]
                }
            },
            "expected_output": "exec_sql=INSERT INTO test VALUES (?)\n"
        }
    ]
}
```

---

### Feature 9: Reusable Statement Configuration

**As a developer**, I want to carry common runner and placeholder settings into subsequently created statements, so I can avoid repeating configuration for every generated statement.

**Expected Behavior / Usage:**

Input describes a reusable statement configuration and a statement created from it. A configured runner must receive the rendered SQL when the statement is executed. A configured [the exact string literal used for numeric operands in case expressions]ed placeholder style must rewrite placeholders in statements created from that configuration before execution.

**Test Cases:** `rcb_tests/public_test_cases/feature9_statement_defaults.json`

```json
{
    "description": "Create statements from a reusable statement configuration that carries runner and placeholder settings into generated statements.",
    "cases": [
        {
            "input": {
                "operation": "statement_config",
                "scenario": "configured_runner",
                "config": {
                    "runner": "recording"
                },
                "statement": {
                    "kind": "select",
                    "columns": [
                        "test"
                    ]
                }
            },
            "expected_output": "exec_sql=SELECT test\n"
        },
        {
            "input": {
                "operation": "statement_config",
                "scenario": "configured_placeholders",
                "config": {
                    "runner": "recording",
                    "placeholder_style": "[the exact string literal used for numeric operands in case expressions]ed"
                },
                "statement": {
                    "kind": "select",
                    "columns": [
                        "test"
                    ],
                    "filter": "x = ?"
                }
            },
            "expected_output": "exec_sql=SELECT test WHERE x = $1\n"
        }
    ]
}
```

---

### Feature 10: Prepared Statement Cache

**As a developer**, I want to reuse prepared statements by SQL text, so I can avoid preparing identical query text more than once.

**Expected Behavior / Usage:**

Input is a sequence of SQL strings to prepare through a recording preparer. Repeated identical SQL text must be prepared only once, and output reports the last prepared SQL text together with the [the exact string literal used for numeric operands in case expressions] of times the underlying preparer was called.

**Test Cases:** `rcb_tests/public_test_cases/feature10_prepared_statement_cache.json`

```json
{
    "description": "Cache prepared statements by query text so the same SQL string is prepared only once while distinct SQL strings are still sent to the underlying preparer.",
    "cases": [
        {
            "input": {
                "operation": "statement_cache",
                "queries": [
                    "SELECT 1",
                    "SELECT 1"
                ]
            },
            "expected_output": "last_prepared_sql=SELECT 1\nprepare_count=1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- handle expressions exactly like the math expression parser does
- order args consistent with the output structure of a full select example
