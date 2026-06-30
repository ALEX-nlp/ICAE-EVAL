## Product Requirement Document

# Consumer Contract Testing Toolkit - Contract Definition and Verification Adapter

## Project Goal

Build a consumer-driven contract testing toolkit that allows developers to describe expected HTTP interactions between a client and a provider, exercise those expectations through a mock service, and verify generated contracts against a provider without hand-writing the mock-service wire format or verifier process invocations.

---

## Background & Problem

Without this library/tool, developers are forced to manually assemble nested JSON contract payloads, manage mock-service lifecycle commands, call mock-service HTTP endpoints, and translate command-line verification options into the external verifier process. This leads to repetitive boilerplate, inconsistent payloads, brittle setup code, and difficult-to-diagnose verification failures.

With this library/tool, developers describe consumers, providers, flexible body expectations, HTTP request/response contracts, mock-service setup, and verification intent using a compact API; the library produces the correct wire payloads, service calls, process arguments, and normalized failure signals.

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

### Feature 1: Flexible Matcher Wire Rendering

**As a developer**, I want to express flexible JSON expectations such as arrays of similar items, values constrained by type, and values constrained by a regular expression, so I can generate the mock-service wire contract without manually building nested matcher objects.

**Expected Behavior / Usage:**

The input is a JSON object describing one flexible expectation. An array-similarity expectation includes `expectation: "array_items_similar"`, a representative `value`, and optionally a `minimum` item count. A same-type expectation includes `expectation: "same_type"` and a representative `value`. A regular-expression expectation includes `expectation: "regex_match"`, a `regex`, and an `example` value to generate. The output is a single line beginning with `json=` followed by compact sorted JSON in the mock-service wire format. Minimum array counts below one are reported as `error=minimum_too_small`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_matcher_wire.json`

```json
{
    "description": "Render flexible JSON value expectations into the wire-format contract used by the mock server.",
    "cases": [
        {
            "input": {
                "expectation": "array_items_similar",
                "value": 1
            },
            "expected_output": "json={\"contents\":1,\"json_class\":\"Pact::ArrayLike\",\"min\":1}\n"
        }
    ]
}
```

---

### Feature 2: Contract Value Conversion

**As a developer**, I want ordinary JSON values and nested flexible expectations to be converted into a contract-ready JSON representation, so I can embed simple and flexible values uniformly in request and response definitions.

**Expected Behavior / Usage:**

The input is an object with a `value` field containing null, a string, a number, an array, an object, or a nested flexible expectation descriptor. Plain JSON-compatible values are preserved. Objects and arrays are recursively converted so any nested flexible expectation becomes its wire-format JSON object. The output is `json=` followed by compact sorted JSON; unsupported values are reported as `error=unsupported_value`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_convert_value.json`

```json
{
    "description": "Convert ordinary JSON-compatible values and nested flexible expectations into the JSON representation sent to the mock server.",
    "cases": [
        {
            "input": {
                "value": {
                    "administrator": false,
                    "id": 123,
                    "username": "user"
                }
            },
            "expected_output": "json={\"administrator\":false,\"id\":123,\"username\":\"user\"}\n"
        }
    ]
}
```

---

### Feature 3: HTTP Message Contract Fragments

**As a developer**, I want request and response message descriptions to be serialized into compact JSON fragments, so I can send exact interaction definitions to a mock server.

**Expected Behavior / Usage:**

The input contains `message` set to `request` or `response`. Request inputs require `method` and `path`, and may include `body`, `headers`, or `query`; response inputs require `status`, and may include `body` or `headers`. Optional fields are omitted when absent or empty. Values inside optional fields are converted using the same flexible expectation rules as contract value conversion. The output is `json=` followed by compact sorted JSON for the message fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature3_http_message.json`

```json
{
    "description": "Build JSON contract fragments for expected HTTP requests and responses, omitting absent optional fields.",
    "cases": [
        {
            "input": {
                "message": "request",
                "method": "GET",
                "path": "/path"
            },
            "expected_output": "json={\"method\":\"GET\",\"path\":\"/path\"}\n"
        }
    ]
}
```

---

### Feature 4: Complete Interaction Definition

**As a developer**, I want to combine a consumer name, provider name, provider state, request, response, endpoint options, and contract version into one interaction definition, so I can inspect the full contract that will be registered with the mock service.

**Expected Behavior / Usage:**

The input includes `consumer`, `provider`, `state`, `description_text`, a `request` object, and a `response` object. It may also include endpoint and storage options such as host, port, HTTPS mode, log directory, contract directory, cross-origin support, and contract specification version. Defaults use HTTP on localhost port 1234, disabled cross-origin support, and version `2.0.0`. The output is a single `json=` line containing the endpoint URL, names, request JSON, response JSON, state, description, directories, cross-origin flag, and version.

**Test Cases:** `rcb_tests/public_test_cases/feature4_interaction_definition.json`

```json
{
    "description": "Define a complete consumer-provider HTTP interaction and expose the resulting endpoint and contract JSON.",
    "cases": [
        {
            "input": {
                "consumer": "TestConsumer",
                "provider": "TestProvider",
                "state": "I am creating a new contract",
                "description_text": "a specific request to the server",
                "request": {
                    "method": "GET",
                    "path": "/path"
                },
                "response": {
                    "status": 200,
                    "body": "success"
                }
            },
            "expected_output": "json={\"consumer\":\"TestConsumer\",\"cors\":false,\"description\":\"a specific request to the server\",\"endpoint\":\"http://localhost:1234\",\"log_dir\":\"/testbed\",\"pact_dir\":\"/testbed\",\"provider\":\"TestProvider\",\"request\":{\"method\":\"GET\",\"path\":\"/path\"},\"response\":{\"body\":\"success\",\"status\":200},\"state\":\"I am creating a new contract\",\"version\":\"2.0.0\"}\n"
        }
    ]
}
```

---

### Feature 5: Consumer-to-Provider Relationship Creation

**As a developer**, I want to create a contract relationship between a named consumer and a named provider with default or custom connection settings, so I can reuse the resulting endpoint and metadata when defining interactions.

**Expected Behavior / Usage:**

The input includes a `consumer` name and a valid `provider` name, plus optional host, port, HTTPS, certificate path, key path, cross-origin, log directory, contract directory, and version settings. The output is `json=` followed by the relationship metadata: consumer, provider, endpoint URL, effective directories, SSL flag, cross-origin flag, and version. If the provider entry is invalid or omitted where required, output is normalized as `error=invalid_provider`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_relationship.json`

```json
{
    "description": "Create a contract relationship from a named consumer to a named provider, using defaults or caller-supplied connection options.",
    "cases": [
        {
            "input": {
                "consumer": "TestConsumer",
                "provider": "TestProvider"
            },
            "expected_output": "json={\"consumer\":\"TestConsumer\",\"cors\":false,\"endpoint\":\"http://localhost:1234\",\"log_dir\":\"/testbed\",\"pact_dir\":\"/testbed\",\"provider\":\"TestProvider\",\"ssl\":false,\"version\":\"2.0.0\"}\n"
        }
    ]
}
```

---

### Feature 6: Mock Server Process Commands

**As a developer**, I want mock-server start and stop operations to produce the exact external process arguments and normalized process-failure output, so I can manage the service lifecycle predictably.

**Expected Behavior / Usage:**

The input includes `operation` set to `start_mock_server` or `stop_mock_server`. Starting accepts consumer, provider, host, port, log directory, contract directory, version, and optional HTTPS certificate/key settings. Stopping uses the configured port. On success, output contains `[a completion status indicator]` and a `command=` JSON array excluding the platform-dependent executable path but preserving every semantic argument. If the spawned process reports failure, output contains `error=process_failed`, the operation name, and the same command array.

**Test Cases:** `rcb_tests/public_test_cases/feature6_service_process.json`

```json
{
    "description": "Render the external mock server process command for start and stop operations, including SSL options, and normalize process failures.",
    "cases": [
        {
            "input": {
                "operation": "start_mock_server",
                "consumer": "consumer",
                "provider": "provider",
                "log_dir": "/logs",
                "pact_dir": "/pacts"
            },
            "expected_output": "[a completion status indicator]\ncommand=[\"start\",\"--host=localhost\",\"--port=1234\",\"--log\",\"/logs/[the default executable name for the platform].log\",\"--pact-dir\",\"/pacts\",\"--pact-specification-version=2.0.0\",\"--consumer\",\"consumer\",\"--provider\",\"provider\"]\n"
        }
    ]
}
```

---

### Feature 7: Mock Service HTTP API Calls

**As a developer**, I want interaction registration and verification to call the mock service HTTP API with observable method, URL, headers, and payload details, so I can distinguish correct framework integration from a stubbed result.

**Expected Behavior / Usage:**

For `register_interaction`, the input includes state, description, request, response, and simulated HTTP status/content sequence. The operation first sends a DELETE request to `/interactions`, then sends a POST request to `/interactions` with a JSON body containing description, provider state, request, and response. For `verify_interactions`, the operation sends a GET request to `/interactions/verification`, then a POST request to `/pact` with consumer, provider, and contract directory. Success outputs `api=completed` and a `calls=` JSON array containing the observed HTTP methods, URLs, headers, and payloads. Non-200 responses output `error=remote_interaction_failed`, a detail line from the mock-service response content when available, the operation, and the observed calls.

**Test Cases:** `rcb_tests/public_test_cases/feature7_mock_service_api.json`

```json
{
    "description": "Register interactions with and verify interactions against the mock service HTTP API, reporting request method, URL, headers, payload, status, and normalized failure details.",
    "cases": [
        {
            "input": {
                "operation": "register_interaction",
                "state": "I am creating a new contract",
                "description_text": "a specific request to the server",
                "request": {
                    "method": "GET",
                    "path": "/path"
                },
                "response": {
                    "status": 200,
                    "body": "success"
                },
                "statuses": [
                    200,
                    200
                ]
            },
            "expected_output": "api=completed\ncalls=[{\"headers\":{\"X-Pact-Mock-Service\":\"true\"},\"method\":\"DELETE\",\"url\":\"http://localhost:1234/interactions\"},{\"headers\":{\"X-Pact-Mock-Service\":\"true\"},\"json\":{\"description\":\"a specific request to the server\",\"provider_state\":\"I am creating a new contract\",\"request\":{\"method\":\"GET\",\"path\":\"/path\"},\"response\":{\"body\":\"success\",\"status\":200}},\"method\":\"POST\",\"url\":\"http://localhost:1234/interactions\"}]\n"
        }
    ]
}
```

---

### Feature 8: Provider Verification Command Line

**As a developer**, I want command-line verification inputs to be validated and translated into an external verifier command with timeout behavior and exit-code propagation, so I can automate provider verification consistently.

**Expected Behavior / Usage:**

The input contains an `args` array matching the public command-line options for provider base URL, one or more contract URLs, provider-state URLs, broker credentials, and timeout. Missing required options produce `exit_code=2` and `error=missing_required_option` with the missing option. Local contract paths that do not exist produce `exit_code=1` and `error=missing_contract_file`. Supplying only one provider-state URL produces `exit_code=1` and `error=incomplete_provider_state_configuration`. Valid inputs output the verifier exit code, the external command arguments excluding the executable path, and the timeout used for the process. If a broker password is supplied through the expected environment variable, it is included in the rendered command.

**Test Cases:** `rcb_tests/public_test_cases/feature8_verifier_cli.json`

```json
{
    "description": "Validate provider verification command-line inputs and render the external verifier command, timeout, and exit code.",
    "cases": [
        {
            "input": {
                "args": []
            },
            "expected_output": "exit_code=2\nerror=missing_required_option\noption=--provider-base-url\n"
        }
    ]
}
```

---

### Feature 9: Contract Location Existence Check

**As a developer**, I want contract locations to be classified as available when they are HTTP(S) URLs and otherwise checked as local files, so verification can reject missing local contracts before starting the external verifier.

**Expected Behavior / Usage:**

The input includes a `path`. Paths beginning with `http://` or `https://` are always considered existing. Other paths are checked against local file existence supplied by the adapter environment. The output is exactly `exists=true` or `exists=false` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature9_path_check.json`

```json
{
    "description": "Classify contract locations as existing when they are HTTP(S) URLs, and otherwise according to local file existence.",
    "cases": [
        {
            "input": {
                "path": "http://localhost"
            },
            "expected_output": "exists=true\n"
        }
    ]
}
```

---

### Feature 10: Platform-Specific Executable Names

**As a developer**, I want platform-specific executable names for the bundled mock-server and provider-verifier tools, so process invocations select the correct binary name on POSIX and Windows-style platforms.

**Expected Behavior / Usage:**

The input includes `tool` set to `mock_server` or `provider_verifier`, and `platform` set to a platform family. POSIX-style platforms use extensionless executable names. Windows-style platforms append `.bat`. The output is one line, `executable=<name>`, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature10_platform_binary.json`

```json
{
    "description": "Choose platform-specific executable names for the mock server and provider verifier tools.",
    "cases": [
        {
            "input": {
                "tool": "mock_server",
                "platform": "posix"
            },
            "expected_output": "executable=[the default executable name for the platform]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. The full hidden evaluation subset lives under `rcb_tests/test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_matcher_wire.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_matcher_wire@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the shipment logic branch for the aggregation type
- look at the last item in the shipment array list
