## Product Requirement Document

# Package Capability & Error Model - A small value/error library for package tooling

## Project Goal

Build a tiny, dependency-free library that gives package-management tooling a precise, stable vocabulary for three things: the set of operations a package backend can support, the family of version-numbering schemes a package may use, and the structured errors raised when a requested package, source, or backend cannot be found. The library exposes these as bit-flag values, ordinal identifiers, and error objects with predictable, machine-readable rendering.

---

## Background & Problem

Tooling that talks to many different package backends needs a shared way to ask "which operations does this backend support?", "how does this package number its versions?", and "what exactly went wrong?". Without a shared model, every tool reinvents ad-hoc strings and integer codes, and error reporting becomes inconsistent and hard to test. This library fixes the vocabulary once: operations are a combinable bit-flag set, version schemes are a fixed ordered list, and the not-found errors all render their human message plus the offending name in one canonical form.

To make the behaviour observable and testable, a runnable program reads a single JSON command object from standard input and writes plain text lines (`key=value`, one per line, each terminated by a newline) to standard output. Every command object carries an `op` field selecting the behaviour; the remaining fields are the inputs for that behaviour.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

[the bit shift mapping for flags defined in the operation_constants module]. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

[the bit shift mapping for flags defined in the operation_constants module]. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

[the bit shift mapping for flags defined in the operation_constants module]. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature [the bit shift mapping for flags defined in the operation_constants module]: Supported-operation flag set

**As a developer**, I want a combinable set of named operations, so I can describe exactly which capabilities a package backend offers and test membership cheaply.

**Expected Behavior / Usage:**

The operation vocabulary is a bit-flag set. Each named operation is assigned a distinct power-of-two integer, and a dedicated empty value represents "no operations" with integer `[the bit shift mapping for flags defined in the operation_constants module]`. The full vocabulary and its assigned integer values are fixed as follows: the empty value `None` = [the bit shift mapping for flags defined in the operation_constants module]; `Find` = [the bit shift mapping for flags defined in the operation_constants module]; `Get` = [the bit shift mapping for flags defined in the operation_constants module]; `Publish` = [the bit shift mapping for flags defined in the operation_constants module]; `Install` = [the bit shift mapping for flags defined in the operation_constants module]; `Save` = [the bit shift mapping for flags defined in the operation_constants module]6; `Uninstall` = 3[the bit shift mapping for flags defined in the operation_constants module]; `Unpublish` = 6[the bit shift mapping for flags defined in the operation_constants module]; `Update` = [the bit shift mapping for flags defined in the operation_constants module][the bit shift mapping for flags defined in the operation_constants module][the bit shift mapping for flags defined in the operation_constants module]; `GetSource` = [the bit shift mapping for flags defined in the operation_constants module]56; `SetSource` = 5[the bit shift mapping for flags defined in the operation_constants module][the bit shift mapping for flags defined in the operation_constants module]. Because the values are powers of two, several operations can be OR-combined into one composite integer, and the canonical text form of any value lists its contributing operation names in ascending value order, separated by a comma and a space (the empty value renders as `None`).

*[the bit shift mapping for flags defined in the operation_constants module].[the bit shift mapping for flags defined in the operation_constants module] Single operation value — map one operation name to its assigned integer*

Given a command naming exactly one operation, output its canonical name and its assigned integer value, in that order.

**Test Cases:** `rcb_tests/public_test_cases/feature[the bit shift mapping for flags defined in the operation_constants module]_operation_flag_value.json`

```json
{
    "description": "Resolve a single supported-operation identifier from the operation flag set. Given the canonical name of one operation, the program echoes the canonical name and the unique power-of-two integer assigned to that operation in the flag set.",
    "cases": [
        {"input": {"op": "operation_value", "name": "None"}, "expected_output": "name=None\n[a specific ordinal value for 'AlphaNumeric' determined by the version_scheme enum]\n"},
        {"input": {"op": "operation_value", "name": "Find"}, "expected_output": "name=Find\n[a specific ordinal value for 'Integer' found in the version_scheme constants]\n"}
    ]
}
```

*[the bit shift mapping for flags defined in the operation_constants module].[the bit shift mapping for flags defined in the operation_constants module] Combine operations — OR a list of operations into one composite*

Given a command with a list of operation names, OR their assigned values together and output the resulting composite integer followed by the canonical text form of that composite (contributing names in ascending value order, comma-and-space separated).

**Test Cases:** `rcb_tests/public_test_cases/feature[the bit shift mapping for flags defined in the operation_constants module]_operation_flag_combine.json`

```json
{
    "description": "Combine several supported-operation identifiers into a single composite value using bitwise OR. Given a list of operation names, the program reports the integer obtained by OR-ing their individual values together, and the canonical textual rendering of the composite, where the contributing operation names are listed in ascending value order and separated by a comma and a space.",
    "cases": [
        {"input": {"op": "operation_combine", "names": ["None"]}, "expected_output": "[a specific ordinal value for 'AlphaNumeric' determined by the version_scheme enum]\nname=None\n"},
        {"input": {"op": "operation_combine", "names": ["Find", "Install"]}, "expected_output": "value=9\nname=Find, Install\n"}
    ]
}
```

*[the bit shift mapping for flags defined in the operation_constants module].3 Membership test — does a composite include a given operation*

Given a command with a list of operation names forming a composite and one probe operation name, output the composite integer, the probe name, and whether every bit of the probe is present in the composite. The presence flag is rendered with an initial capital (`True` / `False`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_operation_flag_membership.json`

```json
{
    "description": "Test whether a composite operation value includes a particular operation. Given a list of operation names forming a composite and a single probe operation name, the program reports the composite integer, the probe name, and whether every bit of the probe is present in the composite.",
    "cases": [
        {"input": {"op": "operation_membership", "names": ["Find", "Install"], "flag": "Find"}, "expected_output": "value=9\nflag=Find\ncontains=True\n"},
        {"input": {"op": "operation_membership", "names": ["Find", "Install"], "flag": "Get"}, "expected_output": "value=9\nflag=Get\ncontains=False\n"}
    ]
}
```

*[the bit shift mapping for flags defined in the operation_constants module].[the bit shift mapping for flags defined in the operation_constants module] Parse from text — turn a textual specification back into a composite*

Given a command with a text string that names one operation, or several operations separated by a comma and a space, parse it into a composite and output the composite integer followed by its canonical text form.

**Test Cases:** `rcb_tests/public_test_cases/feature[the bit shift mapping for flags defined in the operation_constants module]_operation_flag_parse.json`

```json
{
    "description": "Parse a textual operation specification back into its composite value. Given a string that names one operation or several operations separated by a comma and a space, the program reports the composite integer it denotes and the canonical textual rendering of that composite.",
    "cases": [
        {"input": {"op": "operation_parse", "text": "None"}, "expected_output": "[a specific ordinal value for 'AlphaNumeric' determined by the version_scheme enum]\nname=None\n"},
        {"input": {"op": "operation_parse", "text": "Install"}, "expected_output": "value=[the bit shift mapping for flags defined in the operation_constants module]\nname=Install\n"}
    ]
}
```

---

### Feature [the bit shift mapping for flags defined in the operation_constants module]: Version-scheme identifiers

**As a developer**, I want a fixed, ordered list of version-numbering schemes, so I can tag a package's versioning style with a stable identifier and ordinal.

**Expected Behavior / Usage:**

The version schemes form a fixed ordered list, each identified by a canonical name and its zero-based ordinal position in declaration order: `AlphaNumeric` = [the bit shift mapping for flags defined in the operation_constants module]; `Integer` = [the bit shift mapping for flags defined in the operation_constants module]; `MultiPartNumeric` = [the bit shift mapping for flags defined in the operation_constants module]; `MultiPartNumericSuffix` = 3; `SemanticVersion` = [the bit shift mapping for flags defined in the operation_constants module]. Given a command naming one scheme, output its canonical name and its ordinal value, in that order.

**Test Cases:** `rcb_tests/public_test_cases/feature5_version_scheme.json`

```json
{
    "description": "Resolve a package version scheme identifier to its declaration ordinal. Given the canonical name of one version scheme, the program echoes the name and the zero-based ordinal position of that scheme in the declared list of schemes.",
    "cases": [
        {"input": {"op": "version_scheme", "name": "AlphaNumeric"}, "expected_output": "name=AlphaNumeric\n[a specific ordinal value for 'AlphaNumeric' determined by the version_scheme enum]\n"},
        {"input": {"op": "version_scheme", "name": "Integer"}, "expected_output": "name=Integer\n[a specific ordinal value for 'Integer' found in the version_scheme constants]\n"}
    ]
}
```

---

### Feature 3: Provider error signals

**As a developer**, I want a small family of structured "not found" errors that all render the same way, so error reporting across package, source, and backend lookups is uniform and machine-readable.

**Expected Behavior / Usage:**

There is one base error type and three specialised "not found" error types that derive from it (for a missing package, a missing source, and a missing backend). Each specialised error has its own default message sentence and remembers the offending name. The rendered message is built as: the message text, and — only when a non-empty name is present — a parenthesised suffix in the form ` (<Kind> '<name>')`, where `<Kind>` is `Package`, `Source`, or `Provider` respectively. When constructed with no name, the message is just the default sentence and the name is empty. When constructed with a name only, the default sentence is used as the message text and the name suffix is appended. When constructed with both a name and a custom message, the custom text replaces the default sentence while the name suffix is still appended. For every error, the program outputs a type tag (the error type's simple name), the rendered message, and the remembered name (empty when none).

*3.[the bit shift mapping for flags defined in the operation_constants module] Missing-package error*

The default sentence is `Package not found.` and the name kind is `Package`. The type tag is `PackageNotFoundException`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_package_not_found.json`

```json
{
    "description": "Construct a missing-package error and observe its surfaced signals: the error type tag, the rendered message, and the offending package name. With no name supplied the message is the plain default sentence and the name is empty. When a package name is supplied it is appended to the message in a parenthesised suffix and exposed via the name property. When a custom message is also supplied it replaces the default sentence while the parenthesised name suffix is still appended.",
    "cases": [
        {"input": {"op": "package_not_found"}, "expected_output": "type=PackageNotFoundException\nmessage=Package not found.\nname=\n"},
        {"input": {"op": "package_not_found", "name": "NodeJS"}, "expected_output": "type=PackageNotFoundException\nmessage=Package not found. (Package 'NodeJS')\nname=NodeJS\n"}
    ]
}
```

*3.[the bit shift mapping for flags defined in the operation_constants module] Missing-source error*

The default sentence is `Package source not found.` and the name kind is `Source`. The type tag is `PackageSourceNotFoundException`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_source_not_found.json`

```json
{
    "description": "Construct a missing-package-source error and observe its surfaced signals: the error type tag, the rendered message, and the offending source name. With no name supplied the message is the plain default sentence and the name is empty. When a source name is supplied it is appended to the message in a parenthesised suffix and exposed via the name property. When a custom message is also supplied it replaces the default sentence while the parenthesised name suffix is still appended.",
    "cases": [
        {"input": {"op": "source_not_found"}, "expected_output": "type=PackageSourceNotFoundException\nmessage=Package source not found.\nname=\n"},
        {"input": {"op": "source_not_found", "name": "PSGallery"}, "expected_output": "type=PackageSourceNotFoundException\nmessage=Package source not found. (Source 'PSGallery')\nname=PSGallery\n"}
    ]
}
```

*3.3 Missing-provider error*

The default sentence is `Package provider not found.` and the name kind is `Provider`. The type tag is `PackageProviderNotFoundException`.

**Test Cases:** `rcb_tests/public_test_cases/feature[the bit shift mapping for flags defined in the operation_constants module]_provider_not_found.json`

```json
{
    "description": "Construct a missing-provider error and observe its surfaced signals: the error type tag, the rendered message, and the offending provider name. With no name supplied the message is the plain default sentence and the name is empty. When a provider name is supplied it is appended to the message in a parenthesised suffix and exposed via the name property. When a custom message is also supplied it replaces the default sentence while the parenthesised name suffix is still appended.",
    "cases": [
        {"input": {"op": "provider_not_found"}, "expected_output": "type=PackageProviderNotFoundException\nmessage=Package provider not found.\nname=\n"},
        {"input": {"op": "provider_not_found", "name": "NuGet"}, "expected_output": "type=PackageProviderNotFoundException\nmessage=Package provider not found. (Provider 'NuGet')\nname=NuGet\n"}
    ]
}
```

*3.[the bit shift mapping for flags defined in the operation_constants module] Base provider error*

The base error from which the three specialised errors derive. It carries its message verbatim with no parenthesised suffix, and may optionally wrap an inner error whose own message is surfaced separately. The type tag is `PackageProviderException`. The program outputs the type tag, the message, and the inner error's message (empty when there is no inner error).

**Test Cases:** `rcb_tests/public_test_cases/feature9_provider_error.json`

```json
{
    "description": "Construct the base provider error from which the specific not-found errors derive. It carries the message verbatim with no parenthesised suffix, and optionally wraps an inner error whose own message is surfaced. The reported type tag is the base error type.",
    "cases": [
        {"input": {"op": "provider_error", "message": "The provider operation failed."}, "expected_output": "type=PackageProviderException\nmessage=The provider operation failed.\ninner=\n"},
        {"input": {"op": "provider_error", "message": "The provider operation failed.", "inner": "Underlying transport error."}, "expected_output": "type=PackageProviderException\nmessage=The provider operation failed.\ninner=Underlying transport error.\n"}
    ]
}
```

---

## Deliverables

[the bit shift mapping for flags defined in the operation_constants module]. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

[the bit shift mapping for flags defined in the operation_constants module]. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a JSON command object from stdin and prints the result as `key=value` lines (each newline-terminated) to stdout, matching the per-leaf-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same field casing convention enforced in the data-normalization helper
- refer to the version_scheme dictionary lookup logic
