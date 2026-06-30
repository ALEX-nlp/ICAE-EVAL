## Product Requirement Document

# Dead-Code Scan Reporting Toolkit — Value Normalization & Human-Readable Result Reports

## Project Goal

Build a small reporting toolkit for a "dead code" scanner that inspects a project and reports which imports could not be resolved, which declared dependencies are never used, and which source files are never imported. The toolkit turns the raw scan results into clean, fixed-width terminal reports, so every consumer of the scanner renders results the same way without re-inventing layout, alignment, or messaging.

---

## Background & Problem

A project scanner produces three lists — unresolved imports, unused dependencies, and unimported (orphan) files — and, separately, a cleanup operation that can remove unused dependencies and delete orphan files. Each of these needs to be presented to a developer on the terminal.

Without a shared reporting layer, every caller hand-rolls its own table drawing, counting, alignment and "nothing to report" messaging, leading to inconsistent and noisy output. This toolkit provides one well-defined contract: a tiny value-normalization helper used throughout the codebase, a scan-result report renderer, and a cleanup-result report renderer. All reports are laid out to a fixed terminal width of 80 columns and are emitted as plain text (no terminal color codes).

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

### Feature 1: Normalize A Value Into A List

**As a developer**, I want a helper that guarantees I always have a list to work with, so I can accept either a single value or a list of values from configuration and treat them uniformly downstream.

**Expected Behavior / Usage:**

The input carries a single `value` of any JSON type. If `value` is already a list, it is returned unchanged — element order and contents are preserved exactly, and no wrapping or de-duplication occurs. If `value` is anything else (a string, a number, an object, etc.), it is returned as a new one-element list containing exactly that value. The output renders the resulting list as compact JSON (no extra whitespace), so a list input round-trips to itself and a scalar input becomes a single-element list.

**Test Cases:** `rcb_tests/public_test_cases/feature1_normalize_to_array.json`

```json
{
    "description": "Normalize an arbitrary value into a list. If the value is already a list it is returned unchanged, preserving element order and contents; if it is a single scalar or object it is wrapped into a one-element list. The output renders the resulting list as JSON.",
    "cases": [
        {
            "input": {"action": "normalize_array", "value": ["src/a.js", "src/b.js"]},
            "expected_output": "[\"src/a.js\",\"src/b.js\"]"
        },
        {
            "input": {"action": "normalize_array", "value": "src/index.js"},
            "expected_output": "[\"src/index.js\"]"
        }
    ]
}
```

---

### Feature 2: Scan Summary Report

**As a developer**, I want the scan results rendered as a fixed-width summary with per-category tables, so I can immediately see how many problems were found and exactly which imports, dependencies, and files are involved.

**Expected Behavior / Usage:**

The input supplies the tool `version` (string), the `entryFiles` the scan started from (a list of objects each with a `file` path and an optional `label`), the three result lists `unresolved`, `unused`, and `unimported` (lists of strings), and a `clean` boolean.

When `clean` is true, the report is a single confirmation line: `✓ There don't seem to be any unimported files.` (no surrounding blank lines).

When `clean` is false, the report consists of: a summary block, then one boxed table for each non-empty category, then a closing hint line. The summary block opens with a leading blank line, then a header row that contains the caption `summary` and, right-aligned area, a banner of the form `unimported v<version>`, then a full-width horizontal divider (80 `─` characters). Below the divider each entry file is listed as a label/value row (`entry file` for a single entry, `entry file 1`, `entry file 2`, ... when there are several; a label, when present, is appended after the file path as ` — <label>`), followed by a blank row and three count rows: `unresolved imports`, `unused dependencies`, and `unimported files`, each label padded to a common width and followed by ` : ` and its count.

Each non-empty category is then rendered as a boxed table: a top border row, a caption row reading `<count> <category phrase>` (e.g. `2 unresolved imports`, `3 unused dependencies`, `4 unimported files`), a separator row, one row per entry showing a 1-based index right-aligned in a gutter followed by ` │ ` and the entry text, and a bottom border row. Tables appear in the fixed order unresolved → unused → unimported, and a category with an empty list produces no table. The report ends with a blank line and the hint line `       Inspect the results and run[exact CLI command suffix displayed in the final hint] to update ignore lists`. The total rendered width is 80 columns. Refer to the embedded case for the exact box-drawing characters and spacing.

**Test Cases:** `rcb_tests/public_test_cases/feature2_scan_summary.json`

```json
{
    "description": "Render the result of a dead-code scan as a human-readable report. The input carries the tool version, the entry file(s) the scan started from, and three result lists (unresolved imports, unused dependencies, unimported files) plus a clean flag. When the scan is clean a single confirmation line is produced. Otherwise a summary header with per-category counts is emitted, followed by one boxed table per non-empty category listing its entries, and a closing hint line.",
    "cases": [
        {
            "input": {
                "action": "scan_summary",
                "version": "1.0.0",
                "entryFiles": [{"file": "src/client/main.js"}],
                "unresolved": [],
                "unused": [],
                "unimported": [],
                "clean": true
            },
            "expected_output": "✓ There don't seem to be any unimported files."
        },
        {
            "input": {
                "action": "scan_summary",
                "version": "1.0.0",
                "entryFiles": [{"file": "src/client/main.js"}],
                "unresolved": ["string", "string"],
                "unused": ["string", "string", "string"],
                "unimported": ["string", "string", "string", "string"],
                "clean": false
            },
            "expected_output": "\n       summary               unimported v1.0.0\n────────────────────────────────────────────────────────────────────────────────\n       entry file          : src/client/main.js\n\n       unresolved imports  : 2\n       unused dependencies : 3\n       unimported files    : 4\n\n\n─────┬──────────────────────────────────────────────────────────────────────────\n     │ 2 unresolved imports\n─────┼──────────────────────────────────────────────────────────────────────────\n   1 │ string\n   2 │ string\n[specific string used to denote table row separators]\n\n\n─────┬──────────────────────────────────────────────────────────────────────────\n     │ 3 unused dependencies\n─────┼──────────────────────────────────────────────────────────────────────────\n   1 │ string\n   2 │ string\n   3 │ string\n[specific string used to denote table row separators]\n\n\n─────┬──────────────────────────────────────────────────────────────────────────\n     │ 4 unimported files\n─────┼──────────────────────────────────────────────────────────────────────────\n   1 │ string\n   2 │ string\n   3 │ string\n   4 │ string\n[specific string used to denote table row separators]\n\n\n       Inspect the results and run[exact CLI command suffix displayed in the final hint] to update ignore lists"
        }
    ]
}
```

---

### Feature 3: Cleanup Removal Report

**As a developer**, I want the outcome of a cleanup pass rendered clearly, so I can see which dependencies were removed and which files were deleted, or be reassured when there was nothing to clean up.

**Expected Behavior / Usage:**

The input supplies two lists: `removedDeps` (names of unused dependencies that were removed) and `deletedFiles` (paths of orphan files that were deleted).

Each non-empty list is rendered as a boxed table identical in shape to the tables in Feature 2: a top border row, a caption row reading `<count> unused dependencies removed` or `<count> unused files removed`, a separator row, one 1-based-indexed row per entry, and a bottom border row. The dependencies table (when present) is rendered before the files table (when present).

When one of the two lists is empty but the other is not, a confirmation line is emitted in place of the missing table: `✓ There are no unused dependencies.` when `removedDeps` is empty, or `✓ There are no unused files.` when `deletedFiles` is empty, followed by the table for the non-empty list. When both lists are empty, the report is the single line `✓ There are no unused files or dependencies.`. The total rendered width is 80 columns; refer to the embedded case for exact box-drawing characters and spacing.

**Test Cases:** `rcb_tests/public_test_cases/feature3_removal_summary.json`

```json
{
    "description": "Render the outcome of a cleanup operation that removed unused dependencies and/or deleted unused files. The input lists the removed dependency names and the deleted file names. Each non-empty group is rendered as a boxed table; each empty group yields a confirmation line stating there was nothing of that kind to remove. When both groups are empty a single combined confirmation line is produced.",
    "cases": [
        {
            "input": {"action": "removal_summary", "removedDeps": ["unused-package"], "deletedFiles": ["unused-file.txt"]},
            "expected_output": "\n─────┬──────────────────────────────────────────────────────────────────────────\n     │ 1 unused dependencies removed\n─────┼──────────────────────────────────────────────────────────────────────────\n   1 │ unused-package\n[specific string used to denote table row separators]\n\n\n─────┬──────────────────────────────────────────────────────────────────────────\n     │ 1 unused files removed\n─────┼──────────────────────────────────────────────────────────────────────────\n   1 │ unused-file.txt\n[specific string used to denote table row separators]\n"
        },
        {
            "input": {"action": "removal_summary", "removedDeps": [], "deletedFiles": []},
            "expected_output": "✓ There are no unused files or dependencies."
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above: a value-normalization helper and the two report renderers (scan summary and cleanup removal). The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing, and must lay out all reports to a fixed terminal width of 80 columns, emitting plain text without terminal color codes.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting text to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `normalize_array` normalizes the supplied `value`; `scan_summary` renders the scan result report; `removal_summary` renders the cleanup result report.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same report structure as C007 but for unresolved imports
- use the header generation pattern from C007
