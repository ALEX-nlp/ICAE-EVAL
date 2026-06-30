## Product Requirement Document

# Lint Violation Report Formatter — Plain-Text & Color Output for Source Linting Results

## Project Goal

Build a reusable formatter that takes a stream of lint violations discovered in source files and renders them into a clean, human-readable plain-text report, so developers can see exactly where each problem is and why, without each tool having to reinvent its own output format.

---

## Background & Problem

A linting tool inspects source files and produces violations. Each violation knows which file it belongs to, the one-based line and column where it occurs, an identifier for the rule that was broken, and a short human-readable message. Some violations may already have been fixed automatically before reporting.

Without a shared formatter, every tool hand-rolls its own way of printing these results — leading to inconsistent layouts, missing context, and no easy way to toggle features like coloring or per-file grouping. This formatter provides one well-defined contract for turning violations into report text. It supports a default flat listing, an optional colorized variant using ANSI escape codes, an optional mode that groups violations under each file, and a configuration step that can build the formatter from a plain string option map (as a command line would supply) with validation of the requested color.

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

### Feature 1: Default Flat Violation Report

**As a developer**, I want each unfixed violation printed on its own line with its location and message, so I can scan all problems across all files in one flat list.

**Expected Behavior / Usage:**

The input is a request with an action of `render` and a list of `violations`. Each violation supplies `file`, `line` (one-based), `col` (one-based), `rule`, `message`, and a boolean `corrected`. The formatter emits exactly one line per violation whose `corrected` flag is false, preserving the order in which the violations were supplied; any violation whose `corrected` flag is true is silently dropped (it produces no output). Each emitted line has the shape `<file>:<line>:<col>: <message>` — the file path, a colon, the line number, a colon, the column number, a colon, a single space, then the message. The message is printed verbatim, including any special characters. A trailing newline follows every emitted line. If every violation was corrected, the output is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature1_plain_report.json`

```json
{
    "description": "Render a set of lint violations spanning several files using the default settings. Each violation carries a file path, a one-based line and column, a rule identifier and a human-readable message, plus a flag indicating whether it was already auto-corrected. The formatter emits one line per violation that was NOT auto-corrected, in the order received; already-corrected violations are silently omitted. Each emitted line is formatted as the file path, then the line and column separated by colons, then a colon and a space, then the message.",
    "cases": [
        {
            "input": {
                "action": "render",
                "violations": [
                    {"file": "/one-fixed-and-one-not.kt", "line": 1, "col": 1, "rule": "rule-1", "message": "<\"&'>", "corrected": false},
                    {"file": "/one-fixed-and-one-not.kt", "line": 2, "col": 1, "rule": "rule-2", "message": "And if you see my friend", "corrected": true},
                    {"file": "/two-not-fixed.kt", "line": 1, "col": 10, "rule": "rule-1", "message": "I thought I would again", "corrected": false},
                    {"file": "/two-not-fixed.kt", "line": 2, "col": 20, "rule": "rule-2", "message": "A single thin straight line", "corrected": false},
                    {"file": "/all-corrected.kt", "line": 1, "col": 1, "rule": "rule-1", "message": "I thought we had more time", "corrected": true}
                ]
            },
            "expected_output": "/one-fixed-and-one-not.kt:1:1: <\"&'>[ensure proper line termination]/two-not-fixed.kt:1:10: I thought I would again[ensure proper line termination]/two-not-fixed.kt:2:20: A single thin straight line[ensure proper line termination]"
        }
    ]
}
```

---

### Feature 2: Colorized Violation Report

**As a developer**, I want the location parts of each line wrapped in terminal color codes, so the file/line/column stand out from the message when viewing results in a color-capable terminal.

**Expected Behavior / Usage:**

When the `render` request enables coloring (via a `colored` flag in its `config`) and names a foreground color (via a `color` field in its `config`, given as a supported color name), the formatter still prints `<file>:<line>:<col>: <message>` but wraps specific segments in ANSI color escape sequences. A color wrapping consists of the escape sequence that activates the color, the wrapped text, then the reset escape sequence. Exactly three segments are colored: the directory portion of the file path (everything up to and including the final path separator), the colon that immediately follows the file's base name, and the combined `:<col>:` segment. The file's base name and the bare line number are left uncolored. The activating escape sequence encodes the numeric code of the requested color (the default color corresponds to numeric code 90; the reset sequence is `ESC[0m`, where `ESC` is the byte `0x1B`). A trailing newline follows the line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_colored_report.json`

```json
{
    "description": "Render a lint violation with colorized output enabled, supplying a foreground color by name. When coloring is enabled, the directory portion of the file path, the separator after the file name, and the line/column segment are each wrapped in ANSI color escape sequences for the chosen color, while the file's base name and the line number itself are left uncolored. The output is a single line: the colored path separator wrapping, the base file name, a colored colon, the line number, a colored column segment, then a space and the message.",
    "cases": [
        {
            "input": {
                "action": "render",
                "config": {"colored": true, "color": "DARK_GRAY"},
                "violations": [
                    {"file": "/one-fixed-and-one-not.kt", "line": 1, "col": 1, "rule": "rule-1", "message": "<\"&'>", "corrected": false}
                ]
            },
            "expected_output": "\u001b[90m/[ANSI color codes used in report]one-fixed-and-one-not.kt\u001b[90m:[ANSI color codes used in report]1\u001b[90m:1:[ANSI color codes used in report] <\"&'>[ensure proper line termination]"
        }
    ]
}
```

---

### Feature 3: Report Grouped By File

**As a developer**, I want violations collected under a header for each file, so I can read all problems for one file together instead of repeating the file path on every line.

**Expected Behavior / Usage:**

When the `render` request enables grouping (via a `group_by_file` flag in its `config`), the formatter does not print a line immediately for each violation. Instead, for every file that has at least one uncorrected violation, it emits a header line containing that file's path, followed by one indented line per uncorrected violation for that file. Each indented line is two leading spaces, then the line number, a colon, the column number, a single space, then the message. Corrected violations are excluded from the groups, and a file whose violations were all corrected produces no header and no lines. Files are emitted in the order they were first encountered in the violation list. A trailing newline follows every emitted line (both headers and indented lines).

**Test Cases:** `rcb_tests/public_test_cases/feature3_grouped_report.json`

```json
{
    "description": "Render lint violations with grouping-by-file enabled. Violations that were NOT auto-corrected are collected per file and emitted as a group: a header line containing the file path, followed by one indented line per violation. Each indented line shows the line and column separated by a colon, then a space and the message. Files whose violations were all auto-corrected produce no output at all. Groups appear in the order their files were first seen.",
    "cases": [
        {
            "input": {
                "action": "render",
                "config": {"group_by_file": true},
                "violations": [
                    {"file": "/one-fixed-and-one-not.kt", "line": 1, "col": 1, "rule": "rule-1", "message": "<\"&'>", "corrected": false},
                    {"file": "/one-fixed-and-one-not.kt", "line": 2, "col": 1, "rule": "rule-2", "message": "And if you see my friend", "corrected": true},
                    {"file": "/two-not-fixed.kt", "line": 1, "col": 10, "rule": "rule-1", "message": "I thought I would again", "corrected": false},
                    {"file": "/two-not-fixed.kt", "line": 2, "col": 20, "rule": "rule-2", "message": "A single thin straight line", "corrected": false},
                    {"file": "/all-corrected.kt", "line": 1, "col": 1, "rule": "rule-1", "message": "I thought we had more time", "corrected": true}
                ]
            },
            "expected_output": "/one-fixed-and-one-not.kt[ensure proper line termination]  1:1 <\"&'>[ensure proper line termination]/two-not-fixed.kt[ensure proper line termination]  1:10 I thought I would again[ensure proper line termination]  2:20 A single thin straight line[ensure proper line termination]"
        }
    ]
}
```

---

### Feature 4: Configure The Formatter From A String Option Map (With Color Validation)

**As a developer**, I want to build the formatter from a plain map of string options (the way command-line flags arrive) and have an invalid color rejected up front, so misconfiguration fails fast instead of producing wrong output.

**Expected Behavior / Usage:**

The input is a request with an action of `configure` and an `options` map of string keys to string values. The map may carry a `color_name` (the name of the foreground color to use), a `color` flag (a value of `""` or `"true"` enables coloring), and the same boolean-style flags used elsewhere. Building the formatter always requires a valid color name: the `color_name` value must match one of the supported color names. If `color_name` is missing entirely (including when only an unrelated/misspelled key is present) or is the empty string, construction fails and the formatter reports a neutral error line formatted as `error: <message>` followed by a newline, where the message text is `Invalid color parameter.`. When the color name is valid, the formatter is built successfully; if the request also supplies `violations`, they are then rendered through the freshly built formatter (honoring the supplied flags such as `color`), so a valid `color_name` is observable as the color used in the rendered output.

**Test Cases:** `rcb_tests/public_test_cases/feature4_color_option.json`

```json
{
    "description": "Build the reporter from a free-form string-keyed option map (as a command line would pass) and report the outcome. The color selection is driven by a dedicated option whose value must be the name of a supported color; coloring is enabled by a separate flag option. When the color option resolves to a valid color name, the reporter is constructed successfully and rendering a violation through it produces colorized output using that color. When the color name is absent (missing key, including an unrecognized key) or is the empty string, construction is rejected and a neutral error line carrying the failure message is reported instead.",
    "cases": [
        {
            "input": {
                "action": "configure",
                "options": {"color_name": "RED", "color": "true"},
                "violations": [
                    {"file": "/one-fixed-and-one-not.kt", "line": 1, "col": 1, "rule": "rule-1", "message": "<\"&'>", "corrected": false}
                ]
            },
            "expected_output": "\u001b[31m/[ANSI color codes used in report]one-fixed-and-one-not.kt\u001b[31m:[ANSI color codes used in report]1\u001b[31m:1:[ANSI color codes used in report] <\"&'>[ensure proper line termination]"
        },
        {
            "input": {
                "action": "configure",
                "options": {}
            },
            "expected_output": "error: Invalid color parameter.[ensure proper line termination]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting report (or error) to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `render` builds the formatter directly from an optional `config` block and renders the supplied `violations`; `configure` builds the formatter from a string `options` map (validating the requested color) and then renders any supplied `violations` through it. Supported color names include at least `DARK_GRAY` (numeric code 90) and `RED` (numeric code 31); the activating ANSI sequence is `ESC[<code>m` and the reset is `ESC[0m`, where `ESC` is byte `0x1B`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- col segment referenced in feature group
- standard violation line format
