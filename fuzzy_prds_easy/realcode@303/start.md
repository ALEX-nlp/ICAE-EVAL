## Product Requirement Document

# HTTP/JSON Transcoding Toolkit - Declarative Route and Message Translation

## Project Goal

Build a protocol transcoding toolkit that allows developers to expose HTTP/JSON endpoints backed by typed RPC-style messages, route incoming requests by declarative path patterns, and translate request and response payloads without hand-writing repetitive parsing and serialization glue.

---

## Background & Problem

Without this library/tool, developers are forced to manually parse URL paths, decode path and query parameters, merge those values into typed request messages, validate streaming request shapes, frame or unframe binary messages, and convert response messages back to JSON. This leads to duplicated routing code, inconsistent escaping behavior, error-prone payload handling, and fragile streaming integrations.

With this library/tool, developers define path patterns and message schemas once, then rely on a reusable engine to select the correct route, extract bindings, translate JSON requests into typed messages, and render typed responses as JSON in both unary and streaming flows.

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

### Feature 1: Path Pattern Parsing

**As a developer**, I want to parse declarative HTTP path patterns, so I can inspect whether a pattern is valid and understand the segments, variables, and optional terminal action suffix it defines.

**Expected Behavior / Usage:**

The adapter receives an input object with `operation` set to `parse_template` and a `template` string. A valid pattern must start with `/`, must not contain empty path segments, must not attach variable expressions inside a literal segment, and may include literal segments, `*`, `**`, `{field}`, `{field=*}`, `{field=literal/*}`, `{field=literal/**}`, and an optional `:suffix` at the end of the final segment. The output reports `valid=true`, a comma-separated `segments` line where variables are expanded into their matching segment pattern, a `verb` line containing the terminal suffix without the colon, and a `variables` line listing each variable as `field.path[start:end:single|multi]`. Invalid patterns produce only `valid=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_template_parsing.json`

```json
{
    "description": "Parse HTTP-style path patterns into matchable segments, variables, and optional terminal action suffixes; malformed patterns are rejected.",
    "cases": [
        {
            "input": {
                "operation": "parse_template",
                "template": "/shelves/{shelf}/books/{book}"
            },
            "expected_output": "valid=true\nsegments=shelves,*,books,*\nverb=\nvariables=shelf[1:2:single];book[3:4:single]\n"
        },
        {
            "input": {
                "operation": "parse_template",
                "template": "/a{x}"
            },
            "expected_output": "valid=false\n"
        }
    ]
}
```

---

### Feature 2: HTTP Route Matching

**As a developer**, I want registered HTTP method/path patterns to be matched against incoming requests, so I can dispatch each request to the correct route only when the full request path is accepted.

**Expected Behavior / Usage:**

The adapter receives an input object with `operation` set to `match_request`, a `routes` array, and request `method`, `path`, and `query` fields. Each route has a `method` and `template`, plus optional body and system-parameter metadata. Matching is method-sensitive and must consume the entire path after ignoring any query string embedded in the path. `*` matches exactly one path segment, `**` matches the remaining path, and exact or more specific registered routes win over wildcard routes. A successful match prints `matched=true`, the zero-based `route_index`, the matched `body` target, and any extracted `bindings`; a failed match prints only `matched=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_route_matching.json`

```json
{
    "description": "Select the registered route whose HTTP method and path pattern fully match the request, preferring exact and more specific patterns over wildcards and rejecting partial matches.",
    "cases": [
        {
            "input": {
                "operation": "match_request",
                "routes": [
                    {
                        "method": "GET",
                        "template": "/a/**"
                    },
                    {
                        "method": "GET",
                        "template": "/b/*"
                    },
                    {
                        "method": "GET",
                        "template": "/c/*/d/**"
                    },
                    {
                        "method": "GET",
                        "template": "/c/*/d/e"
                    },
                    {
                        "method": "GET",
                        "template": "/c/f/d/e"
                    }
                ],
                "method": "GET",
                "path": "/c/f/d/e",
                "query": ""
            },
            "expected_output": "matched=true\nroute_index=4\nbody=\nbindings=\n"
        },
        {
            "input": {
                "operation": "match_request",
                "routes": [
                    {
                        "method": "GET",
                        "template": "/a/b"
                    }
                ],
                "method": "POST",
                "path": "/a/b",
                "query": ""
            },
            "expected_output": "matched=false\n"
        }
    ]
}
```

---

### Feature 3: Variable and Query Binding

**As a developer**, I want path and query values to be extracted into named bindings, so I can populate request fields from URL data consistently.

**Expected Behavior / Usage:**

The adapter receives a route-matching input whose templates contain variables and whose query string may contain additional field assignments. For a successful match, output `bindings` as semicolon-separated `field.path=value` pairs in extraction order: path variables first, then non-system query parameters. Single-segment captures decode all percent-escaped characters. Multi-segment captures decode unreserved characters by default while preserving reserved characters such as encoded slashes, unless the input `unescape` mode requests a broader decoding policy. Query parameter values are fully percent-decoded, and configured system parameters are ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature3_variable_binding.json`

```json
{
    "description": "Extract named values from matched path variables and query parameters, decoding percent-escaped values according to whether the capture spans one path segment or multiple segments.",
    "cases": [
        {
            "input": {
                "operation": "match_request",
                "routes": [
                    {
                        "method": "GET",
                        "template": "/a/{x}/c/d/e"
                    },
                    {
                        "method": "GET",
                        "template": "/{x=a/*}/b/{y=*}/c"
                    }
                ],
                "method": "GET",
                "path": "/a/hello/b/world/c",
                "query": ""
            },
            "expected_output": "matched=true\nroute_index=1\nbody=\nbindings=x=a/hello;y=world\n"
        },
        {
            "input": {
                "operation": "match_request",
                "routes": [
                    {
                        "method": "GET",
                        "template": "/a/{x}/b",
                        "system_params": [
                            "key",
                            "api_key"
                        ]
                    }
                ],
                "method": "GET",
                "path": "/a/hello/b",
                "query": "y=world&api_key=secret"
            },
            "expected_output": "matched=true\nroute_index=0\nbody=\nbindings=x=hello;y=world\n"
        }
    ]
}
```

---

### Feature 4: Terminal Action Suffix Matching

**As a developer**, I want configured colon suffixes at the end of path patterns to behave as terminal action selectors, so I can distinguish action-style routes from ordinary path text.

**Expected Behavior / Usage:**

The adapter receives a route-matching input with one or more patterns ending in `:suffix`. If the requested path ends with a configured suffix after the last slash, that suffix is treated as an extra terminal segment for matching and is not part of the captured value. If the suffix text is not configured for any registered pattern, the colon and following text remain part of the normal path segment. Colon text before the final slash also remains normal path content.

**Test Cases:** `rcb_tests/public_test_cases/feature4_terminal_action_matching.json`

```json
{
    "description": "Treat a configured colon suffix at the end of a path as a terminal action segment, while leaving unconfigured colon text as normal path content.",
    "cases": [
        {
            "input": {
                "operation": "match_request",
                "routes": [
                    {
                        "method": "GET",
                        "template": "/some/const:verb"
                    },
                    {
                        "method": "GET",
                        "template": "/some/*:verb"
                    },
                    {
                        "method": "GET",
                        "template": "/other/**:verb"
                    },
                    {
                        "method": "GET",
                        "template": "/other/**/const:verb"
                    }
                ],
                "method": "GET",
                "path": "/other/bar/foo/const:verb",
                "query": ""
            },
            "expected_output": "matched=true\nroute_index=3\nbody=\nbindings=\n"
        },
        {
            "input": {
                "operation": "match_request",
                "routes": [
                    {
                        "method": "GET",
                        "template": "/foo/{a=*}"
                    }
                ],
                "method": "GET",
                "path": "/foo/other:verb",
                "query": ""
            },
            "expected_output": "matched=true\nroute_index=0\nbody=\nbindings=a=other:verb\n"
        }
    ]
}
```

---

### Feature 5: JSON Request Translation

**As a developer**, I want JSON request bodies to be translated into typed request messages, so HTTP clients can send JSON while the backend receives structured message data.

**Expected Behavior / Usage:**

The adapter receives an input object with `operation` set to `json_to_proto`, a neutral `schema` name, a JSON payload string in `json`, and optional `body_target` plus URL-derived `bindings`. Object fields are mapped into the target schema, lower-camel JSON field names map to their structured field names, unknown JSON fields are ignored, and scalar JSON can be assigned to a scalar `body_target`. When `body_target` points to a nested message field, the body is inserted under that field; bindings are then merged into the produced request message. Each translated message is printed as `message[index]=`, followed by a stable text representation and `--end--`; successful completion ends with `finished=true`. Invalid JSON prints `error=invalid_json`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_json_request_translation.json`

```json
{
    "description": "Translate JSON request bodies into typed request messages, optionally placing body content under a configured field and merging URL-derived bindings.",
    "cases": [
        {
            "input": {
                "operation": "json_to_proto",
                "schema": "shelf",
                "json": "{ \"name\" : \"1\", \"theme\" : \"Russian\" }"
            },
            "expected_output": "message[0]=\nname: \"1\"\ntheme: \"Russian\"\n--end--\nfinished=true\n"
        },
        {
            "input": {
                "operation": "json_to_proto",
                "schema": "create_book_request",
                "body_target": "book",
                "bindings": [
                    {
                        "field_path": [
                            "book",
                            "authorInfo",
                            "firstName"
                        ],
                        "value": "Leo"
                    },
                    {
                        "field_path": [
                            "book",
                            "authorInfo",
                            "lastName"
                        ],
                        "value": "Tolstoy"
                    }
                ],
                "json": "{ \"name\" : \"11\", \"author\" : \"Leo Tolstoy\", \"title\" : \"Anna Karenina\" }"
            },
            "expected_output": "message[0]=\nbook {\n  author: \"Leo Tolstoy\"\n  name: \"11\"\n  title: \"Anna Karenina\"\n  author_info {\n    first_name: \"Leo\"\n    last_name: \"Tolstoy\"\n  }\n}\n--end--\nfinished=true\n"
        },
        {
            "input": {
                "operation": "json_to_proto",
                "schema": "shelf",
                "json": "Invalid"
            },
            "expected_output": "error=invalid_json\n"
        }
    ]
}
```

---

### Feature 6: Streaming JSON Request Translation

**As a developer**, I want a JSON array request body to be translated into a stream of typed request messages, so client-streaming calls can be driven by one JSON array payload.

**Expected Behavior / Usage:**

The adapter receives a `json_to_proto` input with `streaming=true`. The payload must be a JSON array. Each element becomes one output message using the same schema, body-target, and binding rules as unary request translation. Array elements may themselves be scalars, objects, or repeated-field arrays depending on the configured body target. An empty input array produces no `message[...]` blocks and still ends with `finished=true`. A non-array streaming payload prints `error=invalid_json`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_streaming_json_request_translation.json`

```json
{
    "description": "Translate a JSON array input as a stream of request messages, including scalar and repeated-field body targets, and reject non-array input in streaming mode.",
    "cases": [
        {
            "input": {
                "operation": "json_to_proto",
                "schema": "shelf",
                "streaming": true,
                "json": "[{ \"name\" : \"1\", \"theme\" : \"Russian\" }, { \"name\" : \"2\", \"theme\" : \"History\" }, { \"name\" : \"3\", \"theme\" : \"Mistery\" }]"
            },
            "expected_output": "message[0]=\nname: \"1\"\ntheme: \"Russian\"\n--end--\nmessage[1]=\nname: \"2\"\ntheme: \"History\"\n--end--\nmessage[2]=\nname: \"3\"\ntheme: \"Mistery\"\n--end--\nfinished=true\n"
        },
        {
            "input": {
                "operation": "json_to_proto",
                "schema": "shelf",
                "streaming": true,
                "json": "{\"name\":\"1\"}"
            },
            "expected_output": "error=invalid_json\n"
        }
    ]
}
```

---

### Feature 7: Binary Response to JSON Translation

**As a developer**, I want framed binary response messages to be translated into JSON, so HTTP clients can receive canonical JSON responses from typed backend messages.

**Expected Behavior / Usage:**

The adapter receives an input object with `operation` set to `proto_to_json`, a neutral `schema` name, and a `messages` array whose elements contain text-form message data used by the adapter to create framed binary inputs. In unary mode, the translated JSON object is printed as `json=<canonical-json>`. Nested message fields are rendered as nested JSON objects, integer values that require string representation are emitted as JSON strings, and default primitive values are omitted unless `always_print_primitive_fields=true` is provided.

**Test Cases:** `rcb_tests/public_test_cases/feature7_proto_response_translation.json`

```json
{
    "description": "Translate framed binary response messages into JSON objects, preserving nested data and optionally printing primitive default values.",
    "cases": [
        {
            "input": {
                "operation": "proto_to_json",
                "schema": "shelf",
                "messages": [
                    {
                        "proto_text": "name : \"1\" theme : \"History\""
                    }
                ]
            },
            "expected_output": "json={\"name\":\"1\",\"theme\":\"History\"}\n"
        },
        {
            "input": {
                "operation": "proto_to_json",
                "schema": "shelf",
                "always_print_primitive_fields": true,
                "messages": [
                    {
                        "proto_text": ""
                    }
                ]
            },
            "expected_output": "json={\"name\":\"\",\"theme\":\"\"}\n"
        }
    ]
}
```

---

### Feature 8: Streaming Binary Response to JSON Translation

**As a developer**, I want a stream of framed binary response messages to be translated into a single JSON array, so server-streaming responses are exposed as valid JSON arrays with robust frame validation.

**Expected Behavior / Usage:**

The adapter receives a `proto_to_json` input with `streaming=true`. Each framed message is translated to one JSON array element; no messages produce `json=[]`. If raw malformed frame bytes are supplied through `raw_frame`, frame errors are normalized to language-neutral categories: `error=incomplete_frame_header`, `error=unsupported_frame_flag`, or `error=incomplete_frame`. Error output must not include host-language exception names or runtime-specific messages.

**Test Cases:** `rcb_tests/public_test_cases/feature8_streaming_proto_response_translation.json`

```json
{
    "description": "Translate a stream of framed binary response messages into one JSON array and report malformed frame errors using neutral error categories.",
    "cases": [
        {
            "input": {
                "operation": "proto_to_json",
                "schema": "shelf",
                "streaming": true,
                "messages": [
                    {
                        "proto_text": "name : \"1\" theme : \"History\""
                    },
                    {
                        "proto_text": "name : \"2\" theme : \"Mistery\""
                    },
                    {
                        "proto_text": "name : \"3\" theme : \"Russian\""
                    }
                ]
            },
            "expected_output": "json=[{\"name\":\"1\",\"theme\":\"History\"},{\"name\":\"2\",\"theme\":\"Mistery\"},{\"name\":\"3\",\"theme\":\"Russian\"}]\n"
        },
        {
            "input": {
                "operation": "proto_to_json",
                "schema": "shelf",
                "streaming": true,
                "raw_frame": "0a"
            },
            "expected_output": "error=incomplete_frame_header\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_template_parsing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_template_parsing@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the dot-dot-dot separator pattern from the inner core module
- apply the url-encoding rules defined in the transport layer parsing step
