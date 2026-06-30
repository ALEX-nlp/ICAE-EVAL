## Product Requirement Document

# API Response Formatting Toolkit - Standardized JSON Responses and Transformation Contracts

## Project Goal

Build a response formatting and transformation toolkit that allows developers to produce consistent JSON success responses, error responses, pagination metadata, resource envelopes, sparse field output, and framework-visible HTTP responses without repetitive response-building boilerplate.

---

## Background & Problem

Without this library/tool, developers are forced to manually wrap API data, copy pagination fields, merge related resources, validate HTTP status categories, normalize domain errors, and keep framework response metadata in sync with JSON bodies. This leads to inconsistent wire formats, repetitive code, and hard-to-test response behavior.

With this library/tool, developers describe the payload or error once and receive predictable JSON output plus framework-observable response signals such as status code, headers, and raw JSON content.

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

### Feature 1: Success Payload Serialization

**As a developer**, I want to serialize successful resource results in a predictable envelope, so I can return collections, single items, [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] values, and metadata in a consistent JSON shape.

**Expected Behavior / Usage:**

The adapter accepts a JSON command describing which successful payload shape to serialize. Collection and item payloads are wrapped in a top-level `data` object, [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] resources are represented as `data: [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation]`, and metadata is returned as the metadata object itself.

**Test Cases:** `rcb_tests/public_test_cases/feature1_success_payload_serialization.json`

```json
{
    "description": "Serialize successful resource payloads using the default envelope for collections, single items, [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] resources, and metadata blocks.",
    "cases": [
        {
            "input": {
                "operation": "serialize_success_resource",
                "kind": "collection",
                "data": [
                    {
                        "id": 1,
                        "name": "Alpha"
                    },
                    {
                        "id": 2,
                        "name": "Beta"
                    }
                ]
            },
            "expected_output": "{\"data\":[{\"id\":1,\"name\":\"Alpha\"},{\"id\":2,\"name\":\"Beta\"}]}\n"
        }
    ]
}
```

---

### Feature 2: Pagination Metadata Serialization

**As a developer**, I want to serialize pagination signals alongside successful responses, so I can preserve page and cursor navigation details for API clients.

**Expected Behavior / Usage:**

The adapter accepts either page-number pagination attributes or cursor pagination attributes. Page-number output includes total, count, per-page count, current page, total pages, and previous/next URLs. Cursor output includes current, previous, next, and count values.

**Test Cases:** `rcb_tests/public_test_cases/feature2_success_pagination_serialization.json`

```json
{
    "description": "Serialize successful pagination metadata for page-number and cursor-based pagination without changing the resource data envelope.",
    "cases": [
        {
            "input": {
                "operation": "serialize_success_pagination",
                "pagination": "page",
                "total": 15,
                "count": 5,
                "perPage": 5,
                "currentPage": 2,
                "path": "http://api.test/articles",
                "query": {
                    "filter": "recent"
                }
            },
            "expected_output": "{\"pagination\":{\"count\":5,\"total\":15,\"perPage\":5,\"currentPage\":2,\"totalPages\":3,\"links\":{\"previous\":\"http://api.test/articles?filter=recent&page=1\",\"next\":\"http://api.test/articles?filter=recent&page=3\"}}}\n"
        }
    ]
}
```

---

### Feature 3: Included Resource Merging

**As a developer**, I want to merge included related resources into transformed data, so I can consume related payloads without duplicate data envelopes.

**Expected Behavior / Usage:**

The adapter accepts already transformed primary data and included relation payloads. Each included relation must be unwrapped from its own `data` envelope before being merged into the primary object under the relation name.

**Test Cases:** `rcb_tests/public_test_cases/feature3_included_resource_merging.json`

```json
{
    "description": "Merge side-loaded included resources into transformed data by removing each included resource envelope before attaching it by relation name.",
    "cases": [
        {
            "input": {
                "operation": "merge_included_resources",
                "data": {
                    "id": 1,
                    "title": "Hello"
                },
                "included": {
                    "author": {
                        "data": {
                            "id": 9,
                            "name": "Lin"
                        }
                    },
                    "comments": {
                        "data": [
                            {
                                "id": 4,
                                "body": "Nice"
                            }
                        ]
                    }
                }
            },
            "expected_output": "{\"id\":1,\"title\":\"Hello\",\"author\":{\"id\":9,\"name\":\"Lin\"},\"comments\":[{\"id\":4,\"body\":\"Nice\"}]}\n"
        }
    ]
}
```

---

### Feature 4: Error Payload Serialization

**As a developer**, I want to serialize structured error results, so I can return machine-readable error codes with human-readable context.

**Expected Behavior / Usage:**

The adapter accepts an error code, an optional message, and optional structured fields. Output is a top-level `error` object containing `code`, `message`, and any additional fields.

**Test Cases:** `rcb_tests/public_test_cases/feature4_error_payload_serialization.json`

```json
{
    "description": "Serialize error payloads with an error envelope containing a code, a message, and any additional structured fields.",
    "cases": [
        {
            "input": {
                "operation": "serialize_error",
                "code": "test_error",
                "message": "A test error has occured.",
                "data": {
                    "foo": 1
                }
            },
            "expected_output": "{\"error\":{\"code\":\"test_error\",\"message\":\"A test error has occured.\",\"foo\":1}}\n"
        }
    ]
}
```

---

### Feature 5: JSON HTTP Response Building

**As a developer**, I want to build framework JSON responses from success and error payloads, so I can verify both body data and framework-visible response metadata.

**Expected Behavior / Usage:**

The adapter accepts response data, HTTP status, headers, and optional body decorators. Output includes the framework-observable status code, selected headers, decoded body, and raw JSON content string. Decorators prepend status and success fields to the body in the order applied by the response factory chain.

**Test Cases:** `rcb_tests/public_test_cases/feature5_json_response_building.json`

```json
{
    "description": "Build JSON HTTP responses that preserve response body data, HTTP status codes, selected headers, and optional body decorators.",
    "cases": [
        {
            "input": {
                "operation": "build_success_response",
                "data": {
                    "foo": 1
                },
                "status": 201,
                "headers": {
                    "x-trace": "abc"
                },
                "decorators": [
                    "status",
                    "success"
                ]
            },
            "expected_output": "{\"status\":201,\"headers\":{\"x-trace\":\"abc\"},\"body\":{\"status\":201,\"success\":true,\"data\":{\"foo\":1}},\"content\":\"{\\\"status\\\":201,\\\"success\\\":true,\\\"data\\\":{\\\"foo\\\":1}}\"}\n"
        }
    ]
}
```

---

### Feature 6: HTTP Status Category Validation

**As a developer**, I want to reject status codes outside the response category, so I can avoid returning success responses with error statuses or error responses with success statuses.

**Expected Behavior / Usage:**

The adapter accepts a success or error response request with an HTTP status. Success responses only allow statuses from 100 through 399, while error responses only allow statuses from 400 through 599. Invalid categories print a normalized error line.

**Test Cases:** `rcb_tests/public_test_cases/feature6_status_validation_errors.json`

```json
{
    "description": "Reject HTTP status codes that do not match the response category being built and report the error as a normalized category.",
    "cases": [
        {
            "input": {
                "operation": "build_success_response",
                "data": {
                    "foo": 1
                },
                "status": 400
            },
            "expected_output": "error=invalid_status\n"
        },
        {
            "input": {
                "operation": "build_error_response",
                "code": "test_error",
                "message": "A test error has occured.",
                "status": 200
            },
            "expected_output": "error=invalid_status\n"
        }
    ]
}
```

---

### Feature 7: Cursor Pagination State

**As a developer**, I want to read and update cursor pagination state, so I can navigate cursor-based result sets without offset pagination.

**Expected Behavior / Usage:**

The adapter accepts cursor references and item arrays. Output exposes current, previous, and next cursor references, the raw items, and the collection contents. It can also replace the items and resolve cursor names through a configured resolver; without a resolver, cursor resolution emits a normalized error.

**Test Cases:** `rcb_tests/public_test_cases/feature7_cursor_paginator.json`

```json
{
    "description": "Expose cursor pagination references and paginated items, allow replacing items, and resolve cursor names through an optional resolver.",
    "cases": [
        {
            "input": {
                "operation": "cursor_paginator",
                "items": [
                    "foo",
                    "bar"
                ],
                "current": 2,
                "previous": 1,
                "next": 3
            },
            "expected_output": "{\"current\":2,\"previous\":1,\"next\":3,\"items\":[\"foo\",\"bar\"],\"collection\":[\"foo\",\"bar\"]}\n"
        }
    ]
}
```

---

### Feature 8: Resource Key Resolution

**As a developer**, I want to derive resource keys from data, so I can label transformed resources for sparse fieldsets and API metadata.

**Expected Behavior / Usage:**

The adapter accepts a data source category. It returns a resource key from an explicit binding, from the first model-like item in a list, from a model-provided resource name, from a model table name, or `[the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation]` when no key can be inferred.

**Test Cases:** `rcb_tests/public_test_cases/feature8_resource_key_resolution.json`

```json
{
    "description": "Resolve resource keys from explicit bindings, the first item in a list, model-provided resource names, model table names, or return [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] when no key can be inferred.",
    "cases": [
        {
            "input": {
                "operation": "resource_key",
                "dataType": "none"
            },
            "expected_output": "{\"[the resource key default value — ask the docs for the [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] representation]\":[the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation]}\n"
        }
    ]
}
```

---

### Feature 9: Resource Classification

**As a developer**, I want to classify input data into response resource types, so I can choose the correct transformation path for [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation], item, and collection data.

**Expected Behavior / Usage:**

The adapter accepts arbitrary JSON data and an optional resource key. Null data is classified as a [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] resource, scalar-object data as an item resource, and arrays of non-scalar objects as a collection resource. Output includes the resource type, resource key, and normalized data.

**Test Cases:** `rcb_tests/public_test_cases/feature9_resource_classification.json`

```json
{
    "description": "Classify normalized data as a [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] resource, a single item resource, or a collection resource while retaining the resource key and data.",
    "cases": [
        {
            "input": {
                "operation": "resource_type",
                "data": [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation],
                "[the resource key default value — ask the docs for the [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] representation]": "empty"
            },
            "expected_output": "{\"[the string literal used for [the string literal used for null resources — ask the PM for the exact string] resources — ask the PM for the exact string]\":\"[the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation]\",\"[the resource key default value — ask the docs for the [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] representation]\":\"empty\",\"data\":[the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation]}\n"
        }
    ]
}
```

---

### Feature 10: Sparse Field Transforming

**As a developer**, I want to filter transformed fields by resource key, so I can return only requested fields and reject ambiguous fieldsets.

**Expected Behavior / Usage:**

The adapter accepts item data, an optional resource key, requested includes, and sparse fieldsets. When a resource key is present, output contains only requested fields for that resource. When fieldsets are requested without a resource key, output is a normalized missing-resource-key error.

**Test Cases:** `rcb_tests/public_test_cases/feature10_sparse_field_transforming.json`

```json
{
    "description": "Transform item data with sparse fieldsets keyed by the resource type; nested requested relationships must remain available in parent and child fieldsets.",
    "cases": [
        {
            "input": {
                "operation": "transform_fieldsets",
                "[the resource key default value — ask the docs for the [the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation] representation]": "articles",
                "data": {
                    "id": 1,
                    "title": "Hello",
                    "body": "Long"
                },
                "fieldsets": [
                    "id",
                    "title"
                ]
            },
            "expected_output": "{\"data\":{\"id\":1,\"title\":\"Hello\"}}\n"
        },
        {
            "input": {
                "operation": "transform_fieldsets",
                "data": {
                    "id": 1
                },
                "fieldsets": [
                    "id"
                ]
            },
            "expected_output": "error=missing_resource_key\nfeature=sparse_fieldsets\n"
        }
    ]
}
```

---

### Feature 11: Domain HTTP Exception Contract

**As a developer**, I want to represent domain HTTP exceptions as neutral response data, so I can surface status and error code without leaking runtime exception classes.

**Expected Behavior / Usage:**

The adapter accepts a domain HTTP error type and optional constructor data. Output is a language-neutral object containing `error`, HTTP `status`, machine `code`, optional message, optional data, and headers.

**Test Cases:** `rcb_tests/public_test_cases/feature11_http_exception_contract.json`

```json
{
    "description": "Represent domain HTTP exceptions as neutral error response data with status, error code, optional message, optional data, and headers.",
    "cases": [
        {
            "input": {
                "operation": "http_exception",
                "type": "unauthenticated"
            },
            "expected_output": "{\"error\":\"http_exception\",\"status\":401,\"code\":\"unauthenticated\",\"message\":[the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation],\"data\":[the resource key default value — ask the docs for the [the string literal used for null resources — ask the PM for the exact string] representation],\"headers\":{}}\n"
        }
    ]
}
```

---

### Feature 12: Framework JSON Response Adapter

**As a developer**, I want to create framework-visible JSON responses, so I can ensure body, status code, and headers are observable through the response object.

**Expected Behavior / Usage:**

The adapter accepts response body data, a status code, and headers. Output includes the framework response status, selected headers, decoded body, and raw JSON content string.

**Test Cases:** `rcb_tests/public_test_cases/feature12_framework_json_response_adapter.json`

```json
{
    "description": "Create framework JSON responses that expose body content, status code, and headers through the framework response object.",
    "cases": [
        {
            "input": {
                "operation": "laravel_json_response",
                "data": {
                    "foo": 1
                },
                "status": 201,
                "headers": {
                    "x-foo": "1"
                }
            },
            "expected_output": "{\"status\":201,\"headers\":{\"x-foo\":\"1\"},\"body\":{\"foo\":1},\"content\":\"{\\\"foo\\\":1}\"}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The hidden evaluation cases live under `rcb_tests/test_cases/`, and the cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_success_payload_serialization.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_success_payload_serialization@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- follow the error formatting pattern used in C010 and C015
- reference the cursor pagination keys defined in C005 and C012
