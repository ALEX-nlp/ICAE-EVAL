## Product Requirement Document

# Minimal HTTP Client Polyfill & Universal Transport Resolver - PRD

## Project Goal

Build a tiny HTTP client library that gives developers a single, promise-based request API that works the same way in any JavaScript runtime. It transparently uses the runtime's built-in HTTP client when one exists and falls back to a minimal request engine when it does not, so application code never has to branch on the environment.

---

## Background & Problem

Without this library, developers who want to make HTTP requests must hand-roll low-level request objects, manually wire up load/error callbacks, parse raw header blobs, and decode response bodies themselves. They also have to write environment-detection code so the same module works in a browser-like runtime (where a native client may already exist) and in a server-like runtime (where a different HTTP backend is needed). This leads to repetitive, error-prone boilerplate and modules that silently break when moved between environments.

With this library, the developer calls one function with a URL and an options object and gets back a promise that resolves to a uniform response object with text/JSON/clone/header helpers. A companion resolver picks the right transport for the current runtime automatically, so the exact same import works on the client and on the server.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a micro-utility: a small, well-organized core (the request engine and the environment resolver) is appropriate. Keep clean logical separation between the request engine, the response wrapper, and the environment resolver; avoid bundling unrelated concerns into one undifferentiated blob.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box testing contract** for an execution adapter, NOT the internal data model of the core library. The core request engine must remain decoupled from stdin/stdout and JSON command parsing. The execution adapter alone translates JSON commands into idiomatic calls against the core library and formats the result.

3. **Adherence to SOLID Design Principles:** Separate request construction, transport dispatch, response wrapping, header parsing, and environment resolution into distinct logical units. The core engine should be open for extension (new transports) but closed for modification, and high-level code should depend on the abstract "transport" idea rather than a concrete backend.

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic — a single promise-returning request function plus a response object with helper methods. The library must degrade gracefully: when a native client is present it must be used directly; when it is absent the fallback engine must take over without the caller changing anything.

---

## Core Features

### Feature 1: Issue an HTTP request

**As a developer**, I want to issue an HTTP request by passing a URL and an options object, so I can send requests without manually constructing a low-level request object.

**Expected Behavior / Usage:**

The request function accepts a target URL and an optional options object containing a method, a set of request headers, and a body. It opens a request using the given method, defaulting to a GET when no method is supplied. Every header in the supplied header map is forwarded to the underlying transport. When a body is supplied it is sent with the request; when no body is supplied the request is still dispatched with no body. The observable contract reports whether the request was actually dispatched, the resolved method, the target URL, each forwarded header, and whether/what body was sent.

**Test Cases:** `rcb_tests/public_test_cases/feature1_request.json`

```json
{
    "description": "Issue an HTTP request through the client. The client opens a request with the requested method (defaulting to a GET when none is given), forwards every supplied request header to the underlying transport, and sends the request body when provided. The contract reports whether the request was actually dispatched, the resolved method, the target URL, each forwarded header, and the body.",
    "cases": [
        {
            "input": {"op": "request", "request": {"url": "/foo", "headers": {"a": "b"}}},
            "expected_output": "dispatched=true\nmethod=get\nurl=/foo\n[the specific key name mismatch found in unit test logs — grep for test failures regarding key access]=b\nbody_present=false"
        },
        {
            "input": {"op": "request", "request": {"url": "/foo", "method": "POST", "body": "hello", "headers": {"a": "b", "c": "d"}}},
            "expected_output": "dispatched=true\nmethod=POST\nurl=/foo\n[the specific key name mismatch found in unit test logs — grep for test failures regarding key access]=b\nheader[c]=d\nbody_present=true\nbody=hello"
        }
    ]
}
```

---

### Feature 2: Read the response body

**As a developer**, I want to read the response body either as raw text or as parsed JSON, so I can consume payloads without writing my own decoding logic.

**Expected Behavior / Usage:**

*2.1 Read as text — the text reader returns the raw payload unchanged*

The response exposes a text reader that resolves to the response payload exactly as received, with no transformation. The contract reports the raw text.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_read_text.json`

```json
{
    "description": "Read the response body as plain text. The text reader resolves to the raw response payload exactly as received from the transport.",
    "cases": [
        {
            "input": {"op": "read", "mode": "text", "request": {"url": "/foo"}, "transport": {"responseText": "plain body"}},
            "expected_output": "text=plain body"
        }
    ]
}
```

*2.2 Read as JSON — the JSON reader parses the payload into structured fields*

The response exposes a JSON reader that parses the payload and resolves to the decoded object. The contract lists the decoded fields in sorted key order so the result is deterministically verifiable.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_read_json.json`

```json
{
    "description": "Read the response body as parsed JSON. The JSON reader parses the response payload and exposes its fields. Keys are emitted in sorted order so the decoded object can be verified deterministically.",
    "cases": [
        {
            "input": {"op": "read", "mode": "json", "request": {"url": "/foo"}, "transport": {"responseText": "{\"a\":\"b\"}"}},
            "expected_output": "json[a]=b"
        },
        {
            "input": {"op": "read", "mode": "json", "request": {"url": "/u"}, "transport": {"responseText": "{\"name\":\"ada\",\"age\":36}"}},
            "expected_output": "[the specific key name mismatch found in unit test logs — grep for test failures regarding key access]=36\njson[name]=ada"
        }
    ]
}
```

---

### Feature 3: Inspect and clone the response

**As a developer**, I want the response to expose the final URL and let me clone it, so I can reuse the response in more than one place and follow redirects.

**Expected Behavior / Usage:**

The response carries the final, possibly redirected, URL it was served from. It also supports a clone operation that returns a separate response object (not the same instance) carrying the same observable data, including the same final URL. The contract reports the response URL, whether the clone is a distinct object from the original, and the clone's URL.

**Test Cases:** `rcb_tests/public_test_cases/feature3_response.json`

```json
{
    "description": "Inspect the response object. The response exposes the final (possibly redirected) URL and a clone operation that returns a distinct response object carrying the same observable data. The contract reports the response URL, whether the clone is a different object than the original, and the clone's URL.",
    "cases": [
        {
            "input": {"op": "response", "request": {"url": "/foo"}, "transport": {"responseURL": "/foo?redirect"}},
            "expected_output": "url=/foo?redirect\nclone_is_same_object=false\nclone.url=/foo?redirect"
        }
    ]
}
```

---

### Feature 4: Case-insensitive response headers

**As a developer**, I want to query response headers without worrying about field-name casing or duplicate fields, so I can read headers reliably.

**Expected Behavior / Usage:**

The response exposes a header collection that supports lookup by name and a presence check, both of which ignore the case of the field name. When the same field appears multiple times in the response, its values are joined with commas in the order they arrived. A field that is present but has an empty value reports as present with an empty string. Looking up a field that does not exist returns an empty value and reports as not present.

**Test Cases:** `rcb_tests/public_test_cases/feature4_headers.json`

```json
{
    "description": "Query response headers case-insensitively. Header lookups ignore case for the field name. When the same field appears multiple times its values are joined with commas in arrival order. A present field with an empty value is still reported as present with an empty string. Looking up an absent field yields an empty value and a not-present result.",
    "cases": [
        {
            "input": {"op": "headers", "request": {"url": "/foo"}, "transport": {"responseHeaders": "X-Foo: bar\nX-Foo:baz"}, "queries": ["x-foo", "x-missing"]},
            "expected_output": "get[x-foo]=bar,baz\nhas[x-foo]=true\nget[x-missing]=\nhas[x-missing]=false"
        },
        {
            "input": {"op": "headers", "request": {"url": "/foo"}, "transport": {"responseHeaders": "Server: \nX-Foo:baz"}, "queries": ["server", "X-foo"]},
            "expected_output": "get[server]=\nhas[server]=true\nget[X-foo]=baz\nhas[X-foo]=true"
        }
    ]
}
```

---

### Feature 5: Delegate to a native client when present

**As a developer**, I want the library to use the runtime's built-in HTTP client when one already exists, so I get native behavior with zero configuration.

**Expected Behavior / Usage:**

When the runtime already provides a native HTTP client at load time, the exported request function delegates calls straight to that native client instead of using the fallback engine. The delegating function must remain safe to call even when it is detached from any receiver object (called as a bare function), and it must forward the requested URL to the native client unchanged. The contract reports that the native path was taken, the URL the native client received, and the native client's return value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_native_delegation.json`

```json
{
    "description": "Delegate to the native client when one is available. When the runtime already provides a native HTTP client, the exported function delegates calls to it rather than using the fallback transport. The delegating function works even when invoked without a receiver object, and forwards the requested URL unchanged to the native client.",
    "cases": [
        {
            "input": {"op": "delegate", "url": "/native"},
            "expected_output": "delegated=native\nnative_received_url=/native\nresult=native:/native"
        }
    ]
}
```

---

### Feature 6: Universal transport resolver

**As a developer**, I want a single entry point that automatically selects the correct HTTP transport for the current runtime, so the same import works on the client and the server.

**Expected Behavior / Usage:**

The resolver inspects the runtime and selects a transport, then routes requests through it. Across all entry points, if a native client is already available it is always chosen. The behavior when no native client exists depends on the entry point and the runtime, described per leaf below. In every case the resolver reports which transport was selected (`native`, `polyfill`, or `server`) and the URL routed through it.

*6.1 Client-only entry — falls back to the bundled polyfill*

This entry point is intended for browser-like runtimes. If a native client exists it is selected; otherwise the bundled minimal polyfill engine is selected. The chosen transport routes the requested URL unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_resolver_browser_entry.json`

```json
{
    "description": "Browser-targeted resolver. In a browser-like environment the resolver selects the runtime's native client when one exists, otherwise it falls back to the bundled polyfill transport. The resolved transport routes the requested URL unchanged. The contract reports which transport was selected and the URL it routed.",
    "cases": [
        {
            "input": {"op": "resolve", "entry": "browser", "has_native_fetch": true, "url": "/p"},
            "expected_output": "selected=native\nrouted_url=/p"
        },
        {
            "input": {"op": "resolve", "entry": "browser", "has_native_fetch": false, "url": "/p"},
            "expected_output": "selected=polyfill\nrouted_url=/p"
        }
    ]
}
```

*6.2 Universal entry in a browser-like runtime — falls back to the bundled polyfill*

Using the universal entry point inside a browser-like runtime: if a native client exists it is selected; otherwise the bundled polyfill engine is selected. The chosen transport routes the requested URL unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_resolver_universal_browser.json`

```json
{
    "description": "Universal entry resolver in a browser-like environment. Using the universal entry point inside a browser-like runtime, the resolver selects the native client when one exists, otherwise it falls back to the bundled polyfill transport. The resolved transport routes the requested URL unchanged.",
    "cases": [
        {
            "input": {"op": "resolve", "entry": "main", "server": false, "has_native_fetch": true, "url": "/p"},
            "expected_output": "selected=native\nrouted_url=/p"
        },
        {
            "input": {"op": "resolve", "entry": "main", "server": false, "has_native_fetch": false, "url": "/p"},
            "expected_output": "selected=polyfill\nrouted_url=/p"
        }
    ]
}
```

*6.3 Universal entry in a server-like runtime — falls back to a server transport and normalizes URLs*

Using the universal entry point inside a server-like runtime: if a native client exists it is selected; otherwise requests are routed through a server-side HTTP transport. The server transport additionally normalizes a protocol-relative URL — one beginning with a double slash — into an absolute secure (`https://`) URL before issuing the request.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_resolver_universal_server.json`

```json
{
    "description": "Universal entry resolver in a server-like environment. Using the universal entry point inside a server-like runtime, the resolver selects the native client when one exists. When no native client exists it routes through the server-side HTTP transport, which additionally normalizes a protocol-relative URL (leading double slash) into an absolute secure URL before issuing the request.",
    "cases": [
        {
            "input": {"op": "resolve", "entry": "main", "server": true, "has_native_fetch": true, "url": "/p"},
            "expected_output": "selected=native\nrouted_url=/p"
        },
        {
            "input": {"op": "resolve", "entry": "main", "server": true, "has_native_fetch": false, "url": "//p"},
            "expected_output": "selected=server\nrouted_url=https://p"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, small codebase implementing the request engine, the uniform response wrapper (text/JSON/clone/case-insensitive headers), the native-client delegation, and the universal transport resolver described above. The physical structure must align with the "Scale-Driven Code Organization" constraint — a compact, well-separated micro-utility, not a monolithic blob.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain, and it is solely responsible for normalizing any error into a language-neutral category line.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_request.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_request@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the exact casing logic defined in the invariant_assertion module
