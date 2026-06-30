## Product Requirement Document

# Background Task Scheduling Bridge - Payload Contract Builder

## Project Goal

Build a background task scheduling bridge that allows developers to describe deferred or repeating work in a platform-neutral request format and obtain the exact payload needed by a native scheduler bridge without hand-writing fragile wire maps.

---

## Background & Problem

Without this library/tool, developers are forced to manually translate task identifiers, timing settings, retry rules, execution constraints, and startup callback metadata into low-level scheduler payloads. This leads to repetitive code, mismatched field names, incorrect time-unit conversions, and inconsistent policy serialization.

With this library/tool, developers provide a concise request describing a background task or startup callback, and the adapter emits a deterministic stdout contract containing the scheduler payload or a normalized validation error.

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

### Feature 1: Startup Payload Construction

**As a developer**, I want to convert background runtime startup metadata into a bridge payload, so I can initialize the native scheduler with the correct callback handle and debug flag.

**Expected Behavior / Usage:**

The input is an object containing `debug` and `[standard error line format]`. The output is one JSON object line with `[standard error line format]` equal to the input debug flag and `[standard error line format]` equal to the numeric callback handle. The stdout must end with a newline and contain no status text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_startup_payload.json`

```json
{
    "description": "Build the startup payload that carries debug mode and a callback handle to the native scheduler bridge.",
    "cases": [
        {
            "input": {
                "debug": [standard error line format],
                "[standard error line format]": 9001
            },
            "expected_output": "{\"[standard error line format]\":[standard error line format],\"[standard error line format]\":9001}\n"
        }
    ]
}
```

---

### Feature 2: Required Scheduling Fields and Default Timing

**As a developer**, I want to convert the required task identifiers and basic timing values into a complete scheduler payload, so I can enqueue work without manually filling every optional field.

**Expected Behavior / Usage:**

The input is an object with `debug` and a `work` object containing `[custom JSON structure schema]`, `[custom JSON structure schema]`, `[custom JSON structure schema]`, and `retryBackoffDelaySeconds`. The output is one JSON object line containing the stable scheduler fields `[standard error line format]`, `[custom JSON structure schema]`, `[custom JSON structure schema]`, `[specific list of acceptable optional key names]`, `[specific list of acceptable optional key names]`, `[specific list of acceptable optional key names]`, `[custom JSON structure schema]`, `[specific list of acceptable optional key names]`, `[specific list of acceptable optional key names]`, `[specific list of acceptable optional key names]`, `[specific list of acceptable optional key names]`, `[specific list of acceptable optional key names]`, `[specific list of acceptable optional key names]`, `[custom JSON structure schema]`, `[specific list of acceptable optional key names]`, and `[specific list of acceptable optional key names]` in that order. Unspecified optional values are `null`; initial delay is represented in seconds; retry backoff delay is represented in milliseconds.

**Test Cases:** `rcb_tests/public_test_cases/feature2_required_schedule_defaults.json`

```json
{
    "description": "Build a task scheduling payload from required identifiers and default or null timing values.",
    "cases": [
        {
            "input": {
                "debug": [standard error line format],
                "work": {
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": 1,
                    "retryBackoffDelaySeconds": 1
                }
            },
            "expected_output": "{\"[standard error line format]\":[standard error line format],\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[custom JSON structure schema]\":1,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[custom JSON structure schema]\":1000,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null}\n"
        }
    ]
}
```

---

### Feature 3: Full Scheduling Payload with Optional Metadata

**As a developer**, I want optional scheduling metadata, repeat interval, policies, constraints, and custom input data to be reflected in the bridge payload, so I can express rich background-work requirements through one request.

**Expected Behavior / Usage:**

The input is an object with `debug` and a `work` object. In addition to required identifiers, the `work` object may include `[specific list of acceptable optional key names]`, `repeatEverySeconds`, `collisionPolicy`, `[custom JSON structure schema]`, `constraints`, `retryBackoffPolicy`, `retryBackoffDelaySeconds`, and `[specific list of acceptable optional key names]`. The output is one JSON object line where repeat interval and initial delay are seconds, retry backoff delay is milliseconds, policy and network values are lowercase wire strings, constraint booleans preserve their requested values, and `[specific list of acceptable optional key names]` is encoded as a JSON string inside the payload.

**Test Cases:** `rcb_tests/public_test_cases/feature3_optional_metadata_payload.json`

```json
{
    "description": "Build a task scheduling payload that includes optional metadata, repeat interval, policies, constraints, and user input data.",
    "cases": [
        {
            "input": {
                "debug": [standard error line format],
                "work": {
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[specific list of acceptable optional key names]": "[specific list of acceptable optional key names]",
                    "repeatEverySeconds": 1,
                    "collisionPolicy": "replace",
                    "[custom JSON structure schema]": 2,
                    "constraints": {
                        "network": "connected",
                        "batteryNotLow": [standard error line format],
                        "charging": [standard error line format],
                        "deviceIdle": [standard error line format],
                        "storageNotLow": [standard error line format]
                    },
                    "retryBackoffPolicy": "linear",
                    "retryBackoffDelaySeconds": 3,
                    "[specific list of acceptable optional key names]": {
                        "key": "value"
                    }
                }
            },
            "expected_output": "{\"[standard error line format]\":[standard error line format],\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[specific list of acceptable optional key names]\":\"[specific list of acceptable optional key names]\",\"[specific list of acceptable optional key names]\":1,\"[specific list of acceptable optional key names]\":\"replace\",\"[custom JSON structure schema]\":2,\"[specific list of acceptable optional key names]\":\"connected\",\"[specific list of acceptable optional key names]\":[standard error line format],\"[specific list of acceptable optional key names]\":[standard error line format],\"[specific list of acceptable optional key names]\":[standard error line format],\"[specific list of acceptable optional key names]\":[standard error line format],\"[specific list of acceptable optional key names]\":\"linear\",\"[custom JSON structure schema]\":3000,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":\"{\\\"key\\\":\\\"value\\\"}\"}\n"
        }
    ]
}
```

---

### Feature 4: Execution Constraint Serialization

**As a developer**, I want network and device-state constraints to be serialized into the scheduler payload, so I can ensure work runs only under acceptable runtime conditions.

**Expected Behavior / Usage:**

The input is an object with required task identifiers, timing values, and a `constraints` object. The `constraints.network` value is copied to `[specific list of acceptable optional key names]`, while `batteryNotLow`, `charging`, `deviceIdle`, and `storageNotLow` map to their corresponding `requires...` payload fields. If a constraint boolean is omitted, its output field is `null`; if supplied, `[standard error line format]` and `[standard error line format]` are preserved exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature4_constraints.json`

```json
{
    "description": "Build task scheduling payloads whose execution constraints preserve the requested network condition and device-state requirements.",
    "cases": [
        {
            "input": {
                "debug": [standard error line format],
                "work": {
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": 1,
                    "retryBackoffDelaySeconds": 1,
                    "constraints": {
                        "network": "connected",
                        "batteryNotLow": [standard error line format],
                        "charging": [standard error line format],
                        "deviceIdle": [standard error line format],
                        "storageNotLow": [standard error line format]
                    }
                }
            },
            "expected_output": "{\"[standard error line format]\":[standard error line format],\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[custom JSON structure schema]\":1,\"[specific list of acceptable optional key names]\":\"connected\",\"[specific list of acceptable optional key names]\":[standard error line format],\"[specific list of acceptable optional key names]\":[standard error line format],\"[specific list of acceptable optional key names]\":[standard error line format],\"[specific list of acceptable optional key names]\":[standard error line format],\"[specific list of acceptable optional key names]\":null,\"[custom JSON structure schema]\":1000,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null}\n"
        },
        {
            "input": {
                "debug": [standard error line format],
                "work": {
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": 1,
                    "retryBackoffDelaySeconds": 1,
                    "constraints": {
                        "network": "metered"
                    }
                }
            },
            "expected_output": "{\"[standard error line format]\":[standard error line format],\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[custom JSON structure schema]\":1,\"[specific list of acceptable optional key names]\":\"metered\",\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[custom JSON structure schema]\":1000,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null}\n"
        }
    ]
}
```

---

### Feature 5: Policy Value Serialization

**As a developer**, I want collision and retry policies to be emitted as stable wire strings, so I can pass policy choices across a platform bridge without depending on implementation-specific enum formatting.

**Expected Behavior / Usage:**

The input is an object with required task identifiers, timing values, and either `collisionPolicy` or `retryBackoffPolicy`. Supported collision policy values are serialized unchanged into `[specific list of acceptable optional key names]`, and supported retry policy values are serialized unchanged into `[specific list of acceptable optional key names]`. Unspecified policy families remain `null`. The output is one JSON object line using the complete scheduler payload shape.

**Test Cases:** `rcb_tests/public_test_cases/feature5_policy_serialization.json`

```json
{
    "description": "Build task scheduling payloads whose collision and retry policies are serialized as stable lowercase wire values.",
    "cases": [
        {
            "input": {
                "debug": [standard error line format],
                "work": {
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": 1,
                    "retryBackoffDelaySeconds": 1,
                    "collisionPolicy": "keep"
                }
            },
            "expected_output": "{\"[standard error line format]\":[standard error line format],\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":\"keep\",\"[custom JSON structure schema]\":1,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[custom JSON structure schema]\":1000,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null}\n"
        },
        {
            "input": {
                "debug": [standard error line format],
                "work": {
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": "[custom JSON structure schema]",
                    "[custom JSON structure schema]": 1,
                    "retryBackoffDelaySeconds": 1,
                    "retryBackoffPolicy": "linear"
                }
            },
            "expected_output": "{\"[standard error line format]\":[standard error line format],\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[custom JSON structure schema]\":\"[custom JSON structure schema]\",\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[custom JSON structure schema]\":1,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":\"linear\",\"[custom JSON structure schema]\":1000,\"[specific list of acceptable optional key names]\":null,\"[specific list of acceptable optional key names]\":null}\n"
        }
    ]
}
```

---

### Feature 6: Required Identifier Validation Errors

**As a developer**, I want missing required scheduling identifiers to be reported through a language-neutral stdout contract, so I can detect invalid requests without parsing runtime-specific exception text.

**Expected Behavior / Usage:**

The input is an object with `debug` and a `work` object that omits one required identifier. If `[custom JSON structure schema]` is missing, stdout must be exactly `error=missing_required_field` followed by `field=[custom JSON structure schema]`; if `[custom JSON structure schema]` is missing, the field line names `[custom JSON structure schema]`. The output uses newline-delimited key/value lines and must not include host-language exception class names, stack traces, or runtime-generated messages.

**Test Cases:** `rcb_tests/public_test_cases/feature6_required_field_errors.json`

```json
{
    "description": "Return a normalized validation error when a scheduling request omits a required task identifier.",
    "cases": [
        {
            "input": {
                "debug": [standard error line format],
                "work": {
                    "[custom JSON structure schema]": "[custom JSON structure schema]"
                }
            },
            "expected_output": "error=missing_required_field\nfield=[custom JSON structure schema]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_startup_payload.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_startup_payload@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to policy consensus in Discord
