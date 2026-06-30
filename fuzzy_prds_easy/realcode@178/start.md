## Product Requirement Document

# HTTP Message & Middleware Composition Toolkit - A Library for Modeling Web Requests, Responses, Routing and Composable Handlers

## Project Goal

Build a library that models HTTP requests and responses as immutable, inspectable message objects and lets developers compose request handling out of small, reusable pieces (handlers, middleware, cascades) without re-implementing header parsing, body buffering, content negotiation, routing arithmetic, or transfer-coding by hand. The library exposes a uniform message abstraction (shared by both requests and responses) plus composition primitives so that an application's request/response flow can be assembled declaratively and reasoned about as data.

---

## Background & Problem

Without such a library, developers writing web servers must repeatedly hand-roll the same low-level machinery: normalizing case-insensitive headers, reconciling single-valued and multi-valued header views, computing a body's content length from its bytes vs. its headers, decoding a body using the right character set, splitting a requested URI into "the part this handler owns" vs. "the part still to be routed", and wiring cross-cutting concerns (logging, error handling, redirects) around a core handler. This leads to repetitive, error-prone boilerplate, inconsistent edge-case handling, and tangled control flow that is hard to test.

With this library, a message is an immutable value object you can construct, inspect, and copy-with-changes; a handler is just a function from a request to a response; and middleware, cascades, and transfer-coding wrappers are composable adapters that turn handlers into bigger handlers. Application code declares *what* should happen at each layer and the library guarantees consistent, well-specified behavior for headers, bodies, routing, status semantics, and streaming.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (message model, header normalization, body buffering/encoding, request routing math, response semantics, and handler composition). It MUST NOT be a single "god file". Output a clear, multi-file directory tree that separates the message/body model, the request and response types, and the composition primitives (cascade, pipeline/middleware, transfer-coding wrapper). Do not over-engineer, but reflect a production-grade repository structure.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below define a **black-box testing contract** for an execution adapter, NOT the internal data model of the core system. The core library must remain completely decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating each JSON command into idiomatic calls on the core types and rendering the observable result.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units. The core composition engine must be open for extension (new handlers/middleware) but closed for modification. A request and a response must both be substitutable wherever the shared message abstraction is expected. Keep interfaces small and cohesive; high-level composition must depend on the handler abstraction, not on any I/O implementation.

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language, hiding internal complexity. The system must handle edge cases gracefully and model errors properly: invalid arguments, illegal state (such as reading a body twice), and malformed input must surface as distinct, well-typed error conditions rather than generic faults.

---

## I/O Contract for the Execution Adapter

The execution adapter reads exactly **one JSON object** from stdin describing an `action` plus its parameters, performs the corresponding operation against the core library, and writes a deterministic, line-oriented report to stdout. Conventions used throughout:

- Output is a sequence of `key=value` lines, each terminated by `\n`. Where a feature emits a map view, keys are emitted in ascending sorted order.
- A header map in the input is an object whose values are either a string (single value) or an array of strings (multiple values). Header names are case-insensitive.
- A body spec in the input is one of: `null` (no body); a string; an array of integers (raw bytes); `{"type":"bytes","value":[...]}`; `{"type":"string","value":"..."}`; `{"type":"stream","chunks":[[...],...]}` (a stream of byte chunks, length unknown); or `{"type":"empty_stream"}` (an empty stream, length unknown).
- An `encoding` field names a character set (`utf8`, `latin1`/`iso-8859-1`, `ascii`).
- **Errors are normalized to a language-neutral contract.** An invalid argument emits `error=invalid_argument` plus, when available, a `field=<argument name>` line and a `message=<domain message>` line. An illegal-state condition emits `error=invalid_state` with a `message=` line. A malformed value emits `error=format`. Any other failure emits `error=failure`. No host-language exception class names or runtime-specific text appear in stdout.

---

## Core Features

### Feature 1: Header Model — Single vs. Multi-Valued Views

**As a developer**, I want to construct a message from a header map and inspect both a single-valued and a multi-valued view of its headers, so I can read headers conveniently regardless of how many values a name carries.

**Expected Behavior / Usage:**

A message is built from a header map whose values are each a string or a list of strings. The single-valued view maps every header name to its values joined by `,`; the multi-valued view maps every name to the list of its values. Header names are case-insensitive. A message constructed with no body and no explicit headers still reports a `content-length` of `0`. The output emits the single-valued view (`headers[name]=joined`) followed by the multi-valued view (`headersAll[name]=[json array]`), each with names in sorted order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_header_model.json`

```json
{
  "description": "Construct an HTTP message from a header map whose values may be a single string or a list of strings, then inspect both header views. The single-valued view maps each name to its values joined by commas; the multi-valued view preserves the list per name. Header names are case-insensitive. A message built with no body and no explicit headers carries a default content-length of 0.",
  "cases": [
    {
      "input": {
        "action": "msg_headers",
        "headers": {
          "a": "A",
          "b": [
            "B1",
            "B2"
          ]
        }
      },
      "expected_output": "headers[a]=A\nheaders[b]=B1,B2\nheaders[content-length]=0\nheadersAll[a]=[\"A\"]\nheadersAll[b]=[\"B1\",\"B2\"]\nheadersAll[content-length]=[\"0\"]\n"
    }
  ]
}
```

---

### Feature 2: Content Length Determination

**As a developer**, I want the content length of a message to be derived consistently from its body and headers, so I can rely on a single rule for known vs. unknown body sizes.

**Expected Behavior / Usage:**

A string or byte body yields the byte length of the encoded body, and this computed length always takes precedence over any `content-length` header. A body whose size cannot be determined ahead of time (a stream) yields no length unless a `content-length` header supplies one. A non-identity `transfer-encoding` suppresses any computed length (yielding none), whereas an `identity` transfer-encoding does not. The output is a single line `contentLength=<n>` or `contentLength=null`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_content_length.json`

```json
{
  "description": "Determine the content length of a message from its body and headers. A string or byte body yields the byte length of the encoded body and always takes precedence over any content-length header. A body whose length cannot be determined (a stream) yields no length unless a content-length header supplies one. A non-identity transfer-encoding suppresses the computed length; an identity transfer-encoding does not.",
  "cases": [
    {
      "input": {
        "action": "msg_content_length",
        "body": [
          1,
          2,
          3
        ]
      },
      "expected_output": "contentLength=3\n"
    },
    {
      "input": {
        "action": "msg_content_length",
        "body": {
          "type": "empty_stream"
        }
      },
      "expected_output": "contentLength=null\n"
    }
  ]
}
```

---

### Feature 3: Content Negotiation — MIME Type & Encoding

**As a developer**, I want to read a message's MIME type and character encoding from its content-type header, and have an explicit body encoding rewrite that header, so I can negotiate content consistently.

**Expected Behavior / Usage:**

The MIME type is the bare media type with no parameters. The encoding is taken from the `charset` parameter and is absent when there is no charset or the charset is unknown. When an explicit body encoding is supplied, the content-type's charset is set to match it; if no content-type header was present, the media type defaults to `application/octet-stream`. The output emits `mimeType=...`, `encoding=...` (the charset name, or `null`), then the single-valued header view in sorted order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_content_negotiation.json`

```json
{
  "description": "Derive the MIME type and character encoding of a message from its content-type header, and observe how supplying an explicit body encoding rewrites that header. The MIME type is the bare media type without parameters. The encoding comes from the charset parameter and is absent when there is no charset or the charset is unknown. When an explicit encoding is given, the charset of the content-type is set accordingly, defaulting the media type to application/octet-stream when no content-type was present.",
  "cases": [
    {
      "input": {
        "action": "msg_content_type",
        "headers": {
          "content-type": "text/plain; charset=iso-8859-1"
        }
      },
      "expected_output": "mimeType=text/plain\nencoding=iso-8859-1\nheaders[content-length]=0\nheaders[content-type]=text/plain; charset=iso-8859-1\n"
    },
    {
      "input": {
        "action": "msg_content_type",
        "body": "è",
        "encoding": "latin1"
      },
      "expected_output": "mimeType=application/octet-stream\nencoding=iso-8859-1\nheaders[content-length]=1\nheaders[content-type]=application/octet-stream; charset=iso-8859-1\n"
    }
  ]
}
```

---

### Feature 4: Body Reading — Text, Bytes, and Read-Once

**As a developer**, I want to read a message body once, either as decoded text or as raw bytes, so I can consume the payload while being protected against accidental double reads.

**Expected Behavior / Usage:**

Reading as text decodes the bytes using, in order of precedence, an explicit encoding argument, then the content-type charset, then UTF-8. Reading as raw bytes returns the body unchanged. A string body is encoded to bytes using the message's encoding. The body may be read only once; a second read fails with a neutral illegal-state error. For text mode the output is `body=<text>`; the read-once case emits `first=read` then the normalized error lines `error=invalid_state` and `message=<domain message>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_body_read.json`

```json
{
  "description": "Read the body of a message. Reading as text decodes the bytes using, in order of precedence, an explicit encoding argument, the content-type charset, then UTF-8. Reading as raw bytes returns the body unchanged. A string body is encoded to bytes using the message encoding. The body may be read only once; a second read fails with a neutral state error.",
  "cases": [
    {
      "input": {
        "action": "msg_read",
        "mode": "string",
        "body": {
          "type": "bytes",
          "value": [
            195,
            168
          ]
        }
      },
      "expected_output": "body=è\n"
    },
    {
      "input": {
        "action": "msg_read",
        "mode": "twice"
      },
      "expected_output": "first=read\nerror=invalid_state\nmessage=The 'read' method can only be called once on a shelf.Request/shelf.Response object.\n"
    }
  ]
}
```

---

### Feature 5: Copy-With-Changes (Headers, Context, Body)

**As a developer**, I want to derive a modified copy of a message by applying targeted header/context changes and an optional new body, so I can transform messages immutably as they flow through layers.

**Expected Behavior / Usage:**

A change set maps names to new values. An entry set to `null` removes that name; an entry set to an empty list removes it; an entry set to a string or list replaces it; a name not present in the original is added. Passing an empty change set returns a copy that shares the same underlying header and context instances as the original (observable via identity flags). The body may also be replaced. The output emits the copy's single- and multi-valued header views and context (sorted), then `headersSame=<bool>` and `contextSame=<bool>` reporting whether the copy reused the originals' instances.

**Test Cases:** `rcb_tests/public_test_cases/feature5_message_change.json`

```json
{
  "description": "Create a copy of a message applying targeted changes. A header or context entry set to null is removed; set to an empty list is removed; set to a string or list replaces the value. New entries are added. Passing an empty change set returns the same underlying header and context instances. The body can be replaced with a new value.",
  "cases": [
    {
      "input": {
        "action": "change",
        "kind": "request",
        "base": {
          "headers": {
            "header1": "header value 1"
          }
        },
        "change": {
          "headers": {
            "header1": null
          },
          "context": {
            "context1": null
          }
        }
      },
      "expected_output": "headers[content-length]=0\nheadersAll[content-length]=[\"0\"]\nheadersSame=false\ncontextSame=true\n"
    },
    {
      "input": {
        "action": "change",
        "kind": "request",
        "base": {
          "headers": {
            "header1": "header value 1"
          }
        },
        "change": {
          "headers": {
            "header1": "new header value"
          }
        }
      },
      "expected_output": "headers[content-length]=0\nheaders[header1]=new header value\nheadersAll[content-length]=[\"0\"]\nheadersAll[header1]=[\"new header value\"]\nheadersSame=false\ncontextSame=true\n"
    }
  ]
}
```

---

### Feature 6: Request Routing Fields (url / handlerPath)

**As a developer**, I want a request to expose the path relative to the current handler and the root-relative path to that handler, so I can mount handlers at sub-paths and route correctly.

**Expected Behavior / Usage:**

A request is built from a method and an absolute requested URI. `url` is the resource path relative to the current handler (plus the original query string); `handlerPath` is the root-relative path leading to the current handler. The two can be inferred from one another, with a trailing slash appended to a non-empty handler path. Changing the path moves a leading segment from `url` into `handlerPath`. The protocol version defaults to `1.1`. A requested URI that is not absolute, and other malformed combinations, are reported via the neutral error contract (`error=invalid_argument`, `field=...`, `message=...`). The successful output emits `method=`, `protocolVersion=`, `url=`, `handlerPath=`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_request_routing.json`

```json
{
  "description": "Construct an HTTP request from a method and an absolute requested URI, and observe the routing fields. The url is the resource path relative to the current handler (plus the original query); handlerPath is the root-relative path to the current handler. They can be inferred from one another, with a trailing slash added to a non-empty handler path. Changing the path moves a leading segment from url into handlerPath. Invalid combinations and malformed arguments are reported as neutral errors. The protocol version defaults to 1.1.",
  "cases": [
    {
      "input": {
        "action": "request",
        "uri": "http://localhost/foo/bar?q=1"
      },
      "expected_output": "method=GET\nprotocolVersion=1.1\nurl=foo/bar?q=1\nhandlerPath=/\n"
    },
    {
      "input": {
        "action": "request",
        "uri": "/path"
      },
      "expected_output": "error=invalid_argument\nfield=requestedUri\nmessage=must be an absolute URL.\n"
    }
  ]
}
```

---

### Feature 7: Response Semantics & Factories

**As a developer**, I want semantic response constructors for success, arbitrary status, redirects, errors, and not-modified, so I can produce correct status codes, default bodies, and key headers without manual bookkeeping.

**Expected Behavior / Usage:**

Success and arbitrary-status responses carry the supplied body. Redirect responses set a `location` header and the matching 3xx status. Error responses default their body text and set a `text/plain` content-type when no body is supplied, while preserving any existing content-type parameters. A not-modified response uses status `304`, carries a date header, and has an empty body. A status code below `100` is rejected via the neutral error contract. The successful output emits `status=`, `contentType=` (or `null`), `location=` (or `null`), `hasDate=<bool>`, and `body=`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_responses.json`

```json
{
  "description": "Construct responses using their semantic factories and observe the resulting status code, body and key headers. Success and arbitrary-status responses carry the supplied body. Redirect responses set a location header and the corresponding 3xx status. Error responses default their body and set a text/plain content-type when no body is supplied, preserving any existing content-type parameters. A not-modified response uses status 304, carries a date header and an empty body. A status code below 100 is rejected as a neutral error.",
  "cases": [
    {
      "input": {
        "action": "response",
        "kind": "internalServerError"
      },
      "expected_output": "status=500\ncontentType=text/plain\nlocation=null\nhasDate=false\nbody=Internal Server Error\n"
    },
    {
      "input": {
        "action": "response",
        "kind": "found",
        "location": "/foo"
      },
      "expected_output": "status=302\ncontentType=null\nlocation=/foo\nhasDate=false\nbody=\n"
    }
  ]
}
```

---

### Feature 8: Conditional Date Headers

**As a developer**, I want conditional date headers parsed into timestamps, so I can implement caching/conditional logic without manual date parsing.

**Expected Behavior / Usage:**

A request exposes its `if-modified-since` header as a parsed UTC timestamp. A response exposes its `expires` and `last-modified` headers likewise. When the corresponding header is absent the value is `null`. Timestamps are rendered in ISO-8601 UTC form. The request case emits `ifModifiedSince=...`; the response case emits `expires=...` and `lastModified=...`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_date_headers.json`

```json
{
  "description": "Parse conditional date headers into timestamps. A request exposes its if-modified-since header as a parsed UTC timestamp; a response exposes its expires and last-modified headers likewise. When the corresponding header is absent the value is null.",
  "cases": [
    {
      "input": {
        "action": "dates",
        "kind": "request",
        "headers": {
          "if-modified-since": "Sun, 06 Nov 1994 08:49:37 GMT"
        }
      },
      "expected_output": "ifModifiedSince=1994-11-06T08:49:37.000Z\n"
    },
    {
      "input": {
        "action": "dates",
        "kind": "response",
        "headers": {
          "expires": "Sun, 06 Nov 1994 08:49:37 GMT"
        }
      },
      "expected_output": "expires=1994-11-06T08:49:37.000Z\nlastModified=null\n"
    }
  ]
}
```

---

### Feature 9: Cascade — First Acceptable Response

**As a developer**, I want to compose several handlers into a cascade that returns the first acceptable response, so I can try fallbacks in order.

**Expected Behavior / Usage:**

Handlers are tried in registration order. By default a response is unacceptable (causing the cascade to try the next handler) when its status is `404` or `405`; any other status is returned immediately. If every handler is unacceptable, the final handler's response is returned. The set of cascading statuses can be replaced either by an explicit list of status codes or by a predicate over the status code. An empty cascade, and supplying both a status list and a predicate at once, are reported via the neutral error contract. The output emits `status=` and `body=` of the chosen response.

**Test Cases:** `rcb_tests/public_test_cases/feature9_cascade.json`

```json
{
  "description": "Compose several handlers into a cascade that returns the first acceptable response. By default a response is unacceptable (causing the cascade to try the next handler) when its status is 404 or 405; otherwise it is returned immediately. If all handlers are unacceptable the final response is returned. The set of cascading statuses can be replaced by an explicit list or by a predicate over the status code. An empty cascade and the simultaneous use of both a status list and a predicate are reported as neutral errors.",
  "cases": [
    {
      "input": {
        "action": "cascade",
        "handlers": [
          {
            "type": "toggle",
            "header": "one",
            "body": "handler 1"
          },
          {
            "type": "toggle",
            "header": "two",
            "body": "handler 2"
          },
          {
            "type": "toggle",
            "header": "three",
            "body": "handler 3"
          }
        ],
        "requestHeaders": {
          "one": "false"
        }
      },
      "expected_output": "status=200\nbody=handler 2\n"
    },
    {
      "input": {
        "action": "cascade",
        "statusCodes": [
          302,
          403
        ],
        "handlers": [
          {
            "type": "found",
            "location": "/"
          },
          {
            "type": "forbidden",
            "body": "handler 2"
          },
          {
            "type": "notfound",
            "body": "handler 3"
          },
          {
            "type": "ok",
            "body": "handler 4"
          }
        ]
      },
      "expected_output": "status=404\nbody=handler 3\n"
    }
  ]
}
```

---

### Feature 10: Pipeline & Middleware Composition

**As a developer**, I want to wrap an inner handler with a pipeline of middleware that can inspect/short-circuit requests, transform responses, and handle errors, so I can layer cross-cutting concerns cleanly.

**Expected Behavior / Usage:**

Each middleware may run a request phase before the inner handler and a response phase after it. Request phases run outermost-first; response phases run innermost-first. A middleware's request phase may short-circuit by returning a response, in which case the inner handler and all response phases are skipped. A response phase may replace the response. If the inner handler throws, the error is offered to a middleware error phase, which may produce a replacement response or rethrow; errors thrown from request or response phases bypass the error phase. A hijack signal always propagates untouched. The output traces phase execution (e.g. `request:A`, `handler`, `response:A`) followed by `status=`, optional surfaced headers, and `body=`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_pipeline_middleware.json`

```json
{
  "description": "Compose middleware around an inner handler with a pipeline. Each middleware may inspect the request before the inner handler runs and the response afterwards; request processing runs outermost-first and response processing runs innermost-first. A middleware request phase may short-circuit by returning a response, in which case the inner handler and response phase are skipped. A response phase may replace the response. An error thrown by the inner handler is offered to a middleware error phase, which may produce a replacement response or rethrow; errors from the request or response phases bypass the error phase. A hijack signal always propagates untouched.",
  "cases": [
    {
      "input": {
        "action": "pipeline",
        "middlewares": [
          {
            "name": "A",
            "request": "pass",
            "response": "pass"
          },
          {
            "name": "B",
            "request": "pass",
            "response": "pass"
          }
        ],
        "handler": {
          "type": "trace",
          "body": "ok"
        }
      },
      "expected_output": "request:A\nrequest:B\nhandler\nresponse:B\nresponse:A\nstatus=200\nbody=ok\n"
    },
    {
      "input": {
        "action": "pipeline",
        "middlewares": [
          {
            "name": "A",
            "request": {
              "respond": {
                "status": 200,
                "headers": {
                  "from": "middleware"
                },
                "body": "middleware content"
              }
            },
            "response": "pass"
          }
        ],
        "handler": {
          "type": "fail"
        }
      },
      "expected_output": "request:A\nstatus=200\nfrom=middleware\nbody=middleware content\n"
    }
  ]
}
```

---

### Feature 11: Chunked Transfer Coding

**As a developer**, I want middleware that applies chunked transfer coding to streamed responses only when appropriate, so streaming bodies of unknown length are framed correctly while other responses pass through.

**Expected Behavior / Usage:**

Chunked coding is added (and the `transfer-encoding` header set to `chunked`) only when the response has no known content length, has a normal status (`>= 200`, not `204`, not `304`), is not `multipart/byteranges`, and does not already use a non-identity transfer-encoding. Otherwise the response is returned unchanged. When applied, the body is reframed into hex-size-prefixed chunks terminated by a zero-length chunk, with CRLF separators. The output emits `transferEncoding=` (`chunked` or `null`) and `body=<wire bytes>`; note the chunk framing uses literal carriage-return/line-feed pairs.

**Test Cases:** `rcb_tests/public_test_cases/feature11_chunked_encoding.json`

```json
{
  "description": "Wrap a handler with middleware that applies chunked transfer coding to streamed responses. Chunked coding is added (and the transfer-encoding header set) only when the response has no known content length, has a normal (>=200, not 204, not 304) status, is not multipart/byteranges, and does not already use a non-identity transfer-encoding. Otherwise the response passes through unchanged.",
  "cases": [
    {
      "input": {
        "action": "chunked",
        "kind": "ok",
        "body": {
          "type": "stream",
          "chunks": [
            [
              104,
              105
            ]
          ]
        }
      },
      "expected_output": "transferEncoding=chunked\nbody=2\r\nhi\r\n0\r\n\r\n\n"
    },
    {
      "input": {
        "action": "chunked",
        "kind": "ok",
        "body": "hi"
      },
      "expected_output": "transferEncoding=null\nbody=hi\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the message model (shared header/body/content-length/encoding logic), the request and response types (routing fields, semantic factories, conditional date accessors), and the composition primitives (cascade, pipeline/middleware, chunked-encoding wrapper). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-feature contracts above (including the neutral error contract). This adapter must be logically and physically separated from the core domain; all translation of native exceptions into `error=<category>` lines happens here, never in the core.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw program stdout (no PASS/FAIL or metadata), so it can be byte-compared directly against `expected_output`. Output is namespaced by `<cases-dir>` so different case directories never overwrite each other.
```


---
**Implementation notes:**
- maintain consistency with the sorting logic used in the request body serialization module
- adhere to the protocol negotiation strategy defined in the HTTP/1.1 handshake helper
