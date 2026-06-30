## Product Requirement Document

# Dependency Version Toolkit — Pure-Logic Helpers for Upgrade Reporting

## Project Goal

Build a small library of pure, deterministic helper routines that support reporting on out-of-date software dependencies: decomposing version identifiers, classifying how significant an available upgrade is, looking values up in a map with a safe fallback, modelling a validation error, exposing the fixed option vocabularies used by the tool, and mapping report roles to display colors. The goal is to let a reporting tool reason about versions and present results consistently, without re-implementing this logic everywhere.

---

## Background & Problem

A tool that scans projects for outdated dependencies repeatedly needs the same low-level building blocks: it must break a version string into comparable pieces, decide whether an upgrade is trivial or breaking, read configuration maps without crashing on missing keys, signal invalid user input distinctly from unexpected failures, enumerate the legal values for its command-line options, and color-code its output. Without a shared toolkit each of these is re-coded ad hoc, producing inconsistent classifications and brittle, error-prone code.

With this toolkit each concern is a single, well-specified routine with a fixed input/output contract, so the surrounding tool can rely on consistent, testable behavior.

## Invocation Protocol

The program reads one JSON object from standard input and writes plain text to standard output. The JSON object always has a string field `op` that selects the operation; the remaining fields are operation-specific and are described per feature below. Output is raw text (no status words, no wrapping); where multiple values are produced they are printed one per line.

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

### Feature 1: Version Component Splitter

**As a developer**, I want to break a dotted version identifier into its ordered constituent pieces, so I can compare or display versions component by component.

**Expected Behavior / Usage:**

Given a version string of the form `primary.secondary.tertiary[.fourth][-label[.label...]]`, produce an ordered sequence: first the four numeric position values — the primary number, the secondary number, the tertiary number, and the fourth-position number — followed by each pre-release label in order. Any numeric position that is not present in the input is reported as `0` (notably the fourth position, when the input has only three numeric positions). A pre-release label is the dot-separated text that follows a `-`; each segment is a separate item. Each produced item is printed on its own line as plain text, in order. `op` is `version_parts`; the version string is provided in the field `version`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_version_parts.json`

```json
{
    "description": "Split a dotted version identifier into its ordered sequence of components: first the four numeric position values (the primary number, the secondary number, the tertiary number, and the fourth-position number, with any omitted trailing numeric position reported as 0), then every pre-release label in order. Each component is emitted on its own line as plain text.",
    "cases": [
        {"input": {"op": "version_parts", "version": "1.2.3"}, "expected_output": "1\n2\n3\n0"},
        {"input": {"op": "version_parts", "version": "1.2.3.4-beta.1"}, "expected_output": "1\n2\n3\n4\nbeta\n1"}
    ]
}
```

---

### Feature 2: Upgrade Severity Classification

**As a developer**, I want to classify how significant it is to move a dependency from its currently-resolved version to a candidate latest version, so I can highlight breaking upgrades differently from trivial ones.

**Expected Behavior / Usage:**

Compare a currently-resolved version against a candidate latest version and return one of five named buckets, printed as `severity=<bucket-name>`. The decision is made in order: if either version is absent, the bucket is `Unknown`. Otherwise, if the latest version's primary number is greater than the resolved version's primary number, OR the currently-resolved version is itself a pre-release (it carries any pre-release label), the bucket is `Major`. Otherwise, if the latest version's secondary number is greater, the bucket is `Minor`. Otherwise, if the latest version's tertiary number is greater OR its fourth-position number is greater, the bucket is `Patch`. Otherwise the bucket is `None`. `op` is `upgrade_severity`; the two versions are provided in the fields `resolved` and `latest`, either of which may be `null` to indicate an absent version.

**Test Cases:** `rcb_tests/public_test_cases/feature2_upgrade_severity.json`

```json
{
    "description": "Classify the severity of upgrading a dependency from a currently-resolved version to a candidate latest version. The result is one of five named buckets. A higher primary-number on the latest version, or a currently-resolved version that is itself a pre-release, yields the highest bucket. Otherwise a higher secondary number yields the next bucket, then a higher tertiary or fourth-position number yields the patch bucket, and matching versions yield the no-change bucket. When either version is absent the bucket is the unknown value. The result is printed as severity=<bucket-name>.",
    "cases": [
        {"input": {"op": "upgrade_severity", "resolved": "1.2.3", "latest": "2.0.0"}, "expected_output": "severity=Major"},
        {"input": {"op": "upgrade_severity", "resolved": "1.0.2-al", "latest": "1.0.2"}, "expected_output": "severity=Major"},
        {"input": {"op": "upgrade_severity", "resolved": "1.2.3", "latest": "1.3.0"}, "expected_output": "severity=Minor"},
        {"input": {"op": "upgrade_severity", "resolved": "1.2.3", "latest": "1.2.4"}, "expected_output": "[a specific numeric threshold]"},
        {"input": {"op": "upgrade_severity", "resolved": "1.2.3", "latest": "1.2.3"}, "expected_output": "severity=None"},
        {"input": {"op": "upgrade_severity", "resolved": null, "latest": "2.0.0"}, "expected_output": "[a specific sentinel string for unknown severity]"}
    ]
}
```

---

### Feature 3: Map Lookup With Default Fallback

**As a developer**, I want to read a value from a key/value map and get a safe fallback when the key is missing, so I avoid special-casing absent keys at every call site.

**Expected Behavior / Usage:**

Given a map from string keys to integer values and a lookup key, return the integer associated with the key if it is present; if the key is absent, return the integer type's default value, which is `0`, rather than raising an error. The result is printed as `value=<number>`. `op` is `dict_get_or_default`; the map is provided in the field `entries` (a JSON object of string-to-integer entries) and the lookup key in the field `key`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_dictionary_default.json`

```json
{
    "description": "Look up a key in a string-to-integer map. If the key is present, return its associated integer value; if the key is absent, return the type's default value (zero for integers) rather than raising an error. The result is printed as value=<number>.",
    "cases": [
        {"input": {"op": "dict_get_or_default", "entries": {"alpha": 1, "beta": 2}, "key": "alpha"}, "expected_output": "value=1"},
        {"input": {"op": "dict_get_or_default", "entries": {"alpha": 1, "beta": 2}, "key": "gamma"}, "expected_output": "value=0"}
    ]
}
```

---

### Feature 4: Validation Error Type

**As a developer**, I want a dedicated error type for invalid user input that behaves like a general error and can wrap an underlying cause, so I can distinguish validation failures from unexpected failures while preserving the original cause.

**Expected Behavior / Usage:**

Model an error type intended to represent a validation failure. It carries a human-readable message; it may optionally wrap an underlying cause (an inner error); and it is recognizable as a general error object (it is a kind of error, not a standalone value). Construct it from a message alone, or from a message together with an inner cause. Output reports, line by line: `message=<the carried message>`, `is_exception=<whether it is a general error object>` (always `True`), `has_inner=<whether it wraps an inner cause>`, and — only when an inner cause is present — `inner_message=<the inner cause's message>`. `op` is `command_validation_exception`; the message is provided in the field `message` and, optionally, an inner cause's message in the field `inner_message`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_validation_exception.json`

```json
{
    "description": "Construct a dedicated validation error type that behaves as a general error: it carries a human-readable message, optionally wraps an underlying cause error, and is recognizable as a general error object. Output reports the carried message, whether it is a general error, whether it wraps an inner cause, and (when present) the inner cause's message.",
    "cases": [
        {"input": {"op": "command_validation_exception", "message": "Invalid value for option"}, "expected_output": "message=Invalid value for option\n[exact message and inner message content]\nhas_inner=False"},
        {"input": {"op": "command_validation_exception", "message": "Validation failed", "inner_message": "Underlying parse error"}, "expected_output": "message=Validation failed\n[exact message and inner message content]\n[exact message and inner message content]\ninner_message=Underlying parse error"}
    ]
}
```

---

### Feature 5: Named Enumeration Member Listing

**As a developer**, I want to list the legal member names of each fixed option vocabulary, so I can validate and display command-line option values consistently.

**Expected Behavior / Usage:**

The toolkit defines several fixed enumerations, each a named, ordered set of member names that form part of its externally-visible contract (they surface in serialized output and as command-line option values). Given a neutral identifier that selects one enumeration, print its member names one per line, in declaration order. The selectable enumerations and their exact member-name lists are fully specified by the cases below: `output_format`, `prerelease_reporting`, `upgrade_type`, `upgrade_severity`, and `version_lock`. `op` is `enum_values`; the enumeration identifier is provided in the field `enum`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_enum_values.json`

```json
{
    "description": "List the ordered member names of a named enumeration selected by a neutral identifier. Each enumeration exposes a fixed, ordered set of member names that are part of its wire-visible contract (they surface in serialized output and command-line option values). Output prints one member name per line in declaration order.",
    "cases": [
        {"input": {"op": "enum_values", "enum": "output_format"}, "expected_output": "Json\nCsv"},
        {"input": {"op": "enum_values", "enum": "prerelease_reporting"}, "expected_output": "Auto\nAlways\nNever"},
        {"input": {"op": "enum_values", "enum": "upgrade_type"}, "expected_output": "Auto\nPrompt"},
        {"input": {"op": "enum_values", "enum": "upgrade_severity"}, "expected_output": "None\nPatch\nMinor\nMajor\nUnknown"},
        {"input": {"op": "enum_values", "enum": "version_lock"}, "expected_output": "None\nMajor\nMinor"}
    ]
}
```

---

### Feature 6: Report Color Lookup

**As a developer**, I want a fixed display color for each semantic role in the report, so output is color-coded consistently.

**Expected Behavior / Usage:**

When rendering a report that highlights outdated dependencies, each semantic role maps to a fixed, named console color. Given a role identifier, print the corresponding color name. The roles and their colors are fully specified by the cases below: project name → `Blue`, target framework name → `Cyan`, package name → `Magenta`, a major-level upgrade → `Red`, a minor-level upgrade → `Yellow`, a patch-level upgrade → `Green`, an upgrade success → `Green`, and an upgrade failure → `Red`. `op` is `report_color`; the role is provided in the field `role`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_reporting_colors.json`

```json
{
    "description": "Resolve a fixed console color for a given semantic reporting role used when rendering an outdated-dependency report. Each role maps to a constant named console color. Output prints the color name.",
    "cases": [
        {"input": {"op": "report_color", "role": "project_name"}, "expected_output": "Blue"},
        {"input": {"op": "report_color", "role": "package_name"}, "expected_output": "Magenta"},
        {"input": {"op": "report_color", "role": "major_version_upgrade"}, "expected_output": "Red"},
        {"input": {"op": "report_color", "role": "minor_version_upgrade"}, "expected_output": "Yellow"},
        {"input": {"op": "report_color", "role": "patch_version_upgrade"}, "expected_output": "Green"},
        {"input": {"op": "report_color", "role": "target_framework_name"}, "expected_output": "Cyan"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command from stdin and prints the result to stdout, matching the per-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- default to the integer format used in the metadata_config module
- use the same default value as the cache initialization constant
