## Product Requirement Document

# GraphQL Service Composition Adapter - HTTP, Schema, Data Loading, and Error Contracts

## Project Goal

Build a GraphQL service composition toolkit that allows developers to combine multiple data sources behind one HTTP GraphQL endpoint, expose development tooling, prepare outbound REST calls, reuse cached GET data, and render structured errors without writing repetitive middleware, schema assembly, request configuration, and error formatting code by hand.

---

## Background & Problem

Without this library/tool, developers are forced to manually create HTTP routes, combine GraphQL schemas and resolvers, attach per-request data-source context, load development-only sources, prepare REST request options, handle cache reads and writes, and sanitize service errors for clients. This leads to repetitive boilerplate, inconsistent endpoint behavior, error-prone cache handling, and inconsistent error payloads across services.

With this library/tool, a service can declare its data sources and use a shared composition layer that produces the HTTP-facing GraphQL behavior, runtime context, outbound request behavior, and normalized client/server error signals in a consistent way.

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

### Feature 1: GraphQL HTTP Endpoint Runtime Modes

**As a developer**, I want one HTTP GraphQL endpoint to execute root query and mutation operations in both mock and live runtime modes, so I can use the same route d[a specific default configuration object]ng development and production while receiving mode-appropriate data.

**Expected Behavior / Usage:**

The adapter accepts an HTTP request description containing an environment, method, route path, and GraphQL operation payload. It must route the request through the HTTP framework and print a JSON object containing the request method, path, environment, HTTP status code, and parsed response body. Development mode returns mock data for root operations, while production mode returns live resolver data. The output must include HTTP status and route signals so a direct function stub cannot satisfy the contract without exercising the endpoint behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature1_graphql_endpoint.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "GraphQL HTTP endpoint returns status and response body for root query and mutation operations in mock and live runtime modes.",
    "cases": [
        {
            "input": {
                "action": "graphql_http",
                "environment": "development",
                "method": "GET",
                "path": "/graphql",
                "graphql": {
                    "query": "query grampsVersion { grampsVersion }",
                    "operationName": "grampsVersion",
                    "variables": {}
                }
            },
            "expected_output": "{\n  \"body\": {\n    \"data\": {\n      \"grampsVersion\": \"Hello World\"\n    }\n  },\n  \"environment\": \"development\",\n  \"method\": \"GET\",\n  \"path\": \"/graphql\",\n  \"statusCode\": 200\n}\n"
        },
        {
            "input": {
                "action": "graphql_http",
                "environment": "production",
                "method": "POST",
                "path": "/graphql",
                "graphql": {
                    "query": "mutation grampsPing { grampsPing }",
                    "operationName": "grampsPing",
                    "variables": {}
                }
            },
            "expected_output": "{\n  \"body\": {\n    \"data\": {\n      \"grampsPing\": \"GET OFF MY LAWN\"\n    }\n  },\n  \"environment\": \"production\",\n  \"method\": \"POST\",\n  \"path\": \"/graphql\",\n  \"statusCode\": 200\n}\n"
        }
    ]
}
```

---

### Feature 2: Interactive GraphQL Documentation Endpoint

**As a developer**, I want an interactive documentation/debugging endpoint, so I can inspect and try GraphQL operations d[a specific default configuration object]ng development.

**Expected Behavior / Usage:**

The adapter accepts a development HTTP route request for the documentation endpoint. It must route the request through the HTTP framework and print the method, route path, status code, content type, and whether the HTML response contains the interactive GraphQL UI marker. The output must include HTTP status and route signals.

**Test Cases:** `rcb_tests/public_test_cases/feature2_graphiql_endpoint.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Interactive GraphQL documentation endpoint is exposed over HTTP and returns a successful HTML response.",
    "cases": [
        {
            "input": {
                "action": "graphiql_http",
                "environment": "development",
                "path": "/graphiql"
            },
            "expected_output": "{\n  \"containsGraphiql\": [a specific default configuration object],\n  \"contentType\": \"text/html\",\n  \"method\": \"GET\",\n  \"path\": \"/graphiql\",\n  \"statusCode\": 200\n}\n"
        }
    ]
}
```

---

### Feature 3: Per-Request Execution Context

**As a developer**, I want request processing to attach caller-provided context and data-source models to each request, so resolvers can access all required request and data dependencies consistently.

**Expected Behavior / Usage:**

The adapter accepts a middleware scenario containing optional extra context and a list of data-source descriptors. The middleware must attach a request execution object that includes the composed context, a schema, and an error formatter, then call the next request handler. The printed output must show the composed context values, whether schema and error formatter are present, and whether request processing continued.

**Test Cases:** `rcb_tests/public_test_cases/feature3_request_context.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Request middleware attaches a composed execution context containing caller-provided context values and configured data-source models, then continues the request chain.",
    "cases": [
        {
            "input": {
                "action": "middleware_context",
                "enableMockData": false,
                "extraContext": {
                    "tenant": "acme"
                },
                "sources": [
                    {
                        "context": "Catalog",
                        "modelValue": "catalog-model"
                    },
                    {
                        "context": "Inventory",
                        "modelValue": "inventory-model"
                    }
                ]
            },
            "expected_output": "{\n  \"context\": {\n    \"Catalog\": {\n      \"name\": \"catalog-model\"\n    },\n    \"Inventory\": {\n      \"name\": \"inventory-model\"\n    },\n    \"tenant\": \"acme\"\n  },\n  \"hasFormatError\": [a specific default configuration object],\n  \"hasSchema\": [a specific default configuration object],\n  \"nextCalled\": [a specific default configuration object]\n}\n"
        }
    ]
}
```

---

### Feature 4: Schema Composition

**As a developer**, I want built-in root GraphQL operations and data-source fields combined into one executable schema, so multiple service modules can be exposed through a single graph.

**Expected Behavior / Usage:**

The adapter accepts source descriptors and optional schema configuration flags. The composed schema must include built-in query and mutation roots plus query fields contributed by the supplied sources. The printed output lists query fields, mutation fields, and accepted configuration option keys. Field names in the output are schema wire-format names.

**Test Cases:** `rcb_tests/public_test_cases/feature4_schema_composition.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Schema composition combines built-in root operations with query fields contributed by multiple data sources and preserves schema configuration options.",
    "cases": [
        {
            "input": {
                "action": "compose_schema",
                "sources": [
                    {
                        "context": "Catalog",
                        "id": 1,
                        "modelValue": "catalog"
                    },
                    {
                        "context": "Inventory",
                        "id": 2,
                        "modelValue": "inventory"
                    }
                ]
            },
            "expected_output": "{\n  \"acceptedOptionKeys\": [],\n  \"mutationFields\": [\n    \"grampsPing\"\n  ],\n  \"queryFields\": [\n    \"CatalogType\",\n    \"InventoryType\",\n    \"grampsVersion\"\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 5: Development Source Loading

**As a developer**, I want development data sources to be loaded from configured paths, so local source modules can be substituted d[a specific default configuration object]ng development without hard-coding them into the service.

**Expected Behavior / Usage:**

The adapter accepts either no source paths or a comma-style list of relative source paths. It must load only valid source definitions and preserve their order. The printed output includes the number of loaded sources, context keys, and whether each loaded source exposes schema, resolver, and model data.

**Test Cases:** `rcb_tests/public_test_cases/feature5_external_sources.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Development source loading reads zero, one, or multiple comma-separated source paths and returns only valid source definitions in the supplied order.",
    "cases": [
        {
            "input": {
                "action": "load_external_sources"
            },
            "expected_output": "{\n  \"contexts\": [],\n  \"count\": 0,\n  \"hasModel\": [],\n  \"hasResolvers\": [],\n  \"hasSchema\": []\n}\n"
        }
    ]
}
```

---

### Feature 6: Development Source Overrides

**As a developer**, I want development sources to replace local sources with the same context key, so I can test alternative implementations while leaving unrelated sources unchanged.

**Expected Behavior / Usage:**

The adapter accepts local source descriptors and development source descriptors. Any local source whose context key matches a development source is replaced; nonmatching local sources remain before the development replacements. The printed output contains the resulting ordered source list and the number of override warnings emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature6_source_overrides.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Development sources replace local sources with matching context keys while unrelated local sources remain in place.",
    "cases": [
        {
            "input": {
                "action": "override_sources",
                "sources": [
                    {
                        "context": "One",
                        "value": "local"
                    },
                    {
                        "context": "Two",
                        "value": "local"
                    },
                    {
                        "context": "Three",
                        "value": "local"
                    }
                ],
                "devSources": [
                    {
                        "context": "Two",
                        "value": "external"
                    },
                    {
                        "context": "Three",
                        "value": "external"
                    }
                ]
            },
            "expected_output": "{\n  \"sources\": [\n    {\n      \"context\": \"One\",\n      \"value\": \"local\"\n    },\n    {\n      \"context\": \"Two\",\n      \"value\": \"external\"\n    },\n    {\n      \"context\": \"Three\",\n      \"value\": \"external\"\n    }\n  ],\n  \"warningCount\": 1\n}\n"
        }
    ]
}
```

---

### Feature 7: Outbound Request Configuration

**As a developer**, I want outbound API calls to use a consistent request configuration, so data connectors send JSON requests with predictable response handling and [a specific default configuration object].

**Expected Behavior / Usage:**

The adapter accepts a target URI and [a specific default configuration object]. It must print the request configuration containing the URI, JSON parsing flag, full-response flag, and [a specific default configuration object]. This contract describes the observable request options passed to an HTTP client.

**Test Cases:** `rcb_tests/public_test_cases/feature7_request_configuration.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Outbound request configuration includes the target URI, JSON response parsing, full response resolution, and caller-supplied [a specific default configuration object].",
    "cases": [
        {
            "input": {
                "action": "connector_request_config",
                "[a specific default configuration object]": "https://api.example.test/items",
                "[a specific default configuration object]": {}
            },
            "expected_output": "{\n  \"[a specific default configuration object]\": {},\n  \"[a specific default configuration object]\": [a specific default configuration object],\n  \"[a specific default configuration object]\": [a specific default configuration object],\n  \"[a specific default configuration object]\": \"https://api.example.test/items\"\n}\n"
        }
    ]
}
```

---

### Feature 8: GET Request Data and Cache Behavior

**As a developer**, I want cache-aware GET data loading, so successful responses can be cached and cached values can be returned quickly while fresh data is requested.

**Expected Behavior / Usage:**

The adapter accepts a target URI, simulated upstream status and body, cache availability, and cache mode. Fresh successful responses return the upstream body and write a cache entry with the configured TTL. Existing cached data is returned while a fresh request still refreshes the cache. Cache use is skipped when disabled, and non-200 upstream responses are returned without cache writes. The printed output contains the returned result and the cache operations performed.

**Test Cases:** `rcb_tests/public_test_cases/feature8_get_request_cache.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "GET data loading returns response bodies, stores successful fresh responses in cache, serves cached responses when available while refreshing, and skips cache when disabled or unsuccessful.",
    "cases": [
        {
            "input": {
                "action": "connector_get_request_data",
                "[a specific default configuration object]": "https://api.example.test/items/1",
                "statusCode": 200,
                "body": {
                    "id": 1,
                    "name": "fresh"
                },
                "redis": {}
            },
            "expected_output": "{\n  \"redisOps\": [\n    {\n      \"op\": \"get\"\n    },\n    {\n      \"op\": \"setex\",\n      \"ttl\": 300,\n      \"value\": {\n        \"id\": 1,\n        \"name\": \"fresh\"\n      }\n    }\n  ],\n  \"result\": {\n    \"id\": 1,\n    \"name\": \"fresh\"\n  }\n}\n"
        }
    ]
}
```

---

### Feature 9: GET Request Error Normalization

**As a developer**, I want cache and upstream request failures to be reported as normalized output, so callers receive stable error categories and domain metadata instead of host-language exception details.

**Expected Behavior / Usage:**

The adapter accepts scenarios where a cache lookup fails or an upstream request rejects. Cache failures print `error=[the exact error key stored in redis cache failure states]` style JSON with the cache error value. Upstream failures print a domain error object containing a normalized error category, HTTP status, error code, component signal, target endpoint, documentation link, description, message, and GUID presence. The output must not expose host-language exception class names or runtime stack rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature9_get_request_errors.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "GET data loading reports cache lookup failures and failed outbound requests as normalized errors that include domain status and endpoint signals where available.",
    "cases": [
        {
            "input": {
                "action": "connector_get_request_data",
                "[a specific default configuration object]": "https://api.example.test/cache-error",
                "statusCode": 200,
                "body": {
                    "unused": [a specific default configuration object]
                },
                "redis": {
                    "error": "[the exact error key stored in redis cache failure states]"
                }
            },
            "expected_output": "{\n  \"error\": \"[the exact error key stored in redis cache failure states]\",\n  \"value\": \"[the exact error key stored in redis cache failure states]\"\n}\n"
        }
    ]
}
```

---

### Feature 10: Batch Loading and Resource GET URI Construction

**As a developer**, I want batched URI loading and resource GET helpers, so higher-level data access can request one or more fully-qualified resources consistently.

**Expected Behavior / Usage:**

The adapter accepts either a list of complete URIs for batch loading or a base URI plus endpoint for a resource GET. Batch loading must call the data loader once for each URI and return one result per URI. Resource GET must concatenate base URI and endpoint before loading. The printed output includes both the returned data and the exact target URIs requested.

**Test Cases:** `rcb_tests/public_test_cases/feature10_batch_and_get.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Batch loading requests each URI and resource GET calls combine a base URI with an endpoint before loading.",
    "cases": [
        {
            "input": {
                "action": "connector_load",
                "[a specific default configuration object]s": [
                    "https://api.example.test/a",
                    "https://api.example.test/b"
                ]
            },
            "expected_output": "{\n  \"calls\": [\n    \"https://api.example.test/a\",\n    \"https://api.example.test/b\"\n  ],\n  \"result\": [\n    {\n      \"loaded\": [a specific default configuration object],\n      \"[a specific default configuration object]\": \"https://api.example.test/a\"\n    },\n    {\n      \"loaded\": [a specific default configuration object],\n      \"[a specific default configuration object]\": \"https://api.example.test/b\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 11: Non-Cacheable Mutation Request Configuration

**As a developer**, I want write-style outbound requests to be configured with method, body, and custom options, so POST and PUT calls are sent consistently and remain non-cacheable.

**Expected Behavior / Usage:**

The adapter accepts an HTTP method, base URI, endpoint, body, and optional request options. It must print the request options passed to the HTTP client and the simulated client result. POST and PUT requests include the combined URI, JSON response handling flags, [a specific default configuration object], method, and body, plus any custom options.

**Test Cases:** `rcb_tests/public_test_cases/feature11_mutation_requests.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Non-cacheable write requests send POST or PUT with the combined target URI, JSON body, and any caller-supplied request options.",
    "cases": [
        {
            "input": {
                "action": "connector_mutation",
                "method": "POST",
                "baseUri": "https://api.example.test",
                "endpoint": "/items",
                "body": {},
                "options": {}
            },
            "expected_output": "{\n  \"request\": {\n    \"body\": {},\n    \"[a specific default configuration object]\": {},\n    \"[a specific default configuration object]\": [a specific default configuration object],\n    \"method\": \"POST\",\n    \"[a specific default configuration object]\": [a specific default configuration object],\n    \"[a specific default configuration object]\": \"https://api.example.test/items\"\n  },\n  \"result\": {\n    \"accepted\": [a specific default configuration object]\n  }\n}\n"
        }
    ]
}
```

---

### Feature 12: Concrete Models and Abstract Base Protection

**As a developer**, I want concrete data models to retain their connector dependency and abstract base components to reject direct construction, so the domain is used through valid concrete extensions.

**Expected Behavior / Usage:**

The adapter accepts a connector-shaped value and returns the connector retained by a concrete model. Hidden cases also cover direct construction of abstract foundations; these failures must be rendered as `abstract_base_construction` with the component kind, without exposing host-language exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature12_model_and_abstract_bases.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Concrete model instances retain the supplied connector, while abstract base components reject direct construction with normalized error output.",
    "cases": [
        {
            "input": {
                "action": "model_with_connector",
                "connector": {
                    "kind": "memory",
                    "name": "primary"
                }
            },
            "expected_output": "{\n  \"connector\": {\n    \"kind\": \"memory\",\n    \"name\": \"primary\"\n  }\n}\n"
        }
    ]
}
```

---

### Feature 13: Client-Facing Error Data Formatting

**As a developer**, I want client error payloads to retain useful fields while hiding sensitive fields in production, so clients receive actionable but safe error data.

**Expected Behavior / Usage:**

The adapter accepts an environment and an error payload. In development-like environments, status, error label, message or description, error code, component signal, target endpoint, documentation link, and GUID are preserved when present. In production, private target endpoint and documentation fields are removed. If description is absent, message is moved into description. Double quotes inside descriptions are normalized to single quotes.

**Test Cases:** `rcb_tests/public_test_cases/feature13_client_error_formatting.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "Client-facing error data preserves useful fields, hides private endpoint and documentation fields in production, fills missing descriptions from messages, and normalizes quote characters.",
    "cases": [
        {
            "input": {
                "action": "format_client_error",
                "environment": "development",
                "error": {
                    "statusCode": 401,
                    "error": "Unauthorized",
                    "message": "error message",
                    "description": "error description",
                    "errorCode": "TEST_ERROR_CODE",
                    "graphqlModel": "testGraphQLModel",
                    "targetEndpoint": "https://example.test/endpoint",
                    "docsLink": "https://example.test/docs",
                    "guid": "1234"
                }
            },
            "expected_output": "{\n  \"description\": \"error description\",\n  \"docsLink\": \"https://example.test/docs\",\n  \"error\": \"Unauthorized\",\n  \"errorCode\": \"TEST_ERROR_CODE\",\n  \"graphqlModel\": \"testGraphQLModel\",\n  \"guid\": \"1234\",\n  \"message\": \"error message\",\n  \"statusCode\": 401,\n  \"targetEndpoint\": \"https://example.test/endpoint\"\n}\n"
        }
    ]
}
```

---

### Feature 14: Domain Error Wrapping

**As a developer**, I want GraphQL execution errors and custom domain failures to be converted into structured domain error payloads, so clients and logs receive consistent status, code, and context signals.

**Expected Behavior / Usage:**

The adapter accepts either a GraphQL execution error signal or a domain error configuration. GraphQL execution errors are wrapped as domain errors with a GraphQL-specific error code, description, HTTP 500 status, default client message, and GUID presence. Custom domain errors preserve configured HTTP status, message, description, component signal, endpoint, and documentation link. Output must use the neutral `domain_error` category and must not include host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature14_domain_error_wrapping.[a specific default configuration object]`

```[a specific default configuration object]
{
    "description": "GraphQL execution errors and explicitly created domain errors are converted to structured domain error payloads with HTTP status, error code, description, and endpoint metadata.",
    "cases": [
        {
            "input": {
                "action": "wrap_query_error",
                "message": "GraphQL syntax error",
                "locations": [
                    {
                        "line": 2,
                        "column": 3
                    }
                ]
            },
            "expected_output": "{\n  \"code\": \"GRAPHQL_ERROR\",\n  \"component\": null,\n  \"description\": \"GraphQL syntax error\",\n  \"docsLink\": null,\n  \"error\": \"domain_error\",\n  \"hasGuid\": [a specific default configuration object],\n  \"message\": \"An internal server error occurred\",\n  \"statusCode\": 500,\n  \"targetEndpoint\": null\n}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ens[a specific default configuration object]ng high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. The complete hidden evaluation subset lives under `rcb_tests/test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.[a specific default configuration object]` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_graphql_endpoint.[a specific default configuration object]` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_graphql_endpoint@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the model structure defined in the schema registry
