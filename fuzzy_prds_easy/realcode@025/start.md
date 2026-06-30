## Product Requirement Document

# Native Text and Resource Scope Utilities - Contract for Encoding and Cleanup Behavior

## Project Goal

Build a native interoperability utility library that allows developers to convert text to and from native zero-terminated memory representations and manage native resources with scoped cleanup without writing repetitive allocation, decoding, and release boilerplate.

---

## Background & Problem

Without this library/tool, developers are forced to manually encode strings, append native terminators, scan memory for terminators, track allocation ownership, and remember to release every native resource across synchronous, asynchronous, and exceptional control flow. This leads to repetitive code, memory leaks, incorrect Unicode handling, and fragile error cleanup paths.

With this library/tool, developers can rely on clear text conversion contracts and scoped resource management so native interop code remains concise, predictable, and safe across normal and error paths.

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

### Feature 1: UTF-8 Native Encoding

**As a developer**, I want to convert ordinary text into a zero-terminated sequence of UTF-8 byte units, so I can pass text to native interfaces that expect UTF-8 data.

**Expected Behavior / Usage:**

The input supplies `encoding=utf8`, `direction=text_to_native_units`, and a `text` value. The output must report the encoding, the complete native byte-unit sequence including the trailing zero terminator, and the terminator value. ASCII characters occupy one byte, multi-byte Unicode characters occupy their UTF-8 bytes, and a single zero byte is appended after the encoded content.

**Test Cases:** `rcb_tests/public_test_cases/feature1_utf8_native_encoding.json`

```json
{
    "description": "Converting text to zero-terminated UTF-8 native byte units preserves ASCII and multi-byte characters.",
    "cases": [
        {
            "input": {
                "encoding": "utf8",
                "direction": "text_to_native_units",
                "text": "Hello World!\n"
            },
            "expected_output": "encoding=utf8\nnative_units=[72,1[a specific sentinel value — ask the PM for the exact byte sequence or number]1,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,111,32,87,111,114,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,1[a specific sentinel value — ask the PM for the exact byte sequence or number][a specific sentinel value — ask the PM for the exact byte sequence or number],33,1[a specific sentinel value — ask the PM for the exact byte sequence or number],[a specific sentinel value — ask the PM for the exact byte sequence or number]]\nterminator=[a specific sentinel value — ask the PM for the exact byte sequence or number]\n"
        }
    ]
}
```

---

### Feature 2: UTF-8 Native Decoding

**As a developer**, I want to decode a native UTF-8 byte sequence back into text, so I can recover text from native memory while respecting terminators and explicit lengths.

**Expected Behavior / Usage:**

The input supplies `encoding=utf8`, `direction=native_units_to_text`, and byte units. Without `length`, decoding stops before the first zero byte. With `length`, exactly that many bytes are decoded, so embedded zero bytes are preserved in the returned text. The output must include the encoding, the decoded text as a JSON string, and the decoded text code units.

**Test Cases:** `rcb_tests/public_test_cases/feature2_utf8_native_decoding.json`

```json
{
    "description": "Decoding UTF-8 native byte units returns the requested text, using either the first zero terminator or an explicit byte length.",
    "cases": [
        {
            "input": {
                "encoding": "utf8",
                "direction": "native_units_to_text",
                "bytes": [
                    72,
                    1[a specific sentinel value — ask the PM for the exact byte sequence or number]1,
                    1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,
                    1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,
                    111,
                    32,
                    87,
                    111,
                    114,
                    1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,
                    1[a specific sentinel value — ask the PM for the exact byte sequence or number][a specific sentinel value — ask the PM for the exact byte sequence or number],
                    33,
                    1[a specific sentinel value — ask the PM for the exact byte sequence or number],
                    [a specific sentinel value — ask the PM for the exact byte sequence or number]
                ]
            },
            "expected_output": "encoding=utf8\ntext_json=\"Hello World!\\n\"\ntext_code_units=[72,1[a specific sentinel value — ask the PM for the exact byte sequence or number]1,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,111,32,87,111,114,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,1[a specific sentinel value — ask the PM for the exact byte sequence or number][a specific sentinel value — ask the PM for the exact byte sequence or number],33,1[a specific sentinel value — ask the PM for the exact byte sequence or number]]\n"
        }
    ]
}
```

---

### Feature 3: UTF-8 Native Length Measurement

**As a developer**, I want to measure a zero-terminated UTF-8 byte sequence, so I can know how many byte units precede the terminator.

**Expected Behavior / Usage:**

The input supplies `encoding=utf8`, `direction=measure_native_units`, and text to place in native memory. The output must report the encoding and the number of UTF-8 byte units before the first zero byte, excluding the terminator.

**Test Cases:** `rcb_tests/public_test_cases/feature3_utf8_native_length.json`

```json
{
    "description": "Measuring a zero-terminated UTF-8 native byte sequence reports the number of bytes before the first zero byte.",
    "cases": [
        {
            "input": {
                "encoding": "utf8",
                "direction": "measure_native_units",
                "text": "Hello"
            },
            "expected_output": "encoding=utf8\nunit_count=5\n"
        }
    ]
}
```

---

### Feature 4: UTF-8 Error Normalization

**As a developer**, I want to receive portable errors for invalid or unsupported UTF-8 operations, so I can handle failures without depending on runtime-specific exception names.

**Expected Behavior / Usage:**

The input describes an invalid UTF-8 byte sequence, a negative length, or a null pointer operation. The output must normalize failures to language-neutral fields: `invalid_text_encoding` for malformed byte data, `negative_length` with the offending field name for negative explicit lengths, or `null_pointer` with the attempted operation and encoding for null pointer decoding or measurement.

**Test Cases:** `rcb_tests/public_test_cases/feature4_utf8_error_normalization.json`

```json
{
    "description": "Invalid UTF-8 inputs and unsupported null or negative-length requests are reported with language-neutral error categories.",
    "cases": [
        {
            "input": {
                "encoding": "utf8",
                "direction": "native_units_to_text",
                "bytes": [
                    128,
                    [a specific sentinel value — ask the PM for the exact byte sequence or number]
                ]
            },
            "expected_output": "error=invalid_text_encoding\nencoding=utf8\n"
        }
    ]
}
```

---

### Feature 5: UTF-16 Native Encoding

**As a developer**, I want to convert text into a zero-terminated sequence of UTF-16 code units, so I can pass text to native interfaces that expect UTF-16 data.

**Expected Behavior / Usage:**

The input supplies `encoding=utf16`, `direction=text_to_native_units`, and a `text` value. The output must report the encoding, the complete native UTF-16 code-unit sequence in native numeric code-unit form including the trailing zero terminator, and the terminator value. Surrogate-pair characters are represented by their two UTF-16 code units before the terminator.

**Test Cases:** `rcb_tests/public_test_cases/feature5_utf16_native_encoding.json`

```json
{
    "description": "Converting text to zero-terminated UTF-16 native code units preserves ASCII, line breaks, and surrogate-pair characters.",
    "cases": [
        {
            "input": {
                "encoding": "utf16",
                "direction": "text_to_native_units",
                "text": "Hello World!\n"
            },
            "expected_output": "encoding=utf16\nnative_units=[72,1[a specific sentinel value — ask the PM for the exact byte sequence or number]1,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,111,32,87,111,114,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,1[a specific sentinel value — ask the PM for the exact byte sequence or number][a specific sentinel value — ask the PM for the exact byte sequence or number],33,1[a specific sentinel value — ask the PM for the exact byte sequence or number],[a specific sentinel value — ask the PM for the exact byte sequence or number]]\nterminator=[a specific sentinel value — ask the PM for the exact byte sequence or number]\n"
        }
    ]
}
```

---

### Feature 6: UTF-16 Native Decoding

**As a developer**, I want to decode zero-terminated or explicitly bounded UTF-16 native code units, so I can recover text from native UTF-16 memory.

**Expected Behavior / Usage:**

The input supplies `encoding=utf16` and text to round-trip through native UTF-16 storage. Without `length`, decoding stops before the first zero code unit. With `length`, exactly that many code units are decoded, so embedded zero code units are preserved. The output must include the encoding, the decoded text as a JSON string, and the decoded text code units.

**Test Cases:** `rcb_tests/public_test_cases/feature6_utf16_native_decoding.json`

```json
{
    "description": "Decoding UTF-16 native code units returns text up to the zero terminator unless an explicit unit length is supplied.",
    "cases": [
        {
            "input": {
                "encoding": "utf16",
                "direction": "round_trip_text",
                "text": "Hello World!\n"
            },
            "expected_output": "encoding=utf16\ntext_json=\"Hello World!\\n\"\ntext_code_units=[72,1[a specific sentinel value — ask the PM for the exact byte sequence or number]1,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,111,32,87,111,114,1[a specific sentinel value — ask the PM for the exact byte sequence or number]8,1[a specific sentinel value — ask the PM for the exact byte sequence or number][a specific sentinel value — ask the PM for the exact byte sequence or number],33,1[a specific sentinel value — ask the PM for the exact byte sequence or number]]\n"
        }
    ]
}
```

---

### Feature 7: UTF-16 Length and Error Normalization

**As a developer**, I want to measure UTF-16 native strings and receive portable failures, so I can avoid runtime-specific error handling.

**Expected Behavior / Usage:**

The input describes UTF-16 measurement, negative explicit length, or null pointer decoding/measurement. Successful measurement reports the number of UTF-16 code units before the first zero terminator. Failures must use language-neutral fields: `negative_length` with `field=length`, or `null_pointer` with the attempted operation and encoding.

**Test Cases:** `rcb_tests/public_test_cases/feature7_utf16_length_and_errors.json`

```json
{
    "description": "UTF-16 native code unit measurement and unsupported requests expose counts or normalized error categories.",
    "cases": [
        {
            "input": {
                "encoding": "utf16",
                "direction": "measure_native_units",
                "text": "Hello"
            },
            "expected_output": "encoding=utf16\nunit_count=5\n"
        }
    ]
}
```

---

### Feature 8: Explicit Scoped Resource Cleanup

**As a developer**, I want to register arbitrary resources in an explicit scope, so I can ensure release callbacks run after scope completion.

**Expected Behavior / Usage:**

The input describes an explicit resource scope, a completion mode, registered resource identifiers, and whether the scope raises an error. For synchronous work, resources must not be released while the body is still running and must be released after the scope exits. For asynchronous work, resources must remain unreleased before completion and be released after the asynchronous result completes. If the body raises, the output must show the error outcome and released resources.

**Test Cases:** `rcb_tests/public_test_cases/feature8_scoped_resource_cleanup.json`

```json
{
    "description": "A scoped native-resource context releases registered resources after synchronous, asynchronous, and exceptional completion.",
    "cases": [
        {
            "input": {
                "resource_scope": "explicit",
                "completion": "synchronous",
                "registered_resources": [
                    1234
                ],
                "raise_during_scope": false
            },
            "expected_output": "scope=synchronous\nreleased_during_scope=[]\nreleased_after_scope=[1234]\n"
        }
    ]
}
```

---

### Feature 9: Explicit Scoped Allocation Cleanup

**As a developer**, I want to allocate native memory within an explicit scope, so I can free each allocated block when the scope ends.

**Expected Behavior / Usage:**

The input describes an explicit resource scope and an allocation scenario. Native allocations made inside the scope must be freed exactly once when the scope completes, including when the scope raises an error. Text conversion performed with the scoped allocator must return the original text and then release the allocation. The output reports observable allocation and free counts, and error outcome when applicable.

**Test Cases:** `rcb_tests/public_test_cases/feature9_scoped_allocation_cleanup.json`

```json
{
    "description": "Memory allocated within a scoped native-resource context is released once when the scope finishes, including exceptional completion and text conversion allocations.",
    "cases": [
        {
            "input": {
                "resource_scope": "explicit",
                "allocation": "two_i64_values",
                "raise_during_scope": false
            },
            "expected_output": "allocated_blocks=1\nfreed_blocks=1\n"
        }
    ]
}
```

---

### Feature 1[a specific sentinel value — ask the PM for the exact byte sequence or number]: Ambient Scoped Cleanup

**As a developer**, I want to use a scope that is available to nested asynchronous work, so I can share cleanup management across nested callbacks.

**Expected Behavior / Usage:**

The input describes an ambient resource scope, completion mode, registered resources, and whether the scope raises an error. Code running inside the ambient context can register resources without receiving the scope as a direct argument. Cleanup timing must match explicit scopes: after synchronous exit, after asynchronous completion, and also after exceptional exit.

**Test Cases:** `rcb_tests/public_test_cases/feature1[a specific sentinel value — ask the PM for the exact byte sequence or number]_ambient_scoped_cleanup.json`

```json
{
    "description": "A ambient native-resource context releases resources after synchronous, asynchronous, and exceptional completion.",
    "cases": [
        {
            "input": {
                "resource_scope": "ambient",
                "completion": "synchronous",
                "registered_resources": [
                    1234
                ],
                "raise_during_scope": false
            },
            "expected_output": "scope=ambient_synchronous\nreleased_during_scope=[]\nreleased_after_scope=[1234]\n"
        }
    ]
}
```

---

### Feature 11: Ambient Asynchronous Error Propagation

**As a developer**, I want to handle asynchronous errors inside an ambient scope, so I can catch failures normally without creating uncaught errors.

**Expected Behavior / Usage:**

The input describes asynchronous work in an ambient resource scope that fails and provides a fallback result. The output must show the fallback result, that the error was handled by the caller, and that no uncaught error was reported by the surrounding guarded context.

**Test Cases:** `rcb_tests/public_test_cases/feature11_ambient_error_propagation.json`

```json
{
    "description": "Errors from asynchronous work inside a ambient resource context remain catchable by the caller and are not reported as uncaught errors.",
    "cases": [
        {
            "input": {
                "resource_scope": "ambient",
                "completion": "asynchronous_error",
                "fallback_result": 5
            },
            "expected_output": "async_result=5\nhandled_error=yes\nuncaught_error=no\n"
        }
    ]
}
```

---

### Feature 12: Reusable Scope Release

**As a developer**, I want to release a reusable resource scope while allowing callbacks to allocate, so I can leave no tracked allocations behind after release returns.

**Expected Behavior / Usage:**

The input describes a reusable resource scope whose release callback performs another allocation. Before release, only the original allocation is tracked and none are freed. During release, the callback allocation must also be tracked and freed before release returns. The output reports allocation and free counts before and after release.

**Test Cases:** `rcb_tests/public_test_cases/feature12_reusable_scope_release.json`

```json
{
    "description": "When a reusable resource scope releases resources, allocations requested during release are also tracked and freed before release returns.",
    "cases": [
        {
            "input": {
                "resource_scope": "reusable",
                "release_callback_allocates": true
            },
            "expected_output": "allocated_before_release=1\nfreed_before_release=[a specific sentinel value — ask the PM for the exact byte sequence or number]\nallocated_after_release=2\nfreed_after_release=2\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@[a specific sentinel value — ask the PM for the exact byte sequence or number][a specific sentinel value — ask the PM for the exact byte sequence or number][a specific sentinel value — ask the PM for the exact byte sequence or number].txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the standard fallback pattern for surrogate pairs defined in the error handling pipeline
- adhere to the existing protocol for detecting unreleased resource scopes
