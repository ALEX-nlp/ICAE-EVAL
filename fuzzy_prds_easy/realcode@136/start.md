## Product Requirement Document

# Operation Result Pattern Library — Status-Carrying Return Values for Service Operations

## Project Goal

Build a reusable library that lets a service operation return a single object describing both the outcome of the operation and any value it produced, so callers can branch on a well-defined status (success, error, validation failure, not-found, forbidden, unauthorized) instead of mixing return values with out-of-band signalling such as exceptions, sentinel values, or null checks.

---

## Background & Problem

A service method usually needs to communicate more than a bare value: it may succeed and return data, fail with one or more error messages, reject its input with structured validation failures, report that a resource was missing, or refuse the request for authorization reasons. Without a shared abstraction, each method invents its own convention — throwing exceptions for expected failures, returning null, or returning ad-hoc tuples — which forces every caller to learn a different protocol and makes it easy to forget a failure path.

This library provides one uniform envelope. An operation returns a result object that always exposes a status, a success flag derived from that status, an optional carried value, an optional success message, an optional correlation identifier, a list of error messages, and a list of structured validation failures. The envelope comes in three shapes: a value-carrying result, a no-value result (for operations that succeed or fail without producing data), and a paginated result that augments a value-carrying result with paging metadata. The library also offers ergonomic conversions: a bare value flows implicitly into a successful result and back out again, a failed no-value result widens implicitly into a value-carrying result of any type, and a successful result can be projected to a new value type while failures short-circuit untouched.

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
   - **Resilience:** The system must handle edge cases gracefully. [known set of result states]s should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Result Snapshot Output Contract

Every feature below is exercised through an execution adapter that reads one JSON command from stdin and prints a plain-text snapshot of the resulting result object to stdout. Unless a feature states it prints only the extracted value, the snapshot is exactly these seven lines, in this order, each terminated by a newline:

```
status=<[known set of result states]|[known set of result states]|[known set of result states]|[known set of result states]|[known set of result states]|[known set of result states]>
isSuccess=<true|false>
value=<rendered value>
successMessage=<message text, or empty>
correlationId=<identifier text, or empty>
errors=<error messages joined by "|", or empty>
validation[known set of result states]s=<validation failures joined by "|", or empty>
```

`isSuccess` is `true` only when `status` is `[known set of result states]`. The `value` line renders a string verbatim, an integer as its digits, a structured value as compact JSON, and an absent value as the literal `null`. Each validation failure renders as `identifier=<id>;message=<text>;code=<code>;severity=<[known set of result states]|Warning|Info>`, with empty fields left blank and severity defaulting to `[known set of result states]`. A paginated result appends four further lines after `validation[known set of result states]s`:

```
[standard paging metadata sequence]<n>
[standard paging metadata sequence]<n>
[standard paging metadata sequence]<n>
[standard paging metadata sequence]<n>
```

A command that only extracts a carried value prints a single `value=<rendered value>` line and nothing else.

---

## Core Features

### Feature 1: Construct A Value-Carrying Result

**As a developer**, I want to build a result that holds a value or signals a specific failure, so I can return outcome and data together from one operation.

**Expected Behavior / Usage:**

A value-carrying result can be built directly from a value (`op` = `build_typed`, `factory` = `ctor`) or through named factories (`factory` = `success`, `generic_success`, `generic_success_message`, `error`/`error_empty`, `invalid`, `not_found`/`not_found_message`, `forbidden`). Building from a value — with or without a success message — yields status `[known set of result states]`, `isSuccess` true, and exposes the supplied value verbatim (a string, an integer, a structured object, or `null`). The error factory yields status `[known set of result states]` and surfaces any supplied error messages (none if omitted). The invalid factory yields status `[known set of result states]` carrying the supplied validation failures. The not-found factory yields status `[known set of result states]`, optionally carrying error messages. The forbidden factory yields status `[known set of result states]`. Every non-`[known set of result states]` status reports `isSuccess` false and carries no value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_typed_construction.json`

```json
{
    "description": "Build a value-carrying result through its constructor and its named factory methods, then observe the result's status, success flag, carried value, optional success message, error messages and validation errors. A result built from a plain value (constructor or success factory, with or without a success message) reports a successful status and exposes the value verbatim (including null). The error factory yields an error status and surfaces any supplied error messages; the invalid factory yields an invalid status carrying the supplied validation errors; the not-found factory yields a not-found status (optionally with error messages); the forbidden and unauthorized factories yield their respective statuses. Only the successful states report success; every failure state reports not-successful.",
    "cases": [
        {
            "input": {"op": "build_typed", "factory": "ctor", "value": "test string"},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=test string\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "build_typed", "factory": "error", "errors": ["Something bad happened."]},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=Something bad happened.\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "build_typed", "factory": "not_found"},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "build_typed", "factory": "not_found_message", "errors": ["User Not Found"]},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=User Not Found\nvalidation[known set of result states]s=\n"
        }
    ]
}
```

---

### Feature 2: Implicit Conversion Between A Value And A Result

**As a developer**, I want a bare value to flow into a successful result and back out again without ceremony, so success paths read naturally.

**Expected Behavior / Usage:**

Converting a bare value into a value-carrying result (`op` = `build_typed`, `factory` = `from_value`) produces status `[known set of result states]` whose carried value is exactly the supplied value (including `null`). Extracting the value from a successful result (`op` = `typed_extract_value`) returns the carried value and prints only the `value=` line. Building a successful result with an accompanying success message (`factory` = `success_message`) preserves both the value and the message.

**Test Cases:** `rcb_tests/public_test_cases/feature2_typed_implicit_conversions.json`

```json
{
    "description": "Exercise the two-way implicit conversion between a value and a value-carrying result. Converting a bare value into a result produces a successful result whose carried value is exactly that value (including null), and converting a successful result back to a bare value yields the carried value. Building a successful result with an accompanying success message preserves both the value and the message.",
    "cases": [
        {
            "input": {"op": "build_typed", "factory": "from_value", "value": "test string"},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=test string\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "typed_extract_value", "factory": "success", "value": "test string"},
            "expected_output": "value=test string\n"
        },
        {
            "input": {"op": "build_typed", "factory": "success_message", "value": "test string", "message": "Success"},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=test string\nsuccessMessage=Success\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        }
    ]
}
```

---

### Feature 3: Project A Successful Result To A New Value Type

**As a developer**, I want to transform the value inside a successful result while leaving failures untouched, so I can compose operations without repeatedly checking status.

**Expected Behavior / Usage:**

Applying a projection to a value-carrying result (`op` = `typed_map`) runs the projection on the carried value only when the source status is `[known set of result states]`, producing a successful result that holds the projected value. When the source is in any failure state — `[known set of result states]`, `[known set of result states]`, `[known set of result states]`, `[known set of result states]`, or `[known set of result states]` — the projection is skipped and the failure is propagated unchanged: the status is preserved, error messages and validation failures carry over, and the new result carries no value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_typed_map.json`

```json
{
    "description": "Transform a value-carrying result by applying a projection function to its value. When the source result is successful, the projection runs on the carried value and the outcome is a successful result holding the projected value. When the source result is in any failure state (error, invalid, not-found, forbidden, unauthorized), the projection is skipped and the failure is propagated unchanged: the status is preserved, error messages and validation errors carry over, and no projected value is produced.",
    "cases": [
        {
            "input": {"op": "typed_map", "factory": "success", "value": 123},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=123\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "typed_map", "factory": "not_found"},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "typed_map", "factory": "error", "errors": ["[known set of result states] 1", "[known set of result states] 2"]},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=[known set of result states] 1|[known set of result states] 2\nvalidation[known set of result states]s=\n"
        }
    ]
}
```

---

### Feature 4: Construct A No-Value Result

**As a developer**, I want a result for operations that either succeed or fail without producing data, so I can report outcome without inventing a placeholder value.

**Expected Behavior / Usage:**

A no-value result (`op` = `build_void`) is built through the same family of factories and always carries an absent value (`null`). The plain constructor and the success factory — with or without a success message — report status `[known set of result states]`. The error factory reports status `[known set of result states]` with the supplied messages; a dedicated variant (`factory` = `error_correlation`) additionally attaches a correlation identifier. The invalid factory reports status `[known set of result states]` carrying validation failures. The not-found, forbidden, and unauthorized factories report their respective statuses.

**Test Cases:** `rcb_tests/public_test_cases/feature4_void_construction.json`

```json
{
    "description": "Build a result that carries no value through its constructor and named factory methods, then observe its status, success flag, optional success message, correlation identifier, error messages and validation errors. The carried value is always absent. The plain constructor and the success factory (with or without a success message) report a successful status; the error factory reports an error status with the supplied messages, and a dedicated variant additionally attaches a correlation identifier; the invalid factory reports an invalid status carrying validation errors; the not-found, forbidden and unauthorized factories report their respective statuses.",
    "cases": [
        {
            "input": {"op": "build_void", "factory": "ctor"},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "build_void", "factory": "error", "errors": ["test1", "test2"]},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=test1|test2\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "build_void", "factory": "invalid", "validation_errors": [{"identifier": "name", "error_message": "Name is required"}, {"identifier": "postalCode", "error_message": "PostalCode cannot exceed 10 characters"}]},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=identifier=name;message=Name is required;code=;severity=[known set of result states]|identifier=postalCode;message=PostalCode cannot exceed 10 characters;code=;severity=[known set of result states]\n"
        }
    ]
}
```

---

### Feature 5: Project A No-Value Result To A Value

**As a developer**, I want to attach a value to a successful no-value result via a projection while short-circuiting failures, so I can lift a void outcome into a value-carrying one.

**Expected Behavior / Usage:**

Applying a projection to a no-value result (`op` = `void_map`, with the produced value supplied as `map_value`) substitutes the projection's value as the carried value of a new successful result only when the source status is `[known set of result states]`. When the source is in any failure state, the projection is skipped: the failure status propagates and the new result carries no value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_void_map.json`

```json
{
    "description": "Transform a no-value result by applying a projection that supplies a value. When the source result is successful, the projection result becomes the carried value of a new successful result. When the source result is in any failure state, the projection is skipped: the failure status is propagated and the new result carries no value.",
    "cases": [
        {
            "input": {"op": "void_map", "factory": "success", "map_value": "Success"},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=Success\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "void_map", "factory": "not_found", "map_value": "This should be ignored"},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n"
        }
    ]
}
```

---

### Feature 6: Widen A Failed No-Value Result Into A Value-Carrying Result

**As a developer**, I want a failed no-value result to convert implicitly into a value-carrying result of any type, so a failure produced by a void operation can be returned from an operation that would otherwise produce a value.

**Expected Behavior / Usage:**

Converting a failed no-value result into a value-carrying result (`op` = `void_to_typed`) preserves the failure status and copies the failure payload: error messages for an error source, validation failures for an invalid source, and the bare status for not-found, forbidden, and unauthorized sources. The converted result carries no value.

**Test Cases:** `rcb_tests/public_test_cases/feature6_void_to_typed.json`

```json
{
    "description": "Implicitly convert a no-value result that is in a failure state into a value-carrying result of an arbitrary value type. The conversion preserves the failure status and copies across the failure payload: error messages for an error result, validation errors for an invalid result, and the bare status for not-found, forbidden and unauthorized results. The converted result carries no value.",
    "cases": [
        {
            "input": {"op": "void_to_typed", "factory": "error", "errors": ["test1"]},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=test1\nvalidation[known set of result states]s=\n"
        },
        {
            "input": {"op": "void_to_typed", "factory": "invalid", "validation_errors": [{"identifier": "name", "error_message": "Name is required"}, {"identifier": "postalCode", "error_message": "PostalCode cannot exceed 10 characters"}]},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=identifier=name;message=Name is required;code=;severity=[known set of result states]|identifier=postalCode;message=PostalCode cannot exceed 10 characters;code=;severity=[known set of result states]\n"
        }
    ]
}
```

---

### Feature 7: Construct A Paginated Result

**As a developer**, I want a result that pairs a value with paging metadata, so an operation returning a page of data can report its position within the full set.

**Expected Behavior / Usage:**

A paginated result (`op` = `paged_ctor` to build directly from a value, or `op` = `to_paged` to convert an existing result) augments the standard snapshot with four paging lines: page number, page size, total pages, and total records. Building directly from a value yields status `[known set of result states]` carrying that value (including `null`). Converting an existing result preserves the original status and payload — a successful source carries its value, an error source its error messages, an invalid source its validation failures, and not-found/forbidden sources their statuses — with the paging metadata attached unchanged in every case.

**Test Cases:** `rcb_tests/public_test_cases/feature7_paged_construction.json`

```json
{
    "description": "Build a paginated result that pairs a value-carrying result with paging metadata (page number, page size, total pages, total records), then observe both the underlying result state and the paging metadata. Constructing a paginated result directly from a value yields a successful status carrying that value (including null) alongside the paging metadata. Converting an existing result into a paginated result preserves the original status and payload: a successful source carries its value; an error source carries its error messages; an invalid source carries its validation errors; not-found and forbidden sources carry their statuses. In every case the paging metadata is attached unchanged.",
    "cases": [
        {
            "input": {"op": "paged_ctor", "value": "test string", "paged_info": {"page_number": 0, "page_size": 10, "total_pages": 1, "total_records": 3}},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=test string\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n[standard paging metadata sequence]0\n[standard paging metadata sequence]10\n[standard paging metadata sequence]1\n[standard paging metadata sequence]3\n"
        },
        {
            "input": {"op": "paged_ctor", "value": null, "paged_info": {"page_number": 0, "page_size": 10, "total_pages": 1, "total_records": 3}},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n[standard paging metadata sequence]0\n[standard paging metadata sequence]10\n[standard paging metadata sequence]1\n[standard paging metadata sequence]3\n"
        },
        {
            "input": {"op": "to_paged", "factory": "error", "errors": ["Something bad happened."], "paged_info": {"page_number": 0, "page_size": 10, "total_pages": 1, "total_records": 3}},
            "expected_output": "status=[known set of result states]\nisSuccess=false\nvalue=null\nsuccessMessage=\ncorrelationId=\nerrors=Something bad happened.\nvalidation[known set of result states]s=\n[standard paging metadata sequence]0\n[standard paging metadata sequence]10\n[standard paging metadata sequence]1\n[standard paging metadata sequence]3\n"
        }
    ]
}
```

---

### Feature 8: Convert Values To And From A Paginated Result

**As a developer**, I want a value to flow into a paginated result and its value to flow back out, so paginated success paths read as naturally as ordinary ones.

**Expected Behavior / Usage:**

Converting a bare value into a result and then into a paginated result (`op` = `to_paged`, `factory` = `from_value`) yields a successful paginated result carrying that value (including `null`) plus the paging metadata. Extracting the value from such a paginated result (`op` = `paged_extract_value`) returns the carried value and prints only the `value=` line. Building the source result with a success message (`factory` = `success_message`) preserves the message through the conversion alongside the value and paging metadata.

**Test Cases:** `rcb_tests/public_test_cases/feature8_paged_implicit_conversions.json`

```json
{
    "description": "Convert a value (or a successful result) into a paginated result and back, observing the carried value and the attached paging metadata. Converting a bare value into a result and then into a paginated result yields a successful paginated result carrying that value (including null) plus the paging metadata; extracting the value from such a paginated result returns the carried value. Building the source result with a success message preserves the message through the conversion alongside the value and paging metadata.",
    "cases": [
        {
            "input": {"op": "to_paged", "factory": "from_value", "value": "test string", "paged_info": {"page_number": 0, "page_size": 10, "total_pages": 1, "total_records": 3}},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=test string\nsuccessMessage=\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n[standard paging metadata sequence]0\n[standard paging metadata sequence]10\n[standard paging metadata sequence]1\n[standard paging metadata sequence]3\n"
        },
        {
            "input": {"op": "paged_extract_value", "factory": "success", "value": "test string", "paged_info": {"page_number": 0, "page_size": 10, "total_pages": 1, "total_records": 3}},
            "expected_output": "value=test string\n"
        },
        {
            "input": {"op": "to_paged", "factory": "success_message", "value": "test string", "message": "Success", "paged_info": {"page_number": 0, "page_size": 10, "total_pages": 1, "total_records": 3}},
            "expected_output": "status=[known set of result states]\nisSuccess=true\nvalue=test string\nsuccessMessage=Success\ncorrelationId=\nerrors=\nvalidation[known set of result states]s=\n[standard paging metadata sequence]0\n[standard paging metadata sequence]10\n[standard paging metadata sequence]1\n[standard paging metadata sequence]3\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the result envelope in its three shapes (value-carrying, no-value, paginated), the status model (`[known set of result states]`, `[known set of result states]`, `[known set of result states]`, `[known set of result states]`, `[known set of result states]`, `[known set of result states]`), the structured validation-failure type (identifier, message, code, severity), the factory constructors, the two-way value/result conversions, the failure-widening conversion, and the projection transform. The core business logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to the core system — logically (and ideally physically) separated from it. It reads a single JSON command from stdin and prints the resulting snapshot (or extracted value) to stdout, matching the per-feature contracts above. The command's `op` selects the behavior (`build_typed`, `build_void`, `typed_extract_value`, `typed_map`, `void_map`, `void_to_typed`, `to_paged`, `paged_ctor`, `paged_extract_value`); `factory` selects the constructor/factory; and `value`, `message`, `correlation_id`, `errors`, `validation_errors`, `map_value`, and `paged_info` supply the operands. The adapter is solely responsible for rendering the result snapshot and for translating any native failure into a neutral, language-independent form — no host-language runtime details may appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the root result header convention used in Feature 2
- apply the pipe-joiner pattern seen in validation failure formatting
