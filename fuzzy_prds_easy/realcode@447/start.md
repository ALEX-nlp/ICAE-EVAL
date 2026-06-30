## Product Requirement Document

# HTTP Gateway and Client Routing Utilities - Black-Box Behavior Contract

## Project Goal

Build a gateway support library that allows developers to route service traffic, prepare proxy requests, format operational metrics, and manage routing safety defaults without hand-writing repetitive HTTP gateway glue code.

---

## Background & Problem

Without this library, developers are forced to manually rewrite discovered service names into route paths, preserve and encode proxied URLs, copy request and response headers safely, decide whether outbound traffic should be secure, and render monitoring names consistently. This leads to duplicated routing rules, inconsistent URL handling, fragile header behavior, and metrics that are hard to aggregate.

With this library, gateway and client-routing behavior can be configured through clear inputs and then executed consistently across HTTP requests, proxy responses, service discovery names, and metric monitors.

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

### Feature 1: Service Identifier Route Mapping

**As a developer**, I want to transform discovered service identifiers into URL route paths using capture patterns, so I can expose stable gateway routes without hard-coding every service name.

**Expected Behavior / Usage:**

The input provides a service identifier, a capture pattern, and a route output pattern that references captured groups. When the service identifier matches, the output is the generated route path. When it does not match, the output keeps the original service identifier as the route. Generated routes must be normalized by removing repeated separators and trimming leading or trailing separators so optional groups do not leave malformed paths.

**Test Cases:** `rcb_tests/public_test_cases/feature1_route_mapping.json`

```json
{
  "description": "Maps service identifiers into route paths when the identifier matches configured capture patterns, leaves unmatched identifiers unchanged, and cleans empty path segments from generated routes.",
  "cases": [
    {
      "input": {"servicePattern":"(?<domain>^\\w+)(-(?<name>\\w+)-|-)(?<version>v\\d+$)","routePattern":"${version}/${domain}/${name}","serviceId":"rest-service-v1"},
      "expected_output": "service_id=rest-service-v1\nroute=v1/rest/service\n"
    },
    {
      "input": {"servicePattern":"(?<domain>^\\w+)(-(?<name>\\w+)-|-)(?<version>v\\d+$)","routePattern":"${version}/${domain}/${name}","serviceId":"rest-service"},
      "expected_output": "service_id=rest-service\nroute=rest-service\n"
    },
    {
      "input": {"servicePattern":"(?<domain>^\\w+)(-(?<name>\\w+)-|-)(?<version>v\\d+$)(?<nevermatch>.)?","routePattern":"/${version}/${nevermatch}/${domain}/${name}/","serviceId":"domain-service-v1"},
      "expected_output": "service_id=domain-service-v1\nroute=v1/domain/service\n"
    },
    {
      "input": {"servicePattern":"(?<domain>^\\w+)(-(?<name>\\w+)-|-)(?<version>v\\d+$)(?<nevermatch>.)?","routePattern":"/${version}/${nevermatch}/${domain}/${name}/","serviceId":"domain-v1"},
      "expected_output": "service_id=domain-v1\nroute=v1/domain\n"
    }
  ]
}
```

---

### Feature 2: Proxy Query String Construction

**As a developer**, I want to convert ordered query parameters into an outbound query string, so proxied requests preserve client query semantics.

**Expected Behavior / Usage:**

The input provides a parameter object whose keys are parameter names and whose values are ordered lists of parameter values. The output is a query string beginning with `?` when at least one parameter exists. Parameters are rendered in input order. Non-empty values are rendered as `name=value`; empty values are rendered as bare names without an equals sign.

**Test Cases:** `rcb_tests/public_test_cases/feature2_proxy_query_strings.json`

```json
{
  "description": "Builds outbound query strings from ordered query parameters, preserving parameter order and rendering empty parameter values as bare parameter names.",
  "cases": [
    {
      "input": {"params":{"a":["1234"],"b":["5678"]}},
      "expected_output": "query=?a=1234&b=5678\n"
    },
    {
      "input": {"params":{"wsdl":[""]}},
      "expected_output": "query=?wsdl\n"
    }
  ]
}
```

---

### Feature 3: Proxied Request URI Encoding

**As a developer**, I want the gateway to build an outbound request URI from the routed request path and encoding metadata, so non-ASCII paths are forwarded in a valid wire format.

**Expected Behavior / Usage:**

The input provides the incoming request path, the routed context path, and optionally the request character encoding. When a routed context path is present, it is encoded and used for the outbound URI. UTF-8 requests percent-encode non-ASCII characters as UTF-8 bytes. Requests without an explicit encoding use the platform default HTTP request encoding behavior represented in the contract. Already encoded paths remain in their encoded wire representation.

**Test Cases:** `rcb_tests/public_test_cases/feature3_proxy_request_uri_encoding.json`

```json
{
  "description": "Builds the proxied request URI from the request context and percent-encodes non-ASCII path characters according to the request character encoding, while preserving an already encoded path.",
  "cases": [
    {
      "input": {"method":"GET","requestUri":"/resource/esp%C3%A9cial-char","contextUri":"/resource/espécial-char","characterEncoding":"UTF-8"},
      "expected_output": "request_uri=/resource/esp%C3%A9cial-char\n"
    },
    {
      "input": {"method":"GET","requestUri":"/resource/esp%E9cial-char","contextUri":"/resource/espécial-char"},
      "expected_output": "request_uri=/resource/esp%E9cial-char\n"
    },
    {
      "input": {"method":"GET","requestUri":"/oléדרעק","contextUri":"/oléדרעק","characterEncoding":"UTF-8"},
      "expected_output": "request_uri=/ol%C3%A9%D7%93%D7%A8%D7%A2%D7%A7\n"
    },
    {
      "input": {"method":"GET","requestUri":"/oléדרעק","contextUri":"/oléדרעק"},
      "expected_output": "request_uri=/ol%E9%3F%3F%3F%3F\n"
    }
  ]
}
```

---

### Feature 4: Proxy Header and Response Handling

**As a developer**, I want the gateway to prepare outbound request headers and interpret origin response headers, so HTTP proxy behavior remains observable and standards-compatible.

**Expected Behavior / Usage:**

The input either describes request headers to copy into an upstream request or a response header to interpret from the origin service. Request header copying preserves every value of multi-valued headers and always includes an upstream `accept-encoding` request for gzip. Response handling records the origin status code and recognizes a gzip-encoded origin body when the content-encoding header is present, regardless of the header-name casing.

**Test Cases:** `rcb_tests/public_test_cases/feature4_proxy_header_and_response_handling.json`

```json
{
  "description": "Copies inbound request headers into outbound proxy headers with all observed values, always requests gzip from upstream, and recognizes gzipped origin responses regardless of header-name casing.",
  "cases": [
    {
      "input": {"mode":"request_headers","headers":{"singleName":["singleValue"],"multiName":["multiValue1","multiValue2"]}},
      "expected_output": "header=Accept-Encoding values=[gzip]\nheader=multiName values=[multiValue1, multiValue2]\nheader=singleName values=[singleValue]\n"
    },
    {
      "input": {"mode":"response_gzip","status":200,"headerName":"content-encoding","headerValue":"gzip"},
      "expected_output": "status=200\nresponse_gzipped=true\n"
    },
    {
      "input": {"mode":"response_gzip","status":200,"headerName":"Content-Encoding","headerValue":"gzip"},
      "expected_output": "status=200\nresponse_gzipped=true\n"
    }
  ]
}
```

---

### Feature 5: Secure Outbound Routing Decision

**As a developer**, I want outbound requests to resolve whether a target is secure from configuration and discovered server metadata, so the gateway can upgrade routes to HTTPS only when appropriate.

**Expected Behavior / Usage:**

The input provides an optional explicit secure flag, discovered server security metadata, and an outbound URI. If the explicit flag is set, it takes precedence over server metadata. If it is unset, server metadata determines the secure decision. When the resolved decision is secure and the URI is not already HTTPS, the URI scheme is changed to HTTPS while preserving the rest of the URI. When the resolved decision is not secure, the URI is unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature5_secure_routing_decision.json`

```json
{
  "description": "Determines whether an outbound client request should be treated as secure, giving an explicit client configuration precedence over discovered server metadata and upgrading an HTTP URI to HTTPS when the resolved route is secure.",
  "cases": [
    {
      "input": {"configuredSecure":null,"serverSecure":true,"uri":"http://localhost:8080/path","host":"localhost","port":8080},
      "expected_output": "configured_secure=unset\nserver_secure=true\nsecure=true\nuri=https://localhost:8080/path\n"
    },
    {
      "input": {"configuredSecure":null,"serverSecure":false,"uri":"http://localhost:8080/path","host":"localhost","port":8080},
      "expected_output": "configured_secure=unset\nserver_secure=false\nsecure=false\nuri=http://localhost:8080/path\n"
    },
    {
      "input": {"configuredSecure":true,"serverSecure":false,"uri":"http://localhost:8080/path","host":"localhost","port":8080},
      "expected_output": "configured_secure=true\nserver_secure=false\nsecure=true\nuri=https://localhost:8080/path\n"
    },
    {
      "input": {"configuredSecure":false,"serverSecure":true,"uri":"http://localhost:8080/path","host":"localhost","port":8080},
      "expected_output": "configured_secure=false\nserver_secure=true\nsecure=false\nuri=http://localhost:8080/path\n"
    }
  ]
}
```

---

### Feature 6: Dimensional Metric Name Formatting

**As a developer**, I want metric identifiers to include dimensional tags in a stable text format, so monitoring backends can aggregate and inspect measurements consistently.

**Expected Behavior / Usage:**

The input provides a metric name and zero or more tags. The output renders the metric name followed by parentheses. If no tags are present, the parentheses are empty. If tags are present, each tag is rendered as `key=value` inside the parentheses and multiple tags are comma-separated in deterministic order.

**Test Cases:** `rcb_tests/public_test_cases/feature6_metric_name_formatting.json`

```json
{
  "description": "Formats a metric name as a dimensional identifier with all configured tags rendered inside parentheses in deterministic tag order.",
  "cases": [
    {
      "input": {"name":"testMetric","tags":{}},
      "expected_output": "metric_name=testMetric()\n"
    },
    {
      "input": {"name":"test.Metric","tags":{}},
      "expected_output": "metric_name=test.Metric()\n"
    },
    {
      "input": {"name":"testMetric","tags":{"type":"COUNTER"}},
      "expected_output": "metric_name=testMetric(type=COUNTER)\n"
    },
    {
      "input": {"name":"testMetric","tags":{"instance":"instance0"}},
      "expected_output": "metric_name=testMetric(instance=instance0)\n"
    },
    {
      "input": {"name":"testMetric","tags":{"statistic":"min"}},
      "expected_output": "metric_name=testMetric(statistic=min)\n"
    },
    {
      "input": {"name":"testMetric","tags":{"type":"COUNTER","instance":"instance0","statistic":"min"}},
      "expected_output": "metric_name=testMetric(instance=instance0,statistic=min,type=COUNTER)\n"
    }
  ]
}
```

---

### Feature 7: Gateway Header Filtering Defaults

**As a developer**, I want secure default header filtering with configurable overrides, so sensitive or security-related headers are handled predictably for gateway routes.

**Expected Behavior / Usage:**

The input optionally provides global ignored headers, global sensitive headers, and route-specific sensitive headers. With no overrides, the output includes the built-in security response headers to ignore and the built-in sensitive request headers. When ignored headers are configured, they replace the ignored-header set. When global sensitive headers are configured, they replace the global sensitive-header set. Route-specific sensitive headers are reported independently and do not inherit the global defaults in the same route output.

**Test Cases:** `rcb_tests/public_test_cases/feature7_gateway_header_defaults.json`

```json
{
  "description": "Initializes gateway header filtering with built-in security-related ignored headers and sensitive headers, while allowing callers to replace global sensitive headers and route-specific sensitive headers.",
  "cases": [
    {
      "input": {},
      "expected_output": "[a static list of commonly ignored HTTP headers defined in the gateway configuration]\n[a static list of commonly ignored HTTP headers defined in the gateway configuration]\n"
    },
    {
      "input": {"ignoredHeaders":["x-foo"]},
      "expected_output": "ignored_headers=[Cache-Control, Expires, Pragma, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, x-foo]\n[a static list of commonly ignored HTTP headers defined in the gateway configuration]\n"
    },
    {
      "input": {"sensitiveHeaders":["x-bar"],"routeSensitiveHeaders":["x-foo"]},
      "expected_output": "route_sensitive_headers=[x-foo]\n[a static list of commonly ignored HTTP headers defined in the gateway configuration]\nsensitive_headers=[x-bar]\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_route_mapping.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_route_mapping@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- scheme not already https
- override serverSecure
