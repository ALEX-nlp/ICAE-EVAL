## Product Requirement Document

# HTTP API Test Client - Black-Box Request and Response Verification

## Project Goal

Build an HTTP API test client that allows developers to compose requests, execute them against real endpoints, and verify responses without writing repetitive low-level HTTP plumbing.

---

## Background & Problem

Without this tool, developers are forced to manually construct URLs, headers, cookies, request bodies, assertions, extraction logic, and content-type handling for every API test. This leads to repetitive code, brittle checks, and inconsistent error reporting.

With this tool, request setup, execution, response verification, extraction, and schema validation are expressed through a concise client-facing interface while the execution adapter exposes deterministic input/output contracts for black-box testing.

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

### Feature 1: HTTP Method Execution

**As a developer**, I want to send common HTTP request methods to a target endpoint, so I can exercise server behavior through real HTTP requests.

**Expected Behavior / Usage:**

The input declares an HTTP method, a request path, and the response status configured by a local test server. The adapter must send the specified method to the path and print the method, routed path, and observed status code.

**Test Cases:** `rcb_tests/public_test_cases/feature1_http_methods.json`

```json
{
    "description": "HTTP clients can issue the requested verb to a target endpoint and expose the response status.",
    "cases": [
        {
            "input": {
                "feature": "http_method",
                "method": "GET",
                "path": "/http-get",
                "response_status": 200
            },
            "expected_output": "method=GET\nrequest_path=/http-get\nstatus=200\n"
        }
    ]
}
```

---

### Feature 2: Request Header Construction

**As a developer**, I want to attach request headers and content negotiation metadata, so I can verify that the receiving service observes the intended wire headers.

**Expected Behavior / Usage:**

The input declares a header scenario, including ordinary headers, multi-value headers, content type with charset, or accept preferences. The output must include the request path, the header field being tested, the wire value observed by the server, and the returned status.

**Test Cases:** `rcb_tests/public_test_cases/feature2_request_headers.json`

```json
{
    "description": "Request builders can attach ordinary headers, content metadata, and accept preferences that are seen by the server.",
    "cases": [
        {
            "input": {
                "feature": "request_header",
                "kind": "single",
                "path": "/single-header-value",
                "name": "my_header",
                "value": "my_header_value",
                "response_status": 200
            },
            "expected_output": "method=GET\nrequest_path=/single-header-value\nheader=my_header\nvalue=my_header_value\nstatus=200\n"
        }
    ]
}
```

---

### Feature 3: Authorization Header Construction

**As a developer**, I want to send authentication data as standard authorization headers, so I can test protected APIs without hand-coding authorization header values.

**Expected Behavior / Usage:**

The input declares either basic credentials or a bearer token. The output must show the authorization scheme, the exact authorization header value placed on the wire, the request path, and the status returned by the server.

**Test Cases:** `rcb_tests/public_test_cases/feature3_authorization_headers.json`

```json
{
    "description": "Request builders can derive authorization header values from credentials or bearer tokens.",
    "cases": [
        {
            "input": {
                "feature": "auth_header",
                "scheme": "basic",
                "path": "/basic-auth",
                "username": "username",
                "password": "password",
                "response_status": 200
            },
            "expected_output": "method=GET\nrequest_path=/basic-auth\nauthorization=basic\nvalue=[basic auth header prefix string]dXNlcm5hbWU6cGFzc3dvcmQ=\nstatus=200\n"
        }
    ]
}
```

---

### Feature 4: Cookie Transmission

**As a developer**, I want to attach cookies using supported input shapes, so I can verify cookie-dependent endpoints through real request traffic.

**Expected Behavior / Usage:**

The input declares a cookie name, value, request path, and the form in which the cookie was supplied. The output must show that the same cookie name and value reached the server and include the response status.

**Test Cases:** `rcb_tests/public_test_cases/feature4_cookies.json`

```json
{
    "description": "A request can carry cookies supplied in supported input shapes and the server receives the same name-value pair.",
    "cases": [
        {
            "input": {
                "feature": "cookie",
                "form": "string_pair",
                "path": "/single-cookie-value",
                "name": "my_cookie",
                "value": "my_cookie_value",
                "response_status": 200
            },
            "expected_output": "method=GET\nrequest_path=/single-cookie-value\ncookie=my_cookie\nvalue=my_cookie_value\nstatus=200\n"
        }
    ]
}
```

---

### Feature 5: Query Parameter Routing

**As a developer**, I want to add query parameters to outgoing requests, so I can verify endpoints that depend on URL query values.

**Expected Behavior / Usage:**

The input declares query parameters either as sequential entries or as a grouped parameter set. If the same name appears more than once, the last supplied value is used. The output prints the request path, final query string, and status.

**Test Cases:** `rcb_tests/public_test_cases/feature5_query_parameters.json`

```json
{
    "description": "Query parameters are appended to outgoing URLs, and repeated parameter names use the last supplied value.",
    "cases": [
        {
            "input": {
                "feature": "query_param",
                "mode": "sequential",
                "path": "/single-query-param",
                "parameters": [
                    {
                        "name": "name",
                        "value": "john"
                    }
                ],
                "response_status": 200
            },
            "expected_output": "method=GET\nrequest_path=/single-query-param\nquery=name=john\nstatus=200\n"
        }
    ]
}
```

---

### Feature 6: Path Placeholder Substitution

**As a developer**, I want to replace named path placeholders before dispatch, so I can build dynamic endpoint URLs safely.

**Expected Behavior / Usage:**

The input declares a target path template and one or more placeholder values. The adapter must send the request to the fully substituted path and print the resolved path and response status.

**Test Cases:** `rcb_tests/public_test_cases/feature6_path_parameters.json`

```json
{
    "description": "Named placeholders in a target path are replaced with supplied values before the HTTP request is sent.",
    "cases": [
        {
            "input": {
                "feature": "path_param",
                "mode": "sequential",
                "template": "/user/{{userid}}",
                "expected_path": "[a hardcoded path pattern for lookup tests]",
                "parameters": [
                    {
                        "name": "userid",
                        "value": 1
                    }
                ],
                "response_status": 200
            },
            "expected_output": "method=GET\nrequest_path=[a hardcoded path pattern for lookup tests]\nstatus=200\n"
        }
    ]
}
```

---

### Feature 7: Request Body Transmission

**As a developer**, I want to send request bodies in HTTP POST requests, so I can verify APIs that consume text or JSON payloads.

**Expected Behavior / Usage:**

The input declares a POST path, a body kind, and the body content. The output must include the path, the body sent, and the status returned by a server that matched that body.

**Test Cases:** `rcb_tests/public_test_cases/feature7_request_bodies.json`

```json
{
    "description": "POST requests can send plain text and JSON bodies that are observable by the server.",
    "cases": [
        {
            "input": {
                "feature": "request_body",
                "body_kind": "text",
                "path": "/plaintext-request-body",
                "body": "Here's a plaintext request body.",
                "response_status": 201
            },
            "expected_output": "method=POST\nrequest_path=/plaintext-request-body\nbody=Here's a plaintext request body.\nstatus=201\n"
        }
    ]
}
```

---

### Feature 8: URL-Encoded Form Submission

**As a developer**, I want to send key-value fields as form data, so I can test form endpoints using the correct wire encoding.

**Expected Behavior / Usage:**

The input declares form fields for a POST request. The output must include the URL-encoded body, the form content type, the path, and the server status.

**Test Cases:** `rcb_tests/public_test_cases/feature8_form_data.json`

```json
{
    "description": "Key-value fields can be sent as URL-encoded form data with the expected request content type.",
    "cases": [
        {
            "input": {
                "feature": "form_data",
                "path": "/form-data",
                "fields": [
                    {
                        "name": "name",
                        "value": "John Doe"
                    },
                    {
                        "name": "email",
                        "value": "johndoe@example.com"
                    }
                ],
                "response_status": 201
            },
            "expected_output": "method=POST\nrequest_path=/form-data\ncontent_type=application/x-www-form-urlencoded\nbody=name=John+Doe&email=johndoe%40example.com\nstatus=201\n"
        }
    ]
}
```

---

### Feature 9: User Agent Configuration

**As a developer**, I want to set a product-style user agent on requests, so I can verify endpoints that inspect client identification.

**Expected Behavior / Usage:**

The input declares product and version values and whether they are supplied directly or through reusable defaults. The output must include the resulting user-agent wire value, request path, and status.

**Test Cases:** `rcb_tests/public_test_cases/feature9_user_agent.json`

```json
{
    "description": "A request can set a product-style user agent directly or through reusable request defaults.",
    "cases": [
        {
            "input": {
                "feature": "user_agent",
                "mode": "object",
                "path": "/user-agent",
                "product": "MyUserAgent",
                "version": "1.0",
                "response_status": 200
            },
            "expected_output": "method=GET\nrequest_path=/user-agent\nuser_agent=MyUserAgent/1.0\nstatus=200\n"
        }
    ]
}
```

---

### Feature 10: Status Code Verification

**As a developer**, I want to assert response status codes, so I can fail fast when an endpoint returns an unexpected status.

**Expected Behavior / Usage:**

The input declares a server status and a status expectation. Matching expectations print a verification line; mismatches print a normalized assertion error without host-language exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature10_status_verification.json`

```json
{
    "description": "Response status assertions succeed for matching values and report a normalized assertion failure for mismatches.",
    "cases": [
        {
            "input": {
                "feature": "status_verification",
                "path": "/http-status-code-ok",
                "actual_status": 200,
                "check": "integer",
                "expected_status": 200
            },
            "expected_output": "method=GET\nrequest_path=/http-status-code-ok\nstatus=200\nverification=status_matched\n"
        },
        {
            "input": {
                "feature": "status_verification",
                "path": "/http-status-code-ok",
                "actual_status": 200,
                "check": "matcher_greater_than",
                "threshold": 300
            },
            "expected_output": "error=assertion_failed\nmessage=Expected response status code to match 'greater than 300', but was 200\n"
        }
    ]
}
```

---

### Feature 11: Response Header Verification

**As a developer**, I want to assert response headers and content types, so I can validate response metadata without manual header parsing.

**Expected Behavior / Usage:**

The input declares response headers and a header expectation. Matching checks print a verification line; absent or mismatched headers print a normalized assertion failure with the relevant message.

**Test Cases:** `rcb_tests/public_test_cases/feature11_response_header_verification.json`

```json
{
    "description": "Response headers and content types can be checked exactly or by containment, with normalized failures for absent or mismatched values.",
    "cases": [
        {
            "input": {
                "feature": "response_header_verification",
                "mode": "exact",
                "path": "/custom-response-header",
                "response_status": 200,
                "response_headers": {
                    "custom_header_name": "custom_header_value"
                },
                "header": "custom_header_name",
                "expected": "custom_header_value"
            },
            "expected_output": "method=GET\nrequest_path=/custom-response-header\nstatus=200\nheader=custom_header_name\nverification=header_matched\n"
        },
        {
            "input": {
                "feature": "response_header_verification",
                "mode": "content_type_contains",
                "path": "/custom-response-content-type-header",
                "response_status": 200,
                "response_headers": {
                    "Content-Type": "application/something"
                },
                "header": "Content-Type",
                "contains": "something"
            },
            "expected_output": "method=GET\nrequest_path=/custom-response-content-type-header\nstatus=200\nheader=Content-Type\nverification=header_matched\n"
        }
    ]
}
```

---

### Feature 12: Whole Response Body Verification

**As a developer**, I want to assert complete or partial response bodies, so I can validate payload content returned by an API.

**Expected Behavior / Usage:**

The input declares a response body and either an exact or containment expectation. Matching checks print the body and verification signal; mismatches print a normalized assertion failure.

**Test Cases:** `rcb_tests/public_test_cases/feature12_response_body_verification.json`

```json
{
    "description": "Whole response bodies can be checked exactly or by substring containment, with normalized failures on mismatches.",
    "cases": [
        {
            "input": {
                "feature": "response_body_verification",
                "mode": "exact",
                "path": "/plaintext-response-body",
                "response_status": 200,
                "response_body": "Here's a plaintext response body.",
                "expected": "Here's a plaintext response body."
            },
            "expected_output": "method=GET\nrequest_path=/plaintext-response-body\nstatus=200\nbody=Here's a plaintext response body.\nverification=body_matched\n"
        },
        {
            "input": {
                "feature": "response_body_verification",
                "mode": "exact",
                "path": "/plaintext-response-body",
                "response_status": 200,
                "response_body": "Here's a plaintext response body.",
                "expected": "This is a different plaintext response body."
            },
            "expected_output": "error=assertion_failed\nmessage=Actual response body did not match expected response body.\\nExpected: This is a different plaintext response body.\\nActual: Here's a plaintext response body.\n"
        }
    ]
}
```

---

### Feature 13: JSON Element Verification

**As a developer**, I want to assert selected JSON response elements, so I can validate structured JSON payloads by path.

**Expected Behavior / Usage:**

The input declares a JSON selector and matcher. The adapter must request a JSON document, evaluate the selector, and print a verification signal or a normalized failure for missing or mismatched elements.

**Test Cases:** `rcb_tests/public_test_cases/feature13_json_body_verification.json`

```json
{
    "description": "JSON response elements selected by path expressions can be checked as scalar values or collections.",
    "cases": [
        {
            "input": {
                "feature": "json_body_verification",
                "selector": "$.Places[0].Name",
                "matcher": "contains",
                "value": "City"
            },
            "expected_output": "method=GET\nrequest_path=/json-response-body\nstatus=200\nselector=$.Places[0].Name\nverification=json_element_matched\n"
        },
        {
            "input": {
                "feature": "json_body_verification",
                "selector": "$.Places[0:].Name",
                "matcher": "item_equal",
                "value": "Atlantis"
            },
            "expected_output": "error=assertion_failed\nmessage=Expected elements selected by '$.Places[0:].Name' to match 'a collection containing \"Atlantis\"', but was [Sun City, Pleasure Meadow]\n"
        }
    ]
}
```

---

### Feature 14: XML Element Verification

**As a developer**, I want to assert selected XML response elements, so I can validate structured XML payloads by path.

**Expected Behavior / Usage:**

The input declares an XML selector and matcher. The adapter must request an XML document, evaluate the selector, and print a verification signal or a normalized failure for missing or mismatched elements.

**Test Cases:** `rcb_tests/public_test_cases/feature14_xml_body_verification.json`

```json
{
    "description": "XML response elements selected by path expressions can be checked as scalar values or collections.",
    "cases": [
        {
            "input": {
                "feature": "xml_body_verification",
                "selector": "//Place[1]/Name",
                "matcher": "equal",
                "value": "Sun City"
            },
            "expected_output": "method=GET\nrequest_path=/xml-response-body\nstatus=200\nselector=//Place[1]/Name\nverification=xml_element_matched\n"
        },
        {
            "input": {
                "feature": "xml_body_verification",
                "selector": "//Place/Name",
                "matcher": "item_equal",
                "value": "Atlantis"
            },
            "expected_output": "error=assertion_failed\nmessage=Expected elements selected by '//Place/Name' to match 'a collection containing \"Atlantis\"', but was [Sun City, Pleasure Meadow]\n"
        }
    ]
}
```

---

### Feature 15: JSON Response Extraction

**As a developer**, I want to extract JSON values, headers, and response metadata, so I can reuse values returned by an API in later checks.

**Expected Behavior / Usage:**

The input declares whether to extract a JSON body value, a response header, or full response metadata. The output prints the selected value and observable HTTP signals, or a normalized extraction/assertion error.

**Test Cases:** `rcb_tests/public_test_cases/feature15_json_extraction.json`

```json
{
    "description": "JSON response values, response headers, and full response metadata can be extracted after a successful request.",
    "cases": [
        {
            "input": {
                "feature": "json_extraction",
                "mode": "body",
                "selector": "$.Places[0].Name"
            },
            "expected_output": "method=GET\nrequest_path=/json-response-body\nstatus=200\nselector=$.Places[0].Name\nvalue=Sun City\n"
        },
        {
            "input": {
                "feature": "json_extraction",
                "mode": "response"
            },
            "expected_output": "method=GET\nrequest_path=/json-response-body\nstatus=200\ncustom_header=custom_header_value\n"
        }
    ]
}
```

---

### Feature 16: XML Response Extraction

**As a developer**, I want to extract XML values by selector, so I can reuse XML payload data in later checks.

**Expected Behavior / Usage:**

The input declares an XML selector. The output prints the selected value or list-like value plus request metadata, or a normalized extraction error when the selector has no result.

**Test Cases:** `rcb_tests/public_test_cases/feature16_xml_extraction.json`

```json
{
    "description": "XML response values can be extracted with path expressions, including single values and multiple matches.",
    "cases": [
        {
            "input": {
                "feature": "xml_extraction",
                "selector": "//Place[1]/Name"
            },
            "expected_output": "method=GET\nrequest_path=/xml-response-body\nstatus=200\nselector=//Place[1]/Name\nvalue=Sun City\n"
        },
        {
            "input": {
                "feature": "xml_extraction",
                "selector": "//Place/DoesNotExist"
            },
            "expected_output": "error=extraction_failed\nmessage=XPath expression '//Place/DoesNotExist' did not yield any results.\n"
        }
    ]
}
```

---

### Feature 17: Response Deserialization

**As a developer**, I want to convert JSON or XML responses into data objects, so I can work with typed domain data instead of raw response text.

**Expected Behavior / Usage:**

The input declares a response format. Recognized JSON and XML content types produce object-field output; an unrecognized content type produces a normalized deserialization failure.

**Test Cases:** `rcb_tests/public_test_cases/feature17_deserialization.json`

```json
{
    "description": "JSON and XML responses can be converted into caller-defined data objects when the response content type is recognized.",
    "cases": [
        {
            "input": {
                "feature": "deserialization",
                "format": "json"
            },
            "expected_output": "method=GET\nrequest_path=/json-deserialization\ncontent_type=application/json\ncountry=United States\nplaces_count=2\n"
        },
        {
            "input": {
                "feature": "deserialization",
                "format": "unknown"
            },
            "expected_output": "error=deserialization_failed\nmessage=Unable to deserialize response with Content-Type 'application/something'\n"
        }
    ]
}
```

---

### Feature 18: JSON Schema Validation

**As a developer**, I want to validate JSON responses against schemas, so I can catch contract drift in structured API responses.

**Expected Behavior / Usage:**

The input declares a schema validation scenario. Valid data and schema inputs print a verification signal; invalid schemas, mismatching data, or non-JSON content types print normalized verification failures.

**Test Cases:** `rcb_tests/public_test_cases/feature18_json_schema.json`

```json
{
    "description": "JSON responses can be validated against a supplied schema and produce normalized verification errors for schema, data, or content-type problems.",
    "cases": [
        {
            "input": {
                "feature": "json_schema",
                "mode": "string_schema"
            },
            "expected_output": "method=GET\nrequest_path=/json-schema-validation\nstatus=200\nverification=json_schema_matched\n"
        },
        {
            "input": {
                "feature": "json_schema",
                "mode": "content_type_error"
            },
            "expected_output": "error=response_verification_failed\nmessage=Expected response Content-Type header to contain 'json', but was 'application/something'\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_http_methods.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_http_methods@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the sublitition rule in the path_param feature block
- check the header output section for feature 2
