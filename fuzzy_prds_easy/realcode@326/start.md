## Product Requirement Document

# Online Schema Change Toolkit - Safe relational database migrations and background data repair

## Project Goal

Build a database migration safety and background data repair toolkit that allows developers to evolve relational schemas and repair existing rows without long blocking locks, accidental table rewrites, or unbounded one-shot data updates.

---

## Background & Problem

Without this library/tool, developers are forced to manually reason about database version differences, lock strength, validation timing, retry behavior, index state, and batch data repair semantics for each migration. This leads to repetitive migration boilerplate, unsafe production deploys, hidden blocking operations, and data fixes that are hard to resume or verify.

With this library/tool, developers can ask whether a planned schema operation is safe, use helpers that apply changes in safer phases, and run background batches that expose clear database-visible outcomes.

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

### Feature 1: Column Change Safety Assessment

**As a developer**, I want to assess whether a proposed column addition can run without long blocking table rewrites, so I can avoid unsafe schema changes before they reach production.

**Expected Behavior / Usage:**

The input is an object with action `assess_column_change`, a scenario describing the proposed column addition, and the target database major version. The output is either `[a safe operation under non-transactional validation rules]` or an unsafe result with `error=unsafe_migration` and a normalized `reason`. Constant defaults on older database versions, volatile expression defaults, document-column types without equality support, and stored generated columns are reported as unsafe; cases that the database can apply without the tested blocking behavior are reported safe.

**Test Cases:** `rcb_tests/public_test_cases/feature1_column_safety_assessment.json`

```json
{
    "description": "Assess whether adding a column is safe for the selected database version and default-value shape.",
    "cases": [
        {
            "input": {
                "action": "assess_column_change",
                "scenario": "constant_default",
                "database_major_version": 10
            },
            "expected_output": "result=unsafe\nerror=unsafe_migration\nreason=column_default_rewrite\n"
        },
        {
            "input": {
                "action": "assess_column_change",
                "scenario": "constant_default",
                "database_major_version": 11
            },
            "expected_output": "[a safe operation under non-transactional validation rules]\n"
        },
        {
            "input": {
                "action": "assess_column_change",
                "scenario": "volatile_expression_default",
                "database_major_version": 11
            },
            "expected_output": "result=unsafe\nerror=unsafe_migration\nreason=column_default_rewrite\n"
        }
    ]
}
```

---

### Feature 2: Foreign-Key Change Safety Assessment

**As a developer**, I want to assess foreign-key migration patterns before execution, so I can separate safe deferred validation from lock-heavy validation patterns.

**Expected Behavior / Usage:**

The input is an object with action `assess_foreign_key_change` and a scenario describing how the foreign key is introduced or validated. The output is either `[a safe operation under non-transactional validation rules]` or an unsafe result with `error=unsafe_migration` and a normalized `reason`. Adding a validated foreign key to existing tables is unsafe, adding it without immediate validation is safe, validating while still inside a heavy-lock transaction is unsafe, and validating outside that transaction is safe.

**Test Cases:** `rcb_tests/public_test_cases/feature2_foreign_key_safety_assessment.json`

```json
{
    "description": "Assess whether foreign-key migration patterns are safe based on validation timing, transaction boundaries, and key shape.",
    "cases": [
        {
            "input": {
                "action": "assess_foreign_key_change",
                "scenario": "validated_existing_tables"
            },
            "expected_output": "result=unsafe\nerror=unsafe_migration\nreason=foreign_key_validation_lock\n"
        },
        {
            "input": {
                "action": "assess_foreign_key_change",
                "scenario": "deferred_validation_existing_tables"
            },
            "expected_output": "[a safe operation under non-transactional validation rules]\n"
        },
        {
            "input": {
                "action": "assess_foreign_key_change",
                "scenario": "deferred_then_validated_in_transaction"
            },
            "expected_output": "result=unsafe\nerror=unsafe_migration\nreason=foreign_key_validation_in_transaction\n"
        },
        {
            "input": {
                "action": "assess_foreign_key_change",
                "scenario": "deferred_then_validated_without_transaction"
            },
            "expected_output": "[a safe operation under non-transactional validation rules]\n"
        }
    ]
}
```

---

### Feature 3: Defaulted Column Application

**As a developer**, I want to apply a new column with a default while preserving existing data, so I can observe the real database metadata and row effects after the change.

**Expected Behavior / Usage:**

The input is an object with action `apply_defaulted_column`, the database major version, and whether the requested column should remain nullable. The output reports the new column name, stored default, metadata nullability, the value backfilled into an existing row, and whether a new null value is rejected. Older database behavior can enforce a not-null requirement with a check constraint while the column metadata remains nullable; newer direct not-null behavior is represented by the corresponding metadata and rejection signal in the hidden cases.

**Test Cases:** `rcb_tests/public_test_cases/feature3_defaulted_column_application.json`

```json
{
    "description": "Apply a column with a default value and report database-visible column metadata and effects on existing and new records.",
    "cases": [
        {
            "input": {
                "action": "apply_defaulted_column",
                "database_major_version": 11,
                "nullable": true
            },
            "expected_output": "column=status\ndefault=0\ncolumn_nullable=true\nexisting_record_value=0\nrejects_null=false\n"
        },
        {
            "input": {
                "action": "apply_defaulted_column",
                "database_major_version": 10,
                "nullable": false
            },
            "expected_output": "column=status\ndefault=0\ncolumn_nullable=true\nexisting_record_value=0\n[field representing rejection status enforcement for new rows]\n"
        }
    ]
}
```

---

### Feature 4: Constraint Management

**As a developer**, I want to create and validate data constraints incrementally, so I can protect future writes while handling existing invalid rows explicitly.

**Expected Behavior / Usage:**

The input is an object with action `enforce_check_constraint` and a scenario describing a numeric or text constraint operation. The output reports the normalized constraint name and whether invalid rows are rejected, whether preexisting invalid rows were present, or a normalized error if a requested constraint cannot be found. Unvalidated constraints must still reject new invalid rows, validation must fail while old invalid rows remain, and missing constraint validation must return `error=constraint_not_found` without host-runtime exception details.

**Test Cases:** `rcb_tests/public_test_cases/feature4_constraint_management.json`

```json
{
    "description": "Create or validate check-style constraints and report whether invalid existing rows and invalid future rows are handled correctly.",
    "cases": [
        {
            "input": {
                "action": "enforce_check_constraint",
                "scenario": "positive_points"
            },
            "expected_output": "constraint=points_non_negative\nrejects_invalid=true\n"
        },
        {
            "input": {
                "action": "enforce_check_constraint",
                "scenario": "unvalidated_positive_points"
            },
            "expected_output": "constraint=points_non_negative\nexisting_invalid_rows=1\nrejects_new_invalid=true\n"
        },
        {
            "input": {
                "action": "enforce_check_constraint",
                "scenario": "missing_constraint_validation"
            },
            "expected_output": "error=constraint_not_found\nconstraint=non_existing\n"
        }
    ]
}
```

---

### Feature 5: Index Management

**As a developer**, I want to create and remove indexes through migration helpers, so I can confirm idempotence, generated names, and transaction restrictions through database-visible signals.

**Expected Behavior / Usage:**

The input is an object with action `manage_index` and an index scenario. The output reports index identity and whether it exists before or after the operation, how duplicate creation is handled, or a normalized transaction error. Creating a single-column index makes it visible, creating a composite index exposes its generated database name, removing an existing index removes it, removing a missing index is tolerated in hidden cases, and concurrent index operations inside a transaction return `error=transaction_forbidden`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_index_management.json`

```json
{
    "description": "Create and remove indexes and report database-visible index existence, generated names, idempotence, and transaction restrictions.",
    "cases": [
        {
            "input": {
                "action": "manage_index",
                "scenario": "add_single_column_index"
            },
            "expected_output": "index=name\nexists=true\n"
        },
        {
            "input": {
                "action": "manage_index",
                "scenario": "add_composite_index_with_generated_name"
            },
            "expected_output": "index=index_users_on_name_and_company_id\nexists=true\n"
        },
        {
            "input": {
                "action": "manage_index",
                "scenario": "remove_existing_index"
            },
            "expected_output": "index=name\nexisted_before=true\nexists_after=false\n"
        },
        {
            "input": {
                "action": "manage_index",
                "scenario": "concurrent_add_inside_transaction"
            },
            "expected_output": "error=transaction_forbidden\n"
        }
    ]
}
```

---

### Feature 6: Background Batch Processing

**As a developer**, I want to process data repair batches over database relations, so I can verify both selected records and changed or preserved rows.

**Expected Behavior / Usage:**

The input is an object with action `run_background_batch` and a batch scenario. The output reports relation membership and the row-level effect of the batch. Boolean backfills select rows needing change and update them, identifier copies copy source values to destination columns, text-to-document copies use database casting, orphan deletion removes rows missing required links including rows hidden by default filters, multi-link deletion preserves rows that have at least one required link, and unknown links return `error=association_not_found` with the raw link selector.

**Test Cases:** `rcb_tests/public_test_cases/feature6_background_batch_processing.json`

```json
{
    "description": "Run background data batches and report relation membership plus the database rows changed or preserved by each batch.",
    "cases": [
        {
            "input": {
                "action": "run_background_batch",
                "scenario": "backfill_boolean_column"
            },
            "expected_output": "relation_ids=1,2\nadmin_values=false,false,false\ncount_type=integer\n"
        },
        {
            "input": {
                "action": "run_background_batch",
                "scenario": "copy_identifier_column"
            },
            "expected_output": "copied_values=1,2\nsource_values=1,2\n"
        },
        {
            "input": {
                "action": "run_background_batch",
                "scenario": "delete_records_without_parent"
            },
            "expected_output": "relation_ids=1,2\nremaining_ids=3\nkept_parented=true\n"
        },
        {
            "input": {
                "action": "run_background_batch",
                "scenario": "unknown_parent_link"
            },
            "expected_output": "error=association_not_found\nassociation=missing_link\n"
        }
    ]
}
```

---

### Feature 7: Background Task Resolution

**As a developer**, I want to resolve a named background task, so I can distinguish valid tasks, missing names, and names that point to non-task objects.

**Expected Behavior / Usage:**

The input is an object with action `resolve_background_task` and a task label. The output reports the task label, whether it resolved, and either the normalized base type for a valid task or a normalized error category plus the raw resolved name. Missing labels return `error=background_task_not_found`; labels that resolve to an object that does not implement the background-task contract return `error=not_background_task`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_background_task_resolution.json`

```json
{
    "description": "Resolve a named background task and report whether the name identifies a valid task, is missing, or points to the wrong kind of object.",
    "cases": [
        {
            "input": {
                "action": "resolve_background_task",
                "task_label": "make_records_inactive"
            },
            "expected_output": "task=make_records_inactive\nresolved=true\nbase_type=background_task\n"
        },
        {
            "input": {
                "action": "resolve_background_task",
                "task_label": "does_not_exist"
            },
            "expected_output": "task=does_not_exist\nresolved=false\nerror=background_task_not_found\nname=DoesNotExist\n"
        },
        {
            "input": {
                "action": "resolve_background_task",
                "task_label": "plain_object"
            },
            "expected_output": "task=plain_object\nresolved=false\nerror=not_background_task\nname=PlainObject\n"
        }
    ]
}
```

---

### Feature 8: Lock Retry Behavior

**As a developer**, I want to retry schema changes that hit database locks, so I can differentiate whole-migration retries from operation-level retries.

**Expected Behavior / Usage:**

The input is an object with action `retry_locked_change` and a retry scenario. The output reports `result=lock_timeout`, the number of attempts made, and `error=database_lock_timeout`. A transactional migration retries the whole migration body, so the attempt count includes the initial run plus configured retries; a nontransactional migration retries only the locked database operation, so the migration body is counted once.

**Test Cases:** `rcb_tests/public_test_cases/feature8_lock_retry_behavior.json`

```json
{
    "description": "Run a schema change while the target table is locked and report timeout outcome plus how many times the migration body was attempted.",
    "cases": [
        {
            "input": {
                "action": "retry_locked_change",
                "scenario": "transactional_change"
            },
            "expected_output": "result=lock_timeout\n[integer value for total retry attempts in transactional scenarios]\nerror=database_lock_timeout\n"
        },
        {
            "input": {
                "action": "retry_locked_change",
                "scenario": "nontransactional_change"
            },
            "expected_output": "result=lock_timeout\nattempts=1\nerror=database_lock_timeout\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_column_safety_assessment.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_column_safety_assessment@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the error_format used in constraint validation blocks
- match the retry strategy defined for in-transit validation
