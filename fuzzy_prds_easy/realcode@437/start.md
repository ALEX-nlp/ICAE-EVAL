## Product Requirement Document

# OpenAPI Contract Code Generator - API-to-Code Behavior Contracts

## Project Goal

Build an OpenAPI contract code generator that allows developers to produce API models, HTTP clients, and server routing adapters from API descriptions without hand-writing repetitive serialization, request mapping, and routing glue.

---

## Background & Problem

Without this tool, developers are forced to manually mirror API descriptions across model classes, JSON mappers, HTTP clients, and server bindings. This leads to repetitive code, drift between the contract and implementation, inconsistent error handling, and fragile maintenance whenever the API description changes.

With this tool, developers provide an API description and receive generated artifacts whose externally observable behavior follows the declared schema, wire-format, client, and server contracts.

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
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (for example, specific domain error types or result patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: YAML Quoted Enum Preservation

**As a developer**, I want to preserve quoted enum strings while reading or merging YAML API fragments, so I can reuse author-provided enum wire values safely.

**Expected Behavior / Usage:**

Quoted string values inside enum arrays must remain JSON strings after YAML parsing and after merging two YAML trees. The adapter accepts YAML text and a target field name, then prints whether the target value is an array and the JSON rendering of its first value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_yaml_quoted_enum.json`

```json
{
    "description": "YAML parsing and YAML tree merging preserve quoted string enum values as JSON strings instead of converting them to bare tokens.",
    "cases": [
        {
            "input": {
                "feature": "yaml_quote_preservation",
                "operation": "read",
                "yaml": "ValidPreferentialCountries:\n  type: \"string\"\n  x-extensible-enum:\n    - \"NO\"",
                "field": "x-extensible-enum"
            },
            "expected_output": "is_array=[a specific boolean literal — ask the PM for the exact output format]\nfirst_value_json=\"NO\"\n"
        },
        {
            "input": {
                "feature": "yaml_quote_preservation",
                "operation": "merge",
                "yaml": "ValidPreferentialCountries:\n  type: \"string\"\n  x-extensible-enum:\n    - \"NO\"",
                "field": "x-extensible-enum"
            },
            "expected_output": "is_array=[a specific boolean literal — ask the PM for the exact output format]\nfirst_value_json=\"NO\"\n"
        }
    ]
}
```

---

### Feature 2: YAML Anchor and Alias Detection

**As a developer**, I want to detect whether YAML uses both anchors and aliases, so I can decide when alias expansion behavior is required.

**Expected Behavior / Usage:**

YAML text must be classified as using reusable aliases only when it contains at least one anchor definition and at least one alias reference. Anchor-only, alias-only, and plain YAML inputs must be reported as not containing both signals.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_yaml_anchor_alias_detection.json`

```json
{
    "description": "YAML text is classified as using reusable anchors only when at least one anchor definition and one alias reference are both present.",
    "cases": [
        {
            "input": {
                "feature": "yaml_alias_detection",
                "yaml": "openapi: \"3.0.0\"\ninfo:\n  title: Test\n  version: \"1.0\"\npaths: {}\ncomponents:\n  schemas:\n    AnchorOwner:\n      type: object\n      properties:\n        status:\n          type: string\n          enum: &status_values\n            - Active\n            - Inactive\n    AliasConsumer:\n      type: object\n      properties:\n        status:\n      type: string\n      enum: *status_values"
            },
            "expected_output": "contains_anchor_and_alias=[a specific boolean literal — ask the PM for the exact output format]\n"
        },
        {
            "input": {
                "feature": "yaml_alias_detection",
                "yaml": "openapi: \"3.0.0\"\ninfo:\n  title: Test\n  version: \"1.0\"\npaths: {}\ncomponents:\n  schemas:\n    AnchorOwner:\n      type: object\n      properties:\n        status:\n          type: string\n          enum: &status_values\n            - Active\n            - Inactive"
            },
            "expected_output": "contains_anchor_and_alias=false\n"
        }
    ]
}
```

---

### Feature 3: YAML Alias Enum Resolution

**As a developer**, I want to resolve schema enum values supplied through YAML aliases, so I can treat aliased reusable definitions the same as inline definitions.

**Expected Behavior / Usage:**

When an API schema property receives its enum values from a YAML alias, parsing must expose the resolved list of enum values in original order. The adapter accepts YAML text plus the target schema and property names, then prints the comma-separated resolved enum values.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_yaml_alias_enum_resolution.json`

```json
{
    "description": "When a schema enum is supplied through a YAML alias, the parser exposes the resolved enum values in their original order.",
    "cases": [
        {
            "input": {
                "feature": "yaml_alias_enum_resolution",
                "yaml": "openapi: \"3.0.0\"\ninfo:\n  title: Test\n  version: \"1.0\"\npaths: {}\ncomponents:\n  schemas:\n    AnchorOwner:\n      type: object\n      properties:\n        status:\n          type: string\n          enum: &status_values\n            - Active\n            - Inactive\n            - Pending\n    AliasConsumer:\n      type: object\n      properties:\n        status:\n          type: string\n          enum: *status_values",
                "schema": "AliasConsumer",
                "property": "status"
            },
            "expected_output": "enum_values=\n"
        }
    ]
}
```

---

### Feature 4: OpenAPI Encoding Metadata Acceptance

**As a developer**, I want to accept request-body encoding metadata in API documents, so I can support multipart or encoded payload descriptions without rejecting valid contracts.

**Expected Behavior / Usage:**

An API description containing request-body encoding metadata for a binary property must parse as a valid API document. The adapter accepts the document text and prints the validation flag.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_openapi_encoding_validation.json`

```json
{
    "description": "An OpenAPI document with request-body encoding metadata for a binary property is accepted as a valid API description.",
    "cases": [
        {
            "input": {
                "feature": "openapi_encoding_validation",
                "yaml": "openapi: 3.0.1\ninfo:\n  title: Sample API\n  version: \"1.0\"\npaths:\n  /endpoint:\n    post:\n      requestBody:\n        required: [a specific boolean literal — ask the PM for the exact output format]\n        content:\n          application/json:\n            schema:\n              type: object\n              properties:\n                image:\n                  type: string\n                  format: binary\n            encoding:\n              image:\n                contentType: image/png, image/jpeg, image/webp\n      responses:\n        200:\n          description: Everything OK"
            },
            "expected_output": "is_valid=[a specific boolean literal — ask the PM for the exact output format]\n"
        }
    ]
}
```

---

### Feature 5: Primitive JSON Serialization

**As a developer**, I want to serialize models containing primitive and formatted values to JSON, so I can produce stable wire payloads for common scalar and array formats.

**Expected Behavior / Usage:**

A model containing integer widths, booleans, strings, UUIDs, URIs, date, date-time, high-precision decimal numbers, floating-point numbers, binary data, string arrays, and UUID arrays must serialize to JSON using the expected field names and wire-format values. Binary values are emitted as base64 strings.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_primitive_json_serialization.json`

```json
{
    "description": "A model containing primitive, string-format, binary, numeric, and array values serializes to JSON with the expected field names and wire values.",
    "cases": [
        {
            "input": {
                "feature": "model_primitive_serialization"
            },
            "expected_output": "{\n  \"integer\" : 1,\n  \"integer32\" : 2147483647,\n  \"integer64\" : 9223372036854775807,\n  \"boolean\" : [a specific boolean literal — ask the PM for the exact output format],\n  \"string\" : \"example\",\n  \"stringUuid\" : \"123e4567-e89b-12d3-a456-426614174000\",\n  \"stringUri\" : \"https://example.org\",\n  \"stringDate\" : \"2020-02-04\",\n  \"stringDateTime\" : \"2024-11-04T12:00:00Z\",\n  \"number\" : 109288282772724.4225837838838383888,\n  \"numberFloat\" : 1.23,\n  \"numberDouble\" : 4.56,\n  \"byte\" : \"AETdqhOI3C8/jA184vF3FyUNGesJ9x22cn2TqiQLYpFzvy5Moyie3K1MAy8DVy62HxURtRHwP2SjdV7B+HZQzuCwMsJLxhbNj0okOzdV2EOAr2JV3htYH+vNVJE9NHwzyYTkOA5ZuYpEDZMEL+SqjyeSRXaLimqDbkew6hg1QdU=\",\n  \"binary\" : \"AETdqhOI3C8/jA184vF3FyUNGesJ9x22cn2TqiQLYpFzvy5Moyie3K1MAy8DVy62HxURtRHwP2SjdV7B+HZQzuCwMsJLxhbNj0okOzdV2EOAr2JV3htYH+vNVJE9NHwzyYTkOA5ZuYpEDZMEL+SqjyeSRXaLimqDbkew6hg1QdU=\",\n  \"arrayOfString\" : [ \"one\", \"two\", \"three\" ],\n  \"arrayOfUuid\" : [ \"123e4567-e89b-12d3-a456-426614174000\", \"123e4567-e89b-12d3-a456-426614174001\" ]\n}\n"
        }
    ]
}
```

---

### Feature 6: Primitive JSON Deserialization

**As a developer**, I want to deserialize primitive and formatted JSON values without loss, so I can read incoming payloads into typed values while preserving identity and precision.

**Expected Behavior / Usage:**

JSON containing primitive, formatted, binary, numeric, and array fields must deserialize without losing significant values. The adapter prints each parsed scalar, the decoded byte lengths for binary fields, and comma-separated array contents.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_primitive_json_deserialization.json`

```json
{
    "description": "JSON containing primitive, string-format, binary, numeric, and array values deserializes into values without losing precision, identity, or decoded binary length.",
    "cases": [
        {
            "input": {
                "feature": "model_primitive_deserialization",
                "json": "{\n  \"integer\" : 1,\n  \"integer32\" : 2147483647,\n  \"integer64\" : 9223372036854775807,\n  \"boolean\" : [a specific boolean literal — ask the PM for the exact output format],\n  \"string\" : \"example\",\n  \"stringUuid\" : \"123e4567-e89b-12d3-a456-426614174000\",\n  \"stringUri\" : \"https://example.org\",\n  \"stringDate\" : \"2020-02-04\",\n  \"stringDateTime\" : \"2024-11-04T12:00:00Z\",\n  \"number\" : 109288282772724.4225837838838383888,\n  \"numberFloat\" : 1.23,\n  \"numberDouble\" : 4.56,\n  \"byte\" : \"AETdqhOI3C8/jA184vF3FyUNGesJ9x22cn2TqiQLYpFzvy5Moyie3K1MAy8DVy62HxURtRHwP2SjdV7B+HZQzuCwMsJLxhbNj0okOzdV2EOAr2JV3htYH+vNVJE9NHwzyYTkOA5ZuYpEDZMEL+SqjyeSRXaLimqDbkew6hg1QdU=\",\n  \"binary\" : \"AETdqhOI3C8/jA184vF3FyUNGesJ9x22cn2TqiQLYpFzvy5Moyie3K1MAy8DVy62HxURtRHwP2SjdV7B+HZQzuCwMsJLxhbNj0okOzdV2EOAr2JV3htYH+vNVJE9NHwzyYTkOA5ZuYpEDZMEL+SqjyeSRXaLimqDbkew6hg1QdU=\",\n  \"arrayOfString\" : [ \"one\", \"two\", \"three\" ],\n  \"arrayOfUuid\" : [ \"123e4567-e89b-12d3-a456-426614174000\", \"123e4567-e89b-12d3-a456-426614174001\" ]\n}"
            },
            "expected_output": "integer=1\ninteger32=2147483647\ninteger64=9223372036854775807\nboolean=[a specific boolean literal — ask the PM for the exact output format]\nstring=example\nstringUuid=123e4567-e89b-12d3-a456-426614174000\nstringUri=https://example.org\nstringDate=2020-02-04\nstringDateTime=2024-11-04T12:00Z\nnumber=109288282772724.4225837838838383888\nnumberFloat=1.23\nnumberDouble=4.56\nbyte_length=128\nbinary_length=128\narrayOfString=one,two,three\narrayOfUuid=123e4567-e89b-12d3-a456-426614174000,123e4567-e89b-12d3-a456-426614174001\n"
        }
    ]
}
```

---

### Feature 7: Enum JSON Mapping

**As a developer**, I want to map enum-like values to their JSON wire values, so I can handle closed enum values, extensible strings, references, and enum arrays consistently.

**Expected Behavior / Usage:**

Enum-like fields must serialize to their defined JSON wire strings and deserialize back from those strings. Extensible enum fields must allow arbitrary string values. Arrays and lists of enum values must preserve their wire values and order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_enum_json_mapping.json`

```json
{
    "description": "Enum-like model fields serialize to and deserialize from their defined JSON wire values, including extensible string values and arrays of enum values.",
    "cases": [
        {
            "input": {
                "feature": "model_enum_serialization",
                "variant": "array"
            },
            "expected_output": "{\n  \"array_of_enums\" : [ \"a\", \"b\", \"c\" ],\n  \"inlined_enum\" : null,\n  \"inlined_extensible_enum\" : null,\n  \"enum_ref\" : null,\n  \"extensible_enum_ref\" : null,\n  \"list_enums\" : null\n}\n"
        },
        {
            "input": {
                "feature": "model_enum_serialization",
                "variant": "inlined"
            },
            "expected_output": "{\n  \"array_of_enums\" : null,\n  \"inlined_enum\" : \"inlined_one\",\n  \"inlined_extensible_enum\" : null,\n  \"enum_ref\" : null,\n  \"extensible_enum_ref\" : null,\n  \"list_enums\" : null\n}\n"
        }
    ]
}
```

---

### Feature 8: Unique and Non-Unique Array Deserialization

**As a developer**, I want to honor uniqueness semantics when reading arrays, so I can deduplicate only the arrays declared unique while preserving order.

**Expected Behavior / Usage:**

Arrays declared as unique collections must remove duplicate entries during deserialization while preserving the order of each first occurrence. Arrays not declared unique must keep all supplied entries.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_unique_array_deserialization.json`

```json
{
    "description": "Arrays declared as unique collections deserialize with duplicate entries removed while preserving first-seen order; non-unique arrays preserve all supplied entries.",
    "cases": [
        {
            "input": {
                "feature": "model_array_uniqueness",
                "json": "{\n  \"unique_objects\" : [ {\n    \"one\" : \"first\"\n  }, {\n    \"one\" : \"second\"\n  }, {\n    \"one\" : \"third\"\n  }, {\n    \"one\" : \"fourth\"\n  }, {\n    \"one\" : \"fifth\"\n  }, {\n    \"one\" : \"sixth\"\n  } ]\n}"
            },
            "expected_output": "unique_objects=first,second,third,fourth,fifth,sixth\n"
        },
        {
            "input": {
                "feature": "model_array_uniqueness",
                "json": "{\n  \"unique_ints\" : [ 6, 5, 4, 3, 2, 1 ]\n}"
            },
            "expected_output": "unique_ints=6,5,4,3,2,1\n"
        }
    ]
}
```

---

### Feature 9: Map JSON Serialization

**As a developer**, I want to serialize map-shaped model properties with dynamic keys, so I can represent additional object properties accurately on the wire.

**Expected Behavior / Usage:**

String maps, typed-object maps, nested object maps, and unknown-value maps must serialize as JSON objects. Dynamic keys must be retained exactly, and nested values must preserve their scalar or object structure.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_map_json_serialization.json`

```json
{
    "description": "String maps, typed object maps, nested object maps, and unknown-value maps serialize as JSON objects while retaining dynamic keys and nested value structure.",
    "cases": [
        {
            "input": {
                "feature": "model_map_serialization",
                "variant": "string"
            },
            "expected_output": "{\n  \"wild_card\" : null,\n  \"string_map\" : {\n    \"Key 1\" : \"Value 1\",\n    \"Key 2\" : \"Value 2\"\n  },\n  \"typed_object_map\" : null,\n  \"object_map\" : null,\n  \"inlined_string_map\" : null,\n  \"inlined_object_map\" : null,\n  \"inlined_unknown_map\" : null,\n  \"inlined_typed_object_map\" : null,\n  \"complex_object_with_untyped_map\" : null,\n  \"complex_object_with_typed_map\" : null,\n  \"inlined_complex_object_with_untyped_map\" : null,\n  \"inlined_complex_object_with_typed_map\" : null\n}\n"
        }
    ]
}
```

---

### Feature 10: HTTP Client Request Mapping

**As a developer**, I want to translate operation inputs into real HTTP requests, so I can call remote APIs using the declared method, path, query, header, and body contract.

**Expected Behavior / Usage:**

The generated HTTP client layer must create real HTTP requests from operation inputs. The observable request must include the expected method, routed path, query parameters, headers, and JSON request body. Optional query values are omitted when not supplied and included when present.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_http_client_request_mapping.json`

```json
{
    "description": "Generated HTTP clients translate operation inputs into real HTTP requests with the expected method, path, query parameters, headers, and JSON body.",
    "cases": [
        {
            "input": {
                "feature": "http_client_request_mapping",
                "operation": "create_item"
            },
            "expected_output": "result=success\nmethod=POST\nurl=/catalogs/catalog-a/items?randomNumber=123\nheader_X-Request-ID=request-id\nbody={\"id\":\"id-1\",\"name\":\"item-a\",\"description\":\"description-a\",\"price\":123.45}\n"
        },
        {
            "input": {
                "feature": "http_client_request_mapping",
                "operation": "search"
            },
            "expected_output": "result=success\nmethod=GET\nurl=/catalogs/catalog-a/search?query=query&page=10&sort=desc\nheader_X-Tracing-ID=request-id-123\n"
        }
    ]
}
```

---

### Feature 11: HTTP Client Result Mapping

**As a developer**, I want to convert HTTP responses into success or failure results, so I can handle normal responses, empty responses, HTTP errors, and malformed payloads predictably.

**Expected Behavior / Usage:**

The generated HTTP client layer must classify successful HTTP responses as success results and expose response data when a body is expected. Empty success responses must produce a unit-style success signal. Non-success HTTP statuses must produce an HTTP failure containing status code, status description, and optional response body. Successful responses that cannot be deserialized must produce a serialization failure.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_http_client_result_mapping.json`

```json
{
    "description": "Generated HTTP clients convert HTTP responses into success or failure results using status code, status text, optional body content, and deserialization outcome.",
    "cases": [
        {
            "input": {
                "feature": "http_client_result_mapping",
                "operation": "create_item",
                "status": 200,
                "body": "{\"id\":\"id-1\",\"name\":\"item-a\",\"description\":\"description-a\",\"price\":123.45}"
            },
            "expected_output": "result=success\nid=id-1\nname=item-a\ndescription=description-a\nprice=123.45\n"
        },
        {
            "input": {
                "feature": "http_client_result_mapping",
                "operation": "no_content",
                "status": 204
            },
            "expected_output": "result=success\ndata=unit\n"
        }
    ]
}
```

---

### Feature 12: HTTP Server Routing

**As a developer**, I want to route HTTP requests through generated server bindings, so I can parse incoming HTTP data and expose framework-visible response behavior.

**Expected Behavior / Usage:**

The generated server routing layer must parse JSON request bodies, headers, and query parameters before invoking application handlers. Responses must expose framework-visible status code and body signals. Bad request-body conversion and bad query-parameter conversion must return normalized error categories, while missing route responses must surface the HTTP not-found behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_http_server_routing.json`

```json
{
    "description": "Generated server routing parses request bodies, headers, and query parameters, returns declared response status and body content, and surfaces bad request or missing response statuses through the HTTP layer.",
    "cases": [
        {
            "input": {
                "feature": "http_server_routing",
                "route_group": "events",
                "request": {
                    "method": "POST",
                    "path": "/internal/events",
                    "headers": {
                        "Authorization": "Basic dGVzdDp0ZXN0",
                        "Content-Type": "application/json"
                    },
                    "body": "{\"entities\":[{\"id\":\"1\",\"properties\":{\"entity1PropKey\":\"entity1PropValue\"}}],\"properties\":{\"propKey\":\"propValue\"}}"
                }
            },
            "expected_output": "status=200\nbody={\"change_events\":[{\"entity_id\":\"entityId\",\"data\":{\"dataKey\":1,\"otherDataKey\":\"value\"}}]}\nentities=1\nentity0_properties=entity1PropKey=entity1PropValue\nproperties=propKey=propValue\n"
        },
        {
            "input": {
                "feature": "http_server_routing",
                "route_group": "contributors",
                "request": {
                    "method": "GET",
                    "path": "/contributors?limit=10",
                    "headers": {
                        "X-Flow-Id": "testValue"
                    }
                }
            },
            "expected_output": "status=200\nbody={\"prev\":null,\"next\":null,\"items\":[]}\nx_flow_id=testValue\nlimit=10\n"
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
- follow the exact field join strategy used in the YAML parser module
