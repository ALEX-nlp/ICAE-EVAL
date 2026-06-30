## Product Requirement Document

# HTTP Acceleration Proxy — Caching, Compression-Aware Delivery & Structured Access Logging

## Project Goal

Build a lightweight HTTP front-end that sits between clients and a single application origin and accelerates it transparently: it forwards requests to the origin, caches eligible responses in memory, serves static files on the origin's behalf, records a structured log line for every request, and is driven entirely by process arguments and environment variables. The goal is to let an application gain shared caching, accelerated file delivery and uniform request logging without building any of that into the application itself.

---

## Background & Problem

Application servers are good at producing dynamic responses but are wasteful when asked to repeatedly regenerate identical pages, stream large static files, or implement their own access logging and configuration plumbing. Operators are then forced to bolt on a separate caching tier, a separate file server and a separate log shipper, each with its own configuration surface and subtle correctness pitfalls (stale variants, cookie leakage into shared caches, truncated downloads when content is pre-compressed, and so on).

With this front-end, a single process wraps the origin and provides those cross-cutting behaviors as a well-defined contract: a request goes in, it is routed to the origin, the response is conditionally stored and replayed, files named by the origin are delivered directly from disk, and a one-line summary of the exchange is emitted — all configured from the environment.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This is a multi-responsibility system (routing, caching, file delivery, logging, configuration); it MUST be organized as a clear multi-file tree with one cohesive unit per responsibility, NOT a single "god file". Do not over-engineer, but strictly avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for an execution adapter, NOT the internal data model. The core request-handling components must be decoupled from stdin/stdout and JSON parsing; the adapter alone translates JSON commands into idiomatic calls to the core and renders results.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, caching policy, file delivery, logging and output formatting into distinct units (SRP). The handler pipeline must be open for extension but closed for modification (OCP). Each middleware stage must be substitutable as a standard request handler (LSP). Keep the interfaces (a cache store, a request handler) small (ISP). High-level policy must depend on abstractions such as a cache-store interface, not concrete I/O (DIP).

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language. Edge cases (oversized bodies, pre-compressed files, missing required arguments) must be modeled explicitly rather than producing generic faults. Errors surfaced to the contract must be normalized domain categories, never host-language runtime artifacts.

---

## Core Features

### Feature 1: Reverse Proxy Routing

**As a developer**, I want incoming requests transparently forwarded to a fixed upstream origin and the origin's reply relayed back unchanged, so I can place this front-end ahead of any application without it noticing.

**Expected Behavior / Usage:**

The proxy targets one fixed origin. For an incoming request it preserves the HTTP method, the URL path and the full query string and delivers them to the origin exactly as received; whatever status code, `Content-Type` and body the origin returns are relayed back to the caller verbatim. The contract reports the client-visible status, content type and body, together with the method, path and query string actually observed at the origin (demonstrating routing fidelity in both directions).

**Test Cases:** `rcb_tests/public_test_cases/feature1_proxy_routing.json`

```json
{
    "description": "A reverse proxy forwards an incoming HTTP request to a single fixed upstream origin and relays the origin's response back to the client unchanged. The request method, path and query string must be delivered to the upstream exactly as received (routing fidelity), and the upstream's status code, Content-Type header and response body must be returned verbatim to the caller. Output reports the client-visible status, content type and body, plus the method, path and query string actually observed at the upstream.",
    "cases": [
        {
            "input": {"action": "proxy", "request": {"method": "GET", "path": "/articles", "query": "page=2", "headers": {}}, "upstream": {"status": 200, "headers": {"Content-Type": "[a detected content type]; charset=utf-8"}, "body": "Article listing body"}},
            "expected_output": "status=200\ncontent_type=[a detected content type]; charset=utf-8\nupstream_method=GET\nupstream_path=/articles\nupstream_query=page=2\nbody=Article listing body\n"
        },
        {
            "input": {"action": "proxy", "request": {"method": "POST", "path": "/submit", "query": "id=7", "headers": {}}, "upstream": {"status": 404, "headers": {"Content-Type": "application/json"}, "body": "{\"error\":\"missing\"}"}},
            "expected_output": "status=404\ncontent_type=application/json\nupstream_method=POST\nupstream_path=/submit\nupstream_query=id=7\nbody={\"error\":\"missing\"}\n"
        }
    ]
}
```

---

### Feature 2: HTTP Response Cache

**As a developer**, I want eligible responses stored and replayed for equivalent later requests, so the origin is shielded from repeated identical work while clients never receive a response that was meant for someone else.

**Expected Behavior / Usage:**

Each request passing through the cache reports a disposition signal in an `X-Cache`-style field: `miss` (a fresh response was generated and possibly stored), `hit` (a stored response was replayed), or `bypass` (the request was deliberately not cacheable and went straight to the origin). The per-request contract for this feature always reports, in order, the request index, status code, cache disposition, any cookie header on the response, a tracked custom response header, and the body. The origin numbers successive generated bodies so a replayed response is visibly distinct from a regenerated one.

*2.1 Caching by response directives — when a response may be stored*

Storability is decided solely from the response's caching directives, status and size. A response is storable only when its directives explicitly mark it shareable AND grant a positive freshness lifetime. Directives that mark it private, omit the shareable marker, grant a zero or absent lifetime, or explicitly forbid reuse make it non-storable. Not-modified / informational / redirect / error statuses are never stored, and a body exceeding the configured size limit is never stored. Requests using a non-cacheable method skip the cache entirely (`bypass`). When a stored response is replayed, its original status code and any custom headers are reproduced exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_caching.json`

```json
{
    "description": "A caching layer sits in front of an origin and decides whether each response may be reused for later identical requests, based solely on the response's caching directives, status and size. A response is storable only when its directives mark it explicitly shareable AND give a positive freshness lifetime; directives that mark it private, omit a shareable marker, give a zero or absent lifetime, or explicitly forbid reuse make it non-storable. Redirect/informational/error or not-modified statuses and bodies larger than the configured limit are never stored. Each request reports a cache disposition signal: a freshly generated (and possibly stored) response, a reuse of a previously stored response, or a deliberate skip of the cache. When a stored response is reused, the original status code and any custom headers it carried are reproduced exactly. The origin numbers successive generated bodies so that a reused response is distinguishable from a regenerated one. Output, per request in the sequence, reports the request index, status code, cache disposition, any cookie header, a tracked custom header, and the body.",
    "cases": [
        {
            "input": {"action": "cache", "upstream": {"cacheControl": "public, max-age=60", "bodyMode": "counter", "body": "Hello"}, "requests": [{"url": "http://example.com"}, {"url": "http://example.com"}, {"url": "http://example.com"}]},
            "expected_output": "request=0\nstatus=200\nx_cache=miss\nset_cookie=-\nextra=-\nbody=Hello 1\nrequest=1\nstatus=200\n[a specific query key value]\nset_cookie=-\nextra=-\nbody=Hello 1\nrequest=2\nstatus=200\n[a specific query key value]\nset_cookie=-\nextra=-\nbody=Hello 1\n"
        },
        {
            "input": {"action": "cache", "upstream": {"cacheControl": "public, max-age=60", "bodyMode": "counter", "body": "Hello"}, "requests": [{"method": "POST", "url": "http://example.com"}, {"method": "POST", "url": "http://example.com"}, {"method": "POST", "url": "http://example.com"}]},
            "expected_output": "request=0\nstatus=200\nx_cache=bypass\nset_cookie=-\nextra=-\nbody=Hello 1\nrequest=1\nstatus=200\nx_cache=bypass\nset_cookie=-\nextra=-\nbody=Hello 2\nrequest=2\nstatus=200\nx_cache=bypass\nset_cookie=-\nextra=-\nbody=Hello 3\n"
        }
    ]
}
```

*2.2 Cache keying — which requests are considered equivalent*

The cache key is derived from the request method, the URL path and the complete set of query parameters, with query parameters treated as order-independent (the same parameters in a different order map to the same key). Only requests producing the same key may share a stored response; non-cacheable methods bypass the cache. With an always-storable origin response the keying is visible purely through which requests replay an earlier response.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_keying.json`

```json
{
    "description": "The caching layer derives a cache key for each request so that only genuinely equivalent requests share a stored response. The key is sensitive to the request method, the URL path and the full set of query parameters, but treats query parameters as order-independent (the same parameters supplied in a different order map to the same key). Methods that are not safely cacheable bypass the cache entirely. With an always-storable origin response, output per request reports the request index, status code, cache disposition (fresh generation, reuse, or cache skip), cookie header, tracked custom header, and body, so the keying behaviour is visible through which requests reuse earlier responses.",
    "cases": [
        {
            "input": {"action": "cache", "upstream": {"cacheControl": "public, max-age=60", "bodyMode": "constant", "body": "Hello"}, "requests": [{"url": "http://example.com/one"}, {"url": "http://example.com/two"}, {"url": "http://example.com/three"}, {"url": "http://example.com/three"}]},
            "expected_output": "request=0\nstatus=200\nx_cache=miss\nset_cookie=-\nextra=-\nbody=Hello\nrequest=1\nstatus=200\nx_cache=miss\nset_cookie=-\nextra=-\nbody=Hello\nrequest=2\nstatus=200\nx_cache=miss\nset_cookie=-\nextra=-\nbody=Hello\nrequest=3\nstatus=200\n[a specific query key value]\nset_cookie=-\nextra=-\nbody=Hello\n"
        },
        {
            "input": {"action": "cache", "upstream": {"cacheControl": "public, max-age=60", "bodyMode": "constant", "body": "Hello"}, "requests": [{"url": "http://example.com?a=1&b=2"}, {"url": "http://example.com?a=1&b=2"}, {"url": "http://example.com?b=2&a=1"}]},
            "expected_output": "request=0\nstatus=200\nx_cache=miss\nset_cookie=-\nextra=-\nbody=Hello\nrequest=1\nstatus=200\n[a specific query key value]\nset_cookie=-\nextra=-\nbody=Hello\nrequest=2\nstatus=200\n[a specific query key value]\nset_cookie=-\nextra=-\nbody=Hello\n"
        }
    ]
}
```

*2.3 Variant negotiation — varying a stored entry by named request headers*

When the origin response declares that it varies by one or more request header fields, exactly those request header values become part of the cache key, so clients sending different values for the named headers get distinct stored variants while differences in unnamed headers are ignored. With several varying fields, a stored variant is replayed only when every named header matches. The origin echoes the negotiated value into the body so each variant is observable.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_vary.json`

```json
{
    "description": "When an origin response declares that it varies by one or more request header fields, the caching layer incorporates exactly those request header values into the cache key, so that clients sending different values for the named headers receive distinct stored variants while differences in unnamed headers are ignored. The origin echoes the negotiated header value into its body so each variant is observable. With multiple varying header fields, a stored variant is reused only when every named header matches. Output per request reports the request index, status code, cache disposition, cookie header, tracked custom header, and the negotiated body.",
    "cases": [
        {
            "input": {"action": "cache", "upstream": {"cacheControl": "public, max-age=600", "vary": "Accept", "bodyMode": "echoAccept"}, "requests": [{"url": "http://example.com", "headers": {"Accept": "application/json", "Other": "a"}}, {"url": "http://example.com", "headers": {"Accept": "application/json", "Other": "b"}}, {"url": "http://example.com", "headers": {"Accept": "[a detected content type]", "Other": "a"}}, {"url": "http://example.com", "headers": {"Accept": "[a detected content type]", "Other": "a"}}, {"url": "http://example.com", "headers": {"Accept": "application/json", "Other": "b"}}]},
            "expected_output": "request=0\nstatus=200\nx_cache=miss\nset_cookie=-\nextra=-\nbody=application/json\nrequest=1\nstatus=200\n[a specific query key value]\nset_cookie=-\nextra=-\nbody=application/json\nrequest=2\nstatus=200\nx_cache=miss\nset_cookie=-\nextra=-\nbody=[a detected content type]\nrequest=3\nstatus=200\n[a specific query key value]\nset_cookie=-\nextra=-\nbody=[a detected content type]\nrequest=4\nstatus=200\n[a specific query key value]\nset_cookie=-\nextra=-\nbody=application/json\n"
        }
    ]
}
```

---

### Feature 3: Accelerated Static File Delivery (X-Sendfile)

**As a developer**, I want the origin to hand off sending a static file to the front-end by naming a path on disk, so large assets are streamed efficiently without the application reading them into memory.

**Expected Behavior / Usage:**

When the feature is enabled the front-end advertises support to the origin via a request header. If the origin's response then carries the delegation header naming a file path, the front-end reads that file from disk and sends its contents as the body — discarding any body the origin wrote — strips the delegation header from the client-visible response, sets `Content-Length` to the true on-disk size and infers `Content-Type` by sniffing the file. Critically, even when the origin marked the response with a `Content-Encoding`, the front-end still overrides `Content-Length` with the real file size rather than passing through the origin's (possibly zero) value, which prevents truncated downloads. If no delegation header is present, the origin's own status, headers and body are returned untouched. When the feature is disabled the front-end neither advertises support nor intercepts the delegation header, so the header passes straight through. The contract reports status, `Content-Type`, `Content-Length`, `Content-Encoding`, the final state of the delegation header, and the body.

**Test Cases:** `rcb_tests/public_test_cases/feature3_sendfile.json`

```json
{
    "description": "An accelerated file-delivery feature lets the origin delegate sending a static file to the proxy by returning a header naming a path on disk instead of writing the file body itself. When the feature is enabled, the proxy advertises support to the origin (a request header), and on seeing the delegation header it reads the named file from disk, sends its contents as the response body (discarding any body the origin wrote), strips the delegation header, and sets the Content-Length to the real file size and the Content-Type by sniffing the file. Crucially, even when the origin marked the response with a Content-Encoding, the proxy still sets Content-Length to the true on-disk size rather than passing through the origin's (possibly zero) value, preventing truncated responses. If no delegation header is present the origin's own response (status, headers, body) is returned untouched. When the feature is disabled the proxy neither advertises support nor intercepts the delegation header, which then passes straight through. Output reports the status, Content-Type, Content-Length, Content-Encoding, the delegation header's final state, and the body.",
    "cases": [
        {
            "input": {"action": "sendfile", "enabled": true, "request": {"method": "GET", "path": "/"}, "upstream": {"fileContent": "Sendfile body contents.\n", "body": "this body should not be seen"}},
            "expected_output": "status=200\ncontent_type=[a detected content type]; charset=utf-8\ncontent_length=24\ncontent_encoding=-\nx_sendfile=-\nbody=Sendfile body contents.\n\n"
        },
        {
            "input": {"action": "sendfile", "enabled": false, "request": {"method": "GET", "path": "/"}, "upstream": {"fileContent": "irrelevant\n", "contentType": "application/custom", "status": 418, "body": "This body should be seen"}},
            "expected_output": "status=418\ncontent_type=application/custom\ncontent_length=-\ncontent_encoding=-\nx_sendfile=<passthrough>\nbody=This body should be seen\n"
        }
    ]
}
```

---

### Feature 4: Structured Access Logging

**As a developer**, I want one structured record summarizing every completed request, so I get uniform observability regardless of what the origin does.

**Expected Behavior / Usage:**

A logging stage wraps request handling and, after the response completes, emits exactly one record capturing: the request path (without the query string), the HTTP method, the final response status code, the client address (taken from the forwarded-for header when present), the user agent, the request and response `Content-Type` values, the request body length and the number of response bytes written, the raw query string, and the cache disposition reported downstream. Timing-related fields are deliberately excluded from the contract. The fields are rendered as neutral key/value lines.

**Test Cases:** `rcb_tests/public_test_cases/feature4_logging.json`

```json
{
    "description": "A logging middleware wraps the request handling and emits one structured record summarizing each completed request. The record captures the request path (without query string), HTTP method, final response status code, the client address (taken from the forwarded-for header when present), the user agent, the request and response Content-Type values, the request body length and the number of response bytes written, the raw query string, and the cache disposition reported downstream. Timing-related fields are excluded. Output renders the captured fields as neutral key/value lines.",
    "cases": [
        {
            "input": {"action": "logging", "request": {"method": "POST", "path": "/somepath", "query": "q=ok", "body": "hello", "headers": {"X-Forwarded-For": "192.168.1.1", "User-Agent": "Robot/1", "Content-Type": "application/json"}}, "response": {"status": 201, "headers": {"X-Cache": "miss", "Content-Type": "text/html"}, "body": "goodbye\n"}},
            "expected_output": "path=/somepath\nmethod=POST\nstatus=201\nremote_addr=192.168.1.1\nuser_agent=Robot/1\nreq_content_type=application/json\nresp_content_type=text/html\nreq_content_length=5\nresp_content_length=8\nquery=q=ok\ncache=miss\n"
        }
    ]
}
```

---

### Feature 5: In-Memory Cache Store

**As a developer**, I want a bounded in-memory key/value store with per-entry expiry, so cached responses live somewhere with predictable capacity and size limits.

**Expected Behavior / Usage:**

The store holds byte payloads under numeric keys, each with an expiry time, governed by a total capacity and a per-item size limit. Storing a key records its payload; storing the same key again replaces the previous payload. Retrieving a key returns its current payload when present and not yet expired. A payload whose size exceeds the total capacity (or the per-item limit) is rejected outright and never becomes retrievable. The contract reports, per operation, either the stored payload length or the retrieval outcome (a found flag with the payload, or the payload length for large values).

**Test Cases:** `rcb_tests/public_test_cases/feature5_memcache.json`

```json
{
    "description": "An in-memory key/value store holds byte payloads under numeric keys with a per-entry expiry time, a total capacity and a per-item size limit. Storing a key records its payload; storing the same key again replaces the prior payload. Retrieving a key returns its current payload when present and unexpired. An item whose size exceeds the total capacity (or the per-item limit) is rejected and never becomes retrievable. Output reports, per operation, either the stored payload length or the retrieval outcome (found flag plus the payload, or the payload length for large values).",
    "cases": [
        {
            "input": {"action": "memcache", "capacity": 33554432, "maxItemSize": 1048576, "operations": [{"op": "set", "key": 1, "value": "hello world", "ttlSeconds": 30}, {"op": "get", "key": 1}]},
            "expected_output": "set key=1 value_len=11\nget key=1 found=true value=hello world\n"
        },
        {
            "input": {"action": "memcache", "capacity": 3072, "maxItemSize": 51200, "operations": [{"op": "set", "key": 1, "valueSize": 10240, "ttlSeconds": 3600}, {"op": "get", "key": 1}]},
            "expected_output": "set key=1 value_len=10240\nget key=1 found=false [a specific sentinel payload value]\n"
        }
    ]
}
```

---

### Feature 6: Configuration From Environment

**As a developer**, I want runtime settings resolved from process arguments and environment variables with sensible defaults, so the front-end is configured the way a containerized service expects.

**Expected Behavior / Usage:**

The first positional argument is the upstream command to launch; if it is absent, configuration loading fails with a normalized error. Every tunable setting has a built-in default that an environment variable may override. A variable may be supplied either bare or with a fixed namespace prefix, and the prefixed form takes precedence over the bare form when both are present. A debug flag raises the log level from its default. The resolved settings are reported as neutral key/value lines (port, upstream command, cache size in bytes, max request body, accelerated-delivery flag, read timeout in seconds, certificate-authority directory URL, log level), or a single normalized error line when the required upstream command is missing.

**Test Cases:** `rcb_tests/public_test_cases/feature6_config.json`

```json
{
    "description": "A configuration loader builds the runtime settings from process arguments and environment variables. The first positional argument is the upstream command to run; if it is missing, loading fails. Every tunable setting has a default that is overridden by an environment variable; a variable may be given either bare or with a fixed namespace prefix, and the prefixed form takes precedence over the bare form. A debug flag raises the log level. Output reports the resolved settings as neutral key/value lines, or a normalized error when the required upstream command is absent.",
    "cases": [
        {
            "input": {"action": "config", "args": ["server", "echo", "hello"], "env": {}},
            "expected_output": "target_port=3000\nupstream_command=echo\ncache_size=67108864\nmax_request_body=0\nx_sendfile_enabled=true\nhttp_read_timeout_seconds=30\nacme_directory=https://acme-v02.api.letsencrypt.org/directory\nlog_level=info\n"
        },
        {
            "input": {"action": "config", "args": ["server"], "env": {}},
            "expected_output": "error=missing_upstream_command\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the reverse proxy, response cache (with keying and variant negotiation), accelerated file delivery, access logging, in-memory store and configuration loader described above, each as a cohesive unit with a small public interface.

2. **The Execution/Test Adapter:** A runnable program that reads one JSON command from stdin, invokes the appropriate core component, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. The adapter is the only place that touches stdin/stdout and JSON, and the only place that normalizes any native error into the neutral `error=<category>` form.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the bodyMode sequence counter pattern
- apply the upstream forwarding exact protocol
