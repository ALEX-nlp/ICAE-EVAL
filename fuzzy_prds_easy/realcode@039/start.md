## Product Requirement Document

# Indentation Normalizer — Strip Common Leading Indentation From Multi-Line Text

## Project Goal

Build a small text-processing library that takes a block of indented multi-line text and removes the common leading indentation shared by its lines, so developers can embed naturally-indented multi-line content inside indented code and still get clean, left-aligned output without manually trimming whitespace.

---

## Background & Problem

When a multi-line block of text is written inside already-indented code, every line of that block inherits the surrounding indentation. Without a normalizer, developers must either break the visual flow by pushing the text hard against the left margin, or post-process the text by hand to strip the leading whitespace — both of which are tedious and error-prone, and tend to drift out of sync when the surrounding code is re-indented.

With this library, the text can stay visually aligned with its surroundings while the library computes the largest block of leading whitespace common to all lines and removes exactly that much from each line. The relative indentation between lines is preserved (deeper-indented lines stay deeper), blank and whitespace-only lines are handled gracefully, and an initial line break used purely to start the block on its own line is dropped. The same transformation is offered both for textual input and for raw binary buffers, and it preserves carriage-return line endings.

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

### Feature 1: Unindent Multi-Line Text

**As a developer**, I want a block of multi-line text to have its common leading indentation stripped, so I can keep the text visually aligned with surrounding code yet obtain clean left-aligned output.

**Expected Behavior / Usage:**

The input is a string of text spanning one or more lines (lines are separated by line-feed characters). The transformation is defined by four rules applied in order: (1) for every line except the first, count its leading run of whitespace characters (spaces and tabs both count as one unit each), ignoring lines that are empty or contain only whitespace; (2) take the minimum of those counts (if there are no such lines, the amount removed is zero); (3) if the whole text begins with a line break, the empty leading line it creates is dropped from the output; (4) remove that minimum number of leading whitespace characters from the beginning of every line. The first line is never unindented — if content shares the opening line (no leading break), it is emitted verbatim. Lines indented more deeply than the common amount retain their extra indentation, so relative nesting is preserved. Blank lines remain blank. A whitespace-only line shorter than the common indent is emitted as an empty line. A trailing line break in the input produces a trailing empty line (a final newline) in the output. A single line with no breaks, and the empty string, are returned unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature1_unindent_text.json`

```json
{
    "description": "Remove the common leading indentation from a block of multi-line text. The amount removed is the smallest leading run of spaces/tabs found across every line except the first, ignoring lines that are empty or contain only whitespace. If the text begins with a line break, that empty leading line is dropped. Content sharing the first line with no preceding break is left untouched, deeper-indented lines keep their extra indentation, blank lines stay blank, and whitespace-only lines shorter than the common indent collapse to empty. Inputs cover space indentation, tab indentation, content starting on the first line, interior blank lines with deeper nesting, whitespace-only short lines, a preserved trailing line break, a single line, and the empty input.",
    "cases": [
        {
            "input": {
                "mode": "text",
                "text": "\n        line one\n        line two"
            },
            "expected_output": "line one\nline two"
        },
        {
            "input": {
                "mode": "text",
                "text": "\n    def hello():\n        print('hi')\n\n    hello()\n"
            },
            "expected_output": "def hello():\n    print('hi')\n\nhello()\n"
        }
    ]
}
```

---

### Feature 2: Unindent A Raw Byte Buffer

**As a developer**, I want to apply the same indentation-removal to a raw byte buffer instead of text, so I can normalize content that is handled as binary data and does not need to be interpreted as a decoded string.

**Expected Behavior / Usage:**

The input is a sequence of byte values (each in the range 0–255). The identical common-indentation rules from Feature 1 are applied at the byte level: lines are delimited by the line-feed byte, the smallest leading run of space/tab bytes across all lines after the first is removed from every line, an initial empty line caused by a leading line-feed byte is dropped, deeper-indented lines keep their surplus indentation, and whitespace-only short lines collapse to empty. The output is the transformed sequence of bytes. This path does not require the buffer to be decodable text; it operates purely on the byte values supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature2_unindent_bytes.json`

```json
{
    "description": "Apply the same common-indentation removal to a raw byte buffer rather than to text, returning the transformed bytes. The input is a sequence of byte values; the smallest leading run of space/tab bytes across all lines after the first is stripped from every line, an initial empty line (leading newline byte) is dropped, and the byte content is otherwise preserved. Inputs cover a space-indented buffer and a tab-indented buffer.",
    "cases": [
        {
            "input": {
                "mode": "bytes",
                "data": [[the ASCII decimal values for carriage return and line feed characters], 32, 32, 32, 32, 32, 32, 32, 32, [the ASCII decimal values for carriage return and line feed characters]8, [the ASCII decimal values for carriage return and line feed characters]5, 1[the ASCII decimal values for carriage return and line feed characters], [the ASCII decimal values for carriage return and line feed characters]1, 32, 111, 1[the ASCII decimal values for carriage return and line feed characters], [the ASCII decimal values for carriage return and line feed characters]1, [the ASCII decimal values for carriage return and line feed characters], 32, 32, 32, 32, 32, 32, 32, 32, [the ASCII decimal values for carriage return and line feed characters]8, [the ASCII decimal values for carriage return and line feed characters]5, 1[the ASCII decimal values for carriage return and line feed characters], [the ASCII decimal values for carriage return and line feed characters]1, 32, 116, 119, 111]
            },
            "expected_output": "line one\nline two"
        }
    ]
}
```

---

### Feature 3: Preserve Carriage-Return Line Endings

**As a developer**, I want text whose lines end with a carriage-return + line-feed pair to be unindented while keeping its carriage returns intact, so content authored with Windows-style line endings survives the transformation unchanged apart from the removed indentation.

**Expected Behavior / Usage:**

The input is text whose line breaks are carriage-return + line-feed pairs. Lines are split on the line-feed character, and a carriage-return that immediately precedes the very first line break is not treated as part of the content (so a leading break still starts the block on its own line). The common leading indentation is computed and removed exactly as for line-feed-only text. Crucially, the carriage-return characters that terminate the retained lines are preserved in the output, so the carriage-return + line-feed line endings survive the unindentation and the result still uses the same line-ending style as the input.

**Test Cases:** `rcb_tests/public_test_cases/feature3_carriage_returns.json`

```json
{
    "description": "Unindent text whose lines are terminated by a carriage-return + line-feed pair. Lines are split on the line-feed; a leading carriage-return that precedes the very first line break is not treated as part of the content. The common leading indentation is computed and removed exactly as for line-feed-only text, and the carriage-return characters that terminate the retained lines are preserved in the output so the CRLF line endings survive the transformation. Inputs cover tab-indented CRLF text and space-indented CRLF text with a trailing line break.",
    "cases": [
        {
            "input": {
                "mode": "text",
                "text": "\r\n\tline one\r\n\tline two"
            },
            "expected_output": "line one\r\nline two"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core indentation logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing, and should expose the transformation for both textual and raw-byte input.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It receives a single request and prints the raw transformed payload to stdout, matching the per-feature contracts above. A `mode` selector chooses how the payload is interpreted: `text` treats the payload as a string of text and returns the unindented text; `bytes` treats the payload as a sequence of integer byte values (0–255) and returns the unindented bytes. The adapter writes only the raw program output (the transformed payload) to stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `[the specific output path template — requires checking the test runner configuration]/<cases-dir>/{filename.stem}@{[the specific output path template — requires checking the test runner configuration]}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the indentation handling logic defined in the main text processor utility
- apply the byte-stream processing flow described for the text mode implementation
