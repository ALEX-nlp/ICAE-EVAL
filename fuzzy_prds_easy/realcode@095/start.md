## Product Requirement Document

# Serverless Web Gateway Adapter - Normalize Cloud Events into Web Application Execution

## Project Goal

Build a serverless web gateway adapter that allows developers to run a conventional web application behind managed gateway, load balancer, event bus, queue, configuration, and deployment workflows without rewriting request handling, response formatting, background job execution, or operational setup for each cloud event shape.

---

## Background & Problem

Without this library/tool, developers are forced to hand-map every gateway event into web-server environment fields, manually preserve cookies and binary bodies, special-case background events, write ad hoc maintenance command dispatchers, and maintain repetitive deployment scaffolding. This leads to duplicated glue code, incorrect HTTP semantics, brittle binary handling, inconsistent error behavior, and deployment scripts that drift across projects.

With this library/tool, cloud events are translated into application requests and operational actions through a small adapter surface, and the observable output remains a stable black-box contract across gateway versions and event types.

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

### Feature 1: Gateway Request Handling

**As a developer**, I want cloud HTTP and load balancer events to execute the web application through the normal request pipeline, so I can preserve HTTP behavior without writing per-gateway adapters.

**Expected Behavior / Usage:**

Gateway request handling accepts JSON inputs with an action, gateway kind, and scenario. It prints only stable response signals that an external client or gateway can observe: status, selected headers, cookie placement, binary encoding, content fingerprints, redirect location, error page indicators, and authenticated follow-up state.

*1.1 HTTP API Payload v2 Requests — HTTP API payload version 2 events must be converted into real web requests. The adapter receives a gateway kind and scenario, invokes the application through the gateway path, and prints response signals: status, selected headers, cookie placement, binary encoding, stable body content checks, redirect targets, error-page indicators, and login follow-up state. HEAD responses must keep the successful status while producing no page body signal. Binary image responses must be base64-marked and identified by a stable decoded SHA-256 digest.*

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_http_api_v2_requests.json`

```json
{
    "description": "HTTP API payload version 2 events are translated into web requests and returned as gateway-compatible response fields for normal pages, HEAD requests, multiple cookies, binary image bodies, public static files, redirects, application errors, and login session follow-up.",
    "cases": [
        {
            "input": {
                "action": "gateway_request",
                "gateway": "http_v2",
                "scenario": "root"
            },
            "expected_output": "status=200\ncontent_type=text/html; charset=utf-8\ncache_control=max-age=0, private, must-revalidate\nbody_has_hello=true\nlogged_in=false\nbody_has_error_page=false\nbody_has_public_500=false\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "http_v2",
                "scenario": "cookies"
            },
            "expected_output": "status=200\ncontent_type=text/html; charset=utf-8\ncache_control=max-age=0, private, must-revalidate\ncookies=1=1; path=/|2=2; path=/\nbody_has_hello=true\nlogged_in=false\nbody_has_error_page=false\nbody_has_public_500=false\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "http_v2",
                "scenario": "public_image"
            },
            "expected_output": "status=200\ncontent_type=image/png\ncache_control=public, max-age=2592000\nbase64_encoded=true\nbody_has_hello=false\nbody_has_error_page=false\nbody_has_public_500=false\n[proprietary checksum format]\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "http_v2",
                "scenario": "login"
            },
            "expected_output": "status=302\nlocation=https://myawesomelambda.example.com/\ncontent_type=text/html; charset=utf-8\ncache_control=no-cache\nsession_cookie_present=true\nbody_has_hello=false\nbody_has_error_page=false\nbody_has_public_500=false\nfollowup_status=200\nfollowup_logged_in=true\n"
        }
    ]
}
```

*1.2 HTTP API Payload v1 Requests — HTTP API payload version 1 events must produce the same web behavior while using the version-1 response shape for repeated cookies. The adapter receives a gateway kind and scenario, invokes the application through the gateway path, and prints response signals for normal pages, HEAD requests, repeated cookies, binary images, static files, redirects, error pages, and login follow-up state.*

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_http_api_v1_requests.json`

```json
{
    "description": "HTTP API payload version 1 events are translated into web requests and returned as gateway-compatible response fields for normal pages, HEAD requests, multiple cookies, binary image bodies, public static files, redirects, application errors, and login session follow-up.",
    "cases": [
        {
            "input": {
                "action": "gateway_request",
                "gateway": "http_v1",
                "scenario": "root"
            },
            "expected_output": "status=200\ncontent_type=text/html; charset=utf-8\ncache_control=max-age=0, private, must-revalidate\nbody_has_hello=true\nlogged_in=false\nbody_has_error_page=false\nbody_has_public_500=false\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "http_v1",
                "scenario": "cookies"
            },
            "expected_output": "status=200\ncontent_type=text/html; charset=utf-8\ncache_control=max-age=0, private, must-revalidate\nset_cookie_multi=1=1; path=/|2=2; path=/\nbody_has_hello=true\nlogged_in=false\nbody_has_error_page=false\nbody_has_public_500=false\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "http_v1",
                "scenario": "login"
            },
            "expected_output": "status=302\nlocation=https://myawesomelambda.example.com/\ncontent_type=text/html; charset=utf-8\ncache_control=no-cache\nsession_cookie_present=true\nbody_has_hello=false\nbody_has_error_page=false\nbody_has_public_500=false\nfollowup_status=200\nfollowup_logged_in=true\n"
        }
    ]
}
```

*1.3 REST API Proxy Requests — REST API proxy events must be converted into real web requests and returned using REST proxy response conventions. The adapter receives a gateway kind and scenario, invokes the application through the REST proxy path, and prints status, selected headers, repeated cookie placement, binary encoding, stable body checks, redirect target, error-page indicators, and login follow-up state.*

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_rest_api_requests.json`

```json
{
    "description": "REST API proxy events are translated into web requests and returned as gateway-compatible response fields for normal pages, HEAD requests, multiple cookies, binary image bodies, public static files, redirects, application errors, and login session follow-up.",
    "cases": [
        {
            "input": {
                "action": "gateway_request",
                "gateway": "rest",
                "scenario": "root"
            },
            "expected_output": "status=200\ncontent_type=text/html; charset=utf-8\ncache_control=max-age=0, private, must-revalidate\nbody_has_hello=true\nlogged_in=false\nbody_has_error_page=false\nbody_has_public_500=false\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "rest",
                "scenario": "redirect"
            },
            "expected_output": "status=301\nlocation=https://myawesomelambda.example.com/\ncontent_type=text/html\ncache_control=no-cache\nbody_has_hello=false\nbody_has_error_page=false\nbody_has_public_500=false\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "rest",
                "scenario": "exception"
            },
            "expected_output": "status=500\ncontent_type=text/html; charset=UTF-8\nbody_has_hello=false\nbody_has_error_page=true\nbody_has_public_500=true\n"
        }
    ]
}
```

*1.4 Load Balancer Requests — Load balancer events must be converted into real web requests and returned using load-balancer-compatible response signals. The adapter receives a gateway kind and scenario, invokes the application through the load balancer path, and prints status, selected headers, base64 status, stable body checks, static image digest, redirect target, repeated cookie placement, and application error-page indicators.*

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_load_balancer_requests.json`

```json
{
    "description": "Load balancer events are translated into web requests and returned as load-balancer-compatible response fields for normal pages, HEAD requests, multiple cookies, binary image bodies, public static files, redirects, and application errors.",
    "cases": [
        {
            "input": {
                "action": "gateway_request",
                "gateway": "alb",
                "scenario": "root"
            },
            "expected_output": "status=200\ncontent_type=text/html; charset=utf-8\ncache_control=max-age=0, private, must-revalidate\nbase64_encoded=false\nbody_has_hello=true\nlogged_in=false\nbody_has_error_page=false\nbody_has_public_500=false\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "alb",
                "scenario": "image"
            },
            "expected_output": "status=200\ncontent_type=image/png\ncache_control=private\nbase64_encoded=true\nbody_has_hello=false\nbody_has_error_page=false\nbody_has_public_500=false\n[proprietary checksum format]\n"
        },
        {
            "input": {
                "action": "gateway_request",
                "gateway": "alb",
                "scenario": "exception"
            },
            "expected_output": "status=500\ncontent_type=text/html; charset=UTF-8\nbase64_encoded=false\nbody_has_hello=false\nbody_has_error_page=true\nbody_has_public_500=true\n"
        }
    ]
}
```

---

### Feature 2: Gateway Environment Mapping

**As a developer**, I want gateway events to become a conventional web-server environment, so I can run existing routing, header, cookie, and query-string logic without gateway-specific conditionals.

**Expected Behavior / Usage:**

Environment mapping accepts JSON inputs with an action and gateway kind. It prints deterministic request environment lines that describe the method, path, query string, server, protocol, scheme, request headers, request id, and cookies visible to the application.

*2.1 HTTP API Environment Mapping — HTTP API events must be converted into a web server environment. The adapter receives the gateway kind and prints the externally meaningful environment fields: request method, path, query string, server host and port, protocol, URL scheme, selected HTTP headers, request id, and cookie string. Stage prefixes in incoming paths are removed for application routing.*

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_http_api_environment.json`

```json
{
    "description": "HTTP API events are converted into a web server environment containing request method, script name, path, query string, server identity, scheme, request headers, request id, and cookies.",
    "cases": [
        {
            "input": {
                "action": "gateway_env",
                "gateway": "http_v2"
            },
            "expected_output": "REQUEST_METHOD=GET\nSCRIPT_NAME=\nPATH_INFO=/\nQUERY_STRING=colors[]=blue&colors[]=red\nSERVER_NAME=myawesomelambda.example.com\nSERVER_PORT=443\nSERVER_PROTOCOL=HTTP/1.1\nrack.url_scheme=https\nHTTP_ACCEPT=text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\nHTTP_ACCEPT_ENCODING=gzip, deflate, br\nHTTP_HOST=myawesomelambda.example.com\nHTTP_USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15\nHTTP_VIA=\nHTTP_X_AMZ_CF_ID=\nHTTP_X_AMZN_TRACE_ID=Root=1-5e7fe714-fee6909429159440eb352c40\nHTTP_X_FORWARDED_FOR=72.218.219.201\nHTTP_X_FORWARDED_PORT=443\nHTTP_X_FORWARDED_PROTO=https\nHTTP_X_REQUEST_ID=a59284fd-d48c-4de5-af9e-df4254489ac2\nHTTP_COOKIE=signal1=test; signal2=control\n"
        }
    ]
}
```

*2.2 REST API Environment Mapping — REST API proxy events must be converted into a web server environment. The adapter receives the gateway kind and prints method, path, query string, server identity, protocol, HTTPS scheme, CloudFront-related headers, request id, and cookies as seen by the application.*

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_rest_api_environment.json`

```json
{
    "description": "REST API events are converted into a web server environment containing request method, script name, path, query string, server identity, scheme, CloudFront headers, request id, and cookies.",
    "cases": [
        {
            "input": {
                "action": "gateway_env",
                "gateway": "rest"
            },
            "expected_output": "REQUEST_METHOD=GET\nSCRIPT_NAME=\nPATH_INFO=/\nQUERY_STRING=colors[]=blue&colors[]=red\nSERVER_NAME=4o8v9z4feh.execute-api.us-east-1.amazonaws.com\nSERVER_PORT=443\nSERVER_PROTOCOL=HTTP/1.1\nrack.url_scheme=https\nHTTP_ACCEPT=text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\nHTTP_ACCEPT_ENCODING=gzip\nHTTP_HOST=4o8v9z4feh.execute-api.us-east-1.amazonaws.com\nHTTP_USER_AGENT=Amazon CloudFront\nHTTP_VIA=2.0 7f7e359e1c06a914d3d305785359b84d.cloudfront.net (CloudFront)\nHTTP_X_AMZ_CF_ID=kXZzJ72NOsZSsPu-JzNUGyFei1G0r9uzoup3yHrwk4J5qGLKrdUrRA==\nHTTP_X_AMZN_TRACE_ID=Root=1-5e7fe714-fee6909429159440eb352c40\nHTTP_X_FORWARDED_FOR=72.218.219.201, 34.195.252.119\nHTTP_X_FORWARDED_PORT=443\nHTTP_X_FORWARDED_PROTO=https\nHTTP_X_REQUEST_ID=a59284fd-d48c-4de5-af9e-df4254489ac2\nHTTP_COOKIE=signal1=test; signal2=control\n"
        }
    ]
}
```

*2.3 Load Balancer Environment Mapping — Load balancer events with multi-value headers must be converted into a web server environment. The adapter receives the gateway kind and prints method, path, query string, server identity, protocol, HTTPS scheme, headers, request id, and cookies. Repeated forwarded-for values are joined into a comma-separated header value while other multi-value headers expose the first scalar value.*

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_load_balancer_environment.json`

```json
{
    "description": "Load balancer events with multi-value headers are converted into a web server environment, joining repeated forwarded-for values while preserving the first scalar values for other headers.",
    "cases": [
        {
            "input": {
                "action": "gateway_env",
                "gateway": "alb"
            },
            "expected_output": "REQUEST_METHOD=GET\nSCRIPT_NAME=\nPATH_INFO=/\nQUERY_STRING=colors[]=blue&colors[]=red\nSERVER_NAME=myawesomelambda.example.com\nSERVER_PORT=443\nSERVER_PROTOCOL=HTTP/1.1\nrack.url_scheme=https\nHTTP_ACCEPT=text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\nHTTP_ACCEPT_ENCODING=gzip\nHTTP_HOST=myawesomelambda.example.com\nHTTP_USER_AGENT=Amazon CloudFront\nHTTP_VIA=2.0 3dc5b7040885724e78019cc31f0ef3d9.cloudfront.net (CloudFront)\nHTTP_X_AMZ_CF_ID=BSlDkHoVD8-009TATJzymLqSBzViE_6jj7DlkiJkub-PpDb8wI4Pxw==\nHTTP_X_AMZN_TRACE_ID=Root=1-5e7c160a-0a9065c7a28a428cd8b98215\nHTTP_X_FORWARDED_FOR=72.218.219.201, 72.218.219.201, 34.195.252.132\nHTTP_X_FORWARDED_PORT=443\nHTTP_X_FORWARDED_PROTO=https\nHTTP_X_REQUEST_ID=a59284fd-d48c-4de5-af9e-df4254489ac2\nHTTP_COOKIE=signal1=test; signal2=control\n"
        }
    ]
}
```

---

### Feature 3: Debug Activation Gate

**As a developer**, I want this behavior exposed through a stable adapter contract, so I can rely on the externally observable result without depending on implementation details.

**Expected Behavior / Usage:**

Debug output must be enabled only when the application is in a development environment and the incoming request explicitly contains debug=1. The adapter receives environment settings and an optional debug query value, then prints whether debug mode is enabled.

**Test Cases:** `rcb_tests/public_test_cases/feature3_debug_gate.json`

```json
{
    "description": "Debug mode is enabled only when a development environment is active and the incoming query includes debug=1; missing the query flag disables debug output even in development.",
    "cases": [
        {
            "input": {
                "action": "debug_gate",
                "rack_env": "development",
                "app_env": null,
                "debug": "1"
            },
            "expected_output": "debug_enabled=true\n"
        },
        {
            "input": {
                "action": "debug_gate",
                "rack_env": "development",
                "app_env": null
            },
            "expected_output": "debug_enabled=false\n"
        }
    ]
}
```

---

### Feature 4: Parameter Exporting

**As a developer**, I want this behavior exposed through a stable adapter contract, so I can rely on the externally observable result without depending on implementation details.

**Expected Behavior / Usage:**

Named configuration parameters must be exportable either into process environment variables or into dotenv file lines. The adapter receives an export mode and prints the resulting key-value lines. Existing environment values are overwritten by default, preserved when overwrite is disabled, and dotenv output is rendered as NAME=value lines.

**Test Cases:** `rcb_tests/public_test_cases/feature4_parameter_store_exports.json`

```json
{
    "description": "Named parameter values can be exported to process environment variables with configurable overwrite behavior or rendered as dotenv file lines.",
    "cases": [
        {
            "input": {
                "action": "parameter_store",
                "mode": "env_overwrite"
            },
            "expected_output": "FOO=foo\nBAR=bar\n"
        },
        {
            "input": {
                "action": "parameter_store",
                "mode": "env_preserve"
            },
            "expected_output": "FOO=test\nBAR=bar\n"
        },
        {
            "input": {
                "action": "parameter_store",
                "mode": "dotenv"
            },
            "expected_output": "FOO=foo\nBAR=bar\n"
        }
    ]
}
```

---

### Feature 5: Maintenance Runner Commands

**As a developer**, I want this behavior exposed through a stable adapter contract, so I can rely on the externally observable result without depending on implementation details.

**Expected Behavior / Usage:**

Maintenance runner events must execute only allowed command patterns. For an allowed migration command, the adapter prints the command response status, whether headers are empty, whether the command output contains the unknown-task signal, and whether the response body contains the same signal. For a disallowed command, the adapter normalizes the failure into a language-neutral error category and prints the raw command separately.

**Test Cases:** `rcb_tests/public_test_cases/feature5_runner_commands.json`

```json
{
    "description": "Runner events execute allowed maintenance command patterns and expose their exit status, empty headers, stdout signal, and response body signal; disallowed commands are rejected with a normalized error category and the raw command.",
    "cases": [
        {
            "input": {
                "action": "runner",
                "command": "./bin/rake db:migrate"
            },
            "expected_output": "status=1\nheaders_empty=true\nstdout_has_unknown_task=true\nbody_has_unknown_task=true\n"
        },
        {
            "input": {
                "action": "runner",
                "command": "ls -lAGp"
            },
            "expected_output": "error=unknown_runner_command\ncommand=ls -lAGp\n"
        }
    ]
}
```

---

### Feature 6: Event Bus Messages

**As a developer**, I want this behavior exposed through a stable adapter contract, so I can rely on the externally observable result without depending on implementation details.

**Expected Behavior / Usage:**

Event bus messages containing a source, detail type, and detail payload must be sent to the configured event callback. The adapter receives the event-bus action and prints whether the emitted log contains the event identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_event_bus_events.json`

```json
{
    "description": "Non-HTTP event bus messages with source, detail type, and detail payload are handled by the configured event callback and emit a log containing the event identifier.",
    "cases": [
        {
            "input": {
                "action": "event_bridge"
            },
            "expected_output": "log_contains_event_id=true\n"
        }
    ]
}
```

---

### Feature 7: Queue Job Messages

**As a developer**, I want this behavior exposed through a stable adapter contract, so I can rely on the externally observable result without depending on implementation details.

**Expected Behavior / Usage:**

Queue job messages containing an active job payload must execute the queued work and report batch item failures. The adapter receives the queue-job action and prints whether the job work signal appeared on stdout and how many batch failures were returned.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_queue_job_events.json`

```json
{
    "description": "Queue job events containing an active job payload are executed, print the job work signal, and return an empty batch failure list.",
    "cases": [
        {
            "input": {
                "action": "queue_job"
            },
            "expected_output": "stdout_has_job=true\nbatch_failures=0\n"
        }
    ]
}
```

---

### Feature 8: Deployment Installers

**As a developer**, I want this behavior exposed through a stable adapter contract, so I can rely on the externally observable result without depending on implementation details.

**Expected Behavior / Usage:**

Deployment installer modes must generate the expected handler, infrastructure template, build script, and deployment scripts for HTTP and REST gateway deployments. The adapter receives an installer mode and prints whether the installer banner appeared and whether the generated files contain the required deployment signals.

**Test Cases:** `rcb_tests/public_test_cases/feature7_deployment_installers.json`

```json
{
    "description": "Installation tasks for both HTTP and REST gateway deployment modes create handler, infrastructure template, build script, and deployment scripts with the expected deployment signals.",
    "cases": [
        {
            "input": {
                "action": "installer",
                "mode": "http_gateway"
            },
            "expected_output": "installer_banner=true\nhandler_contains_bridge=true\ntemplate_has_transform=true\ntemplate_has_description=true\nbuild_script_exists=true\nbuild_script_installs_bundle=true\ndeploy_scripts_exist=true\ndeploy_packages_image=true\ndeploy_stack_uses_env=true\n"
        },
        {
            "input": {
                "action": "installer",
                "mode": "rest_gateway"
            },
            "expected_output": "installer_banner=true\nhandler_contains_bridge=true\ntemplate_has_transform=true\ntemplate_has_description=true\nbuild_script_exists=true\nbuild_script_installs_bundle=true\ndeploy_scripts_exist=true\ndeploy_packages_image=true\ndeploy_stack_uses_env=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_http_api_v2_requests.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_http_api_v2_requests@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- include a dynamic boilerplate string matching Amazon's latest error convention
