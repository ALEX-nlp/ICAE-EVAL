## Product Requirement Document

# HTTP/2 Protocol Engine - Asynchronous Client, Server, Frame, and Flow-Control Behavior

## Project Goal

Build an HTTP/2 protocol engine that allows developers to create compliant asynchronous clients and servers, exchange framed messages, and manage protocol-level flow control without manually encoding pseudo-headers, handling connection state, or tracking window accounting.

---

## Background & Problem

Without this library/tool, developers are forced to handcraft HTTP/2 frames, translate request and response metadata into wire-level fields, respond to keepalive frames, and maintain stream and connection windows themselves. This leads to fragile protocol code, interoperability bugs, repetitive boilerplate, and errors that only appear under realistic peer interaction.

With this library/tool, callers work with high-level request, response, body, trailer, ping, frame, and capacity concepts while the engine preserves the externally observable HTTP/2 behavior required by peers on the wire.

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

### Feature 1: Client Request and Response Behavior

**As a developer**, I want the client side of an HTTP/2 connection to translate high-level requests and peer responses into protocol-observable behavior, so I can send valid requests and consume responses without handcrafting frames.

**Expected Behavior / Usage:**

*1.1 Client Request Target Normalization — accepted request targets are encoded as HTTP/2 request pseudo-header fields and receive peer responses.*

A client request command provides an operation, method, version, and either a URI or authority/path pieces. For accepted inputs, the adapter must print the method, path, scheme, authority, end-of-stream flag, and final response status observed through an HTTP/2 peer exchange. A path-only HTTP/1.1-style request is accepted and defaults to an `http` scheme with no authority; an absolute URI contributes its authority and normalized path; an authority plus `*` path preserves the asterisk request target.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_client_request_target_normalization.json`

```json
{
    "description": "Client requests with permitted request-target forms are encoded into HTTP/2 pseudo-headers and receive the peer response.",
    "cases": [
        {
            "input": {
                "method": "GET",
                "uri": "/",
                "version": "HTTP/1.1",
                "operation": "client-request-target"
            },
            "expected_output": "sent_method=GET\nsent_path=/\nsent_scheme=http\nsent_authority=\nend_stream=true\nresponse_status=200\n"
        }
    ]
}
```

*1.2 Client Request Validation — invalid request metadata is rejected before opening a stream.*

A client validation command provides an operation and, when testing headers, the candidate header name and value. HTTP/2 requests with only a path target are invalid when the request explicitly declares HTTP/2 semantics, and connection-specific headers are invalid in HTTP/2 requests. The adapter must print a normalized error category and, for header validation, the rejected header name; it must not print host-language exception class names or runtime-specific diagnostic suffixes.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_client_request_validation.json`

```json
{
    "description": "Client request creation rejects invalid HTTP/2 targets and connection-specific headers before sending a stream.",
    "cases": [
        {
            "input": {
                "operation": "http2-path-only-rejection"
            },
            "expected_output": "error=malformed_request_target\n"
        }
    ]
}
```

*1.3 Client Response Body Handling — informational responses, empty data, and trailers are surfaced through response/body observation.*

A client response command drives a peer exchange and prints the protocol-visible final status, body data, empty body chunk length, or trailer metadata depending on the operation. Informational response headers must not replace the final response; empty DATA on a HEAD response must be deliverable as a zero-length chunk; a response with only trailers must expose no body chunk and must expose the trailer count and value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_client_response_body_handling.json`

```json
{
    "description": "Client response handling preserves observable final response status, body data, empty body chunks, and trailers.",
    "cases": [
        {
            "input": {
                "operation": "informational-then-final-response"
            },
            "expected_output": "final_status=200\n[a generic body status indicator — consult the payload spec for the exact string]\n"
        }
    ]
}
```

---

### Feature 2: Server Request Acceptance

**As a developer**, I want the server side of an HTTP/2 connection to accept valid request forms and emit responses on the wire, so I can implement services without manually decoding request pseudo-headers.

**Expected Behavior / Usage:**

A server command supplies an operation and, for ordinary requests, a method and URI. The server must surface the accepted request method and path to application code and then write the response status observed by the peer. CONNECT requests without a path are accepted and expose an empty path. Origin-form requests with a scheme but no authority are accepted and expose `authority_present=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_server_request_acceptance.json`

```json
{
    "description": "Server-side handshakes surface accepted request method and path, then emit the configured response status on the wire.",
    "cases": [
        {
            "input": {
                "method": "GET",
                "uri": "https://example.com/",
                "operation": "server-request-response"
            },
            "expected_output": "accepted_method=GET\naccepted_path=/\nwire_response_status=200\n"
        }
    ]
}
```

---

### Feature 3: Ping Exchange

**As a developer**, I want HTTP/2 ping handling to respond to peers and protect user-initiated ping state, so I can monitor liveness without violating the protocol.

**Expected Behavior / Usage:**

A ping command supplies an operation. When a peer sends a ping payload, the connection must emit a pong with ACK set and the same payload. When the user sends a ping, a second user ping before the previous pong is received must be rejected with the neutral category `error=pending_ping`, and the previously outstanding pong must still be receivable.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_ping_exchange.json`

```json
{
    "description": "Ping handling returns protocol pongs for peer pings and prevents a second user ping while the previous pong is pending.",
    "cases": [
        {
            "input": {
                "operation": "peer-ping-auto-pong"
            },
            "expected_output": "pong_ack=true\npong_payload=[0, 0, 0, 0, 0, 0, 0, 0]\n"
        }
    ]
}
```

---

### Feature 4: Raw Frame Decoding

**As a developer**, I want raw HTTP/2 frames to decode into protocol fields, so I can inspect wire data without manually parsing frame bytes.

**Expected Behavior / Usage:**

A frame decoding command supplies an operation and, for DATA frames, a payload and end-stream flag. DATA output must include the frame type, stream identifier, decoded payload, and end-stream flag. GOAWAY output must include the frame type, last processed stream identifier, protocol reason token, and debug data bytes rendered as text.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_frame_decoding.json`

```json
{
    "description": "Raw frame decoding exposes DATA and GOAWAY frame fields as protocol-level values.",
    "cases": [
        {
            "input": {
                "payload": "hello",
                "end_stream": false,
                "operation": "decode-data-frame"
            },
            "expected_output": "frame_type=data\nstream_id=1\npayload=hello\nend_stream=false\n"
        }
    ]
}
```

---

### Feature 5: Flow-Control Window Management

**As a developer**, I want receive-window accounting to emit window updates and detect overflow violations, so I can process large response bodies safely and remain compliant with HTTP/2 flow control.

**Expected Behavior / Usage:**

A flow-control command supplies an operation. When consumed body capacity is released, the engine must emit both connection-level and stream-level WINDOW_UPDATE signals with the released size while continuing to consume the response body. If a peer sends more DATA than the connection window permits, the body and connection must report the neutral category `flow_control_violation`, and the wire-level signal must be a GOAWAY with reason `FLOW_CONTROL_ERROR` and last stream identifier `0`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_flow_control_window_updates.json`

```json
{
    "description": "Flow-control handling emits window updates after capacity release and reports protocol-visible flow-control violations.",
    "cases": [
        {
            "input": {
                "operation": "release-capacity-window-update"
            },
            "expected_output": "response_status=200\n[cumulative throughput metrics — verify against the latest load test baseline]\nwindow_update_stream=0\nwindow_update_size=32768\nwindow_update_stream=1\nwindow_update_size=32768\n[cumulative throughput metrics — verify against the latest load test baseline]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_client_request_target_normalization.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_client_request_target_normalization@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the default stream ID convention used throughout the decoder
