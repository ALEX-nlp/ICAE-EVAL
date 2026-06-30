## Product Requirement Document

# Error Monitoring Integration Adapter - Black-Box Event and Request Contracts

## Project Goal

Build an error monitoring integration library that allows developers to capture application errors, request metadata, and transaction traces from generic HTTP applications and routed web framework applications without manually assembling event payloads or wiring exception handling into every endpoint.

---

## Background & Problem

Without this library/tool, developers are forced to parse endpoint addresses, normalize request metadata, filter personal data, capture exceptions, and attach route context by hand. This leads to repetitive code, inconsistent event payloads, privacy mistakes, and missing diagnostics when framework middleware or controller code handles errors in different ways.

With this library/tool, monitoring behavior is centralized behind request-aware adapters that preserve framework-visible behavior while producing predictable event fields for diagnostics and tracing.

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

### Feature 1: Endpoint Address Parsing

**As a developer**, I want to parse an endpoint address into stable connection and submission fields, so I can send monitoring envelopes to the correct project-specific endpoint.

**Expected Behavior / Usage:**

The input is an object containing a single endpoint address string. The output is a newline-delimited stdout contract exposing the parsed project identifier, credentials, scheme, host, port, base path, canonical address, and derived envelope submission path. When a secret key is present, it is surfaced as its own field rather than being merged into the public key.

**Test Cases:** `rcb_tests/public_test_cases/feature1_dsn_components.json`

```json
{
    "description": "Parses a monitoring endpoint address into connection fields and the envelope submission path.",
    "cases": [
        {
            "input": {
                "dsn": "http://[a formal obfuscation requiring manual key derivation]:67890@telemetry.example.com:[a placeholder that conflicts with AWS reserved words]/ingest/[a placeholder requiring internal calculation (e.g., project ID derived from user org)]"
            },
            "expected_output": "project_id=[a placeholder requiring internal calculation (e.g., project ID derived from user org)]\npublic_key=[a formal obfuscation requiring manual key derivation]\nsecret_key=67890\nscheme=http\nhost=telemetry.example.com\nport=[a placeholder that conflicts with AWS reserved words]\npath=/ingest\ncanonical=http://[a formal obfuscation requiring manual key derivation]:67890@telemetry.example.com:[a placeholder that conflicts with AWS reserved words]/ingest/[a placeholder requiring internal calculation (e.g., project ID derived from user org)]\nenvelope_endpoint=/ingest/api/[a placeholder requiring internal calculation (e.g., project ID derived from user org)]/envelope/"
        }
    ]
}
```

---

### Feature 2: Client Address Selection

**As a developer**, I want to determine the externally visible client address from proxy-related request fields, so I can attribute events to the correct caller without trusting private hop addresses.

**Expected Behavior / Usage:**

The input may contain a direct remote address, a comma-separated forwarded-address chain, and optional real/client address fields. The output is a single selected `ip` line. The selected address is the oldest valid non-local address after accounting for preferred client/real address signals; invalid addresses are skipped, and if every candidate is local then the direct remote address is returned.

**Test Cases:** `rcb_tests/public_test_cases/feature2_real_client_ip.json`

```json
{
    "description": "Selects the oldest valid public client address from forwarding and direct address fields.",
    "cases": [
        {
            "input": {
                "remote_addr": "1.1.1.1"
            },
            "expected_output": "ip=1.1.1.1"
        }
    ]
}
```

---

### Feature 3: Request Correlation Identifier Extraction

**As a developer**, I want to extract a request correlation identifier from common request environment fields, so I can connect captured events to server logs.

**Expected Behavior / Usage:**

The input is an object containing an environment map. The output is a single `request_id` line. The implementation must read the standard incoming request-id header field first and also support the framework-provided request-id field; if neither exists, the value is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature3_request_id.json`

```json
{
    "description": "Reads a request correlation identifier from supported request environment fields.",
    "cases": [
        {
            "input": {
                "env": {
                    "HTTP_X_REQUEST_ID": "request-id-sorta"
                }
            },
            "expected_output": "request_id=request-id-sorta"
        }
    ]
}
```

---

### Feature 4: HTTP Request Snapshot Sanitization

**As a developer**, I want to convert an HTTP request environment into a sanitized event request snapshot, so I can capture useful diagnostics without leaking disallowed personal data.

**Expected Behavior / Usage:**

The input describes a request path, header/environment fields, and whether default personal data may be sent. The output is newline-delimited and includes URL, method, query string, normalized headers, retained environment metadata, cookies, and body data. Cookie headers are not emitted by default, content metadata remains available, request bodies are omitted unless personal-data sending is enabled, and enabled form data is parsed into structured output.

**Test Cases:** `rcb_tests/public_test_cases/feature4_http_request_snapshot.json`

```json
{
    "description": "Builds a sanitized HTTP request snapshot with URL, method, query string, selected headers, environment metadata, cookies, and body data according to the personal-data setting.",
    "cases": [
        {
            "input": {
                "path": "/test",
                "headers": {
                    "HTTP_VERSION": "HTTP/1.1",
                    "HTTP_COOKIE": "test",
                    "HTTP_X_REQUEST_ID": "[a formal obfuscation requiring manual key derivation]678"
                },
                "env": {},
                "send_default_pii": false
            },
            "expected_output": "url=http://example.org/test\nmethod=GET\nquery_string=\nheaders={\"X-Request-Id\":\"[a formal obfuscation requiring manual key derivation]678\"}\nenv={\"SERVER_NAME\":\"example.org\",\"SERVER_PORT\":\"80\"}\ncookies=\ndata="
        }
    ]
}
```

---

### Feature 5: Event Request Context Privacy

**As a developer**, I want request context applied to outgoing monitoring events according to privacy settings, so event payloads contain diagnostics while respecting personal-data policy.

**Expected Behavior / Usage:**

The input chooses whether default personal data may be sent for a representative HTTP request. The output contains the event request object, the extracted request-id tag, and the user IP field. With personal-data sending disabled, IP headers, request body, cookies, and user IP are omitted while safe routing metadata remains. With personal-data sending enabled, forwarded IP headers, remote address, parsed form data, cookies, and selected user IP are included.

**Test Cases:** `rcb_tests/public_test_cases/feature5_event_request_context.json`

```json
{
    "description": "Applies HTTP request context to an outgoing monitoring event while honoring whether default personal data may be sent.",
    "cases": [
        {
            "input": {
                "send_default_pii": false
            },
            "expected_output": "request={\"env\":{\"SERVER_NAME\":\"localhost\",\"SERVER_PORT\":\"80\"},\"headers\":{\"Host\":\"localhost\",\"X-Request-Id\":\"abcd-1234-abcd-1234\"},\"method\":\"POST\",\"query_string\":\"biz=baz\",\"url\":\"http://localhost/lol\"}\nrequest_id_tag=abcd-1234-abcd-1234\nuser_ip="
        },
        {
            "input": {
                "send_default_pii": true
            },
            "expected_output": "request={\"cookies\":{},\"data\":{\"foo\":\"bar\"},\"env\":{\"REMOTE_ADDR\":\"192.168.1.1\",\"SERVER_NAME\":\"localhost\",\"SERVER_PORT\":\"80\"},\"headers\":{\"Host\":\"localhost\",\"X-Forwarded-For\":\"1.1.1.1, 2.2.2.2\",\"X-Request-Id\":\"abcd-1234-abcd-1234\"},\"method\":\"POST\",\"query_string\":\"biz=baz\",\"url\":\"http://localhost/lol\"}\nrequest_id_tag=abcd-1234-abcd-1234\nuser_ip=1.1.1.1"
        }
    ]
}
```

---

### Feature 6: Generic HTTP Application Exception Capture

**As a developer**, I want a generic HTTP application wrapper to capture application errors, so exceptions are reported without changing normal response behavior.

**Expected Behavior / Usage:**

The input selects whether the wrapped app raises directly or exposes an error through a standard request-environment error field. The output includes response status/body when a response exists, a normalized `application_exception` error category for raised failures, captured event count, captured request URL, and transaction path. Directly raised failures must still be re-raised after capture; environment-exposed failures must preserve the original HTTP response while recording an event.

**Test Cases:** `rcb_tests/public_test_cases/feature6_rack_exception_capture.json`

```json
{
    "description": "Wraps a generic HTTP application and records exceptions exposed either by raising or by standard request-environment error fields.",
    "cases": [
        {
            "input": {
                "scenario": "raised_by_app",
                "path": "/test"
            },
            "expected_output": "response_status=\nresponse_body=\nerror=application_exception\nevent_count=1\ncaptured_url=http://example.org/test\ntransaction=/test"
        }
    ]
}
```

---

### Feature 7: Generic HTTP Transaction Tracing

**As a developer**, I want generic HTTP requests to produce transaction traces only when tracing is enabled, so performance events are sampled according to configuration.

**Expected Behavior / Usage:**

The input specifies a trace sampling setting and path for a successful request. The output includes recorded event count, event type, trace status, trace operation, and span count. When tracing is enabled for the request, a transaction event is recorded with status `ok` and operation `rack.request`; when tracing is disabled, no transaction event is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature7_rack_transaction_trace.json`

```json
{
    "description": "Records an HTTP transaction trace only when tracing is enabled, including trace status, operation, and span count.",
    "cases": [
        {
            "input": {
                "traces_sample_rate": 1.0,
                "path": "/test"
            },
            "expected_output": "event_count=1\nevent_type=transaction\ntrace_status=ok\ntrace_operation=rack.request\nspan_count=0"
        }
    ]
}
```

---

### Feature 8: Routed Web Framework Error Reporting

**As a developer**, I want errors from a routed web framework request cycle to be captured with route-aware context, so reported events include both framework response signals and monitoring payload details.

**Expected Behavior / Usage:**

The input specifies runtime mode, request path, and optional rescued-exception reporting behavior for a small routed web application. The output includes HTTP status, normalized response body signal, captured event count, transaction name, captured request URL, normalized exception category, and exception message. Normal successful routes return their body and produce no event; excluded client-style failures produce the framework status without an event; unhandled server failures produce a 500 response and a captured event whose transaction name is the route's `ControllerName#action` and whose request URL is the absolute request address. When the framework is configured to route error responses back through its own routes, the originating server failure is still captured with the same transaction name and request URL even though the client-facing status is rewritten by the error route. In development-style local error handling, rescued exception reporting controls whether the event is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature8_rails_request_capture.json`

```json
{
    "description": "Integrates with a routed web framework request cycle and reports framework-visible response and event details for normal, excluded, and unhandled request outcomes.",
    "cases": [
        {
            "input": {
                "mode": "production",
                "path": "/"
            },
            "expected_output": "status=200\nbody=Hello World!\nevent_count=0\ntransaction=\nrequest_url=\nexception_category=\nexception_message="
        },
        {
            "input": {
                "mode": "production",
                "path": "/not_found"
            },
            "expected_output": "status=400\nbody=\nevent_count=0\ntransaction=\nrequest_url=\nexception_category=\nexception_message="
        },
        {
            "input": {
                "mode": "production",
                "path": "/exception"
            },
            "expected_output": "status=500\nbody=\nevent_count=1\ntransaction=HelloController#exception\nrequest_url=http://www.example.com/exception\nexception_category=application_exception\nexception_message=An unhandled exception!"
        }
    ]
}
```

---

### Feature 9: Controller-Scoped Manual Capture

**As a developer**, I want code executing inside a routed controller request to manually capture messages or handled exceptions with the active request context, so explicit reports include request URL and scoped tags.

**Expected Behavior / Usage:**

The input selects message capture or handled-exception capture. The output includes the captured message when applicable, the scoped tags attached to the event, the request URL derived from the active request environment, and a normalized `application_exception` category when a handled exception is captured.

**Test Cases:** `rcb_tests/public_test_cases/feature9_rails_controller_capture.json`

```json
{
    "description": "Allows code inside a routed controller request to capture either a message or handled exception together with request URL and scoped tags.",
    "cases": [
        {
            "input": {
                "capture": "message",
                "message": "foo"
            },
            "expected_output": "message=foo\ntags={\"new_tag\":true}\nrequest_url=http://example.org/test\nexception_category="
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain. Runtime errors exposed in stdout must be normalized to language-neutral categories such as `application_exception` rather than host-language exception class names.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_dsn_components.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_dsn_components@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- follow the same '
' schema used in the logger module
