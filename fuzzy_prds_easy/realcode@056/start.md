## Product Requirement Document

# HTTP Outcome Result Mapper — Turning Responses, Failures, and Status Codes into a Typed Result

## Project Goal

Build a small mapping layer that converts the raw outcome of an HTTP call into a single, closed family of result values — a success carrying its payload, a server error carrying its status code and error body, a network error, or an unknown error — so developers can branch on a well-defined result type instead of juggling nullable bodies, status-code checks, and thrown exceptions by hand.

---

## Background & Problem

When an HTTP call completes, its outcome arrives in several shapes: a delivered response with some status code and an optional body, or a thrown failure (a lost connection, an HTTP-protocol error that still carries a response, or some other error such as a payload that could not be decoded). Without a unifying layer, every call site repeats the same fragile boilerplate: check whether the status was successful, null-check the body, special-case empty bodies, and wrap everything in try/catch to convert exceptions into something usable.

This library centralizes that decision once. It defines one result type with exactly four outcomes and a deterministic rule for choosing which outcome a given HTTP situation maps to, plus the field each outcome should expose (the success payload, or the status code and error body for a server error). A convenience accessor is also provided to pull the success value out in one step. The result is implementation-independent: the same status-code/body/failure inputs always produce the same outcome and fields.

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

The result is a closed family of four outcomes. Every feature below describes which HTTP situation produces which outcome and what fields that outcome exposes. The execution adapter renders an outcome as a set of newline-terminated `key=value` lines: every outcome begins with a `result=<variant>` line where variant is one of `success`, `server_error`, `network_error`, `unknown_error`. A success line is followed by a `body=` line (the payload, or the literal token `<empty>` when the success carried no payload). A server-error is followed by a `code=` line (the numeric status) and a `body=` line (the error content, [a specific sentinel token — ask the PM for the exact literal] when no error body is present at all, or an empty value when the error content was an empty string). A network-error is followed by `error=io` and an unknown-error by `error=unknown`. When a mapped outcome retains response headers, each retained header is rendered as an additional `header.<name>=<value>` line, with header names in ascending order.

### Feature 1: Map A Received HTTP Response To A Result

**As a developer**, I want a delivered HTTP response (its status code, optional body, and headers) classified into a success or a server error automatically, so I can branch on a typed result instead of manually inspecting status codes and null-checking bodies.

**Expected Behavior / Usage:**

The input names a `map_response` action and supplies the response's status `code`, an optional `body` (the decoded payload text; absent means no body was present), an optional `success_type` flag, and an optional `headers` map. The mapping rule is driven by the status code (2xx is "successful") and the presence of a body, as detailed in the leaf sub-features below.

*1.1 Successful Response With A Body — a 2xx status carrying a payload maps to success*

When the status code is in the 2xx range and a body is present, the outcome is a success whose value is that body. Any headers supplied on the response are retained on the result and remain observable. The adapter emits the `success` result line, the `body=` line carrying the payload, then one `header.<name>=<value>` line per retained header (header names sorted ascending).

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_success_with_body.json`

```json
{
    "description": "A received HTTP response carries a 2xx status code together with a decoded payload. The mapping treats this as the success outcome, exposing the payload as the result's value, and any response headers that were present are carried through and remain observable on the result. The value and headers are echoed back so the caller can confirm both the payload content and that header metadata survived the mapping.",
    "cases": [
        {
            "input": {"action": "map_response", "code": 200, "body": "Hi!", "headers": {"TEST": "test"}},
            "expected_output": "result=success\nbody=Hi!\nheader.TEST=test\n"
        }
    ]
}
```

*1.2 Successful Response With An Empty Body — a 2xx status with no payload, where none is expected, maps to an empty success*

When the status code is in the 2xx range, no body is present, and the caller declared (via `[a specific sentinel flag value — ask the PM for the exact string]) that this endpoint is not expected to return a payload, the outcome is a success carrying an empty payload. The adapter emits the `success` result line followed by `body=<empty>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_success_empty_body.json`

```json
{
    "description": "A received HTTP response carries a successful (2xx) status code but no payload, and the caller declared that this endpoint is not expected to return a body. The mapping treats this as a successful outcome with an empty payload rather than an error, so the caller can distinguish a deliberately bodyless success (e.g. a no-content acknowledgement) from a failure.",
    "cases": [
        {
            "input": {"action": "map_response", "code": 204, "success_type": "empty"},
            "expected_output": "result=success\nbody=<empty>\n"
        }
    ]
}
```

*1.3 Non-Successful Response — any non-2xx status maps to a server error*

When the status code is outside the 2xx range, the outcome is a server error that preserves the numeric status code and exposes the decoded error content as its body. The error body is the decoded content text; when the error response had no content, the body is the empty string (present, not absent). Headers supplied on the response are retained and remain observable. The adapter emits the `server_error` result line, a `code=` line, a `body=` line, then any retained header lines (sorted ascending by name).

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_server_error.json`

```json
{
    "description": "A received HTTP response carries a non-2xx status code. The mapping treats this as a server-error outcome, preserving the numeric status code and exposing the error payload content as the result's error body. When the error response had no content the error body is the empty string (still present, not absent), and any headers present on the response are carried through and remain observable.",
    "cases": [
        {
            "input": {"action": "map_response", "code": 404, "body": "An error occurred"},
            "expected_output": "result=server_error\ncode=404\nbody=An error occurred\n"
        },
        {
            "input": {"action": "map_response", "code": 404, "headers": {"TEST": "test"}},
            "expected_output": "result=server_error\ncode=404\nbody=\nheader.TEST=test\n"
        }
    ]
}
```

---

### Feature 2: Map A Thrown Failure To A Result

**As a developer**, I want a failure raised during a call classified into the right outcome category, so a lost connection, a server error surfaced as an exception, and any other error each land in a distinct, predictable result variant.

**Expected Behavior / Usage:**

The input names a `map_failure` action and supplies a `kind` describing the nature of the failure. The mapping classifies the failure by kind, as detailed below.

*2.1 Connectivity/IO Failure — maps to a network error*

When the failure is a connectivity/IO failure (`kind` of `io`), meaning the exchange could not be delivered or completed at the transport level, the outcome is a network error. The adapter emits the `network_error` result line followed by `error=io`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_failure_io.json`

```json
{
    "description": "A request fails before any HTTP response is received because of a connectivity/IO failure (the transport could not deliver or complete the exchange). The mapping classifies this as a network-error outcome, a distinct category from a server-side error, so the caller can react to transient connectivity problems (for example, by retrying) separately from real server responses.",
    "cases": [
        {
            "input": {"action": "map_failure", "kind": "io"},
            "expected_output": "result=network_error\nerror=io\n"
        }
    ]
}
```

*2.2 HTTP-Protocol Failure Carrying A Response — maps to a server error*

When the failure is an HTTP-protocol failure (`kind` of `http`) that still carries the server's response, the outcome is a server error: the carried status `code` and decoded error `body` are unwrapped exactly as if the error had been received as a direct response. The adapter emits the `server_error` result line, a `code=` line, and a `body=` line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_failure_http.json`

```json
{
    "description": "A request fails by raising an HTTP-protocol failure that still carries the server's response (a status code plus an error payload). The mapping unwraps that carried response into a server-error outcome, preserving the numeric status code and decoding the error payload content as the error body, so an error surfaced via a raised failure is treated identically to an error received as a direct response.",
    "cases": [
        {
            "input": {"action": "map_failure", "kind": "http", "code": 404, "body": "Server Error"},
            "expected_output": "result=server_error\ncode=404\nbody=Server Error\n"
        }
    ]
}
```

*2.3 Any Other Failure — maps to an unknown error*

When the failure is neither a connectivity/IO failure nor an HTTP-protocol failure carrying a response (`kind` of `other`) — for example a payload decoding/parsing failure — the outcome is an unknown error, the catch-all category. The adapter emits the `unknown_error` result line followed by `error=unknown`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_failure_unknown.json`

```json
{
    "description": "A request fails with a failure that is neither a connectivity/IO failure nor an HTTP-protocol failure carrying a response (for example, a payload decoding/parsing failure raised while interpreting the body). The mapping classifies this as an unknown-error outcome, the catch-all category for failures that do not fit the network or server buckets.",
    "cases": [
        {
            "input": {"action": "map_failure", "kind": "other"},
            "expected_output": "result=unknown_error\nerror=unknown\n"
        }
    ]
}
```

---

### Feature 3: Extract The Success Value From A Result

**As a developer**, I want a one-step accessor that yields the success payload or nothing, so I can write value-or-default code without explicitly matching on every outcome.

**Expected Behavior / Usage:**

The input names an `extract_value` action and supplies a `variant` describing which outcome to build (a `success` with a `body`, or a non-success outcome). The accessor returns the contained payload when the result is a success, and returns nothing (a null/absent value) for every non-success outcome. The adapter emits a single `value=<payload>` line for a success, or [a specific null-indicating sentinel — ask the PM for the exact output string] when there is no value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_extract_value.json`

```json
{
    "description": "A convenience accessor pulls the success value out of a result. When the result is a success outcome it returns the contained payload; for any non-success outcome (server error, network error, or unknown error) it returns nothing (a null/absent value). This lets a caller obtain the value-or-default in one step without explicitly inspecting which outcome occurred.",
    "cases": [
        {
            "input": {"action": "extract_value", "variant": "success", "body": "Hello!"},
            "expected_output": "value=Hello!\n"
        },
        {
            "input": {"action": "extract_value", "variant": "network_error"},
            "expected_output": "value=<null>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the result family and the mapping rules above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core mapping logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing, and must model errors as proper result variants rather than leaking host-language runtime exception identities.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting outcome to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `map_response` classifies a delivered response (`code`, optional `body`, optional `success_type`, optional `headers`); `map_failure` classifies a thrown failure by `kind` (`io`, `http` with `code`/`body`, or `other`); `extract_value` builds a result of the given `variant` and prints the extracted success value or `<null>`. The adapter is solely responsible for translating native failures into the neutral `error=io` / `error=unknown` category lines; the core domain may raise idiomatic exceptions but their language identity must never appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Follow the same header-ordering convention used in the response-mapping module.
- The output block structure mirrors the pattern described in the result-line spec.
