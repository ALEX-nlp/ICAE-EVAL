## Product Requirement Document

# Bulk Database Row Insertion - Batched record persistence and SQL preview contracts

## Project Goal

Build a database row insertion helper that allows developers to queue many records, persist them in batches, and inspect backend-specific insert statements without writing repetitive per-row database calls.

---

## Background & Problem

Without this library/tool, developers are forced to loop over records and issue many individual inserts or manually construct database-specific multi-row statements. This leads to repetitive code, inconsistent default handling, fragile conflict clauses, and unnecessary database round trips.

With this library/tool, developers can describe rows once, save them as batches, rely on database defaults and generated timestamps, attach save hooks, and obtain backend-appropriate insert behavior through one consistent interface.

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

### Feature 1: Queue State and Default Batch Limit

**As a developer**, I want to create a bulk row writer and inspect its queue state before saving, so I can decide when to flush rows.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `queue_state`. The input may request the default batch limit and may provide rows as ordered arrays of field values. The output reports the default batch limit when requested, whether the writer is pending before any row is added, the initial pending count, and the pending flag and pending count after each row is queued.

**Test Cases:** `rcb_tests/public_test_cases/feature1_queue_state.json`

```json
{
    "description": "A newly created bulk row writer reports an empty queue, exposes its default batch limit, and reports queued row counts as rows are added before any explicit save.",
    "cases": [
        {
            "input": {
                "scenario": "queue_state",
                "show_default_batch_limit": [a boolean toggle for this buffered insert state],
                "rows": [
                    [
                        "Hello",
                        15,
                        [a boolean toggle for this buffered insert state]
                    ]
                ]
            },
            "expected_output": "default_batch_limit=500\npending_initial=false\npending_count_initial=0\npending_after_row1=[a boolean toggle for this buffered insert state]\npending_count_after_row1=1\n"
        }
    ]
}
```

---

### Feature 2: Buffered Save

**As a developer**, I want to queue rows and persist them with an explicit save, so I can batch multiple records into one database write.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `buffered_insert` and whose `rows` value is an array of row arrays or row objects. Row arrays map values to the writable fields in order; row objects map field names to values. The output reports pending state and database count before and after save, generated identifier batch count, and each persisted record's externally visible fields. Missing color uses the database default, while an explicit null color is persisted as null.

**Test Cases:** `rcb_tests/public_test_cases/feature2_buffered_save.json`

```json
{
    "description": "Rows added to a buffered writer remain pending until saved, then are persisted with their supplied field values and database-backed defaults.",
    "cases": [
        {
            "input": {
                "scenario": "buffered_insert",
                "rows": [
                    [
                        "Yo",
                        15,
                        false
                    ],
                    [
                        "Hello",
                        25,
                        [a boolean toggle for this buffered insert state]
                    ]
                ]
            },
            "expected_output": "pending_before_save=[a boolean toggle for this buffered insert state]\npending_count_before_save=2\ndatabase_count_before_save=0\npending_after_save=false\npending_count_after_save=0\ndatabase_count_after_save=2\ngenerated_id_batches=0\nrecord1.greeting=Yo\nrecord1.age=15\nrecord1.happy=false\nrecord1.color=chartreuse\nrecord1.created_at_present=[a boolean toggle for this buffered insert state]\nrecord1.updated_at_present=[a boolean toggle for this buffered insert state]\nrecord2.greeting=Hello\nrecord2.age=25\nrecord2.happy=[a boolean toggle for this buffered insert state]\nrecord2.color=chartreuse\nrecord2.created_at_present=[a boolean toggle for this buffered insert state]\nrecord2.updated_at_present=[a boolean toggle for this buffered insert state]\n"
        },
        {
            "input": {
                "scenario": "buffered_insert",
                "rows": [
                    {
                        "greeting": "Yo",
                        "age": 20,
                        "happy": false
                    }
                ]
            },
            "expected_output": "pending_before_save=[a boolean toggle for this buffered insert state]\npending_count_before_save=1\ndatabase_count_before_save=0\npending_after_save=false\npending_count_after_save=0\ndatabase_count_after_save=1\ngenerated_id_batches=0\nrecord1.greeting=Yo\nrecord1.age=20\nrecord1.happy=false\nrecord1.color=chartreuse\nrecord1.created_at_present=[a boolean toggle for this buffered insert state]\nrecord1.updated_at_present=[a boolean toggle for this buffered insert state]\n"
        },
        {
            "input": {
                "scenario": "buffered_insert",
                "rows": [
                    {
                        "greeting": "Hello",
                        "age": 20,
                        "happy": false,
                        "color": null
                    }
                ]
            },
            "expected_output": "pending_before_save=[a boolean toggle for this buffered insert state]\npending_count_before_save=1\ndatabase_count_before_save=0\npending_after_save=false\npending_count_after_save=0\ndatabase_count_after_save=1\ngenerated_id_batches=0\nrecord1.greeting=Hello\nrecord1.age=20\nrecord1.happy=false\nrecord1.color=null\nrecord1.created_at_present=[a boolean toggle for this buffered insert state]\nrecord1.updated_at_present=[a boolean toggle for this buffered insert state]\n"
        }
    ]
}
```

---

### Feature 3: Immediate Save Entry Points

**As a developer**, I want to submit rows for immediate insertion or through a scoped writer block, so I can persist a collection without manually managing a separate save step.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `immediate_insert` or `block_insert` and whose `rows` value is the collection to persist. The output reports the final database count and persisted record fields. The collection may mix ordered row arrays and row objects, and omitted optional fields are persisted using database defaults or null-compatible field behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature3_immediate_save.json`

```json
{
    "description": "Supplying rows to the high-level insert entry point persists the full collection immediately without requiring a separate save call.",
    "cases": [
        {
            "input": {
                "scenario": "immediate_insert",
                "rows": [
                    [
                        "Hello",
                        15,
                        [a boolean toggle for this buffered insert state]
                    ],
                    {
                        "greeting": "Hey",
                        "age": 20,
                        "happy": false
                    }
                ]
            },
            "expected_output": "database_count=2\nrecord1.greeting=Hello\nrecord1.age=15\nrecord1.happy=[a boolean toggle for this buffered insert state]\nrecord1.color=chartreuse\nrecord1.created_at_present=[a boolean toggle for this buffered insert state]\nrecord1.updated_at_present=[a boolean toggle for this buffered insert state]\nrecord2.greeting=Hey\nrecord2.age=20\nrecord2.happy=false\nrecord2.color=chartreuse\nrecord2.created_at_present=[a boolean toggle for this buffered insert state]\nrecord2.updated_at_present=[a boolean toggle for this buffered insert state]\n"
        },
        {
            "input": {
                "scenario": "block_insert",
                "rows": [
                    {
                        "greeting": "Hello"
                    }
                ]
            },
            "expected_output": "database_count=1\nrecord1.greeting=Hello\nrecord1.age=null\nrecord1.happy=false\nrecord1.color=chartreuse\nrecord1.created_at_present=[a boolean toggle for this buffered insert state]\nrecord1.updated_at_present=[a boolean toggle for this buffered insert state]\n"
        }
    ]
}
```

---

### Feature 4: Automatic Flush at Batch Limit

**As a developer**, I want queued rows to flush automatically when the configured batch limit is exceeded, so large imports can be split into manageable database writes.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `batch_limit`, a numeric `batch_limit`, and a `rows` collection. The output reports the database count and pending count after each row is added and after the final save. When the queue is already at the batch limit before a new row is added, the existing queued rows are persisted first and the new row remains pending until a later save.

**Test Cases:** `rcb_tests/public_test_cases/feature4_batch_limit.json`

```json
{
    "description": "When the queued row count reaches the configured batch limit, adding the next row flushes the current batch automatically and leaves the new row pending until the final save.",
    "cases": [
        {
            "input": {
                "scenario": "batch_limit",
                "batch_limit": 1,
                "rows": [
                    [
                        "Hello",
                        15,
                        [a boolean toggle for this buffered insert state]
                    ],
                    [
                        "Yo",
                        20,
                        false
                    ]
                ]
            },
            "expected_output": "after_row1_database_count=0\nafter_row1_pending_count=1\nafter_row2_database_count=1\nafter_row2_pending_count=1\nafter_final_save_database_count=2\nrecord1.greeting=Hello\nrecord1.age=15\nrecord1.happy=[a boolean toggle for this buffered insert state]\nrecord1.color=chartreuse\nrecord1.created_at_present=[a boolean toggle for this buffered insert state]\nrecord1.updated_at_present=[a boolean toggle for this buffered insert state]\nrecord2.greeting=Yo\nrecord2.age=20\nrecord2.happy=false\nrecord2.color=chartreuse\nrecord2.created_at_present=[a boolean toggle for this buffered insert state]\nrecord2.updated_at_present=[a boolean toggle for this buffered insert state]\n"
        }
    ]
}
```

---

### Feature 5: Timestamp Defaults

**As a developer**, I want missing timestamp fields to be populated consistently during a batch save, so records have valid creation and update timestamps without manual values.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `timestamp_defaults` and whose rows omit timestamp fields. The output reports that the records were persisted, that creation and update timestamps are present, and that rows saved in the same batch share one generated timestamp value for creation and update time.

**Test Cases:** `rcb_tests/public_test_cases/feature5_time_defaults.json`

```json
{
    "description": "Missing timestamp fields are filled during save; rows in the same batch share one generated timestamp value for creation and update time.",
    "cases": [
        {
            "input": {
                "scenario": "timestamp_defaults",
                "rows": [
                    [
                        "Hello",
                        15,
                        [a boolean toggle for this buffered insert state]
                    ],
                    [
                        "Howdy",
                        20,
                        false
                    ]
                ]
            },
            "expected_output": "database_count=2\nrecord1.created_at_present=[a boolean toggle for this buffered insert state]\nrecord1.updated_at_present=[a boolean toggle for this buffered insert state]\nrecord2.created_at_present=[a boolean toggle for this buffered insert state]\nrecord2.updated_at_present=[a boolean toggle for this buffered insert state]\nbatch_created_at_equal=[a boolean toggle for this buffered insert state]\nbatch_created_updated_equal=[a boolean toggle for this buffered insert state]\n"
        }
    ]
}
```

---

### Feature 6: Empty Save and Default Writable Fields

**As a developer**, I want empty saves to be harmless and want to discover the default writable fields, so I can build import flows safely.

**Expected Behavior / Usage:**

The adapter accepts either an input object whose `scenario` is `save_empty` or one whose `scenario` is `default_columns`. Empty save output reports no pending rows before and after save and a zero database count. Default field output reports the comma-separated writable field names, excluding the generated primary identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature6_empty_and_columns.json`

```json
{
    "description": "Saving an empty writer performs no database insert, and the default writable field list contains every data field except the generated primary identifier.",
    "cases": [
        {
            "input": {
                "scenario": "save_empty"
            },
            "expected_output": "pending_before_save=false\ndatabase_count_after_save=0\npending_after_save=false\n"
        },
        {
            "input": {
                "scenario": "default_columns"
            },
            "expected_output": "columns=greeting,age,happy,created_at,updated_at,color\n"
        }
    ]
}
```

---

### Feature 7: Generated Identifier Result Batches

**As a developer**, I want to optionally collect generated identifier result batches, so I can associate saved rows with database-generated identifiers when the backend supports it.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `generated_ids` and whose `batches` value is an array of row collections to save one batch at a time. The output reports the result-batch count initially, after an empty save, after each non-empty batch save, and the final database count. Empty saves do not create result batches; each non-empty save creates one.

**Test Cases:** `rcb_tests/public_test_cases/feature7_generated_ids.json`

```json
{
    "description": "When generated identifier collection is requested, each non-empty save adds one result batch while empty saves add none.",
    "cases": [
        {
            "input": {
                "scenario": "generated_ids",
                "batches": [
                    [
                        {
                            "greeting": "first"
                        },
                        {
                            "greeting": "second"
                        }
                    ],
                    [
                        {
                            "greeting": "third"
                        },
                        {
                            "greeting": "fourth"
                        }
                    ]
                ]
            },
            "expected_output": "generated_id_batches_initial=0\ngenerated_id_batches_after_empty_save=0\ngenerated_id_batches_after_batch1=1\ngenerated_id_batches_after_batch2=2\ndatabase_count=4\n"
        }
    ]
}
```

---

### Feature 8: Save Hooks

**As a developer**, I want callbacks around a save to observe or alter pending rows, so I can apply import-time filtering or side effects before persistence completes.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `hook_counters`, `hook_filter`, or `hook_clear`. Counter output reports that before-save and after-save hooks ran once around a non-empty save. Filter output reports only rows not rejected by the configured greeting value. Clear output reports that clearing the pending rows before persistence results in zero records and no pending rows after save.

**Test Cases:** `rcb_tests/public_test_cases/feature8_save_hooks.json`

```json
{
    "description": "Registered save hooks run once around a non-empty save and may inspect or alter the pending rows before persistence.",
    "cases": [
        {
            "input": {
                "scenario": "hook_counters",
                "rows": [
                    [
                        "Yo",
                        15,
                        false
                    ],
                    [
                        "Hello",
                        25,
                        [a boolean toggle for this buffered insert state]
                    ]
                ]
            },
            "expected_output": "before_save_calls=1\nafter_save_calls=1\ndatabase_count=2\n"
        },
        {
            "input": {
                "scenario": "hook_filter",
                "reject_greeting": "Yo",
                "rows": [
                    [
                        "Yo",
                        15,
                        false
                    ],
                    [
                        "Hello",
                        25,
                        [a boolean toggle for this buffered insert state]
                    ]
                ]
            },
            "expected_output": "database_count=1\nrecord1.greeting=Hello\nrecord1.age=25\nrecord1.happy=[a boolean toggle for this buffered insert state]\nrecord1.color=chartreuse\nrecord1.created_at_present=[a boolean toggle for this buffered insert state]\nrecord1.updated_at_present=[a boolean toggle for this buffered insert state]\n"
        },
        {
            "input": {
                "scenario": "hook_clear",
                "rows": [
                    [
                        "Yo",
                        15,
                        false
                    ],
                    [
                        "Hello",
                        25,
                        [a boolean toggle for this buffered insert state]
                    ]
                ]
            },
            "expected_output": "database_count=0\npending_after_save=false\n"
        }
    ]
}
```

---

### Feature 9: SQLite-Style SQL Rendering

**As a developer**, I want generated SQL previews for SQLite-style engines, so I can verify the engine-specific conflict-skip syntax before execution.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `sql_preview`, whose `database_engine` is `SQLite`, and whose options include whether conflicts should be skipped. The output reports the selected database engine and the exact SQL statement, including quoted table and field names, inserted literal values, default color handling, and the SQLite conflict-skip modifier when enabled.

**Test Cases:** `rcb_tests/public_test_cases/feature9_sql_sqlite.json`

```json
{
    "description": "For SQLite-style engines, conflict skipping is rendered with the engine-specific insert modifier and the generated statement includes quoted table and field names plus database defaults.",
    "cases": [
        {
            "input": {
                "scenario": "sql_preview",
                "database_engine": "SQLite",
                "skip_conflicts": false,
                "rows": [
                    [
                        "Yo",
                        15,
                        false,
                        null,
                        null
                    ]
                ]
            },
            "expected_output": "database_engine=SQLite\nsql=INSERT  INTO \"testings\" (\"greeting\",\"age\",\"happy\",\"created_at\",\"updated_at\",\"color\") VALUES ('Yo',15,0,NULL,NULL,'chartreuse')\n"
        },
        {
            "input": {
                "scenario": "sql_preview",
                "database_engine": "SQLite",
                "skip_conflicts": [a boolean toggle for this buffered insert state],
                "rows": [
                    [
                        "Yo",
                        15,
                        false,
                        null,
                        null
                    ]
                ]
            },
            "expected_output": "database_engine=SQLite\nsql=INSERT OR IGNORE INTO \"testings\" (\"greeting\",\"age\",\"happy\",\"created_at\",\"updated_at\",\"color\") VALUES ('Yo',15,0,NULL,NULL,'chartreuse')\n"
        }
    ]
}
```

---

### Feature 10: MySQL- and PostgreSQL-Family SQL Rendering

**As a developer**, I want generated SQL previews for MySQL-family and PostgreSQL-family engines, so I can verify conflict handling and generated identifier return clauses before execution.

**Expected Behavior / Usage:**

The adapter accepts an input object whose `scenario` is `sql_preview`, with `database_engine` set to a MySQL-family or PostgreSQL-family engine and options for conflict skipping, conflict updating, and generated identifier returning. The output reports the selected database engine and exact SQL statement using the engine's native conflict-skip, duplicate-update, conflict-update, and identifier-returning fragments.

**Test Cases:** `rcb_tests/public_test_cases/feature10_sql_mysql_postgresql.json`

```json
{
    "description": "For MySQL-family and PostgreSQL-family engines, conflict skipping, conflict updating, and generated identifier returning are rendered using the database engine's native statement fragments.",
    "cases": [
        {
            "input": {
                "scenario": "sql_preview",
                "database_engine": "MySQL",
                "skip_conflicts": [a boolean toggle for this buffered insert state],
                "rows": [
                    [
                        "Yo",
                        15,
                        false,
                        null,
                        null
                    ]
                ]
            },
            "expected_output": "database_engine=MySQL\nsql=INSERT IGNORE INTO \"testings\" (\"greeting\",\"age\",\"happy\",\"created_at\",\"updated_at\",\"color\") VALUES ('Yo',15,0,NULL,NULL,'chartreuse')\n"
        },
        {
            "input": {
                "scenario": "sql_preview",
                "database_engine": "Mysql2",
                "skip_conflicts": [a boolean toggle for this buffered insert state],
                "update_on_conflict": [a boolean toggle for this buffered insert state],
                "rows": [
                    [
                        "Yo",
                        15,
                        false,
                        null,
                        null
                    ]
                ]
            },
            "expected_output": "database_engine=Mysql2\nsql=INSERT IGNORE INTO \"testings\" (\"greeting\",\"age\",\"happy\",\"created_at\",\"updated_at\",\"color\") VALUES ('Yo',15,0,NULL,NULL,'chartreuse') ON DUPLICATE KEY UPDATE `greeting`=VALUES(`greeting`), `age`=VALUES(`age`), `happy`=VALUES(`happy`), `created_at`=VALUES(`created_at`), `updated_at`=VALUES(`updated_at`), `color`=VALUES(`color`)\n"
        },
        {
            "input": {
                "scenario": "sql_preview",
                "database_engine": "PostgreSQL",
                "skip_conflicts": [a boolean toggle for this buffered insert state],
                "return_generated_ids": [a boolean toggle for this buffered insert state],
                "rows": [
                    [
                        "Yo",
                        15,
                        false,
                        null,
                        null
                    ]
                ]
            },
            "expected_output": "database_engine=PostgreSQL\nsql=INSERT  INTO \"testings\" (\"greeting\",\"age\",\"happy\",\"created_at\",\"updated_at\",\"color\") VALUES ('Yo',15,0,NULL,NULL,'chartreuse') ON CONFLICT DO NOTHING RETURNING id\n"
        },
        {
            "input": {
                "scenario": "sql_preview",
                "database_engine": "PostgreSQL",
                "update_on_conflict": [
                    "greeting",
                    "age",
                    "happy"
                ],
                "return_generated_ids": [a boolean toggle for this buffered insert state],
                "rows": [
                    [
                        "Yo",
                        15,
                        false,
                        null,
                        null
                    ]
                ]
            },
            "expected_output": "database_engine=PostgreSQL\nsql=INSERT  INTO \"testings\" (\"greeting\",\"age\",\"happy\",\"created_at\",\"updated_at\",\"color\") VALUES ('Yo',15,0,NULL,NULL,'chartreuse') ON CONFLICT(greeting, age, happy) DO UPDATE SET greeting=EXCLUDED.greeting, age=EXCLUDED.age, happy=EXCLUDED.happy, created_at=EXCLUDED.created_at, updated_at=EXCLUDED.updated_at, color=EXCLUDED.color RETURNING id\n"
        },
        {
            "input": {
                "scenario": "sql_preview",
                "database_engine": "PostGIS",
                "skip_conflicts": [a boolean toggle for this buffered insert state],
                "return_generated_ids": [a boolean toggle for this buffered insert state],
                "rows": [
                    [
                        "Yo",
                        15,
                        false,
                        null,
                        null
                    ]
                ]
            },
            "expected_output": "database_engine=PostGIS\nsql=INSERT  INTO \"testings\" (\"greeting\",\"age\",\"happy\",\"created_at\",\"updated_at\",\"color\") VALUES ('Yo',15,0,NULL,NULL,'chartreuse') ON CONFLICT DO NOTHING RETURNING id\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the string escaping convention used in the PRD for single-line string literals
- align with the PostgreSQL-specific syntax rules established in the facts section
