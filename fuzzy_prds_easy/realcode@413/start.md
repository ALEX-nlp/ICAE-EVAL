## Product Requirement Document

# Source Code Formatting Adapter - Deterministic Formatting, Range, and Error Contracts

## Project Goal

Build a source code formatting library and execution adapter that allows developers to normalize source text, preserve meaningful comments and selections, and receive deterministic output without manually implementing whitespace, wrapping, version, and error-handling rules.

---

## Background & Problem

Without this library/tool, developers are forced to hand-normalize source code whitespace, indentation, line endings, trailing commas, selected ranges, and syntax-version edge cases. This leads to inconsistent output, fragile editor integrations, repetitive formatting logic, and error-prone handling of parse failures.

With this library/tool, callers send a simple JSON command describing the source text and formatting options, and the adapter returns only the externally visible formatted text or a normalized error report.

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

### Feature 1: File Unit Formatting

**As a developer, I want to format complete source files, so I can store canonical file text with stable whitespace and a final line terminator.**

**Expected Behavior / Usage:**

The adapter accepts an input object with `operation` set to `format`, `scope` set to `file`, and `source` containing the full source text. It prints the formatted file text directly to stdout. File formatting normalizes redundant spaces, preserves trailing comments, collapses extra blank lines where appropriate, and ensures successful file outputs end with exactly one newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_file_unit_formatting.json`

```json
{
    "description": "Formats whole source files by normalizing whitespace, preserving comments, and ensuring file output ends with exactly one newline.",
    "cases": [
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "source": "var x = 1;"
            },
            "expected_output": "var x = 1;\n"
        },
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "source": "library foo; //zamm"
            },
            "expected_output": "library foo; //zamm\n"
        }
    ]
}
```

---

### Feature 2: Statement Formatting

**As a developer, I want to format a single statement or source fragment, so I can use the formatter in tools that operate on snippets instead of complete files.**

**Expected Behavior / Usage:**

The adapter accepts `operation: format`, `scope: statement`, and `source`. It prints only the formatted statement text. Statement formatting does not add a file-level trailing newline. When an `indent` integer is supplied, each output line is prefixed by that many spaces while still applying normal nested indentation.

**Test Cases:** `rcb_tests/public_test_cases/feature2_statement_formatting.json`

```json
{
    "description": "Formats a single statement or expression fragment without adding a file-level trailing newline, while supporting caller-provided leading indentation.",
    "cases": [
        {
            "input": {
                "operation": "format",
                "scope": "statement",
                "source": "var x = 1;"
            },
            "expected_output": "var x = 1;"
        }
    ]
}
```

---

### Feature 3: Width-Driven Layout Splitting

**As a developer, I want layout decisions to honor page width and style version settings, so I can obtain predictable single-line or multiline output.**

**Expected Behavior / Usage:**

The adapter accepts `operation: format`, `scope: statement`, `source`, and optional `language_version` and `page_width` fields. The formatter keeps short argument lists compact when they fit, splits long argument and collection structures when they exceed the configured width, and uses the requested style version to choose indentation and trailing-comma layout rules. The stdout is the formatted source text only.

**Test Cases:** `rcb_tests/public_test_cases/feature3_width_and_style_splitting.json`

```json
{
    "description": "Splits or keeps argument and collection layouts according to the selected formatting style and configured page width.",
    "cases": [
        {
            "input": {
                "operation": "format",
                "scope": "statement",
                "language_version": "3.6",
                "page_width": 40,
                "source": "method(first, second, third, fourth, fifth, sixth, seventh, eighth, ninth,\n    tenth, eleventh, twelfth);"
            },
            "expected_output": "method(\n    first,\n    second,\n    third,\n    fourth,\n    fifth,\n    sixth,\n    seventh,\n    eighth,\n    ninth,\n    tenth,\n    eleventh,\n    twelfth);"
        },
        {
            "input": {
                "operation": "format",
                "scope": "statement",
                "language_version": "3.10",
                "page_width": 40,
                "source": "function ( one: \"value\" , two: \"data\" , three: \"more stuff\" ) ;"
            },
            "expected_output": "function(\n  one: \"value\",\n  two: \"data\",\n  three: \"more stuff\",\n);"
        }
    ]
}
```

---

### Feature 4: Language Version Behavior

**As a developer, I want syntax support and formatting style to follow an explicit version, so I can format old and new source consistently.**

**Expected Behavior / Usage:**

The adapter accepts `language_version` as a dotted version string. A leading source version comment in the input may override the configured version for both parsing and formatting style. When the effective version supports the syntax, stdout is formatted source text. When the effective version does not support the syntax, stdout is a normalized parse-error report with `error=parse_error`, a diagnostic `count`, and comma-separated source `lines`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_language_version_behavior.json`

```json
{
    "description": "Uses the configured language version and any leading source version comment to select syntax support and versioned formatting behavior.",
    "cases": [
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "language_version": "3.0",
                "source": "// @dart=2.19\nmain() { switch (o) { case 1+2: break; } }\n"
            },
            "expected_output": "// @dart=2.19\nmain() {\n  switch (o) {\n    case 1 + 2:\n      break;\n  }\n}\n"
        },
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "language_version": "3.7",
                "source": "// @dart=3.6\nmain() { f(argument, // comment\nanother);}\n"
            },
            "expected_output": "// @dart=3.6\nmain() {\n  f(\n      argument, // comment\n      another);\n}\n"
        },
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "language_version": "3.6",
                "source": "// @dart=3.7\nmain() { f(argument, // comment\nanother);}\n"
            },
            "expected_output": "// @dart=3.7\nmain() {\n  f(\n    argument, // comment\n    another,\n  );\n}\n"
        }
    ]
}
```

---

### Feature 5: Line Ending Selection

**As a developer, I want line ending behavior to be deterministic, so I can preserve platform-specific files or force a chosen separator.**

**Expected Behavior / Usage:**

The adapter accepts an optional `line_ending` string. If supplied, every formatter-created line break uses that separator. If omitted, the first line ending found in `source` determines the output line ending; otherwise the default successful file output uses `
`. Multiline string contents retain their internal line structure while surrounding formatting uses the selected separator.

**Test Cases:** `rcb_tests/public_test_cases/feature5_line_endings.json`

```json
{
    "description": "Chooses output line separators from an explicit option or from the first line ending found in the input, including multiline string handling.",
    "cases": [
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "line_ending": "\t",
                "source": "var i = 1;"
            },
            "expected_output": "var i = 1;\t"
        },
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "source": "var\r\ni\n=\n1;\n"
            },
            "expected_output": "var i = 1;\r\n"
        }
    ]
}
```

---

### Feature 6: Trailing Comma Policy

**As a developer, I want trailing comma handling to be configurable, so I can preserve author-signaled multiline layouts without forcing every compact input to expand.**

**Expected Behavior / Usage:**

The adapter accepts optional `trailing_commas`. With `preserve`, existing trailing commas in supported constructs force multiline output that retains trailing commas. Inputs without such commas may remain compact when they fit the configured width, and may still split when they exceed it. Stdout is the formatted statement text only.

**Test Cases:** `rcb_tests/public_test_cases/feature6_trailing_comma_policy.json`

```json
{
    "description": "Applies the requested trailing-comma policy so existing commas can force multiline layouts when preservation is requested, while comma-free inputs may remain compact.",
    "cases": [
        {
            "input": {
                "operation": "format",
                "scope": "statement",
                "language_version": "3.10",
                "page_width": 40,
                "trailing_commas": "preserve",
                "source": "[1,];"
            },
            "expected_output": "[\n  1,\n];"
        },
        {
            "input": {
                "operation": "format",
                "scope": "statement",
                "language_version": "3.10",
                "page_width": 40,
                "trailing_commas": "preserve",
                "source": "[1,2,3];"
            },
            "expected_output": "[1, 2, 3];"
        }
    ]
}
```

---

### Feature 7: Selection Tracking

**As a developer, I want selected source ranges to be updated during formatting, so editor integrations can keep the same logical selection after whitespace changes.**

**Expected Behavior / Usage:**

The adapter accepts `operation: format`, a `source`, and both `selection_start` and `selection_length`. It prints a structured stdout block: `[a specific sentinel delimiter — ask the PM for the exact string separating text and metadata]`, the formatted text, `[a specific sentinel delimiter — ask the PM for the exact string separating text and metadata]`, then `[a specific delimiter pattern — ask the PM for the exact string used in JSON payloads]<offset>` and `[a specific delimiter pattern — ask the PM for the exact string used in JSON payloads]<length>`. Offsets are zero-based character positions in the formatted text, adjusted to follow inserted or removed whitespace around the original selected range.

**Test Cases:** `rcb_tests/public_test_cases/feature7_selection_tracking.json`

```json
{
    "description": "Returns formatted text together with the adjusted selected range when a caller supplies a source selection.",
    "cases": [
        {
            "input": {
                "operation": "format",
                "scope": "statement",
                "page_width": 40,
                "source": "a+first+second;",
                "selection_start": 3,
                "selection_length": 8
            },
            "expected_output": "[a specific sentinel delimiter — ask the PM for the exact string separating text and metadata]\na + first + second;\n[a specific sentinel delimiter — ask the PM for the exact string separating text and metadata]\n[a specific delimiter pattern — ask the PM for the exact string used in JSON payloads]5\n[a specific delimiter pattern — ask the PM for the exact string used in JSON payloads]10\n"
        }
    ]
}
```

---

### Feature 8: Source Range Segments

**As a developer, I want to inspect the text around a selected range, so I can build editor features that operate on before/selected/after segments.**

**Expected Behavior / Usage:**

The adapter accepts `operation: source_segments`, `source`, and optionally both `selection_start` and `selection_length`. With a complete valid range, stdout contains `before=...`, `selected=...`, and `after=...` lines. With no range, `before` is the entire source and `selected` and `after` are empty. Invalid ranges are reported as normalized selection errors using `[a specific error flag — ask the PM for the exact string used to mark invalid selections]`, `field`, and `reason` lines.

**Test Cases:** `rcb_tests/public_test_cases/feature8_source_range_segments.json`

```json
{
    "description": "Exposes the text before, inside, and after an optional selected range, and rejects ranges whose bounds are incomplete or outside the source text.",
    "cases": [
        {
            "input": {
                "operation": "source_segments",
                "source": "123456;",
                "selection_start": 3,
                "selection_length": 2
            },
            "expected_output": "before=123\nselected=45\nafter=6;\n"
        },
        {
            "input": {
                "operation": "source_segments",
                "source": "123456;"
            },
            "expected_output": "before=123456;\nselected=\nafter=\n"
        }
    ]
}
```

---

### Feature 9: Normalized Error Reporting

**As a developer, I want failures to be reported in a language-neutral stdout format, so callers can compare black-box results without depending on runtime exception names.**

**Expected Behavior / Usage:**

For parse failures, stdout contains `error=parse_error`, `count=<number>`, and `lines=<comma-separated line numbers>`. For formatter safety-check failures where formatting would change non-whitespace source content, stdout contains `error=non_whitespace_output_change`. These outputs must not include host-language exception class names, stack traces, or runtime-specific message suffixes.

**Test Cases:** `rcb_tests/public_test_cases/feature9_error_reporting.json`

```json
{
    "description": "Reports parse failures and formatter safety-check failures using normalized, language-neutral stdout categories.",
    "cases": [
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "source": "wat?!"
            },
            "expected_output": "error=parse_error\ncount=4\nlines=1\n"
        },
        {
            "input": {
                "operation": "format",
                "scope": "file",
                "source": "\n\n      var a = some error;\n\n      var b = another one;\n      ",
                "uri": "my_file.dart"
            },
            "expected_output": "error=parse_error\ncount=4\nlines=3,5\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_file_unit_formatting.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_file_unit_formatting@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- parse the '@language' comment exactly as defined in the parser directives module
- enforce multiline layout per the alignment rules found in the macro expansion test suite
