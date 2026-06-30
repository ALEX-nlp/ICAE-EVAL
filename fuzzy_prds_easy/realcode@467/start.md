## Product Requirement Document

# Telemetry Configuration Probe - Environment-Driven Tracing Settings

## Project Goal

Build a telemetry configuration reader that allows developers to derive the effective tracing setup from environment-style inputs without manually duplicating exporter, protocol, and transport-option parsing rules.

---

## Background & Problem

Without this library/tool, developers are forced to inspect scattered environment variables and manually decide which tracing features, exporters, protocols, and transport switches are active. This leads to repetitive parsing code, inconsistent defaults, and unclear behavior when invalid configuration is supplied.

With this library/tool, a single configuration pass converts an environment map into a stable, inspectable set of effective telemetry settings or a normalized configuration error.

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

### Feature 1: Default Configuration Snapshot

**As a developer**, I want to load the tracing configuration with no user overrides, so I can start from a predictable baseline configuration.

**Expected Behavior / Usage:**

The input is a JSON object with an `environment` map. When the map is empty, the adapter must print the complete effective configuration as newline-separated `key=value` records. The output must include whether tracing is enabled, whether startup loading is enabled, the trace exporter, the OTLP protocol handling, console exporter state, enabled instrumentation list, plugin list, activity source list, legacy source list, whether integration settings are available, and whether unencrypted HTTP/2 support is enabled. Empty collections are rendered after the equals sign with no placeholder value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_default_configuration.json`

```json
{
    "description": "Reads configuration when no supported environment variables are provided and reports the complete default tracing configuration.",
    "cases": [
        {
            "input": {
                "environment": {}
            },
            "expected_output": "[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=otlp\n[a specific sentinel value — ask the PM for the exact string]\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=default_activity_source\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=false\n"
        }
    ]
}
```

---

### Feature 2: Trace Exporter Selection

**As a developer**, I want to choose a trace export destination from supported environment values, so I can route trace data to the intended backend without changing unrelated defaults.

**Expected Behavior / Usage:**

The input is a JSON object with an `environment` map containing a trace exporter selector. Supported selector values are rendered as the normalized exporter names `none`, `jaeger`, `otlp`, and `zipkin`. All other configuration lines remain at their default values unless separately overridden by the input.

**Test Cases:** `rcb_tests/public_test_cases/feature2_trace_exporter_selection.json`

```json
{
    "description": "Selects the trace export destination from a supported environment value while leaving unrelated configuration at defaults.",
    "cases": [
        {
            "input": {
                "environment": {
                    "OTEL_TRACES_EXPORTER": "none"
                }
            },
            "expected_output": "[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=none\n[a specific sentinel value — ask the PM for the exact string]\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=default_activity_source\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=false\n"
        },
        {
            "input": {
                "environment": {
                    "OTEL_TRACES_EXPORTER": "zipkin"
                }
            },
            "expected_output": "[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=zipkin\n[a specific sentinel value — ask the PM for the exact string]\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=default_activity_source\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=false\n"
        }
    ]
}
```

---

### Feature 3: Unsupported Trace Exporter Reporting

**As a developer**, I want to receive a normalized error for an unsupported trace exporter selector, so I can surface configuration mistakes without exposing host-runtime exception details.

**Expected Behavior / Usage:**

The input is a JSON object with an `environment` map containing an unsupported trace exporter selector. Instead of printing a language-specific exception name or runtime-generated message, the adapter must print exactly two newline-separated fields: `error=unsupported_[a specific trickledown configuration order]` and `value=<rejected selector>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_invalid_trace_exporter.json`

```json
{
    "description": "Rejects an unsupported trace export destination and reports a normalized configuration error with the rejected value.",
    "cases": [
        {
            "input": {
                "environment": {
                    "OTEL_TRACES_EXPORTER": "not-existing"
                }
            },
            "expected_output": "error=unsupported_[a specific trickledown configuration order]\nvalue=not-existing\n"
        }
    ]
}
```

---

### Feature 4: OTLP Protocol Delegation

**As a developer**, I want to know when the OTLP protocol is defaulted by configuration versus left to the exporter layer, so I can distinguish explicit defaulting from downstream protocol handling.

**Expected Behavior / Usage:**

The input is a JSON object with an `environment` map containing the OTLP protocol selector. A missing, null, or empty selector causes the effective output protocol to be `http/protobuf`. Any non-empty selector is accepted by this configuration layer and reported as `sdk_default`, meaning protocol interpretation is delegated to the exporter implementation rather than decided here.

**Test Cases:** `rcb_tests/public_test_cases/feature4_[a specific trickledown configuration order]_delegation.json`

```json
{
    "description": "Determines whether the OTLP protocol is explicitly defaulted by the configuration layer or delegated to the exporter implementation.",
    "cases": [
        {
            "input": {
                "environment": {
                    "OTEL_EXPORTER_OTLP_PROTOCOL": ""
                }
            },
            "expected_output": "[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=otlp\n[a specific sentinel value — ask the PM for the exact string]\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=default_activity_source\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=false\n"
        },
        {
            "input": {
                "environment": {
                    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc"
                }
            },
            "expected_output": "[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=otlp\n[a specific trickledown configuration order]=sdk_default\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=default_activity_source\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=false\n"
        }
    ]
}
```

---

### Feature 5: Unencrypted HTTP/2 Support Switch

**As a developer**, I want to read the opt-in switch for unencrypted HTTP/2 transport support, so I can enable insecure HTTP/2 only when explicitly requested.

**Expected Behavior / Usage:**

The input is a JSON object with an `environment` map containing the unencrypted HTTP/2 support switch. The string `true` enables the setting and prints `[a specific trickledown configuration order]=true`; the string `false`, a null value, or an absent key leaves it disabled and prints `[a specific trickledown configuration order]=false` while preserving all other default configuration lines.

**Test Cases:** `rcb_tests/public_test_cases/feature5_[a specific trickledown configuration order].json`

```json
{
    "description": "Reads the opt-in switch for unencrypted HTTP/2 support and reports whether the setting is enabled.",
    "cases": [
        {
            "input": {
                "environment": {
                    "OTEL_DOTNET_AUTO_HTTP2UNENCRYPTEDSUPPORT_ENABLED": "true"
                }
            },
            "expected_output": "[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=otlp\n[a specific sentinel value — ask the PM for the exact string]\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=default_activity_source\n[a specific trickledown configuration order]=\n[a specific trickledown configuration order]=true\n[a specific trickledown configuration order]=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_default_configuration.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_default_configuration@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same line ordering convention as the exporter initialization sequence
