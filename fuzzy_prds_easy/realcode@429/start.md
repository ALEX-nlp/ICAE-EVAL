## Product Requirement Document

# EPUB Content-Reference & Media-Overlay Timing Utilities — Path Resolution, Hyperlink Splitting, and Clock Parsing

## Project Goal

Build a small, dependency-free utility library that handles the low-level string conventions an e-book reader must deal with when working with the internal resources of a digital publication: resolving relative resource paths inside the package, deciding whether a reference points inside the package or out to the network, splitting hyperlink references into a target and a fragment, and parsing media-overlay (synchronized-narration) clock values into normalized timestamps. The goal is to give a reading engine one well-tested place for these conventions so each part of the engine does not re-implement them inconsistently.

---

## Background & Problem

A digital publication is, in effect, a bundle of resource files (markup documents, images, audio, navigation metadata) that reference each other using relative paths and hyperlinks, plus optional synchronized-narration data that times audio against text using clock values. Without a shared utility layer, every component that touches these references must independently re-derive the same rules: how to join a containing directory with a `../`-style relative reference, how to strip a fragment identifier from a link, whether a path is internal or an external URL, and how to interpret the several notations a narration clock value can take. Each ad-hoc re-implementation is a place for subtle inconsistencies and bugs.

With this library, those conventions live behind a few precise, side-effect-free operations whose behavior is fully specified by their inputs and outputs. The operations never perform I/O; they only transform strings into normalized strings or structured timestamps.

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

### Feature 1: Content Path Resolution

**As a developer**, I want to interpret and normalize the relative resource paths that link the files inside a publication, so I can locate a referenced resource from the location of the file that references it.

**Expected Behavior / Usage:**

Resource paths inside a publication use the forward slash `/` as their separator and may use `../` segments to refer to a parent directory. This feature provides three independent operations over such path strings. Every operation is a pure string transformation and performs no file-system access.

*1.1 Local-vs-Remote Reference Classification — decide whether a reference points inside the package or out to the network*

Given a reference string, report whether it is a local (in-package) reference or a remote/absolute one. A reference is local when it does NOT contain the scheme separator `://`, and non-local when it does. An empty string is local. A null reference is invalid and is reported as a missing-argument error whose parameter field names the offending argument (`path`). The output echoes the inspected reference and the boolean verdict.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_local_path_classification.json`

```json
{
    "description": "Classify a content reference as either a local (in-package) path or a remote/absolute reference. The classifier inspects the raw reference string: a reference is treated as local when it does NOT contain a scheme separator (the '://' sequence), and as non-local otherwise. An empty reference is considered local. A null reference is rejected as a missing-argument error. The output echoes the inspected reference and reports the local/non-local verdict.",
    "cases": [
        {"input": {"op": "classify_path", "path": "Directory/File.html"}, "expected_output": "path=Directory/File.html\nlocal=true\n"},
        {"input": {"op": "classify_path", "path": "https://example.com/books/123/chapter1.html"}, "expected_output": "path=https://example.com/books/123/chapter1.html\nlocal=false\n"},
        {"input": {"op": "classify_path", "path": null}, "expected_output": "[return argument null error with url param]\nparam=path\n"}
    ]
}
```

*1.2 Directory Extraction — obtain the containing directory of a file path*

Given a file path, return the directory portion: everything before the last `/`, with the final segment removed. A path with no `/` has an empty directory. A path ending in `/` returns the part before that trailing slash. Any `..` segments that occur before the final slash are kept verbatim. The output reports the resulting directory (possibly empty).

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_directory_path.json`

```json
{
    "description": "Extract the directory portion of a content file path. The directory is everything that precedes the last forward-slash separator in the path; the segment after the final slash (the file name) is discarded. A path that contains no slash has an empty directory. A path that ends with a slash yields the part before that trailing slash. Parent-traversal segments ('..') that appear before the final slash are preserved verbatim. The output reports the resulting directory string (which may be empty).",
    "cases": [
        {"input": {"op": "directory_of", "path": "Directory/Subdirectory/File.html"}, "expected_output": "directory=Directory/Subdirectory\n"},
        {"input": {"op": "directory_of", "path": "File.html"}, "expected_output": "directory=\n"}
    ]
}
```

*1.3 Path Combination — join a directory with a relative reference, resolving parent traversal*

Given a base directory and a relative file reference (either of which may be null), produce the combined, normalized path. First, runs of consecutive slashes in each input are collapsed to a single slash. If the directory is null or empty, the file reference alone is returned; if the file reference is null or empty, the directory alone is returned; if both are null, the result is null (reported as the literal token `<null>`). Otherwise, each leading `../` segment in the file reference strips the last segment off the directory and is consumed; if the directory is exhausted, the remaining file reference is the result. The directory and remaining file reference are joined with a single slash.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_combine_path.json`

```json
{
    "description": "Combine a base directory with a relative file reference into a single normalized content path. Before combining, repeated consecutive slashes in either input are collapsed to a single slash. If the directory is null or empty, the file reference alone is the result; if the file reference is null or empty, the directory alone is the result; if both are null, the result is null. Each leading parent-traversal segment ('../') in the file reference removes the last segment of the directory and is itself consumed; traversal that exhausts the directory leaves the remaining file reference as the result. The directory and the (remaining) file reference are otherwise joined with a single slash. A null combined result is reported with the literal token <null>.",
    "cases": [
        {"input": {"op": "combine_path", "directory": "Directory/Subdirectory", "file": "../File.html"}, "expected_output": "combined=Directory/File.html\n"},
        {"input": {"op": "combine_path", "directory": null, "file": null}, "expected_output": "combined=<null>\n"}
    ]
}
```

---

### Feature 2: Hyperlink Reference Splitting

**As a developer**, I want to separate a hyperlink reference into the resource it targets and the in-resource fragment it points at, so I can load the target resource and then scroll to the referenced anchor.

**Expected Behavior / Usage:**

A hyperlink reference may carry a fragment identifier introduced by `#` (for example, a link to a specific anchor within a document). Given a reference string, split it at the first `#`: the part before it is the path, and the part after it is the fragment. When there is no `#`, the whole reference is the path and there is no fragment. The output reports the path, an explicit flag for whether a fragment was present (this distinguishes a missing fragment from an empty one), and the fragment text (empty when absent). A null reference is invalid and is reported as a missing-argument error whose parameter field names the offending argument (`url`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_href_reference.json`

```json
{
    "description": "Split a hyperlink reference into its path component and its optional fragment (anchor) component. The fragment is the part that follows the first '#' character; the path is everything before it. When the reference contains no '#', there is no fragment and the whole reference is the path. The output reports the path, whether a fragment was present, and the fragment text (empty when absent). A null reference is rejected as a missing-argument error.",
    "cases": [
        {"input": {"op": "parse_reference", "href": "file.html#anchor"}, "expected_output": "path=file.html\nanchor_present=true\nanchor=anchor\n"},
        {"input": {"op": "parse_reference", "href": "file.html"}, "expected_output": "path=file.html\nanchor_present=false\nanchor=\n"}
    ]
}
```

---

### Feature 3: Media-Overlay Clock Parsing

**As a developer**, I want to parse the clock values used to synchronize narration audio with text into normalized timestamps, so I can position playback at the right moment regardless of which notation the source used.

**Expected Behavior / Usage:**

Synchronized-narration data times audio using clock values that come in two notations. Both notations are parsed by a single tolerant parser that trims surrounding whitespace, returns a structured timestamp on success, and signals failure (rather than throwing) on any malformed input. On success the timestamp is reported broken down into hour, minute, second, and millisecond components together with a canonical rendering of the form `h:mm:ss[.fff]` — the hour is unpadded, minute and second are two digits, and the `.fff` millisecond part appears only when the millisecond component is non-zero. On failure the output reports only that the value is not valid. A blank value (null, empty, or whitespace-only) is always invalid. Fractional parts are always truncated toward zero (never rounded), down to whole-millisecond resolution.

*3.1 Colon Notation (Clock Value) — `[hours:]minutes:seconds[.fraction]`*

The colon notation is recognized when the trimmed value contains a `:`. It is either a full clock `hours:minutes:seconds` or a partial clock `minutes:seconds`; either form may carry a fractional-seconds suffix after a `.`. The minute and second fields must each be an integer in the range 0–59; the hour field, when present, must be a non-negative integer. The value is rejected if it has more than three colon-separated parts, if any field is empty, non-numeric, negative, or out of range, or if a comma is used instead of a dot for the fraction.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_clock_value.json`

```json
{
    "description": "Parse a media-overlay clock value written in colon-separated notation into a normalized timestamp. The value may be a full clock of the form hours:minutes:seconds (with optional fractional seconds) or a partial clock of the form minutes:seconds (with optional fractional seconds); surrounding whitespace is ignored. Minutes and seconds must each be in the range 0..59; hours must be non-negative. Fractional seconds are truncated to whole milliseconds (digits beyond the third are discarded, not rounded). A blank value (null, empty, or whitespace-only), a value with too many colon-separated parts, an empty or non-numeric or negative or out-of-range component, or a non-dot decimal separator is rejected. On success the output reports the broken-down hour, minute, second, and millisecond components plus a canonical h:mm:ss[.fff] rendering (the fractional part is shown only when non-zero); on failure it reports that the value is not valid.",
    "cases": [
        {"input": {"op": "parse_clock", "value": "02:30:03"}, "expected_output": "valid=true\nhour=2\nminute=30\nsecond=3\nmillisecond=0\ntimestamp=2:30:03\n"},
        {"input": {"op": "parse_clock", "value": "00:10.5"}, "expected_output": "valid=true\nhour=0\nminute=0\nsecond=10\nmillisecond=500\ntimestamp=0:00:10.500\n"},
        {"input": {"op": "parse_clock", "value": "1:02,1"}, "expected_output": "valid=false\n"}
    ]
}
```

*3.2 Timecount Notation (Metric Value) — `<number>[unit]`*

The timecount notation is recognized when the trimmed value contains no `:`. It is a non-negative decimal number followed by an optional metric unit: `h` (hours), `min` (minutes), `s` (seconds), or `ms` (milliseconds). With no unit, the number is interpreted as seconds. The numeric magnitude is converted to whole milliseconds and then normalized so the minute and second components wrap at 60 while the hour component absorbs any overflow (so a large hour count is allowed). The value is rejected if its magnitude exceeds the maximum supported timecount, if the number is negative or non-numeric, if the unit is unrecognized or differently cased (units are case-sensitive and lowercase), or if whitespace separates the number from the unit.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_timecount_value.json`

```json
{
    "description": "Parse a media-overlay clock value written in timecount notation into a normalized timestamp. A timecount is a non-negative number, optionally fractional, followed by an optional metric unit: 'h' for hours, 'min' for minutes, 's' for seconds, or 'ms' for milliseconds; when no unit is given the number is interpreted as seconds. Surrounding whitespace is ignored. The numeric magnitude is converted to whole milliseconds (the fractional part beyond a millisecond is truncated, not rounded) and then broken down into hour, minute, second, and millisecond components, where the minute and second components wrap at 60 and the hour component absorbs the overflow. A value whose magnitude exceeds the maximum supported timecount, a negative number, an unrecognized or wrongly-cased unit, or a unit preceded by whitespace is rejected. On success the output reports the broken-down components plus a canonical h:mm:ss[.fff] rendering (the fractional part is shown only when non-zero); on failure it reports that the value is not valid.",
    "cases": [
        {"input": {"op": "parse_clock", "value": "3.2h"}, "expected_output": "valid=true\nhour=3\nminute=12\nsecond=0\nmillisecond=0\ntimestamp=3:12:00\n"},
        {"input": {"op": "parse_clock", "value": "5ms"}, "expected_output": "valid=true\nhour=0\nminute=0\nsecond=0\nmillisecond=5\ntimestamp=0:00:00.005\n"},
        {"input": {"op": "parse_clock", "value": "1H"}, "expected_output": "valid=false\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin, selects the operation from the request's `op` field, invokes the appropriate core logic, and prints the result to stdout, matching the per-feature contracts above. The recognized operations are `classify_path` (field `path`), `directory_of` (field `path`), `combine_path` (fields `directory`, `file`), `parse_reference` (field `href`), and `parse_clock` (field `value`). String fields may be JSON `null`. Errors must be rendered as language-neutral lines: a missing-argument failure prints `[return argument null error with url param]` followed by `param=<argument name>`; values that fail to parse are reported within their feature's contract (e.g. `valid=false`). No host-language exception type names or runtime message text may appear in the output.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Resolve any relative segments like ../ matching the traversal logic in features3
- Ensure all attributes end with newline per codebase standard
