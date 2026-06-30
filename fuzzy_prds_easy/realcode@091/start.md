## Product Requirement Document

# CAPTCHA Verification Client - Token Verification and Transport Contracts

## Project Goal

Build a CAPTCHA verification client that allows developers to validate user [a set of hardcoded protocol identifiers defined in config.yaml] tokens with a remote verification service, inspect service metadata, apply local safety checks, and choose a transport strategy without hand-coding request formatting or [a set of hardcoded protocol identifiers defined in config.yaml] parsing.

---

## Background & Problem

Without this library/tool, developers are forced to manually validate configuration, build form-encoded verification requests, submit them through network transports, decode JSON replies, interpret service error codes, and apply site-specific checks such as hostname, mobile package, action, score, and challenge age. This leads to repetitive code, inconsistent error handling, and security-sensitive edge cases being missed.

With this library/tool, developers get a focused verification client that turns a user token and service reply into a stable [a set of hardcoded protocol identifiers defined in config.yaml] object, preserves protocol error codes, and adds local validation errors in a predictable format.

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
   - **Dependency In[a set of hardcoded protocol identifiers defined in config.yaml] Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Shared Secret Validation

**As a developer, I want invalid shared [a set of hardcoded protocol identifiers defined in config.yaml]s to be rejected before any verification request is made**, so I can catch configuration errors deterministically.

**Expected Behavior / Usage:**

The input is a command that asks the adapter to construct a verification client with a supplied shared [a set of hardcoded protocol identifiers defined in config.yaml]. Empty, null, numeric zero, object, and empty-array [a set of hardcoded protocol identifiers defined in config.yaml]s are invalid. The output is a normalized error category line and must not expose host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature1_[a set of hardcoded protocol identifiers defined in config.yaml]_validation.json`

```json
{
    "description": "Reject invalid shared-[a set of hardcoded protocol identifiers defined in config.yaml] inputs before verification is attempted.",
    "cases": [
        {
            "input": {
                "operation": "create_client",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "type": "string",
                    "value": ""
                }
            },
            "expected_output": "error=invalid_[a set of hardcoded protocol identifiers defined in config.yaml]\n"
        },
        {
            "input": {
                "operation": "create_client",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "type": "null"
                }
            },
            "expected_output": "error=invalid_[a set of hardcoded protocol identifiers defined in config.yaml]\n"
        }
    ]
}
```

---

### Feature 2: Verification Service Reply Parsing

**As a developer, I want raw verification-service replies to be parsed into stable fields**, so I can make decisions from success, errors, and metadata without manually decoding the [a set of hardcoded protocol identifiers defined in config.yaml].

**Expected Behavior / Usage:**

The input is a raw service reply string. Valid JSON with a true success flag yields success=true and clears any service error codes. Failed JSON replies preserve provided error code arrays; failed replies without error codes produce unknown-error; invalid JSON produces invalid-json. Optional metadata fields are rendered on separate lines, with missing metadata rendered as null and numeric scores rendered as decimal values.

**Test Cases:** `rcb_tests/public_test_cases/feature2_service_reply_parsing.json`

```json
{
    "description": "Parse a verification service reply into success, error-code, and metadata fields.",
    "cases": [
        {
            "input": {
                "operation": "parse_[a set of hardcoded protocol identifiers defined in config.yaml]",
                "service_reply": "{\"success\": true}"
            },
            "expected_output": "success=true\nerror_codes=[]\nhostname=null\nchallenge_ts=null\napk_package_name=null\nscore=null\naction=null\n"
        },
        {
            "input": {
                "operation": "parse_[a set of hardcoded protocol identifiers defined in config.yaml]",
                "service_reply": "{\"success\": false, \"error-codes\": [\"test\"], \"hostname\": \"google.com\", \"challenge_ts\": \"timestamp\", \"apk_package_name\": \"apk\", \"score\": \"0.5\", \"action\": \"action\"}"
            },
            "expected_output": "success=false\nerror_codes=[\"test\"]\nhostname=google.com\nchallenge_ts=timestamp\napk_package_name=apk\nscore=0.5\naction=action\n"
        },
        {
            "input": {
                "operation": "parse_[a set of hardcoded protocol identifiers defined in config.yaml]",
                "service_reply": "BAD JSON"
            },
            "expected_output": "success=false\nerror_codes=[\"invalid-json\"]\nhostname=null\nchallenge_ts=null\napk_package_name=null\nscore=null\naction=null\n"
        }
    ]
}
```

---

### Feature 3: Outbound Request Payload Formatting

**As a developer, I want verification request data to be formatted consistently**, so I can send the exact field set expected by the verification endpoint.

**Expected Behavior / Usage:**

The input provides a [a set of hardcoded protocol identifiers defined in config.yaml], a user [a set of hardcoded protocol identifiers defined in config.yaml] token, and optional remote IP and client-[a set of hardcoded protocol identifiers defined in config.yaml] values. The output first renders the field object that would be submitted and then renders the form-encoded query string. Null optional values are omitted from both the field object and query string.

**Test Cases:** `rcb_tests/public_test_cases/feature3_request_payload_formatting.json`

```json
{
    "description": "Build the outbound verification payload fields and form-encoded query string.",
    "cases": [
        {
            "input": {
                "operation": "build_request",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "SECRET",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "RESPONSE",
                "remote_ip": "REMOTEIP",
                "client_[a set of hardcoded protocol identifiers defined in config.yaml]": "VERSION"
            },
            "expected_output": "fields={\"[a set of hardcoded protocol identifiers defined in config.yaml]\":\"SECRET\",\"[a set of hardcoded protocol identifiers defined in config.yaml]\":\"RESPONSE\",\"[a set of hardcoded protocol identifiers defined in config.yaml]\":\"REMOTEIP\",\"[a set of hardcoded protocol identifiers defined in config.yaml]\":\"VERSION\"}\nquery=[a set of hardcoded protocol identifiers defined in config.yaml]=SECRET&[a set of hardcoded protocol identifiers defined in config.yaml]=RESPONSE&[a set of hardcoded protocol identifiers defined in config.yaml]=REMOTEIP&[a set of hardcoded protocol identifiers defined in config.yaml]=VERSION\n"
        }
    ]
}
```

---

### Feature 4: Token Verification and Local Validation

**As a developer**, I want token verification and optional local checks to run as one workflow, so I can enforce both service results and application-specific acceptance rules.

**Expected Behavior / Usage:**

*4.1 Token Verification Basics — Verify a token and handle missing user [a set of hardcoded protocol identifiers defined in config.yaml] input*

The input supplies a shared [a set of hardcoded protocol identifiers defined in config.yaml], a user [a set of hardcoded protocol identifiers defined in config.yaml] token, and, when the token is non-empty, a mocked service reply. A missing token returns success=false with missing-input-[a set of hardcoded protocol identifiers defined in config.yaml] and no service metadata. A non-empty token returns the parsed service outcome.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_token_verification_basics.json`

```json
{
    "description": "Verify a user [a set of hardcoded protocol identifiers defined in config.yaml] token and return either the service outcome or a missing-token error without contacting the service.",
    "cases": [
        {
            "input": {
                "operation": "verify_token",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "user_[a set of hardcoded protocol identifiers defined in config.yaml]_token": ""
            },
            "expected_output": "success=false\nerror_codes=[\"missing-input-[a set of hardcoded protocol identifiers defined in config.yaml]\"]\nhostname=null\nchallenge_ts=null\napk_package_name=null\nscore=null\naction=null\n"
        },
        {
            "input": {
                "operation": "verify_token",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "user_[a set of hardcoded protocol identifiers defined in config.yaml]_token": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "service_[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "success": true
                }
            },
            "expected_output": "success=true\nerror_codes=[]\nhostname=null\nchallenge_ts=null\napk_package_name=null\nscore=null\naction=null\n"
        }
    ]
}
```

*4.2 Additional Verification Checks — Apply caller-specified constraints to the parsed service reply.*

The input may include an expected hostname, expected mobile application package name, expected action, or minimum score threshold. The service reply is parsed first; then each configured constraint is compared case-insensitively for string fields and numerically for score. Mismatches append domain error codes while preserving any original service error codes.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_additional_verification_checks.json`

```json
{
    "description": "Apply optional hostname, mobile application package, action, and score constraints after the service reply is parsed.",
    "cases": [
        {
            "input": {
                "operation": "verify_token",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "user_[a set of hardcoded protocol identifiers defined in config.yaml]_token": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "expected_hostname": "host.name",
                "service_[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "success": true,
                    "hostname": "host.NOTname"
                }
            },
            "expected_output": "success=false\nerror_codes=[\"hostname-mismatch\"]\nhostname=host.NOTname\nchallenge_ts=null\napk_package_name=null\nscore=null\naction=null\n"
        },
        {
            "input": {
                "operation": "verify_token",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "user_[a set of hardcoded protocol identifiers defined in config.yaml]_token": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "expected_apk_package_name": "apk.name",
                "service_[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "success": true,
                    "apk_package_name": "apk.NOTname"
                }
            },
            "expected_output": "success=false\nerror_codes=[\"apk_package_name-mismatch\"]\nhostname=null\nchallenge_ts=null\napk_package_name=apk.NOTname\nscore=null\naction=null\n"
        },
        {
            "input": {
                "operation": "verify_token",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "user_[a set of hardcoded protocol identifiers defined in config.yaml]_token": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "expected_action": "action/name",
                "service_[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "success": true,
                    "action": "action/NOTname"
                }
            },
            "expected_output": "success=false\nerror_codes=[\"action-mismatch\"]\nhostname=null\nchallenge_ts=null\napk_package_name=null\nscore=null\naction=action/NOTname\n"
        },
        {
            "input": {
                "operation": "verify_token",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "user_[a set of hardcoded protocol identifiers defined in config.yaml]_token": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "score_threshold": "0.5",
                "service_[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "success": true,
                    "score": "0.1"
                }
            },
            "expected_output": "success=false\nerror_codes=[\"score-threshold-not-met\"]\nhostname=null\nchallenge_ts=null\napk_package_name=null\nscore=0.1\naction=null\n"
        },
        {
            "input": {
                "operation": "verify_token",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "user_[a set of hardcoded protocol identifiers defined in config.yaml]_token": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "score_threshold": "0.5",
                "service_[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "success": false,
                    "error-codes": [
                        "initial-error"
                    ],
                    "score": "0.1"
                }
            },
            "expected_output": "success=false\nerror_codes=[\"initial-error\",\"score-threshold-not-met\"]\nhostname=null\nchallenge_ts=null\napk_package_name=null\nscore=0.1\naction=null\n"
        }
    ]
}
```

*4.3 Challenge Timeout Check — Reject stale challenge timestamps.*

The input includes a maximum challenge age in seconds and a service reply containing a challenge timestamp. If the timestamp is older than the configured timeout at execution time, the output reports success=false and includes challenge-timeout while preserving the timestamp field.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_challenge_timeout_check.json`

```json
{
    "description": "Reject a successful service reply when the challenge timestamp is older than the configured timeout.",
    "cases": [
        {
            "input": {
                "operation": "verify_token",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "user_[a set of hardcoded protocol identifiers defined in config.yaml]_token": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "challenge_timeout_seconds": "60",
                "service_[a set of hardcoded protocol identifiers defined in config.yaml]": {
                    "success": true,
                    "challenge_ts": "2018-Jul-31T13:48:41Z"
                }
            },
            "expected_output": "success=false\nerror_codes=[\"challenge-timeout\"]\nhostname=null\nchallenge_ts=2018-Jul-31T13:48:41Z\napk_package_name=null\nscore=null\naction=null\n"
        }
    ]
}
```

---

### Feature 5: Verification Request Transports

**As a developer**, I want interchangeable verification request transports, so I can submit the same form-encoded request in environments with different network capabilities.

**Expected Behavior / Usage:**

*5.1 HTTP Form Transport — Send form-encoded verification data through an HTTP-style transport*

The input describes form data, an optional verification URL override, and a raw transport result. When the transport returns a [a set of hardcoded protocol identifiers defined in config.yaml] body, the output is that raw body. When the transport reports connection failure, the output is the standardized JSON error body with connection-failed. Cases that include a transport signal also render the verification URL used by the transport.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_http_form_transport.json`

```json
{
    "description": "Submit form-encoded verification data through an HTTP form transport and surface the raw service body or connection error body.",
    "cases": [
        {
            "input": {
                "operation": "http_post_transport",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "raw_reply": false
            },
            "expected_output": "raw_reply={\"success\": false, \"error-codes\": [\"connection-failed\"]}\n"
        },
        {
            "input": {
                "operation": "http_post_transport",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "verify_url": "OVERRIDE",
                "raw_reply": "RESPONSEBODY",
                "include_transport_signal": true
            },
            "expected_output": "verify_url=OVERRIDE\nraw_reply=RESPONSEBODY\n"
        }
    ]
}
```

*5.2 Socket Form Transport — Send form-encoded verification data through a direct TLS socket transport.*

The input describes form data, an optional HTTPS verification URL, and a simulated HTTP wire reply or connection failure. The transport opens a TLS connection to the URL host on port 443, writes a POST request to the URL path, and returns the body for HTTP/1.1 200 OK replies. Non-200 replies return the standardized JSON error body with bad-[a set of hardcoded protocol identifiers defined in config.yaml], and connection failures return connection-failed. Cases that include transport signals render the connection target, request line, and Host header.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_socket_form_transport.json`

```json
{
    "description": "Submit form-encoded verification data over a direct TLS socket and parse the HTTP [a set of hardcoded protocol identifiers defined in config.yaml] body or synthesize transport error bodies.",
    "cases": [
        {
            "input": {
                "operation": "socket_post_transport",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "remote_ip": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "client_[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "verify_url": "https://over.ride/some/path",
                "wire_reply": "HTTP/1.1 200 OK\n\nRESPONSEBODY",
                "include_transport_signal": true
            },
            "expected_output": "connection={\"host\":\"ssl://over.ride\",\"port\":443,\"timeout\":30}\nrequest_line=POST /some/path HTTP/1.1\nhost_header=Host: over.ride\nraw_reply=RESPONSEBODY\n"
        },
        {
            "input": {
                "operation": "socket_post_transport",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "remote_ip": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "client_[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "wire_reply": "HTTP/1.1 500 NOPEn\\nBOBBINS"
            },
            "expected_output": "raw_reply={\"success\": false, \"error-codes\": [\"bad-[a set of hardcoded protocol identifiers defined in config.yaml]\"]}\n"
        },
        {
            "input": {
                "operation": "socket_post_transport",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "remote_ip": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "client_[a set of hardcoded protocol identifiers defined in config.yaml]": "[a set of hardcoded protocol identifiers defined in config.yaml]",
                "wire_reply": false
            },
            "expected_output": "raw_reply={\"success\": false, \"error-codes\": [\"connection-failed\"]}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the compact JSON serialization pattern used in headers
- apply the standard verbatim newline rule
