## Product Requirement Document

# Web-Native Navigation Toolkit - Black-Box Behavior Contract

## Project Goal

Build a web-native navigation and bridge toolkit that allows developers to connect embedded web content with native navigation, routing, configuration, and diagnostics without writing repetitive message parsing, route matching, or error classification code.

---

## Background & Problem

Without this library/tool, developers are forced to manually parse web message payloads, encode reply payloads, classify browser and HTTP failures, summarize page responses, and map URL paths to native navigation behavior. This leads to duplicated glue code, inconsistent diagnostics, and routing bugs around app-host versus external-host URLs.

With this library/tool, web-to-native messages, response summaries, failure categories, declarative path properties, and navigation route decisions are exposed through stable input/output behavior that can be verified without depending on a particular internal implementation.

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

### Feature 1: Bridge Payload Decoding

**As a developer**, I want to decode structured payloads sent from web content, so I can consume web-to-native messages without manually parsing JSON strings.

**Expected Behavior / Usage:**

A message input contains an identifier, component name, event name, optional metadata URL, and a raw JSON payload string. The adapter must decode the payload according to the requested payload shape. When the payload matches the requested shape, stdout lists the decoded fields as separate lines. When the payload cannot be decoded into that shape, stdout contains a null data marker rather than a host-language exception.

**Test Cases:** `rcb_tests/public_test_cases/feature1_bridge_payload_decoding.json`

```json
{
    "description": "Decode bridge message JSON payloads into a requested structured payload shape, returning the decoded fields or a null data marker when the payload cannot satisfy that shape.",
    "cases": [
        {
            "input": {
                "action": "decode_bridge_payload",
                "message": {
                    "id": "1",
                    "component": "page",
                    "event": "connect",
                    "metadata_url": "https://37signals.com",
                    "json_data": "{\"title\":\"Page-title\",\"subtitle\":\"Page-subtitle\"}"
                },
                "payload_schema": "title_subtitle"
            },
            "expected_output": "title=Page-title\nsubtitle=Page-subtitle\n"
        },
        {
            "input": {
                "action": "decode_bridge_payload",
                "message": {
                    "id": "1",
                    "component": "page",
                    "event": "connect",
                    "metadata_url": "https://37signals.com",
                    "json_data": "{\"title\":\"Page-title\",\"subtitle\":\"Page-subtitle\"}"
                },
                "payload_schema": "unsupported_empty_shape"
            },
            "expected_output": "data=null\n"
        }
    ]
}
```

---

### Feature 2: Bridge Message Replacement

**As a developer**, I want to derive outbound messages from inbound messages, so I can reply to web content while preserving correlation and metadata.

**Expected Behavior / Usage:**

A message input contains an existing message plus replacement content. The adapter must preserve the original identifier, component, and metadata URL, replace the event, and render the replacement payload. Replacement content may be supplied either as a raw JSON payload string or as structured data that is encoded to JSON. Stdout lists each resulting message field on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_bridge_message_replacement.json`

```json
{
    "description": "Create an outbound bridge message by preserving the incoming identifier, component, and metadata while replacing the event and either a raw JSON payload or an encoded structured payload.",
    "cases": [
        {
            "input": {
                "action": "replace_bridge_message",
                "message": {
                    "id": "1",
                    "component": "page",
                    "event": "connect",
                    "metadata_url": "https://37signals.com",
                    "json_data": "{\"title\":\"Page-title\",\"subtitle\":\"Page-subtitle\"}"
                },
                "replacement_event": "disconnect",
                "replacement_json": "{}"
            },
            "expected_output": "id=1\ncomponent=page\nevent=disconnect\nmetadata_url=https://37signals.com\njson_data={}\n"
        },
        {
            "input": {
                "action": "replace_bridge_message",
                "message": {
                    "id": "1",
                    "component": "page",
                    "event": "connect",
                    "metadata_url": "https://37signals.com",
                    "json_data": "{}"
                },
                "replacement_event": "disconnect",
                "replacement_data": {
                    "title": "New-title",
                    "subtitle": "New-subtitle"
                }
            },
            "expected_output": "id=1\ncomponent=page\nevent=disconnect\nmetadata_url=https://37signals.com\njson_data={\"title\":\"New-title\",\"subtitle\":\"New-subtitle\"}\n"
        }
    ]
}
```

---

### Feature 3: Bridge Payload Encoding Error Normalization

**As a developer**, I want to receive stable error categories for bridge payload encoding failures, so I can handle misconfigured JSON support consistently across implementations.

**Expected Behavior / Usage:**

When structured bridge reply data must be encoded, JSON conversion support is required. If conversion support is missing or invalid, stdout must not expose a runtime exception type or runtime-generated message. It must instead print a language-neutral error category that identifies the configuration problem.

**Test Cases:** `rcb_tests/public_test_cases/feature3_bridge_payload_encoding_errors.json`

```json
{
    "description": "Report language-neutral error categories when a structured bridge payload cannot be encoded because JSON conversion support is missing or invalid.",
    "cases": [
        {
            "input": {
                "action": "encode_bridge_payload_with_converter",
                "converter": "none",
                "message": {
                    "id": "1",
                    "component": "page",
                    "event": "connect",
                    "metadata_url": "https://37signals.com",
                    "json_data": "{}"
                },
                "replacement_data": {
                    "title": "New-title",
                    "subtitle": "New-subtitle"
                }
            },
            "expected_output": "error=no_json_converter\n"
        },
        {
            "input": {
                "action": "encode_bridge_payload_with_converter",
                "converter": "invalid",
                "message": {
                    "id": "1",
                    "component": "page",
                    "event": "connect",
                    "metadata_url": "https://37signals.com",
                    "json_data": "{}"
                },
                "replacement_data": {
                    "title": "New-title",
                    "subtitle": "New-subtitle"
                }
            },
            "expected_output": "error=invalid_json_converter\n"
        }
    ]
}
```

---

### Feature 4: Visit Response Summary Rendering

**As a developer**, I want to summarize a completed page visit response, so I can log status and compact response content without dumping entire HTML documents.

**Expected Behavior / Usage:**

A response input contains an HTTP status code and either no HTML body or a raw HTML body. The adapter must print the status, a normalized HTML preview, and the original body length. Newlines are removed, repeated whitespace is collapsed, and long HTML is truncated in the middle with an explicit omission marker while preserving the original length.

**Test Cases:** `rcb_tests/public_test_cases/feature4_visit_response_summary.json`

```json
{
    "description": "Render a visit response summary with status, normalized HTML preview, middle truncation for long responses, and original response length.",
    "cases": [
        {
            "input": {
                "action": "summarize_visit_response",
                "status_code": 200,
                "response_html": null
            },
            "expected_output": "status=200\nresponse_html=null\nresponse_length=0\n"
        },
        {
            "input": {
                "action": "summarize_visit_response",
                "status_code": 200,
                "response_html": "<html><head></head></html>"
            },
            "expected_output": "status=200\nresponse_html=<html><head></head></html>\nresponse_length=26\n"
        },
        {
            "input": {
                "action": "summarize_visit_response",
                "status_code": 200,
                "response_html": "<html><head></head>This is a really long response that is truncated.</html>"
            },
            "expected_output": "status=200\nresponse_html=<html><head></head>This i [...] that is truncated.</html>\nresponse_length=75\n"
        },
        {
            "input": {
                "action": "summarize_visit_response",
                "status_code": 200,
                "response_html": "<html>\n<head></head>This   is a really long response that is truncated.\n</html>"
            },
            "expected_output": "status=200\nresponse_html=<html><head></head>This i [...] that is truncated.</html>\nresponse_length=79\n"
        }
    ]
}
```

---

### Feature 5: HTTP Status Classification

**As a developer**, I want to classify HTTP status failures, so I can route client, server, and unknown status responses consistently.

**Expected Behavior / Usage:**

A status-code input is classified as a client error for 400 through 499, a server error for 500 through 599, and unknown outside those ranges. Known status codes include their standard reason phrase. Other status codes in the client or server ranges keep the numeric status and category but leave the reason blank.

**Test Cases:** `rcb_tests/public_test_cases/feature5_http_status_classification.json`

```json
{
    "description": "Classify HTTP response status codes into client, server, or unknown error categories while preserving the numeric status and known reason phrase.",
    "cases": [
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 400
            },
            "expected_output": "status=400\ncategory=client\nreason=Bad Request\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 401
            },
            "expected_output": "status=401\ncategory=client\nreason=Unauthorized\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 402
            },
            "expected_output": "status=402\ncategory=client\nreason=Payment Required\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 403
            },
            "expected_output": "status=403\ncategory=client\nreason=Forbidden\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 404
            },
            "expected_output": "status=404\ncategory=client\nreason=Not Found\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 405
            },
            "expected_output": "status=405\ncategory=client\nreason=Method Not Allowed\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 406
            },
            "expected_output": "status=406\ncategory=client\nreason=Not Accessible\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 407
            },
            "expected_output": "status=407\ncategory=client\nreason=Proxy Authentication Required\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 408
            },
            "expected_output": "status=408\ncategory=client\nreason=Request Timeout\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 409
            },
            "expected_output": "status=409\ncategory=client\nreason=Conflict\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 421
            },
            "expected_output": "status=421\ncategory=client\nreason=Misdirected Request\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 422
            },
            "expected_output": "status=422\ncategory=client\nreason=Unprocessable Entity\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 428
            },
            "expected_output": "status=428\ncategory=client\nreason=Precondition Required\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 429
            },
            "expected_output": "status=429\ncategory=client\nreason=Too Many Requests\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 430
            },
            "expected_output": "status=430\ncategory=client\nreason=\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 499
            },
            "expected_output": "status=499\ncategory=client\nreason=\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 500
            },
            "expected_output": "status=500\ncategory=server\nreason=Internal Server Error\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 501
            },
            "expected_output": "status=501\ncategory=server\nreason=Not Implemented\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 502
            },
            "expected_output": "status=502\ncategory=server\nreason=Bad Gateway\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 503
            },
            "expected_output": "status=503\ncategory=server\nreason=Service Unavailable\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 504
            },
            "expected_output": "status=504\ncategory=server\nreason=Gateway Timeout\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 505
            },
            "expected_output": "status=505\ncategory=server\nreason=Http Version Not Supported\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 506
            },
            "expected_output": "status=506\ncategory=server\nreason=\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 599
            },
            "expected_output": "status=599\ncategory=server\nreason=\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 399
            },
            "expected_output": "status=399\ncategory=unknown\nreason=\n"
        },
        {
            "input": {
                "action": "classify_http_status",
                "status_code": 600
            },
            "expected_output": "status=600\ncategory=unknown\nreason=\n"
        }
    ]
}
```

---

### Feature 6: Web Load Error Classification

**As a developer**, I want to classify browser page-load failures, so I can display stable diagnostics for navigation failures.

**Expected Behavior / Usage:**

A browser load error input contains a numeric error code. Recognized codes produce a stable category and human-readable description. Unrecognized codes preserve the numeric code, use the other category, and leave the description blank. Stdout must not contain host-language exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature6_web_load_error_classification.json`

```json
{
    "description": "Classify browser page-load error codes into stable categories and descriptions, using an other category for unrecognized codes.",
    "cases": [
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -1
            },
            "expected_output": "code=-1\ncategory=unknown\ndescription=Unknown\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -2
            },
            "expected_output": "code=-2\ncategory=host_lookup\ndescription=Host Lookup\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -3
            },
            "expected_output": "code=-3\ncategory=unsupported_auth_scheme\ndescription=Unsupported Auth Scheme\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -4
            },
            "expected_output": "code=-4\ncategory=authentication\ndescription=Authentication\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -5
            },
            "expected_output": "code=-5\ncategory=proxy_authentication\ndescription=Proxy Authentication\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -6
            },
            "expected_output": "code=-6\ncategory=connect\ndescription=Connect\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -7
            },
            "expected_output": "code=-7\ncategory=io\ndescription=IO\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -8
            },
            "expected_output": "code=-8\ncategory=timeout\ndescription=Timeout\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -9
            },
            "expected_output": "code=-9\ncategory=redirect_loop\ndescription=Redirect Loop\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -10
            },
            "expected_output": "code=-10\ncategory=unsupported_scheme\ndescription=Unsupported Scheme\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -11
            },
            "expected_output": "code=-11\ncategory=failed_ssl_handshake\ndescription=Failed SSL Handshake\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -12
            },
            "expected_output": "code=-12\ncategory=bad_url\ndescription=Bad URL\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -13
            },
            "expected_output": "code=-13\ncategory=file\ndescription=File\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -14
            },
            "expected_output": "code=-14\ncategory=file_not_found\ndescription=File Not Found\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -15
            },
            "expected_output": "code=-15\ncategory=too_many_requests\ndescription=Too Many Requests\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -16
            },
            "expected_output": "code=-16\ncategory=unsafe_resource\ndescription=Unsafe Resource\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": -17
            },
            "expected_output": "code=-17\ncategory=other\ndescription=\n"
        },
        {
            "input": {
                "action": "classify_web_load_error",
                "error_code": 1
            },
            "expected_output": "code=1\ncategory=other\ndescription=\n"
        }
    ]
}
```

---

### Feature 7: SSL Certificate Error Classification

**As a developer**, I want to classify certificate validation failures, so I can distinguish certificate problems during secure page loads.

**Expected Behavior / Usage:**

A certificate error input contains a numeric validation error code. Recognized certificate problems produce a stable category and description. Unrecognized codes preserve the numeric code, use the other category, and leave the description blank.

**Test Cases:** `rcb_tests/public_test_cases/feature7_ssl_certificate_error_classification.json`

```json
{
    "description": "Classify SSL certificate validation error codes into stable certificate-error categories and descriptions, using an other category for unrecognized codes.",
    "cases": [
        {
            "input": {
                "action": "classify_ssl_certificate_error",
                "error_code": 0
            },
            "expected_output": "code=0\ncategory=not_yet_valid\ndescription=Not Yet Valid\n"
        },
        {
            "input": {
                "action": "classify_ssl_certificate_error",
                "error_code": 1
            },
            "expected_output": "code=1\ncategory=expired\ndescription=Expired\n"
        },
        {
            "input": {
                "action": "classify_ssl_certificate_error",
                "error_code": 2
            },
            "expected_output": "code=2\ncategory=id_mismatch\ndescription=ID Mismatch\n"
        },
        {
            "input": {
                "action": "classify_ssl_certificate_error",
                "error_code": 3
            },
            "expected_output": "code=3\ncategory=untrusted\ndescription=Untrusted\n"
        },
        {
            "input": {
                "action": "classify_ssl_certificate_error",
                "error_code": 4
            },
            "expected_output": "code=4\ncategory=date_invalid\ndescription=Date Invalid\n"
        },
        {
            "input": {
                "action": "classify_ssl_certificate_error",
                "error_code": 5
            },
            "expected_output": "code=5\ncategory=invalid\ndescription=Invalid\n"
        },
        {
            "input": {
                "action": "classify_ssl_certificate_error",
                "error_code": -1
            },
            "expected_output": "code=-1\ncategory=other\ndescription=\n"
        },
        {
            "input": {
                "action": "classify_ssl_certificate_error",
                "error_code": 6
            },
            "expected_output": "code=6\ncategory=other\ndescription=\n"
        }
    ]
}
```

---

### Feature 8: Path Configuration Property Lookup

**As a developer**, I want to load path rules and resolve properties for URLs, so I can drive navigation behavior from declarative URL patterns.

**Expected Behavior / Usage:**

A lookup input contains a list of absolute URLs. The system loads the configured path rules and top-level settings, then applies all matching rules to each URL path in order. Stdout first reports rule and settings metadata, then prints each URL and the resulting context, presentation behavior, query-string behavior, title, pull-to-refresh flag, and destination URI.

**Test Cases:** `rcb_tests/public_test_cases/feature8_path_configuration_lookup.json`

```json
{
    "description": "Load navigation path configuration and return the merged properties that match each requested URL path, including settings, context, presentation, title, refresh behavior, and destination URI.",
    "cases": [
        {
            "input": {
                "action": "lookup_path_properties",
                "urls": [
                    "https://turbo.hotwired.dev/home",
                    "https://turbo.hotwired.dev/new",
                    "https://turbo.hotwired.dev/edit",
                    "https://turbo.hotwired.dev/image.jpg"
                ]
            },
            "expected_output": "rules_count=10\nsettings_count=1\nsetting_custom_app_feature_enabled=true\nurl=https://turbo.hotwired.dev/home\ncontext=default\npresentation=clear_all\nquery_string_presentation=default\ntitle=\npull_to_refresh_enabled=true\nuri=hotwire://fragment/web/home\nurl=https://turbo.hotwired.dev/new\ncontext=modal\npresentation=default\nquery_string_presentation=default\ntitle=\npull_to_refresh_enabled=false\nuri=hotwire://fragment/web/modal\nurl=https://turbo.hotwired.dev/edit\ncontext=modal\npresentation=default\nquery_string_presentation=default\ntitle=\npull_to_refresh_enabled=false\nuri=hotwire://fragment/web/modal\nurl=https://turbo.hotwired.dev/image.jpg\ncontext=default\npresentation=default\nquery_string_presentation=default\ntitle=Image Viewer\npull_to_refresh_enabled=true\nuri=hotwire://fragment/image_viewer\n"
        }
    ]
}
```

---

### Feature 9: Navigation Route Classification

**As a developer**, I want to decide whether a URL stays in app navigation or is handed off externally, so I can protect in-app routing while sending foreign hosts to an external browser surface.

**Expected Behavior / Usage:**

A route input contains a route kind, an application start URL, and a target URL. In-app routes match only when the target host equals the start host and use a navigate decision. External browser routes match when the target host differs from the start host and use a cancel decision to stop in-app navigation. The rendered output includes the start host, target host, decision, and match result so framework routing behavior is observable.

**Test Cases:** `rcb_tests/public_test_cases/feature9_navigation_route_classification.json`

```json
{
    "description": "Classify a requested URL against the application start host for in-app navigation or external handoff routes, preserving the route decision and match result.",
    "cases": [
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "app",
                "start_location": "https://my.app.com",
                "url": "https://my.app.com/page"
            },
            "expected_output": "route_kind=app\nstart_host=my.app.com\ntarget_host=my.app.com\ndecision=navigate\nmatches=true\n"
        },
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "app",
                "start_location": "https://my.app.com",
                "url": "https://app.com/page"
            },
            "expected_output": "route_kind=app\nstart_host=my.app.com\ntarget_host=app.com\ndecision=navigate\nmatches=false\n"
        },
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "app",
                "start_location": "https://my.app.com",
                "url": "https://app.my.com@fake.domain"
            },
            "expected_output": "route_kind=app\nstart_host=my.app.com\ntarget_host=fake.domain\ndecision=navigate\nmatches=false\n"
        },
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "external_browser",
                "start_location": "https://my.app.com",
                "url": "https://external.com/page"
            },
            "expected_output": "route_kind=external_browser\nstart_host=my.app.com\ntarget_host=external.com\ndecision=cancel\nmatches=true\n"
        },
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "external_browser",
                "start_location": "https://my.app.com",
                "url": "https://app.com/page"
            },
            "expected_output": "route_kind=external_browser\nstart_host=my.app.com\ntarget_host=app.com\ndecision=cancel\nmatches=true\n"
        },
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "external_browser",
                "start_location": "https://my.app.com",
                "url": "https://my.app.com/page"
            },
            "expected_output": "route_kind=external_browser\nstart_host=my.app.com\ntarget_host=my.app.com\ndecision=cancel\nmatches=false\n"
        },
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "external_browser_tab",
                "start_location": "https://my.app.com",
                "url": "https://external.com/page"
            },
            "expected_output": "route_kind=external_browser_tab\nstart_host=my.app.com\ntarget_host=external.com\ndecision=cancel\nmatches=true\n"
        },
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "external_browser_tab",
                "start_location": "https://my.app.com",
                "url": "https://app.com/page"
            },
            "expected_output": "route_kind=external_browser_tab\nstart_host=my.app.com\ntarget_host=app.com\ndecision=cancel\nmatches=true\n"
        },
        {
            "input": {
                "action": "classify_navigation_route",
                "route_kind": "external_browser_tab",
                "start_location": "https://my.app.com",
                "url": "https://my.app.com/page"
            },
            "expected_output": "route_kind=external_browser_tab\nstart_host=my.app.com\ntarget_host=my.app.com\ndecision=cancel\nmatches=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_bridge_payload_decoding.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_bridge_payload_decoding@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
