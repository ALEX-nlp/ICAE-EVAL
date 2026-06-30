## Product Requirement Document

# Push Service Utility Contracts - Observable Formatting and Change Tracking

## Project Goal

Build a push-service utility layer that allows developers to normalize client metadata, format service base URLs, and compute broadcast update deltas without duplicating protocol-sensitive glue code.

---

## Background & Problem

Without this library/tool, developers are forced to hand-code repeated parsing, URL formatting, and subscription delta logic around push-service requests and connection state. This leads to inconsistent metrics labels, malformed service URLs, unnecessary broadcast traffic, and hard-to-maintain edge-case handling.

With this library/tool, common externally observable behaviors are centralized behind a small execution adapter that accepts JSON inputs and prints stable line-oriented results for black-box verification.

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

### Feature 1: User-Agent Classification

**As a developer**, I want to classify incoming user-agent strings into normalized browser and operating-system fields, so I can emit stable metrics labels without storing high-cardinality raw strings.

**Expected Behavior / Usage:**

The adapter accepts an object with `operation` set to `classify_user_agent` and a `user_agent` string. It prints four newline-delimited fields: `metrics_os`, `os`, `metrics_browser`, and `browser_name`. Recognized Linux, Windows, and Mac OS X clients preserve their normalized operating-system identity for metrics; unrecognized or unsupported clients use `Other` for metric labels while still reporting the parsed operating-system and browser-name fields when available. The output is deterministic text intended for direct comparison.

**Test Cases:** `rcb_tests/public_test_cases/feature1_user_agent_classification.json`

```json
{
    "description": "Classify representative user-agent strings into normalized operating-system and browser fields for metrics output.",
    "cases": [
        {
            "input": {
                "operation": "classify_user_agent",
                "user_agent": "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.2) Gecko/20090807 Mandriva Linux/1.9.1.2-1.1mud2009.1 (2009.1) Firefox/3.5.2 FirePHP/0.3,gzip(gfe),gzip(gfe)"
            },
            "expected_output": "metrics_os=Linux\nos=Linux\nmetrics_browser=Firefox\nbrowser_name=Firefox\n"
        }
    ]
}
```

---

### Feature 2: Connection URL Formatting

**As a developer**, I want to derive externally visible router and endpoint base URLs from host, scheme, and port settings, so I can publish canonical service locations without redundant default ports.

**Expected Behavior / Usage:**

The adapter accepts an object with `operation` set to `build_connection_urls`, router host and port fields, and endpoint scheme, host, and port fields. It prints `router_url` and `endpoint_url` on separate lines. Router URLs use the HTTP scheme. Port 80 is omitted for HTTP URLs, port 443 is omitted for HTTPS endpoint URLs, and all non-default ports are appended with `:<port>`. The endpoint scheme controls only the endpoint URL.

**Test Cases:** `rcb_tests/public_test_cases/feature2_connection_url_formatting.json`

```json
{
    "description": "Format externally visible router and endpoint base URLs from host, scheme, and port settings while omitting default ports.",
    "cases": [
        {
            "input": {
                "operation": "build_connection_urls",
                "router_hostname": "testname",
                "router_port": 80,
                "endpoint_scheme": "http",
                "endpoint_hostname": "testname",
                "endpoint_port": 80
            },
            "expected_output": "router_url=http://testname\nendpoint_url=http://testname\n"
        }
    ]
}
```

---

### Feature 3: Broadcast Change Tracking

**As a developer**, I want to compare a client's subscribed broadcast versions against server-side broadcast revisions, so I can send only the updates that the client needs.

**Expected Behavior / Usage:**

The adapter accepts an object with `operation` set to `track_broadcast_changes`, an `initial` server broadcast list, a `client` subscription/version list, and ordered `actions`. It first prints `initial_delta`, which is `none` when the client already has the server versions for all subscribed broadcasts. For each action, it prints `action_<index>_delta`. Updating an existing subscribed broadcast yields that broadcast identifier and its latest version as `[a specific format string — see the broadcast_delta formatter module]`. Adding a new broadcast does not produce a delta for a client that has not subscribed to it. Subscribing to an existing new broadcast with an outdated version yields the latest server version. Multiple changed broadcasts, when present, are comma-separated in the printed value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_broadcast_change_tracking.json`

```json
{
    "description": "Report only subscribed broadcast identifiers whose server-side versions changed after client initialization, and include new broadcasts only after subscription.",
    "cases": [
        {
            "input": {
                "operation": "track_broadcast_changes",
                "initial": [
                    {
                        "id": "bcasta",
                        "version": "rev1"
                    },
                    {
                        "id": "bcastb",
                        "version": "revalha"
                    }
                ],
                "client": [
                    {
                        "id": "bcasta",
                        "version": "rev1"
                    },
                    {
                        "id": "bcastb",
                        "version": "revalha"
                    }
                ],
                "actions": [
                    {
                        "type": "update",
                        "id": "bcasta",
                        "version": "rev2"
                    }
                ]
            },
            "expected_output": "[a specific output string generated by the test runner for this scenario]\n[a specific output string generated by the test runner for this scenario]\n"
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
- use the same scheme enforcement logic as the url_sanitizer module
- return the 'null' representation for matching lists
