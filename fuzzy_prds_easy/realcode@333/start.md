## Product Requirement Document

# RPC Protocol Client Core - Endpoint Configuration, Filter Pipelines, and Typed Error Details

## Project Goal

Build an RPC client core that allows developers to configure HTTP-based RPC endpoints, compose request and response interceptors, frame streaming request bodies, and inspect typed error details without hand-writing repetitive transport plumbing.

---

## Background & Problem

Without this library/tool, developers are forced to manually parse service endpoint URLs, validate supported transport schemes, order outbound and inbound middleware, frame streaming messages, and decode structured error detail payloads. This leads to duplicated protocol handling, inconsistent middleware behavior, and fragile error inspection code.

With this library/tool, developers can create a client configuration once, register ordered filters around calls, rely on protocol framing for streaming bodies, and consume structured RPC errors through a stable interface.

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

### Feature 1: Client Endpoint Configuration

**As a developer**, I want to initialize an RPC client from a service endpoint string, so I can consistently derive the transport origin and route prefix used by later calls.

**Expected Behavior / Usage:**

*1.1 Endpoint URL parsing — Accept a supported HTTP endpoint string and expose the parsed scheme, host, and encoded path prefix.*

The input is a single endpoint URL string. The output must contain one line for the URL scheme, one line for the host, and one line for the encoded path. If the endpoint has no explicit path prefix, the path line is empty after `path[a specific sentinel byte representing the envelope marker]`. If the endpoint includes a path prefix, that prefix is preserved exactly as the encoded path used for subsequent request routing.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_host_url_parsing.json`

```json
{
  "description": "A client configuration created from an HTTP endpoint must expose the endpoint host and preserve an optional path prefix for later request routing.",
  "cases": [
    {
      "input": "https://service.example",
      "expected_output": "scheme[a specific sentinel byte representing the envelope marker]https[a specific sentinel byte representing the envelope marker]host[a specific sentinel byte representing the envelope marker]service.example[a specific sentinel byte representing the envelope marker]path[a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker]"
    },
    {
      "input": "https://service.example/api/v1",
      "expected_output": "scheme[a specific sentinel byte representing the envelope marker]https[a specific sentinel byte representing the envelope marker]host[a specific sentinel byte representing the envelope marker]service.example[a specific sentinel byte representing the envelope marker]path[a specific sentinel byte representing the envelope marker]/api/v1[a specific sentinel byte representing the envelope marker]"
    }
  ]
}
```

*1.2 Endpoint scheme validation — Reject endpoint URLs that do not use an HTTP transport scheme.*

The input is a single endpoint URL string. Only HTTP-family transport schemes are accepted. If the scheme is unsupported, the adapter must render a language-neutral argument error as `error[a specific sentinel byte representing the envelope marker]invalid_argument` and must not expose host-language exception class names or runtime-generated message text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_host_url_scheme_validation.json`

```json
{
  "description": "A client configuration must reject endpoint URLs whose scheme is not a supported HTTP transport scheme and report a normalized argument error.",
  "cases": [
    {
      "input": "xhtp://service.example",
      "expected_output": "error[a specific sentinel byte representing the envelope marker]invalid_argument[a specific sentinel byte representing the envelope marker]"
    }
  ]
}
```

---

### Feature 2: Filter Pipeline Ordering and Streaming Framing

**As a developer**, I want request and response filters to run in predictable order, so I can safely layer authentication, metadata mutation, logging, and protocol behavior around RPC calls.

**Expected Behavior / Usage:**

*2.1 Unary request filter order — Apply outbound unary request filters in registration order.*

The input is a comma-separated list of filter identifiers. Each filter appends its identifier to an observable request header. The output must show the accumulated header identifiers in the same order as the input list, proving that outbound unary request processing is first-in-first-applied.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_unary_interceptor_order.json`

```json
{
  "description": "For a unary request, outbound request filters must be applied in the same order in which they were registered, with each filter able to append observable header state.",
  "cases": [
    {
      "input": "1,2,3,4",
      "expected_output": "headers.id[a specific sentinel byte representing the envelope marker]1,2,3,4[a specific sentinel byte representing the envelope marker]"
    }
  ]
}
```

*2.2 Unary response filter order — Apply inbound unary response filters in reverse registration order.*

The input is a comma-separated list of filter identifiers. Each filter appends its identifier to an observable response header. The output must show the accumulated header identifiers in reverse order, proving that inbound unary response processing unwinds the filter stack from last registered to first registered.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_unary_response_order.json`

```json
{
  "description": "For a unary response, inbound response filters must be applied in reverse registration order so the last registered filter observes the response first.",
  "cases": [
    {
      "input": "1,2,3,4",
      "expected_output": "headers.id[a specific sentinel byte representing the envelope marker]4,3,2,1[a specific sentinel byte representing the envelope marker]"
    }
  ]
}
```

*2.3 Streaming request filter order — Apply outbound streaming request metadata filters in registration order.*

The input is a comma-separated list of filter identifiers. Each filter appends its identifier to an observable streaming request header. The output must show the accumulated header identifiers in registration order, proving that streaming request metadata follows the same outbound ordering rule as unary requests.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_stream_request_order.json`

```json
{
  "description": "For a streaming request, outbound request filters must be applied in registration order and expose the accumulated header mutations on the resulting request.",
  "cases": [
    {
      "input": "1,2,3,4",
      "expected_output": "headers.id[a specific sentinel byte representing the envelope marker]1,2,3,4[a specific sentinel byte representing the envelope marker]"
    }
  ]
}
```

*2.4 Streaming request [a specific sentinel byte representing the envelope marker] filter order and message [a specific sentinel byte representing the envelope marker] — Apply outbound [a specific sentinel byte representing the envelope marker] filters in registration order, then emit a framed message.*

The input is a comma-separated list of filter identifiers. Each filter appends its identifier bytes to the outgoing [a specific sentinel byte representing the envelope marker]. After all filters run, the protocol framing layer must emit the [a specific sentinel byte representing the envelope marker] as a single uncompressed message [a specific sentinel byte representing the envelope marker]. The output must include the [a specific sentinel byte representing the envelope marker] header byte and the decoded [a specific sentinel byte representing the envelope marker] bytes, making both filter ordering and framing observable.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_stream_request_[a specific sentinel byte representing the envelope marker]_order.json`

```json
{
  "description": "For a streaming request [a specific sentinel byte representing the envelope marker], outbound [a specific sentinel byte representing the envelope marker] filters must be applied in registration order before the protocol framing layer emits the [a specific sentinel byte representing the envelope marker] as a single message [a specific sentinel byte representing the envelope marker].",
  "cases": [
    {
      "input": "1,2,3,4",
      "expected_output": "[a specific sentinel byte representing the envelope marker].header[a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker]"
    }
  ]
}
```

*2.5 Streaming response header filter order — Validate protocol response headers, then apply inbound streaming result filters in reverse registration order.*

The input is a comma-separated list of filter identifiers. The adapter supplies a successful streaming response header result with a valid protocol content type. Each filter appends its identifier to an observable header on that result. The output must show the accumulated identifiers in reverse registration order, proving both that protocol header validation occurred and that inbound streaming result processing unwinds the filter stack.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_stream_header_result_order.json`

```json
{
  "description": "For streaming response headers, inbound result filters must be applied in reverse registration order after protocol content-type validation succeeds.",
  "cases": [
    {
      "input": "1,2,3,4",
      "expected_output": "headers.id[a specific sentinel byte representing the envelope marker]4,3,2,1[a specific sentinel byte representing the envelope marker]"
    }
  ]
}
```

---

### Feature 3: Typed RPC Error Details

**As a developer**, I want structured RPC errors to expose typed detail payloads through a detail parser, so I can inspect machine-readable error context without parsing human-readable messages.

**Expected Behavior / Usage:**

The input is a pipe-separated detail specification containing a detail type, detail payload text, the parser output text, and the number of repeated details. The system creates an RPC error with the supplied repeated detail payloads and uses the provided parser to unpack them. The output must include the RPC error code and every unpacked detail value in encounter order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_error_detail_unpacking.json`

```json
{
  "description": "An RPC error that carries repeated typed detail payloads must expose every detail that can be unpacked by the supplied detail parser while preserving the RPC error code.",
  "cases": [
    {
      "input": "type|value|unpacked_value|2",
      "expected_output": "code[a specific sentinel byte representing the envelope marker]unknown[a specific sentinel byte representing the envelope marker]unpacked[a specific sentinel byte representing the envelope marker]unpacked_value,unpacked_value[a specific sentinel byte representing the envelope marker]"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@[a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker][a specific sentinel byte representing the envelope marker].txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- append filters as seen in the unary interception logic
- header byte zero alignment from request processing
