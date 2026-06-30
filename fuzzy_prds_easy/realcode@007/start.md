## Product Requirement Document

# Storage-Device Listing Toolkit — Parse Tool Output Into Structured Device Records

## Project Goal

Build a small toolkit that turns the raw textual output of system storage-inspection tools into a clean, structured list of device records, and that selects the right inspection step for the host operating system, so developers can enumerate attached drives without hand-writing fragile text scraping for every platform.

---

## Background & Problem

Operating systems expose their block/storage devices through platform-specific command-line tools, each printing a different free-form text layout. Application code that needs a uniform view of "what drives are attached" is otherwise forced to re-implement brittle string parsing per platform and to branch on the host operating system by hand. This leads to duplicated, error-prone code and inconsistent device descriptors.

This toolkit defines one stable contract. A parsing component converts a block of `key: value` text — as produced by an inspection tool — into an ordered list of device records (each a map of fields such as device path, description, size, and mount point). An enumeration component selects the inspection step appropriate to the named operating-system platform, feeds that step's raw output through the same parser, and returns the resulting records, failing cleanly when the platform is not supported.

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

### Feature 1: Parse Tool Output Into Structured Device Records

**As a developer**, I want to convert the free-form `key: value` text emitted by a storage-inspection tool into an ordered list of structured records, so I can work with attached devices as data instead of scraping strings.

**Expected Behavior / Usage:**

The input is a request with an action of `parse` and an `input` string holding the raw tool output. The output is the structured result rendered as a single line of canonical JSON followed by a trailing newline. A non-empty input parses to a JSON array of records; the empty/absent-input case is special and parses to a JSON object instead (the empty-object sentinel). The behavior below is split into independent leaf points.

*1.1 Empty Or Whitespace-Only Input — yields the empty-object sentinel*

When the request carries no `input` field at all, an empty `input` string, or an `input` consisting solely of whitespace, the result is the empty-object sentinel: the output is the two-character empty-object form followed by a newline. This is deliberately distinct in shape from the array produced for real content, so callers can tell "nothing to report" apart from "an empty list of one record".

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_empty_input.json`

```json
{
    "description": "Parsing an input that is absent, empty, or composed only of whitespace yields the empty-collection sentinel rather than a list of records. The output is the textual empty-object form.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "input": ""
            },
            "expected_output": "[an empty object string]\n"
        }
    ]
}
```

*1.2 Blank-Line-Separated Records — parses one or more `key: value` blocks into an ordered list*

Real content is a block of lines. Records are separated from one another by a blank line; within a record, each non-blank line is a `key: value` pair. The parser returns a JSON array with one object per record, preserving both the order of records and the order of keys within each record. Records are independent and need not share the same set of keys (heterogeneous records are allowed). Any blank lines trailing the final record are ignored and do not produce an extra empty record.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_records.json`

```json
{
    "description": "Parsing a textual block of one or more records, where records are separated by a blank line and each record is a set of `key: value` lines, produces an ordered list of key/value maps. Record order and per-record key order follow the input; records need not share the same keys, and any blank lines trailing the final record are ignored.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "input": "device: /dev/disk1\ndescription: Macintosh HD\nsize: 249.8 GB\nmountpoint: /"
            },
            "expected_output": "[{\"device\":\"/dev/disk1\",\"description\":\"Macintosh HD\",\"size\":\"249.8 GB\",\"mountpoint\":\"/\"}]\n"
        },
        {
            "input": {
                "action": "parse",
                "input": "device: /dev/disk1\ndescription: Macintosh HD\nsize: 249.8 GB\nmountpoint: /\n\ndevice: /dev/disk2\ndescription: elementary OS\nsize: 15.7 GB\nmountpoint: /Volumes/Elementary"
            },
            "expected_output": "[{\"device\":\"/dev/disk1\",\"description\":\"Macintosh HD\",\"size\":\"249.8 GB\",\"mountpoint\":\"/\"},{\"device\":\"/dev/disk2\",\"description\":\"elementary OS\",\"size\":\"15.7 GB\",\"mountpoint\":\"/Volumes/Elementary\"}]\n"
        }
    ]
}
```

*1.3 Trailing Comma Trimming — strips a single trailing comma from a value*

When a value ends with a trailing comma, that one trailing comma is removed from the parsed value. Commas that appear in the interior of the value are left untouched, so a comma-separated value keeps its inner separators and loses only the dangling one at the end.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_trailing_commas.json`

```json
{
    "description": "When a value ends with one trailing comma, that comma is stripped from the parsed value while internal commas are preserved.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "input": "hello: foo,bar,baz,"
            },
            "expected_output": "[{\"hello\":\"foo,bar,baz\"}]\n"
        }
    ]
}
```

*1.4 Missing Values And Keyless Lines — map to the null sentinel*

A line that declares a key followed by the separator but no value maps that key to the null sentinel. A bare line that contains no `key: value` separator at all is interpreted as a key with no value: the entire line text becomes the key (including any embedded spaces) and maps to null. In all cases the key text is preserved verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_null_values.json`

```json
{
    "description": "A line that declares a key with no value, or a bare line with no `key: value` separator at all, parses to that key mapped to the null sentinel. The remaining text becomes the key verbatim, including embedded spaces.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "input": "hello:"
            },
            "expected_output": "[{\"hello\":null}]\n"
        },
        {
            "input": {
                "action": "parse",
                "input": "hello"
            },
            "expected_output": "[{\"hello\":null}]\n"
        }
    ]
}
```

---

### Feature 2: Enumerate Devices For The Host Platform

**As a developer**, I want to ask for the device list while naming the operating-system platform and supplying that platform's raw inspection output, so I get back the parsed records through one uniform entry point and a clear failure when the platform is unsupported.

**Expected Behavior / Usage:**

The input is a request with an action of `list`, a `platform` naming the operating system, and an `output` string carrying the raw text the platform's inspection step would have produced. The enumeration selects the step appropriate to the platform, runs it to obtain that raw text, and feeds the text through the same parsing contract as Feature 1, returning the records as canonical JSON plus a trailing newline.

*2.1 Supported Platform — routes by platform and returns parsed records*

For a recognized platform, the supplied raw output is parsed and the resulting device records are returned as a JSON array followed by a newline. The parsing contract is identical across platforms; only the raw text differs from platform to platform. Quoted values in the raw text are unquoted by the parser, so a device record's fields carry their literal values.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_platform_enumeration.json`

```json
{
    "description": "Enumerating devices for a recognized operating-system platform routes to that platform's collection step, captures its raw textual output, and returns the parsed list of device records. The same parsing contract applies regardless of platform; only the supplied raw output differs.",
    "cases": [
        {
            "input": {
                "action": "list",
                "platform": "linux",
                "output": "device: \"/dev/sda\"\ndescription: \"My drive\"\nsize: \"15 GB\"\nmountpoint: \"/mnt/drive\""
            },
            "expected_output": "[{\"device\":\"/dev/sda\",\"description\":\"My drive\",\"size\":\"15 GB\",\"mountpoint\":\"/mnt/drive\"}]\n"
        },
        {
            "input": {
                "action": "list",
                "platform": "win32",
                "output": "device: \"\\\\\\\\.\\\\PHYSICALDRIVE1\"\ndescription: \"My drive\"\nsize: \"15 GB\"\nmountpoint: \"D:\""
            },
            "expected_output": "[{\"device\":\"\\\\\\\\.\\\\PHYSICALDRIVE1\",\"description\":\"My drive\",\"size\":\"15 GB\",\"mountpoint\":\"D:\"}]\n"
        }
    ]
}
```

*2.2 Unsupported Platform — fails fast with a neutral error*

When the named platform is not one the toolkit knows how to inspect, enumeration fails immediately, before any inspection step is run. The failure is reported as a neutral, language-independent error: a line `error=unsupported_platform` followed by a line `platform=<name>` carrying the offending platform name in its own field. No host-language runtime details appear in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_unsupported_platform.json`

```json
{
    "description": "Requesting enumeration for a platform the toolkit does not support fails up front with a neutral, language-independent error category and the offending platform name carried in its own field.",
    "cases": [
        {
            "input": {
                "action": "list",
                "platform": "foobar",
                "output": ""
            },
            "expected_output": "error=unsupported_platform\nplatform=foobar\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The text-to-records parser and the platform-aware enumeration must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `parse` converts a raw `input` string into the structured records; `list` selects the inspection step for the named `platform`, runs it to obtain raw text (supplied here as `output`), and parses that text. Structured results are rendered as canonical JSON on one line followed by a trailing newline; a non-empty parse yields a JSON array of records while empty/whitespace/absent input yields the empty-object sentinel. Unsupported-platform failures are rendered as the neutral two-line error contract.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the convention used in the test_harness module
- adhere to the error formatting pattern specified in the support section
