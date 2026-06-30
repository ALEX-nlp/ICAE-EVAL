## Product Requirement Document

# Dictionary-Aware Page Processing - Selection and Projection Contracts for Encoded Numeric Pages

## Project Goal

Build a page-processing library that allows developers to filter and project rows from numeric column pages while preserving externally visible results across plain, repeated-value, and dictionary-encoded page layouts without forcing callers to manually decode every page before applying row-level logic.

---

## Background & Problem

Without this library, developers are forced to normalize encoded column pages by hand before selecting rows or projecting values. This leads to repetitive adapter code, inconsistent handling of repeated values and dictionary pages, and avoidable mistakes when an encoded page contains values that are not referenced by the selected rows.

With this library, a caller can provide the same logical row-selection or value-projection request for multiple page encodings and receive a deterministic, inspectable stdout contract containing selected positions, projected values, row counts, and result encoding signals.

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

### Feature 1: Processing Metadata Reporting

**As a developer**, I want to query the processing components for stable metadata, so I can wire them into a larger page-processing pipeline with confidence.

**Expected Behavior / Usage:**

The adapter accepts a metadata request naming either the row-selection component or the value-projection component. It prints the component name, whether execution is deterministic, the input channel list used by the component, and, for value projection, the produced scalar type. The output is newline-delimited `key=value` text and contains no pass/fail status words.

**Test Cases:** `rcb_tests/public_test_cases/feature1_metadata.json`

```json
{
  "description": "Reports stable execution metadata for the row-selection and value-projection components.",
  "cases": [
    {
      "input": {"operation":"metadata","component":"filter"},
      "expected_output": "component=filter\ndeterministic=true\ninput_channels=[3]\n"
    },
    {
      "input": {"operation":"metadata","component":"projection"},
      "expected_output": "component=projection\ndeterministic=true\ninput_channels=[3]\noutput_type=bigint\n"
    }
  ]
}
```

---

### Feature 2: Row Selection for Plain and Repeated Numeric Pages

**As a developer**, I want to select row positions from plain and repeated numeric pages, so I can reuse one filtering contract across different physical encodings.

**Expected Behavior / Usage:**

The adapter accepts `operation=filter`, a numeric predicate mode, and a page block. For plain pages, `values` lists one integer per row. For repeated pages, `value` and `position_count` describe a page where every row has the same integer. When `filter_range` is true, rows are selected if their value is greater than 3 and less than 11. When `filter_range` is false, rows are selected if their value leaves remainder 1 when divided by 3. The output prints the operation name, zero-based selected row positions in encounter order, and the selected count.

**Test Cases:** `rcb_tests/public_test_cases/feature2_filter_plain_and_repeated.json`

```json
{
  "description": "Selects row positions from plain and repeated numeric pages using either a bounded numeric window or a modular predicate.",
  "cases": [
    {
      "input": {"operation":"filter","filter_range":true,"block":{"encoding":"plain","values":[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14]}},
      "expected_output": "operation=filter\n[a list of selected zero-based indices]\n[a list of selected zero-based indices]\n"
    }
  ]
}
```

---

### Feature 3: Row Selection for Dictionary-Encoded Numeric Pages

**As a developer**, I want row selection to work on dictionary-encoded numeric pages, so I can filter encoded data without changing the logical result.

**Expected Behavior / Usage:**

The adapter accepts `operation=filter`, a predicate mode, and a dictionary page containing `dictionary` values and row-level `ids` that reference those values. The logical value for a row is `dictionary[ids[row]]`. Selection uses the same predicate modes as plain pages and prints zero-based selected row positions, not dictionary indexes. Empty row-id lists produce an empty selection. If a dictionary contains unused invalid values but all referenced rows can be evaluated, output is based only on the logical row values that are referenced by `ids`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_filter_dictionary.json`

```json
{
  "description": "Selects row positions from dictionary-encoded numeric pages, including partial matches, empty pages, all-match dictionaries, and dictionaries with unused invalid entries.",
  "cases": [
    {
      "input": {"operation":"filter","filter_range":true,"block":{"encoding":"dictionary","dictionary":[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19],"ids":[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]}},
      "expected_output": "operation=filter\n[a list of selected zero-based indices (potentially extended list)]\nselected_count=14\n"
    }
  ]
}
```

---

### Feature 4: Value Projection for Plain and Repeated Numeric Pages

**As a developer**, I want to project selected numeric rows from plain and repeated pages, so I can materialize the requested values while preserving the observable page encoding when appropriate.

**Expected Behavior / Usage:**

The adapter accepts `operation=project`, a page block, and selected positions. Positions may be a contiguous range described by `offset` and `size`, or an explicit list of zero-based row positions. The output prints projected values in requested order, the result position count, and an encoding signal. Plain input produces a plain result. Repeated input produces a repeated-result encoding signal and contains the repeated value once per selected output row in the rendered `values` list.

**Test Cases:** `rcb_tests/public_test_cases/feature4_project_plain_and_repeated.json`

```json
{
  "description": "Projects selected numeric values from plain and repeated pages while preserving row order and reporting the resulting page encoding.",
  "cases": [
    {
      "input": {"operation":"project","block":{"encoding":"plain","values":[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]},"positions":{"kind":"range","offset":5,"size":10}},
      "expected_output": "operation=project\n[a specific range of extracted values]\nposition_count=10\nresult_encoding=plain\n"
    }
  ]
}
```

---

### Feature 5: Value Projection for Dictionary-Encoded Numeric Pages

**As a developer**, I want to project selected rows from dictionary-encoded pages, so I can preserve row order and observe whether the result remains dictionary-encoded or must be materialized plainly.

**Expected Behavior / Usage:**

The adapter accepts `operation=project`, a dictionary page, and selected positions. The logical value for each selected row is `dictionary[ids[row]]`; output values appear in the same order as the selected positions. When all dictionary entries can be projected, the result may remain dictionary-encoded and the output must report `result_encoding=dictionary`. When unused dictionary entries contain invalid negative values but selected rows reference only valid values, projection succeeds by materializing the selected values as a plain result and reports `result_encoding=plain`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_project_dictionary.json`

```json
{
  "description": "Projects selected numeric values from dictionary-encoded pages, preserving selected row order and falling back to a plain page when unused dictionary entries are invalid.",
  "cases": [
    {
      "input": {"operation":"project","block":{"encoding":"dictionary","dictionary":[0,1,2,3,4,5,6,7,8,9],"ids":[0,1,2,3,4,5,6,7,8,9,0,1,2,3,4,5,6,7,8,9]},"positions":{"kind":"range","offset":5,"size":10}},
      "expected_output": "operation=project\nvalues=[5, 6, 7, 8, 9, 0, 1, 2, 3, 4]\nposition_count=10\nresult_encoding=dictionary\n"
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
- follows the strict inequality rules defined earlier for row selection
- uses the list-based position extraction logic described in the previous section
