## Product Requirement Document

# Error Reporting Client - Browser and Server Diagnostic Report Contracts

## Project Goal

Build an error reporting client that allows developers to collect browser and server failure reports with structured request context, redaction, breadcrumbs, and framework integration without hand-writing serialization, filtering, transport, and error-hook plumbing.

---

## Background & Problem

Without this library/tool, developers are forced to manually capture thrown errors, normalize stack traces, redact sensitive request data, track contextual breadcrumbs, and wire browser, server, and middleware delivery paths. This leads to repetitive code, accidental data leaks, inconsistent payloads, and brittle integrations.

With this library/tool, applications can provide a small amount of configuration and notice data, and the client produces consistent report payloads, applies redaction and sanitization, preserves useful context, and integrates with browser and HTTP framework error surfaces.

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

### Feature 1: Filter URL Parameters

**As a developer**, I want to sanitize URL query strings before a report is sent, so I can avoid leaking configured sensitive query values.

**Expected Behavior / Usage:**

The input is an object containing a URL string and a list of filter terms. The output is a single `url=` line. Any query pair whose key contains a filter term is rewritten to `[FILTERED]`; non-matching parameters and malformed query text remain unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature1_filter_url_parameters.json`

```json
{
    "description": "Sensitive URL query parameters named by configured filters are replaced while other URL text is preserved.",
    "cases": [
        {
            "input": {
                "url": "https://www.example.com/?secret=value",
                "filters": [
                    "secret"
                ]
            },
            "expected_output": "url=https://www.example.com/?secret=[FILTERED]\n"
        }
    ]
}
```

---

### Feature 2: Filter Structured Data

**As a developer**, I want to redact sensitive keys inside structured request data, so I can send useful diagnostics without exposing secret values.

**Expected Behavior / Usage:**

The input is an object containing arbitrary structured data and filter terms. The output is `data=` followed by JSON. Object keys are matched case-insensitively and by substring; matching values are replaced with `[FILTERED]`, while non-matching nested data is preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature2_filter_structured_data.json`

```json
{
    "description": "Object keys that partially match configured filter names are redacted recursively and case-insensitively.",
    "cases": [
        {
            "input": {
                "data": {
                    "secret_key": "secret"
                },
                "filters": [
                    "secret"
                ]
            },
            "expected_output": "data={\"secret_key\":\"[FILTERED]\"}\n"
        }
    ]
}
```

---

### Feature 3: Sanitize Payload Values

**As a developer**, I want to make arbitrary report data safe to serialize, so I can prevent recursive or excessively deep values from breaking delivery.

**Expected Behavior / Usage:**

The input is a data value plus an optional maximum depth. The output is `data=` followed by JSON. Values deeper than the configured depth become `[DEPTH]`; recursive references and non-serializable values are represented by stable neutral marker strings; absent object fields are omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_sanitize_payload_values.json`

```json
{
    "description": "Payload data is sanitized by limiting nesting depth, dropping absent object fields, and replacing recursive or non-serializable values with neutral markers.",
    "cases": [
        {
            "input": {
                "data": {
                    "one": {
                        "two": {
                            "three": {
                                "four": "five"
                            }
                        }
                    }
                },
                "maxDepth": 3
            },
            "expected_output": "data={\"one\":{\"two\":{\"three\":\"[DEPTH]\"}}}\n"
        }
    ]
}
```

---

### Feature 4: Parse Stack Trace Text

**As a developer**, I want to turn stack trace text into structured frames, so I can display file, function, line, and column information consistently.

**Expected Behavior / Usage:**

The input is stack trace text. The output is `backtrace=` followed by an array of frame objects. Each parsed frame contains `file`, `method`, `number`, and `column`; missing or unparsable stack text yields an empty array.

**Test Cases:** `rcb_tests/public_test_cases/feature4_parse_stack_trace.json`

```json
{
    "description": "A textual stack trace is converted into structured frame data with file, function, line, and column fields.",
    "cases": [
        {
            "input": {
                "stack": "Error: Something unexpected has occurred.\n    at bar (foo.js:1:2)"
            },
            "expected_output": "backtrace=[{\"column\":2,\"file\":\"foo.js\",\"method\":\"bar\",\"number\":1}]\n"
        }
    ]
}
```

---

### Feature 5: Gate Notice Delivery

**As a developer**, I want to drop reports when reporting is not configured or disabled, so I can avoid unwanted network reporting in disabled or development modes.

**Expected Behavior / Usage:**

The input contains reporting configuration and a notice value. The output states whether delivery proceeds. Reports are dropped without a configured key, when reporting is disabled, or in a development environment unless explicit report-data override enables delivery.

**Test Cases:** `rcb_tests/public_test_cases/feature5_notice_delivery_gating.json`

```json
{
    "description": "Error notices are delivered only when reporting is configured and enabled for the current environment.",
    "cases": [
        {
            "input": {
                "config": {},
                "notice": "test"
            },
            "expected_output": "delivered=false\n"
        },
        {
            "input": {
                "config": {
                    "apiKey": "testing",
                    "environment": "development",
                    "reportData": true
                },
                "notice": "test"
            },
            "expected_output": "delivered=true\nclass=Error\nmessage=test\n"
        }
    ]
}
```

---

### Feature 6: Map Notices to Report Payloads

**As a developer**, I want to convert user-supplied notice data into a complete report payload, so I can preserve error identity, request data, context, metadata, and redaction behavior.

**Expected Behavior / Usage:**

The input contains reporting configuration, optional accumulated context, notice data, and optional mutation instructions representing a pre-send callback. The output is a fixed set of payload fields: error class and message, request URL and metadata, environment and revision, context, params, CGI-style data, session, and details. Configured filters apply to URLs and request data.

**Test Cases:** `rcb_tests/public_test_cases/feature6_notice_payload_mapping.json`

```json
{
    "description": "A notice is transformed into a report payload that preserves supplied error identity, request data, context, details, and configurable metadata.",
    "cases": [
        {
            "input": {
                "config": {
                    "apiKey": "testing"
                },
                "notice": {
                    "message": "expected message"
                }
            },
            "expected_output": "class=Error\nmessage=expected message\nurl=none\ncomponent=null\naction=null\nenvironment=null\nrevision=null\ncontext={}\nparams={}\ncgi_data={}\nsession={}\ndetails={}\n"
        },
        {
            "input": {
                "config": {
                    "apiKey": "testing",
                    "environment": "config environment",
                    "component": "config component",
                    "action": "config action",
                    "revision": "config revision",
                    "projectRoot": "config projectRoot",
                    "filters": [
                        "secret"
                    ]
                },
                "context": {
                    "foo": "foo"
                },
                "notice": {
                    "message": "expected message",
                    "context": {
                        "bar": "bar"
                    },
                    "url": "https://www.example.com/?secret=value&foo=bar",
                    "params": {
                        "secret": "secret",
                        "other": "expected"
                    },
                    "cgiData": {
                        "secret": "secret",
                        "other": "expected"
                    },
                    "session": {
                        "secret": "secret",
                        "other": "expected"
                    },
                    "headers": {
                        "secret": "secret",
                        "other": "expected"
                    }
                },
                "mutateNotice": {
                    "name": "mutated name",
                    "message": "mutated message",
                    "component": "mutated component",
                    "action": "mutated action",
                    "revision": "mutated revision"
                }
            },
            "expected_output": "class=mutated name\nmessage=mutated message\nurl=https://www.example.com/?secret=[FILTERED]&foo=bar\ncomponent=mutated component\naction=mutated action\nenvironment=config environment\nrevision=mutated revision\ncontext={\"bar\":\"bar\",\"foo\":\"foo\"}\nparams={\"other\":\"expected\",\"secret\":\"[FILTERED]\"}\ncgi_data={\"HTTP_OTHER\":\"expected\",\"HTTP_SECRET\":\"[FILTERED]\",\"other\":\"expected\",\"secret\":\"[FILTERED]\"}\nsession={\"other\":\"expected\",\"secret\":\"[FILTERED]\"}\ndetails={}\n"
        }
    ]
}
```

---

### Feature 7: Normalize Tags

**As a developer**, I want to combine tags from multiple sources into a clean ordered list, so I can group reports without duplicates or unsafe tag characters.

**Expected Behavior / Usage:**

The input may contain notice tags, context tags, and configured tags as strings or arrays. The output is `tags=` followed by JSON. Tags are split on commas, stripped to word characters, blank entries are removed, notice tags precede context tags which precede configured tags, and duplicates are omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature7_normalize_tags.json`

```json
{
    "description": "Tags from notice data, context, and configuration are split on commas, stripped to word characters, ordered by precedence, and de-duplicated.",
    "cases": [
        {
            "input": {
                "noticeTags": "  tag1, &%&@<$^tag2,tag3 , tag4,,tag5,"
            },
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]\"tag1\",\"tag2\",\"tag3\",\"tag4\",\"tag5\"]\n"
        },
        {
            "input": {
                "configTags": [
                    "tag4"
                ],
                "context": {
                    "tags": "tag3"
                },
                "noticeTags": [
                    "tag1, tag2"
                ]
            },
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]\"tag1\",\"tag2\",\"tag3\",\"tag4\"]\n"
        }
    ]
}
```

---

### Feature 8: Maintain Breadcrumb Trail

**As a developer**, I want to attach recent application events to a report, so I can understand what happened before an error.

**Expected Behavior / Usage:**

The input contains a sequence of breadcrumb events and reporting options. The output reports whether breadcrumbs are enabled, trail length, first breadcrumb fields, and the last breadcrumb message. Breadcrumbs default to the `custom` category, copy supplied metadata, include an automatic notice breadcrumb when enabled, keep only the most recent forty records, and produce an empty trail when disabled.

**Test Cases:** `rcb_tests/public_test_cases/feature8_breadcrumb_trail.json`

```json
{
    "description": "Breadcrumb records capture recent events with category and metadata, are included in notice payloads by default, and respect queue limits and disabling.",
    "cases": [
        {
            "input": {
                "breadcrumbs": [
                    {
                        "message": "expected message"
                    }
                ],
                "message": "message"
            },
            "expected_output": "enabled=true\ntrail_count=2\nfirst_message=expected message\nfirst_category=custom\nfirst_metadata={}\nlast_message=Honeybadger Notice\n"
        },
        {
            "input": {
                "breadcrumbs": [
                    {
                        "message": "expected message 0"
                    },
                    {
                        "message": "expected message 1"
                    },
                    {
                        "message": "expected message 2"
                    },
                    {
                        "message": "expected message 3"
                    },
                    {
                        "message": "expected message 4"
                    },
                    {
                        "message": "expected message 5"
                    },
                    {
                        "message": "expected message 6"
                    },
                    {
                        "message": "expected message 7"
                    },
                    {
                        "message": "expected message 8"
                    },
                    {
                        "message": "expected message 9"
                    },
                    {
                        "message": "expected message 10"
                    },
                    {
                        "message": "expected message 11"
                    },
                    {
                        "message": "expected message 12"
                    },
                    {
                        "message": "expected message 13"
                    },
                    {
                        "message": "expected message 14"
                    },
                    {
                        "message": "expected message 15"
                    },
                    {
                        "message": "expected message 16"
                    },
                    {
                        "message": "expected message 17"
                    },
                    {
                        "message": "expected message 18"
                    },
                    {
                        "message": "expected message 19"
                    },
                    {
                        "message": "expected message 20"
                    },
                    {
                        "message": "expected message 21"
                    },
                    {
                        "message": "expected message 22"
                    },
                    {
                        "message": "expected message 23"
                    },
                    {
                        "message": "expected message 24"
                    },
                    {
                        "message": "expected message 25"
                    },
                    {
                        "message": "expected message 26"
                    },
                    {
                        "message": "expected message 27"
                    },
                    {
                        "message": "expected message 28"
                    },
                    {
                        "message": "expected message 29"
                    },
                    {
                        "message": "expected message 30"
                    },
                    {
                        "message": "expected message 31"
                    },
                    {
                        "message": "expected message 32"
                    },
                    {
                        "message": "expected message 33"
                    },
                    {
                        "message": "expected message 34"
                    },
                    {
                        "message": "expected message 35"
                    },
                    {
                        "message": "expected message 36"
                    },
                    {
                        "message": "expected message 37"
                    },
                    {
                        "message": "expected message 38"
                    },
                    {
                        "message": "expected message 39"
                    },
                    {
                        "message": "expected message 40"
                    },
                    {
                        "message": "expected message 41"
                    },
                    {
                        "message": "expected message 42"
                    },
                    {
                        "message": "expected message 43"
                    },
                    {
                        "message": "expected message 44"
                    },
                    {
                        "message": "expected message 45"
                    }
                ],
                "message": "message"
            },
            "expected_output": "enabled=true\ntrail_count=40\nfirst_message=expected message 7\nfirst_category=custom\nfirst_metadata={}\nlast_message=Honeybadger Notice\n"
        }
    ]
}
```

---

### Feature 9: Describe Browser Elements

**As a developer**, I want to render browser elements as concise selector and text snippets, so I can record useful UI context in diagnostics.

**Expected Behavior / Usage:**

The input describes a browser element tree and optional target path. The output contains the element name fragment, full selector path, and text snippet. Names use lower-case tag names plus id, classes, allowed attributes, and sibling `nth-child` information. Selector paths include parent elements from the document body. Text content longer than 300 characters is truncated with `...`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_dom_element_descriptors.json`

```json
{
    "description": "Browser elements are rendered as concise selector fragments and text snippets using tag, id, class, allowed attributes, parent path, sibling index, and truncation rules.",
    "cases": [
        {
            "input": {
                "element": {
                    "tag": "button"
                }
            },
            "expected_output": "name=button\nselector=body > button\ntext=\n"
        },
        {
            "input": {
                "element": {
                    "tag": "div",
                    "children": [
                        {
                            "tag": "button"
                        },
                        {
                            "tag": "button"
                        }
                    ]
                },
                "targetPath": [
                    1
                ]
            },
            "expected_output": "name=button:nth-child(2)\nselector=body > div > button:nth-child(2)\ntext=\n"
        },
        {
            "input": {
                "element": {
                    "tag": "div",
                    "text": "****************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************"
                }
            },
            "expected_output": "name=div\nselector=body > div\ntext=************************************************************************************************************************************************************************************************************************************************************************************************************...\n"
        }
    ]
}
```

---

### Feature 10: Capture Browser Global Error Events

**As a developer**, I want to turn browser-level error and unhandled rejection events into reportable notices, so I can catch failures that escape application code.

**Expected Behavior / Usage:**

The input describes a browser global error or unhandled rejection event. The output reports how many notices and breadcrumbs were produced and the normalized notice fields. Ordinary global errors create a notice and an error breadcrumb with a fallback stack when needed; cross-origin script-error placeholders are ignored; unhandled rejection reasons become notices with a warning-style message.

**Test Cases:** `rcb_tests/public_test_cases/feature10_browser_global_error_events.json`

```json
{
    "description": "Browser global error and unhandled rejection events are converted into normalized notices and error breadcrumbs while ignored cross-origin script errors are skipped.",
    "cases": [
        {
            "input": {
                "kind": "global_error",
                "message": "expected message",
                "url": "https://www.example.com/",
                "line": "1"
            },
            "expected_output": "notify_count=1\nname=window.onerror\nmessage=expected message\nstack=expected message\n    at ? (https://www.example.com/:1:0)\nbreadcrumb_count=1\nbreadcrumb_message=window.onerror\nbreadcrumb_category=error\n"
        },
        {
            "input": {
                "kind": "global_error",
                "message": "Script error",
                "url": "https://www.example.com/",
                "line": 0
            },
            "expected_output": "notify_count=0\nname=none\nmessage=none\nstack=none\nbreadcrumb_count=0\nbreadcrumb_message=none\nbreadcrumb_category=none\n"
        },
        {
            "input": {
                "kind": "unhandled_rejection",
                "reasonSpecified": true,
                "reason": "Honeybadgers!"
            },
            "expected_output": "notify_count=1\nname=window.onunhandledrejection\nmessage=UnhandledPromiseRejectionWarning: Honeybadgers!\nstack=none\nbreadcrumb_count=0\nbreadcrumb_message=none\nbreadcrumb_category=none\n"
        }
    ]
}
```

---

### Feature 11: Build Browser HTTP Request Payload

**As a developer**, I want to send browser reports through an HTTP request with filtered cookies, so I can deliver reports while preserving browser request signals.

**Expected Behavior / Usage:**

The input contains browser notice options such as message and optional cookies. The output includes request method, target URL, asynchronous flag, key and content-type headers, encoded cookie data, and whether user-agent data is present. Cookies are omitted by default; string or object cookies are encoded as semicolon-separated pairs and filtered using configured secret terms.

**Test Cases:** `rcb_tests/public_test_cases/feature11_browser_http_payload.json`

```json
{
    "description": "Browser delivery sends a JSON report through an HTTP request and encodes cookie data only when explicitly provided, with configured filters applied.",
    "cases": [
        {
            "input": {
                "options": {}
            },
            "expected_output": "request_method=POST\nrequest_url=https://api.honeybadger.io/v1/notices/js\nasync=true\napi_key_header=testing\ncontent_type_header=application/json\ncookie=none\nuser_agent_present=true\n"
        },
        {
            "input": {
                "options": {
                    "cookies": "expected=value; password=secret"
                }
            },
            "expected_output": "request_method=POST\nrequest_url=https://api.honeybadger.io/v1/notices/js\nasync=true\napi_key_header=testing\ncontent_type_header=application/json\ncookie=expected=value;password=[FILTERED]\nuser_agent_present=true\n"
        }
    ]
}
```

---

### Feature 12: Deliver Server Reports over HTTP

**As a developer**, I want to post server-side reports to the configured endpoint, so I can surface success ids and HTTP failures to completion callbacks.

**Expected Behavior / Usage:**

The input contains an endpoint, HTTP response status, response body, and message. The output confirms that a POST was made to `/v1/notices/js`, identifies the endpoint, returns the callback message and report id on success, and represents failed delivery as `error=http_status` with the status code.

**Test Cases:** `rcb_tests/public_test_cases/feature12_server_http_delivery.json`

```json
{
    "description": "Server-side delivery posts notices to the configured endpoint path and invokes completion callbacks with either the returned report id or a normalized HTTP-status error signal.",
    "cases": [
        {
            "input": {
                "status": 201,
                "response": {
                    "id": "48b98609-dd3b-48ee-bffc-d51f309a2dfa"
                },
                "message": "testing"
            },
            "expected_output": "requested=true\nendpoint=https://api.honeybadger.io\npath=/v1/notices/js\ncallback_message=testing\ncallback_id=48b98609-dd3b-48ee-bffc-d51f309a2dfa\nerror=none\nstatus=none\n"
        },
        {
            "input": {
                "status": 403,
                "response": "",
                "message": "testing"
            },
            "expected_output": "requested=true\nendpoint=https://api.honeybadger.io\npath=/v1/notices/js\ncallback_message=testing\ncallback_id=none\nerror=http_status\nstatus=403\n"
        }
    ]
}
```

---

### Feature 13: Integrate with HTTP Middleware

**As a developer**, I want to connect request lifecycle handling with an HTTP framework, so I can clear per-request state and report route errors without swallowing framework behavior.

**Expected Behavior / Usage:**

The input describes an HTTP route, whether state and error-reporting middleware are installed, and whether the route throws. The output includes the routed URL, HTTP status, response body, notification count and message, later error-handler count, and context-clear count. Successful routes are not reported; installed request middleware clears state once per request; thrown errors are reported and forwarded to subsequent error handlers while the framework returns a 500 response.

**Test Cases:** `rcb_tests/public_test_cases/feature13_http_middleware_integration.json`

```json
{
    "description": "HTTP middleware clears per-request state, reports thrown route errors, forwards them to later error handlers, and leaves successful routes unreported.",
    "cases": [
        {
            "input": {
                "route": "/user",
                "okStatus": 200,
                "okBody": "{\"name\":\"john\"}",
                "throwError": false,
                "installRequestState": false,
                "installErrorReporter": false
            },
            "expected_output": "route=/user\nstatus=200\nbody={\"name\":\"john\"}\nnotify_count=0\nnotified_message=none\nnext_error_handler_count=0\nclear_count=0\n"
        },
        {
            "input": {
                "route": "/",
                "throwError": true,
                "errorMessage": "Badgers!",
                "installRequestState": true,
                "installErrorReporter": true
            },
            "expected_output": "route=/\nstatus=500\nbody=internal_error_response\nnotify_count=1\nnotified_message=Badgers!\nnext_error_handler_count=1\nclear_count=1\n"
        },
        {
            "input": {
                "route": "/",
                "okStatus": 200,
                "okBody": "Hello World!",
                "throwError": false,
                "installRequestState": true,
                "installErrorReporter": true
            },
            "expected_output": "route=/\nstatus=200\nbody=Hello World!\nnotify_count=0\nnotified_message=none\nnext_error_handler_count=0\nclear_count=1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_filter_url_parameters.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_filter_url_parameters@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same ordering convention as the headers module
