## Product Requirement Document

# HTTP Reverse Proxy Router with Zero-Downtime Deployments — Host Routing, Health-Gated Activation, and Request/Response Shaping

## Project Goal

Build an HTTP reverse-proxy router that lets operators publish backend applications behind a single front door and swap their backends with zero downtime, so developers can deploy continuously without dropping in-flight traffic or manually editing proxy configuration.

---

## Background & Problem

Without this tool, operators are forced to hand-edit a static proxy configuration for every deployment, reload the proxy, and hope no request is dropped while a backend restarts; routing to the wrong instance, serving an unhealthy backend, or leaking plaintext traffic to a secure endpoint are all easy mistakes. There is no built-in way to gate activation on a health check, to roll a new backend out to a deterministic fraction of clients, or to hold traffic briefly while a backend drains.

With this tool, an operator registers a named service under one or more hostnames pointing at a backend; the router health-checks the backend before sending it traffic, swaps backends atomically, enforces transport security, can pause/resume/stop a service, can roll a candidate backend out to a reproducible slice of clients, and buffers or reshapes requests and responses through a small middleware chain.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility system (host routing, service lifecycle, health checking, transport-security enforcement, rollout selection, request/response buffering, error-page rendering). It MUST be organized as a clear multi-file tree separating routing, per-service state, and the middleware chain; it MUST NOT be a single "god file". Do not over-engineer, but keep each responsibility in its own unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a black-box contract for an execution adapter, NOT the internal data model. The core routing/proxy logic must be completely decoupled from stdin/stdout and JSON parsing; the adapter alone translates JSON commands into idiomatic calls on the core and renders the textual contract.

3. **Adherence to SOLID Design Principles:** Separate host matching, service lifecycle, health gating, rollout selection, and output formatting into distinct cohesive units; the routing core must be open for extension (new middleware) but closed for modification; middleware must be substitutable; high-level routing must depend on abstractions, not on concrete I/O.

4. **Robustness & Interface Design:** The core interface must be idiomatic to the target language and hide internal complexity. Error conditions (host already claimed, backend unhealthy, wildcard incompatible with automatic certificates, unloadable error pages, oversize bodies) must be modeled as explicit, typed error conditions rather than generic faults, so the adapter can render them as neutral category lines.

---

## Core Features

### Feature 1: Host-Based Routing

**As a developer**, I want requests dispatched to backends by their host, so I can serve many applications behind one proxy.

**Expected Behavior / Usage:**

A service is registered ("deployed") by name under one or more exact hostnames pointing at a backend address. An incoming request is matched against the registered services by its host: a match forwards the request to that service's backend and returns the backend's status and body verbatim; a host that matches no service yields a not-found response. A single service may own several hostnames, each of which routes to it. Each deployment line reports the service name and `ok`; each request probe prints `status=<code> target=<backend-body>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_host_routing.json`

```json
{
    "description": "An incoming request is routed to a backend by matching the request host against the set of services registered in the router. Each service is registered under one or more exact hostnames. When the incoming host matches a registered service the request is forwarded to that service's backend and the backend's response status and body are returned to the client. When the incoming host matches no registered service the router returns a not-found response. Each registration is reported as succeeding, and each probe reports the resulting response status together with the backend-provided body.",
    "cases": [
        {
            "input": {
                "kind": "router_scenario",
                "backends": { "primary": { "body": "primary-app" } },
                "steps": [
                    { "op": "deploy", "name": "s1", "hosts": ["app.example.com"], "target": "primary" },
                    { "op": "request", "url": "http://app.example.com/", "method": "GET" },
                    { "op": "request", "url": "http://unknown.example.com/", "method": "GET" }
                ]
            },
            "expected_output": "deploy s1 ok\nstatus=200 target=primary-app\nstatus=404 target=Not Found\n"
        }
    ]
}
```

---

### Feature 2: Wildcard and Catch-All Routing

**As a developer**, I want wildcard and catch-all host registrations, so I can serve whole subdomain families or a default backend.

**Expected Behavior / Usage:**

A service may be registered under a wildcard pattern of the form `*.<base-domain>` that matches any single-label subdomain of the base domain but NOT the bare base domain itself, or with an empty host set, which makes it the catch-all that receives any request not matched by another service. When both a wildcard and an exact registration could match a host, the exact registration wins. Each probe prints `status=<code> target=<backend-body>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_wildcard_routing.json`

```json
{
    "description": "A service may be registered under a wildcard host pattern that matches any single-label subdomain of a base domain, or with an empty host set that makes it the catch-all for requests not matched by any other service. An exact host registration takes precedence over an overlapping wildcard registration. A wildcard pattern matches subdomains but not the bare base domain itself. Each probe reports the resulting response status and the backend-provided body.",
    "cases": [
        {
            "input": {
                "kind": "router_scenario",
                "backends": { "wildcard": { "body": "wildcard-app" } },
                "steps": [
                    { "op": "deploy", "name": "sw", "hosts": ["*.example.com"], "target": "wildcard" },
                    { "op": "request", "url": "http://foo.example.com/", "method": "GET" },
                    { "op": "request", "url": "http://example.com/", "method": "GET" }
                ]
            },
            "expected_output": "deploy sw ok\nstatus=200 target=wildcard-app\nstatus=404 target=Not Found\n"
        }
    ]
}
```

---

### Feature 3: Host Ownership and Conflict Rejection

**As a developer**, I want a host to be owned by exactly one service, so two deployments cannot silently collide.

**Expected Behavior / Usage:**

A host may be claimed by at most one service. Deploying a new, differently-named service onto a host already claimed by another service is rejected with a host-already-in-use error (`error=host_in_use`), and the original service keeps serving that host. Re-deploying an existing service under its own name onto the same host is allowed and atomically swaps its backend (the next request observes the new backend). Each deployment line reports `ok` or `error=<category>`; each probe prints `status=<code> target=<backend-body>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_host_conflict.json`

```json
{
    "description": "A host may be claimed by at most one service at a time. Registering a new service under a host that is already claimed by a different service is rejected with a host-already-in-use error, and the original service keeps serving that host. Re-registering an existing service by the same name under the same host is allowed and atomically swaps its backend. Each registration reports success or the normalized error category, and each probe reports the response status and backend body.",
    "cases": [
        {
            "input": {
                "kind": "router_scenario",
                "backends": { "a": { "body": "service-a" }, "b": { "body": "service-b" } },
                "steps": [
                    { "op": "deploy", "name": "s1", "hosts": ["h.example.com"], "target": "a" },
                    { "op": "deploy", "name": "s2", "hosts": ["h.example.com"], "target": "b" },
                    { "op": "request", "url": "http://h.example.com/", "method": "GET" }
                ]
            },
            "expected_output": "deploy s1 ok\ndeploy s2 error=host_in_use\nstatus=200 target=service-a\n"
        }
    ]
}
```

---

### Feature 4: Health-Gated Activation

**As a developer**, I want a backend to pass a health check before receiving traffic, so a broken deploy never serves users.

**Expected Behavior / Usage:**

When a service is deployed, the router probes the backend's health endpoint and only activates it once the endpoint returns a success status within a bounded deploy window. A backend that fails to become healthy within the window causes the deployment to fail with a target-unhealthy error (`error=target_unhealthy`) and leaves routing unchanged. A backend that passes is activated and subsequently serves matching requests. Each deployment line reports `ok` or `error=<category>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_target_health.json`

```json
{
    "description": "Before a newly registered backend begins receiving traffic it must pass a health check within a bounded deploy window. A backend whose health endpoint does not return a success status within the window causes the registration to fail with a target-unhealthy error and no routing change takes effect. A backend that passes its health check is activated and subsequently serves matching requests. Each registration reports success or the normalized error category.",
    "cases": [
        {
            "input": {
                "kind": "router_scenario",
                "backends": { "bad": { "body": "broken", "status": 503 } },
                "steps": [
                    { "op": "deploy", "name": "s1", "hosts": ["h.example.com"], "target": "bad", "deploy_timeout_ms": 300 }
                ]
            },
            "expected_output": "deploy s1 error=target_unhealthy\n"
        }
    ]
}
```

---

### Feature 5: Transport Security Enforcement

**As a developer**, I want the proxy to enforce HTTPS per service, so plaintext and secure traffic are handled correctly.

**Expected Behavior / Usage:**

When a service has TLS enabled, a plaintext (non-secure) request is answered with a permanent redirect (status 301) to the same URL under the secure scheme; for request methods that emit a redirect body, the body contains the HTML redirect link, while for methods that do not, the body is empty. When a service does NOT have TLS enabled, a request that arrives over the secure transport is rejected with a service-unavailable response. Registering a TLS-enabled service under a wildcard host is rejected because automatic certificate provisioning cannot cover wildcard hosts (`error=automatic_tls_wildcard_unsupported`). Each probe prints `status=<code> target=<body>`; each deployment reports `ok` or `error=<category>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_tls_enforcement.json`

```json
{
    "description": "When a service has TLS enabled, a plaintext request to it is answered with a permanent redirect to the same URL over the secure scheme; for methods where a redirect body is emitted the response body contains the redirect link. When a service does not have TLS enabled, a request arriving over the secure transport is rejected with a service-unavailable response. Registering a TLS-enabled service under a wildcard host is rejected because automatic certificate provisioning does not support wildcard hosts. Each probe reports the response status and body; each registration reports success or the normalized error category.",
    "cases": [
        {
            "input": {
                "kind": "router_scenario",
                "backends": { "a": { "body": "secure-app" } },
                "steps": [
                    { "op": "deploy", "name": "s1", "hosts": ["secure.example.com"], "target": "a", "tls": true },
                    { "op": "request", "url": "http://secure.example.com/path", "method": "GET" },
                    { "op": "request", "url": "http://secure.example.com/path", "method": "POST" }
                ]
            },
            "expected_output": "deploy s1 ok\nstatus=301 target=<a href=\"https://secure.example.com/path\">Moved Permanently</a>.\nstatus=301 target=\n"
        }
    ]
}
```

---

### Feature 6: Service Lifecycle — Pause, Resume, Stop

**As a developer**, I want to pause, resume, or stop a service, so I can drain or take down a backend cleanly.

**Expected Behavior / Usage:**

A deployed service can be paused, resumed, or stopped. While paused, matching requests are held until a bounded pause window elapses and are then answered with a gateway-timeout response (status 504); resuming restores normal routing so subsequent requests reach the backend again. While stopped, the service still answers its health endpoint with a success response (empty body) but answers every other matching request with a service-unavailable response. Each lifecycle command reports `<op> <name> ok`; each probe prints `status=<code> target=<body>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_pause_resume_stop.json`

```json
{
    "description": "A service can be paused, resumed, or stopped. While paused, matching requests are held until a bounded pause window elapses and then answered with a gateway-timeout response; resuming restores normal routing. While stopped, the service answers its health endpoint with a success response but answers all other matching requests with a service-unavailable response. Each lifecycle command reports success, and each probe reports the response status and body.",
    "cases": [
        {
            "input": {
                "kind": "router_scenario",
                "backends": { "a": { "body": "live-app" } },
                "steps": [
                    { "op": "deploy", "name": "s1", "hosts": ["h.example.com"], "target": "a" },
                    { "op": "pause", "name": "s1", "pause_timeout_ms": 50 },
                    { "op": "request", "url": "http://h.example.com/", "method": "GET" },
                    { "op": "resume", "name": "s1" },
                    { "op": "request", "url": "http://h.example.com/", "method": "GET" }
                ]
            },
            "expected_output": "deploy s1 ok\npause s1 ok\nstatus=504 target=Gateway Timeout\nresume s1 ok\nstatus=200 target=live-app\n"
        }
    ]
}
```

---

### Feature 7: Per-Service Request Size Limit

**As a developer**, I want a service to cap request body size, so oversized uploads are rejected before reaching the backend.

**Expected Behavior / Usage:**

A service may be configured to buffer request bodies with a maximum allowed size. With buffering enabled, a request whose body fits within the maximum is forwarded to the backend and its response returned; a request whose body exceeds the maximum is rejected with a payload-too-large response (status 413, body `[a configurable rejection threshold]`) and never reaches the backend. Each probe prints `status=<code> target=<body>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_request_size_limit.json`

```json
{
    "description": "A service may be configured to buffer request bodies with a maximum allowed size. When buffering is enabled, a request whose body fits within the configured maximum is forwarded to the backend and its response returned, while a request whose body exceeds the maximum is rejected with a payload-too-large response and never reaches the backend. Each probe reports the response status and body.",
    "cases": [
        {
            "input": {
                "kind": "router_scenario",
                "backends": { "a": { "body": "app-ok" } },
                "steps": [
                    { "op": "deploy", "name": "s1", "hosts": ["h.example.com"], "target": "a", "buffer_requests": true, "max_request_body_size": 8 },
                    { "op": "request", "url": "http://h.example.com/", "method": "POST", "body": "tiny" },
                    { "op": "request", "url": "http://h.example.com/", "method": "POST", "body": "this body is too large" }
                ]
            },
            "expected_output": "deploy s1 ok\nstatus=200 target=app-ok\nstatus=413 target=[a configurable rejection threshold]\n"
        }
    ]
}
```

---

### Feature 8: Deterministic Rollout Selection

**As a developer**, I want a reproducible canary split, so a candidate backend reaches a stable fraction of clients.

**Expected Behavior / Usage:**

A canary rollout selects a deterministic fraction of clients into a rollout group based on a per-client identifier value carried by the request. Membership is decided by a stable 32-bit FNV-1a hash of the identifier value reduced modulo one hundred, included in the group when that result is strictly less than the configured target percentage; the same identifier therefore always yields the same decision and the selected fraction is reproducible across a large population. Identifiers listed in an explicit allowlist are always in the group regardless of percentage; a request that carries no identifier is never in the group. Each evaluation prints `value=<identifier> group=<true|false>` (a missing identifier prints `value=<none> ...`); a population sweep prints `matched=<n> total=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_rollout_selection.json`

```json
{
    "description": "A canary rollout selects a deterministic fraction of clients into a rollout group based on a per-client identifier value carried by the request. Membership is decided by a stable 32-bit FNV-1a hash of the identifier reduced modulo one hundred and compared against the configured target percentage, so the same identifier always yields the same decision and the selected fraction is reproducible across a large population. Identifiers present in an explicit allowlist are always in the group; a request that carries no identifier is never in the group. Each evaluation reports the identifier and whether it falls in the rollout group; a population sweep reports the number selected out of the total.",
    "cases": [
        {
            "input": {
                "kind": "rollout_split",
                "percent": 0,
                "allowlist": ["vip"],
                "cookie_values": ["vip", "00001", null]
            },
            "expected_output": "value=vip group=true\nvalue=00001 group=false\nvalue=<none> group=false\n"
        }
    ]
}
```

---

### Feature 9: Size-Limited Spillable Buffer

**As a developer**, I want a buffer that caps total size and spills to disk, so large payloads are bounded without exhausting memory.

**Expected Behavior / Usage:**

A size-limited buffer accumulates bytes written into it or read through it up to a configured maximum. Content within the maximum is preserved and replayable exactly. Content exceeding the maximum yields a size-exceeded error (`error=maximum_size_exceeded`). A maximum of zero means unlimited. The buffer keeps a bounded amount in memory and transparently spills the remainder to backing storage, so spilled content is still preserved exactly. Each case prints `content=<preserved-bytes>` or the normalized error line.

**Test Cases:** `rcb_tests/public_test_cases/feature9_size_limited_buffer.json`

```json
{
    "description": "A size-limited buffer accumulates bytes written to it or read through it up to a configured maximum. Content that stays within the maximum is preserved and can be replayed exactly. Content that exceeds the maximum yields a size-exceeded error. A maximum of zero means unlimited. The buffer keeps a bounded amount in memory and transparently spills the remainder to backing storage, so spilled content is still preserved exactly. Each case reports the preserved content or the normalized size-exceeded error.",
    "cases": [
        {
            "input": {
                "kind": "buffer",
                "mode": "write",
                "max_bytes": 20,
                "max_mem_bytes": 20,
                "data": "hello world"
            },
            "expected_output": "content=hello world\n"
        }
    ]
}
```

---

### Feature 10: Request Identifier Middleware

**As a developer**, I want every request to carry an identifier, so requests are traceable end to end.

**Expected Behavior / Usage:**

A middleware guarantees every request carries a request-identifier header before reaching the handler. If the incoming request already has one, it is preserved unchanged; otherwise a fresh identifier is generated and attached. The request always proceeds to the handler. Each case prints `status=<code>` and then either `request_id=<value>` (when an identifier was supplied and preserved) or `request_id_present=<true|false>` plus `request_id_length=<n>` (when one was generated).

**Test Cases:** `rcb_tests/public_test_cases/feature10_request_id.json`

```json
{
    "description": "A middleware ensures every request carries a request-identifier header before reaching the handler. When the incoming request already carries an identifier it is preserved unchanged. When the incoming request has no identifier a fresh one is generated and attached. The request always proceeds to the handler. Each case reports the response status and either the preserved identifier or whether an identifier was generated together with its length.",
    "cases": [
        {
            "input": { "kind": "request_id", "has_incoming": false },
            "expected_output": "status=200\nrequest_id_present=true\nrequest_id_length=36\n"
        }
    ]
}
```

---

### Feature 11: Request Buffering Middleware

**As a developer**, I want request bodies buffered with a hard cap, so handlers see a complete body and oversize uploads are rejected.

**Expected Behavior / Usage:**

A middleware buffers the request body in memory up to a memory threshold, spilling beyond it to backing storage, and enforces an overall maximum body size. A request within the overall maximum is passed to the handler, whose response is returned. A request exceeding the overall maximum is rejected with a payload-too-large response (status 413) and the handler is not invoked. Each case prints `status=<code> body=<response-body>`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_request_buffering.json`

```json
{
    "description": "A middleware buffers the request body in memory up to a memory threshold, spilling to backing storage beyond it, and enforces an overall maximum body size. A request whose body fits within the overall maximum is passed to the handler, which returns its response. A request whose body exceeds the overall maximum is rejected with a payload-too-large response and the handler is not invoked. Each case reports the response status and body.",
    "cases": [
        {
            "input": {
                "kind": "request_buffer_mw",
                "max_mem_bytes": 1024,
                "max_bytes": 100,
                "request_body": "small",
                "response_body": "handled"
            },
            "expected_output": "status=200 body=handled\n"
        }
    ]
}
```

---

### Feature 12: Response Buffering Middleware

**As a developer**, I want responses buffered with a cap but streams passed through, so I can bound normal responses yet still stream events.

**Expected Behavior / Usage:**

A middleware buffers the handler's response up to a configured maximum before forwarding it. A response within the limit is forwarded with its status and body intact. A response whose content type marks it as an event stream switches to unbuffered pass-through once the handler writes its header, so its content streams regardless of the buffer limit. A redirect emitted by the handler is forwarded with its redirect status and HTML link body. A buffered response that exceeds the maximum is replaced with an internal-server-error response (status 500). Each case prints `status=<code> body=<body>`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_response_buffering.json`

```json
{
    "description": "A middleware buffers the handler's response up to a configured maximum before forwarding it to the client. A response within the limit is forwarded with its status and body intact. A response whose content type marks it as an event stream switches to unbuffered pass-through once the handler writes its header, so its content is streamed regardless of the buffer limit. A redirect produced by the handler is forwarded with its redirect status and link body. A buffered response that exceeds the maximum is replaced with an internal-server-error response. Each case reports the response status and body.",
    "cases": [
        {
            "input": {
                "kind": "response_buffer_mw",
                "max_mem_bytes": 1024,
                "max_bytes": 1024,
                "response_body": "hello body"
            },
            "expected_output": "status=200 body=hello body\n"
        }
    ]
}
```

---

### Feature 13: Custom Error Pages Middleware

**As a developer**, I want custom error pages with nesting and a generic fallback, so error responses are branded and overridable.

**Expected Behavior / Usage:**

A middleware renders a custom error page when a downstream handler signals an error status. Templates are HTML files named after the status code (e.g. `404.html`); when a template for the signalled status exists it is rendered with the supplied arguments (the resulting content type is `text/html; charset=utf-8`), otherwise the outermost middleware emits a generic `<h1><code> <reason></h1>` page. Middlewares may be nested: an inner template set overrides the outer for statuses it defines, while statuses it does not define fall through to the outer set. A template source that contains no usable HTML templates is rejected when constructed with an unable-to-load error (`error=unable_to_load_error_pages`). Each case prints `status=<code> content_type=<type> body=<rendered>` or the normalized error line.

**Test Cases:** `rcb_tests/public_test_cases/feature13_error_pages.json`

```json
{
    "description": "A middleware renders a custom error page when a downstream handler signals an error status. Error page templates are HTML files named after the status code; when a template for the signalled status exists it is rendered with the supplied arguments, otherwise a generic page is produced by the outermost middleware. Middlewares may be nested so an inner set of templates overrides an outer one for statuses it defines, while statuses it does not define fall through to the outer set. A template source that contains no usable templates is rejected with an unable-to-load error. Each case reports the response status, content type and rendered body, or the normalized load error.",
    "cases": [
        {
            "input": {
                "kind": "error_page",
                "root": true,
                "outer_pages": { "404.html": "<h1>custom not found</h1>" },
                "status": 404,
                "message": "missing"
            },
            "expected_output": "status=404 content_type=text/html; charset=utf-8 body=<h1>custom not found</h1>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the routing, service lifecycle, health gating, transport-security enforcement, rollout selection, buffering, and error-page features above, with each responsibility in its own unit.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command object from stdin (discriminated by its `kind`), invokes the appropriate core logic, and prints the result to stdout, matching the per-feature contracts above. Native error conditions are normalized into neutral `error=<category>` lines in this adapter layer only. The adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` runs the full suite and accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{idx:03d}.txt` containing only the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- fetch the backend payload representation
- verify failure reason is not optional
