## Product Requirement Document

# Deferred Pagination Optimizer - Efficient Bounded Database Loading

## Project Goal

Build a database-query pagination optimizer that allows developers to load bounded result sets efficiently without changing the externally visible records or pagination metadata returned to application code.

---

## Background & Problem

Without this library/tool, developers are forced to load paginated database records with a single broad bounded query that may scan or materialize more row data than needed before identifying the target page. This leads to slower deep pagination, repetitive hand-written query rewrites, and a risk that optimized code diverges from normal query semantics.

With this library/tool, developers can apply an optimized loading step to an existing bounded query. The optimized step first asks the database for matching row identifiers, then loads the full records for those identifiers, while preserving ordinary query results and pagination helper metadata.

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

### Feature 1: Two-Step Loading for Bounded Queries

**As a developer**, I want a bounded record query to load through an identifier query followed by a full-record query, so I can reduce the amount of row data scanned while preserving query execution through the database layer.

**Expected Behavior / Usage:**

When the input describes a bounded record request with a row limit, the optimizer must execute exactly two observable SQL statements: one statement that selects only row identifiers using the requested limit, and one statement that loads full records whose identifiers match the first statement. The output must expose the SQL statement count and each SQL statement in execution order, so implementations that bypass the database layer or return hard-coded records are distinguishable.

**Test Cases:** `rcb_tests/public_test_cases/feature1_deferred_join_sql.json`

```json
{
    "description": "A bounded record query is loaded through a two-step pagination strategy that first selects row identifiers and then loads the matching rows.",
    "cases": [
        {
            "input": {
                "mode": "optimized_sql",
                "page_request": {
                    "limit": 5
                }
            },
            "expected_output": "sql_count=2\nsql=SELECT \"users\".\"id\" FROM \"users\" LIMIT ?\nsql=SELECT \"users\".* FROM \"users\" WHERE \"users\".\"id\" IN (?, ?, ?, ?, ?)\n"
        }
    ]
}
```

---

### Feature 2: Relationship Preload Preservation

**As a developer**, I want optimized loading to preserve requested relationship preloading, so I can keep association data available without making the identifier query unnecessarily join or preload related rows.

**Expected Behavior / Usage:**

When the input describes a bounded record request that asks for related organization data to be preloaded, the identifier-selection statement must still select only primary row identifiers and must not load related table data. After the full records are loaded, the requested relationship preload must execute as a separate observable SQL statement. The output must include the SQL count and statements, including the separate relationship-loading statement.

**Test Cases:** `rcb_tests/public_test_cases/feature2_relationship_preload_sql.json`

```json
{
    "description": "A bounded record query that preloads a related collection keeps relationship loading out of the identifier query and still loads the related records afterward.",
    "cases": [
        {
            "input": {
                "mode": "optimized_sql",
                "page_request": {
                    "relationship_loading": "preload_organization",
                    "limit": 50
                }
            },
            "expected_output": "sql_count=3\nsql=SELECT \"users\".\"id\" FROM \"users\" LIMIT ?\nsql=SELECT \"users\".* FROM \"users\" WHERE \"users\".\"id\" IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\nsql=SELECT \"organizations\".* FROM \"organizations\" WHERE \"organizations\".\"id\" = ?\n"
        }
    ]
}
```

---

### Feature 3: Result Equivalence for Supported Boundaries

**As a developer**, I want optimized loading to return the same records as the ordinary bounded query, so I can enable optimization without changing application-visible data.

**Expected Behavior / Usage:**

When the input describes an ordered record request with supported pagination boundaries, the optimized result must contain the same number of records, row identifiers, and login values as the ordinary query for the same request. Supported boundaries include using both a limit and an offset, using only a limit, and using only an offset. The output must show the ordinary result and optimized result side by side with counts, identifiers, and login values.

**Test Cases:** `rcb_tests/public_test_cases/feature3_result_equivalence.json`

```json
{
    "description": "Optimized pagination returns the same ordered records as the ordinary bounded query for supported limit and offset combinations.",
    "cases": [
        {
            "input": {
                "mode": "compare_standard",
                "page_request": {
                    "limit": 5,
                    "offset": 5,
                    "order": "newest_first"
                }
            },
            "expected_output": "standard_count=5\nstandard_ids=5,4,3,2,1\nstandard_logins=phani,frances,nicknicknick,iheanyi,mikeissocool\noptimized_count=5\noptimized_ids=5,4,3,2,1\noptimized_logins=phani,frances,nicknicknick,iheanyi,mikeissocool\n"
        }
    ]
}
```

---

### Feature 4: Missing Boundary Error

**As a developer**, I want unbounded queries to be rejected before optimized loading is attempted, so I can avoid accidental full-table optimized loads that do not represent pagination.

**Expected Behavior / Usage:**

When the input describes an optimized loading request with no limit and no offset, the system must report a normalized domain error. The output must not expose host-language exception class names, stack traces, or runtime-generated messages; it must contain only the neutral error category and the missing requirement.

**Test Cases:** `rcb_tests/public_test_cases/feature4_missing_boundary_error.json`

```json
{
    "description": "An unbounded query cannot use optimized pagination and reports that a limit or offset boundary is required.",
    "cases": [
        {
            "input": {
                "mode": "missing_boundary_error"
            },
            "expected_output": "[a specific missing boundary error identifier]\nrequired=limit_or_offset\n"
        }
    ]
}
```

---

### Feature 5: Page-Number Pagination Metadata Preservation

**As a developer**, I want optimized loading to work with page-number pagination relations, so I can keep page navigation metadata while changing how page records are fetched.

**Expected Behavior / Usage:**

When the input describes a page-number request with a page index and item count, optimized loading must return the page's selected records and preserve pagination metadata including current page, next page, and previous page. The same behavior must hold for page-number requests that operate without a total count. The output must include record count, identifiers, login values, and navigation metadata.

**Test Cases:** `rcb_tests/public_test_cases/feature5_page_number_adapter.json`

```json
{
    "description": "A page-number pagination relation keeps its selected records and navigation metadata after optimized loading.",
    "cases": [
        {
            "input": {
                "mode": "page_number_adapter",
                "page_request": {
                    "page": 2,
                    "items": 1
                }
            },
            "expected_output": "records_count=1\nrecords_ids=9\nrecords_logins=ayrton\ncurrent_page=2\nnext_page=3\nprev_page=1\n"
        }
    ]
}
```

---

### Feature 6: Backend Pagination Helper Integration

**As a developer**, I want backend pagination helpers to fetch page records through optimized loading, so I can preserve helper metadata and count behavior while optimizing record retrieval.

**Expected Behavior / Usage:**

When the input describes a backend pagination request with page number and item count, the helper must still perform its total-count query, then fetch records through the two-step identifier-and-record loading sequence. The output must include the observable SQL statements, page item count, current page, next page, and selected records, so both framework behavior and optimized record loading are verifiable.

**Test Cases:** `rcb_tests/public_test_cases/feature6_backend_pagination_adapter.json`

```json
{
    "description": "A backend pagination helper can fetch its page records through optimized loading while preserving page metadata and count-query behavior.",
    "cases": [
        {
            "input": {
                "mode": "backend_adapter",
                "page_request": {
                    "page": 1,
                    "items": 5
                }
            },
            "expected_output": "sql_count=3\nsql=SELECT COUNT(*) FROM \"users\"\nsql=SELECT \"users\".\"id\" FROM \"users\" LIMIT ? OFFSET ?\nsql=SELECT \"users\".* FROM \"users\" WHERE \"users\".\"id\" IN (?, ?, ?, ?, ?)\npage_items=5\ncurrent_page=1\nnext_page=2\nrecords_count=5\nrecords_ids=4,7,8,9,10\nrecords_logins=frances,derek,dgraham,ayrton,dbussink\n"
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
- use the placeholders-for-all sequence defined in the audit module
