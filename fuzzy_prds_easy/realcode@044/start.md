## Product Requirement Document

# Serverless HTTP Gateway Proxy for In-Process Web Frameworks - Run a standard web application as a serverless function handler

## Project Goal

Build a library that lets a developer take an ordinary in-process web framework application (with its routes, hooks, body parsers and plugins) and expose it directly as a serverless function handler. The library translates an incoming HTTP gateway invocation event into a single in-memory request against the framework, then translates the framework's response back into the gateway result shape. The developer benefits by reusing one application unchanged across both a long-running server and a serverless deployment, without spinning up a real network socket per invocation.

---

## Background & Problem

Without this library, developers deploying a web application as a serverless function must hand-write glue for every invocation: pull the method, path, query, headers and body out of the gateway event; rebuild a request; boot or reuse an HTTP listener; capture the response; and reshape status, headers, cookies and body back into the gateway's expected payload. They must also juggle several incompatible event encodings (gateway payload format 1.0 vs 2.0, and load-balancer events), base64-encoded bodies and binary responses, multi-valued headers and query parameters, stage-prefixed paths, and cookie handling differences between formats. This glue is repetitive, easy to get subtly wrong, and tightly coupled to one framework's internals.

With this library, the developer wraps the application once and receives a handler function. The handler accepts the raw invocation event (and optional context) and returns the gateway result. All the encoding/decoding, normalization and edge-case handling described in the features below happen inside the library, so the application code stays a normal web app.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. The core translation logic (event-in / result-out) is cohesive enough to live in a small, well-organized module, but the request-side translation, response-side translation, encoding decisions and option handling MUST be cleanly separated as logical units. The execution/test adapter MUST be physically separate from the core library.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below describe a **black-box contract for the execution adapter**, not the core library's data model. The core library exposes a function that takes an application plus options and returns a handler; it knows nothing about stdin/stdout or the JSON scenario format. The adapter is solely responsible for building an application from a JSON scenario, invoking the handler, and rendering the language-neutral line projection.

3. **Adherence to SOLID Design Principles:** Separate event parsing, URL/path resolution, query parsing, header translation, response rendering, binary-encoding decision and option resolution into distinct units. The encoding decision MUST be open for extension via a caller-supplied predicate without modifying the core. High-level translation must depend on abstractions, not on a concrete I/O channel.

4. **Robustness & Interface Design:** The public interface must be a single idiomatic factory that returns a handler usable both as an awaited promise and via a node-style callback. The system must degrade gracefully: an unexpected internal failure during request processing must produce a well-formed error result rather than propagate a raw runtime fault.

---

## Adapter I/O Contract (how to read the cases)

The execution adapter reads one JSON **scenario** object from stdin. A scenario describes how to build the application and how to invoke the handler:

- `options` — options passed to the library factory (e.g. `serializeLambdaArguments`, `binaryMimeTypes`, `retainStage`, `pathParameterUsedAsPath`, `parseCommaSeparatedQueryParams`, `callbackWaitsForEmptyEventLoop`, `decorateRequest`).
- `enforceBase64` — `{ "header": <name>, "equals": <value> }`, declaratively building a predicate that returns true when the named response header equals the value.
- `multipart` — when true, register a multipart/form-data body parser that attaches parsed fields to the request body.
- `route` — `{ "method", "path", "reply" }`. `reply` describes what the handler does: `headers` to set (string or array values), `removeContentType`, `status`, and a `body` whose `type` is one of `json`, `text`, `bytes` (Base64 of raw bytes to send), `echoQuery` (send the parsed query), `echoBody` (send the parsed body), `echoMultipart` (send normalized metadata of the listed parsed `fields`), or `empty`.
- `probe` — request fields to read inside the handler and emit, as dot paths into `{ headers, query, body, url, awsLambdaEvent, awsLambdaContext }`.
- `onRequestProbe` — same dot paths, but read inside a pre-handler lifecycle hook.
- `invoke` — `"promise"` (default) or `"callback"`.
- `context` — the invocation context object (when relevant).
- `emitContext` — context fields to read and emit after invocation.
- `simulateInjectError` — force an unexpected internal failure during request processing.
- `event` — the gateway invocation event to feed the handler.

The adapter writes a deterministic, language-neutral, line-oriented projection to stdout. A `[request]` section (present only when probes are used) lists `request.<path>=<value>` and `onRequest.<path>=<value>` lines. A `[response]` section always lists `status`, `isBase64Encoded`, `body`, then sorted `header.<name>=<value>` lines, then optional `cookies=` and `multiValueHeaders.<name>=` lines. An optional `[context]` section lists `context.<field>=<value>`. The non-deterministic `Date` header value is normalized to `<present>`; absent values are rendered as `<undefined>`. Unexpected internal failures are rendered purely as the resulting error result (no host-language identity is ever emitted).

---

## Core Features

### Feature 1: Request Body Decoding

**As a developer**, I want incoming request bodies (plain or Base64-encoded) decoded and forwarded to my handler with a correct Content-Length, so I can read the body exactly as in a normal HTTP request.

**Expected Behavior / Usage:**

The library passes the event body through to the framework so the framework's body parser produces the handler's `body`. When the event flags the body as Base64-encoded, it is decoded to its raw bytes first. When the body is present but no content-length header was supplied by the gateway, the library computes and sets it from the decoded byte length. The reader can verify the parsed body and the computed content-length below.

**Test Cases:** `rcb_tests/public_test_cases/feature1_request_body.json`

```json
{
  "description": "Decode an incoming request body and forward it to the routed handler, computing the Content-Length header; supports both a plain UTF-8 body and a Base64-encoded body.",
  "cases": [
    {
      "input": {
        "route": { "method": "POST", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world2" } } } },
        "probe": ["headers.content-type", "headers.content-length", "body"],
        "event": { "httpMethod": "POST", "path": "/test", "headers": { "X-My-Header": "wuuusaaa", "Content-Type": "application/json" }, "body": "{\"greet\":\"hi\"}" }
      },
      "expected_output": "[request]\nrequest.headers.content-type=application/json\nrequest.headers.content-length=14\nrequest.body={\"greet\":\"hi\"}\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world2\"}\nheader.connection=keep-alive\nheader.content-length=18\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "route": { "method": "POST", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world2" } } } },
        "probe": ["headers.content-type", "headers.content-length", "body"],
        "event": { "httpMethod": "POST", "path": "/test", "headers": { "X-My-Header": "wuuusaaa", "Content-Type": "application/json" }, "body": "eyJncmVldCI6ICJoaSJ9", "isBase64Encoded": true }
      },
      "expected_output": "[request]\nrequest.headers.content-type=application/json\nrequest.headers.content-length=15\nrequest.body={\"greet\":\"hi\"}\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world2\"}\nheader.connection=keep-alive\nheader.content-length=18\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

---

### Feature 2: Path & URL Resolution

**As a developer**, I want the library to compute the correct path to route to from the many possible event shapes, so my routes match regardless of how the gateway encodes the path.

**Expected Behavior / Usage:**

*2.1 Path selection & method derivation — choose the routed path and the HTTP method from the event*

The routed path is taken from the explicit request path when present, otherwise from the raw path. When only a request-context HTTP block is available, the method is derived from it. The resolved path is what the framework actually routes against (visible as the request URL, including any query string).

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_path_resolution.json`

```json
{
  "description": "Choose the path the framework routes to: prefer the explicit request path, and fall back to the raw path (deriving the method from the request context) when only that is present.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["url"],
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[request]\nrequest.url=/test\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "route": { "method": "GET", "path": "/prod/projects", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["url", "query.t"],
        "event": { "version": "2.0", "rawPath": "/prod/projects", "requestContext": { "http": { "method": "GET", "path": "/prod/projects" } }, "headers": { "X-My-Header": "wuuusaaa" }, "queryStringParameters": { "t": "1698604776681" } }
      },
      "expected_output": "[request]\nrequest.url=/prod/projects?t=1698604776681\nrequest.query.t=1698604776681\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*2.2 Named path parameter as path — route to a configured path parameter instead of the full path*

When the library is configured with the name of a path parameter, the value of that parameter (prefixed with a slash) becomes the routed path, overriding both the request path and the raw path. This works the same way for both proxy-integration event shapes.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_path_parameter_as_path.json`

```json
{
  "description": "When configured to use a named path parameter as the path, route to that parameter value instead of the full request/raw path, for both proxy-integration event shapes.",
  "cases": [
    {
      "input": {
        "options": { "pathParameterUsedAsPath": "proxy" },
        "route": { "method": "GET", "path": "/projects", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["url"],
        "event": { "version": "2.0", "rawPath": "/prod/projects", "requestContext": { "http": { "method": "GET", "path": "/prod/projects" } }, "headers": { "X-My-Header": "wuuusaaa" }, "queryStringParameters": { "t": "1698604776681" }, "pathParameters": { "proxy": "projects" } }
      },
      "expected_output": "[request]\nrequest.url=/projects?t=1698604776681\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "options": { "pathParameterUsedAsPath": "proxy" },
        "route": { "method": "GET", "path": "/projects", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["url"],
        "event": { "path": "/area/projects", "httpMethod": "GET", "headers": { "X-My-Header": "wuuusaaa" }, "queryStringParameters": { "t": "1698604776681" }, "pathParameters": { "proxy": "projects" }, "requestContext": { "resourcePath": "/area/{proxy+}", "httpMethod": "GET", "path": "/dev/area/projects", "stage": "dev" } }
      },
      "expected_output": "[request]\nrequest.url=/projects?t=1698604776681\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*2.3 Stage prefix handling — strip the stage segment by default, retain it on request*

When the path begins with the deployment stage segment but the resource path does not, the library removes that leading stage segment so routes are stage-agnostic. An option forces the stage segment to be retained, in which case the path is left untouched.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_stage_handling.json`

```json
{
  "description": "Strip the API stage prefix from the path by default so handlers are stage-agnostic; retain the stage prefix when explicitly requested.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["url"],
        "event": { "httpMethod": "GET", "path": "/dev/test", "headers": { "X-My-Header": "wuuusaaa" }, "requestContext": { "resourcePath": "/test", "stage": "dev" } }
      },
      "expected_output": "[request]\nrequest.url=/test\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "options": { "retainStage": true },
        "route": { "method": "GET", "path": "/dev/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["url"],
        "event": { "httpMethod": "GET", "path": "/dev/test", "headers": { "X-My-Header": "wuuusaaa" }, "requestContext": { "resourcePath": "/test", "stage": "dev" } }
      },
      "expected_output": "[request]\nrequest.url=/dev/test\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

---

### Feature 3: Query String Parsing

**As a developer**, I want query parameters parsed consistently into the framework's query object across the event encodings, so my handler sees the values it expects.

**Expected Behavior / Usage:**

*3.1 Multi-valued query parameters — expose repeated values as arrays*

When the event provides an explicit multi-value query map, each parameter is exposed to the handler as an array of its values.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_multi_value_query.json`

```json
{
  "description": "Expose multi-valued query string parameters to the handler as arrays of values.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "echoQuery" } } },
        "event": { "httpMethod": "GET", "path": "/test", "queryStringParameters": { "foo": "bar" }, "multiValueQueryStringParameters": { "foo": ["qux", "bar"] } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"foo\":[\"qux\",\"bar\"]}\nheader.connection=keep-alive\nheader.content-length=21\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*3.2 Comma-separated values (format 2.0) — optionally split on commas*

For payload format version 2.0, a single query value containing commas may be split into an array. A toggle controls the behavior: enabled (the default) splits the value into an array; disabled leaves it as one comma-joined string.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_comma_separated_query.json`

```json
{
  "description": "For protocol version 2.0, optionally split comma-separated query values into arrays; a toggle controls whether the split happens.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "echoQuery" } } },
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "queryStringParameters": { "foo": "qux,bar" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"foo\":[\"qux\",\"bar\"]}\nheader.connection=keep-alive\nheader.content-length=21\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "options": { "parseCommaSeparatedQueryParams": false },
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "echoQuery" } } },
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "queryStringParameters": { "foo": "qux,bar" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"foo\":\"qux,bar\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*3.3 Load-balancer URL decoding — decode keys and values*

For load-balancer sourced events, both query keys and query values arrive percent-encoded and are URL-decoded by the library, for single-valued and multi-valued parameters alike.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_elb_url_decoding.json`

```json
{
  "description": "For load-balancer sourced events, URL-decode both query keys and query values (single and multi-valued).",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "echoQuery" } } },
        "event": { "requestContext": { "elb": { "targetGroupArn": "xxx" } }, "httpMethod": "GET", "path": "/test", "queryStringParameters": { "q%24": "foo%3Fbar" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"q$\":\"foo?bar\"}\nheader.connection=keep-alive\nheader.content-length=16\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "echoQuery" } } },
        "event": { "requestContext": { "elb": { "targetGroupArn": "xxx" } }, "httpMethod": "GET", "path": "/test", "queryStringParameters": { "q%24": "foo%3Fbar" }, "multiValueQueryStringParameters": { "q%24": ["foo%40bar", "foo%3Fbar"] } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"q$\":[\"foo@bar\",\"foo?bar\"]}\nheader.connection=keep-alive\nheader.content-length=28\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*3.4 Verbatim passthrough (non load-balancer) — no decoding*

For non load-balancer events, query values are passed through exactly as received, with no URL-decoding applied.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_query_no_decode.json`

```json
{
  "description": "For non load-balancer events, query values are passed through verbatim, without URL-decoding.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "echoQuery" } } },
        "event": { "httpMethod": "GET", "path": "/test", "queryStringParameters": { "foo": "foo%3Fbar" }, "multiValueQueryStringParameters": { "foo": ["foo%40bar", "foo%3Fbar"] } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"foo\":[\"foo%40bar\",\"foo%3Fbar\"]}\nheader.connection=keep-alive\nheader.content-length=33\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*3.5 Original event preserved — do not mutate the source event*

Splitting comma-separated values for the handler must not change the original event's query map. The original event remains readable through request decoration and still holds the unsplit value, whether or not splitting was enabled.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_retain_event_query.json`

```json
{
  "description": "Splitting comma-separated values for the handler must not mutate the original event's query parameters, which remain readable through request decoration regardless of the split toggle.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "echoQuery" } } },
        "probe": ["awsLambdaEvent.queryStringParameters"],
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "queryStringParameters": { "foo": "qux,bar" } }
      },
      "expected_output": "[request]\nrequest.awsLambdaEvent.queryStringParameters={\"foo\":\"qux,bar\"}\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"foo\":[\"qux\",\"bar\"]}\nheader.connection=keep-alive\nheader.content-length=21\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "options": { "parseCommaSeparatedQueryParams": false },
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "echoQuery" } } },
        "probe": ["awsLambdaEvent.queryStringParameters"],
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "queryStringParameters": { "foo": "qux,bar" } }
      },
      "expected_output": "[request]\nrequest.awsLambdaEvent.queryStringParameters={\"foo\":\"qux,bar\"}\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"foo\":\"qux,bar\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

---

### Feature 4: Request Header Translation

**As a developer**, I want event headers, cookies and multi-valued headers normalized into the request my handler sees, plus the option to expose the raw event, so my handler reads consistent headers.

**Expected Behavior / Usage:**

*4.1 Cookie list to Cookie header — join format 2.0 cookies*

A payload format 2.0 cookie list is joined into a single `Cookie` request header so the framework's cookie handling works as usual.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_cookies_to_cookie_header.json`

```json
{
  "description": "Join the protocol v2 cookie list into a single Cookie request header visible to the handler.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["headers.cookie"],
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" }, "cookies": ["foo=bar"], "queryStringParameters": "" }
      },
      "expected_output": "[request]\nrequest.headers.cookie=foo=bar\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*4.2 Multi-valued headers — promote only when more than one value*

A header supplied through the multi-value header map is added to the request only when it carries more than one value; a multi-value entry with a single value is not promoted and stays absent. A header with several values is exposed as the combined value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_multi_value_headers.json`

```json
{
  "description": "Promote a header to the request only when it carries more than one value; a multi-header with a single value is not promoted, and a header with several values is exposed as the combined value.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["headers.x-multi"],
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "x-multi": "just-the-first" }, "multiValueHeaders": { "x-multi": ["just-the-first", "and-the-second"] } }
      },
      "expected_output": "[request]\nrequest.headers.x-multi=just-the-first,and-the-second\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["headers.x-custom-multi-bad", "headers.x-custom-multi-gut"],
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" }, "multiValueHeaders": { "x-custom-multi-bad": ["100"], "x-custom-multi-gut": ["100", "200"] } }
      },
      "expected_output": "[request]\nrequest.headers.x-custom-multi-bad=<undefined>\nrequest.headers.x-custom-multi-gut=100,200\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*4.3 Serialized event header — optionally expose the raw event*

When enabled, the library serializes the original invocation event into a URL-encoded request header so a handler can inspect the raw event. The header is absent when the feature is off, which is the default.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_serialize_event_header.json`

```json
{
  "description": "Optionally serialize the original invocation event into a URL-encoded request header so handlers can inspect the raw event; the header is absent when the feature is off (the default).",
  "cases": [
    {
      "input": {
        "options": { "serializeLambdaArguments": true },
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["headers.x-apigateway-event"],
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[request]\nrequest.headers.x-apigateway-event=%7B%22version%22%3A%222.0%22%2C%22httpMethod%22%3A%22GET%22%2C%22path%22%3A%22%2Ftest%22%2C%22headers%22%3A%7B%22X-My-Header%22%3A%22wuuusaaa%22%7D%7D\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["headers.x-apigateway-event"],
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[request]\nrequest.headers.x-apigateway-event=<undefined>\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

---

### Feature 5: Response Rendering

**As a developer**, I want my handler's response rendered into the gateway result with format-correct cookie and header handling, so clients receive a valid response.

**Expected Behavior / Usage:**

*5.1 JSON body and format-2.0 cookies — Set-Cookie becomes a cookie list*

A JSON handler response is rendered into a result with the JSON serialized in the body and `isBase64Encoded` false. For payload format 2.0, response Set-Cookie headers are returned as a dedicated cookie list rather than as response headers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_response_json_cookies_v2.json`

```json
{
  "description": "Render a JSON handler response into a proxy result; for protocol v2, Set-Cookie headers are returned as a dedicated cookie list rather than response headers.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "headers": { "Set-Cookie": ["qwerty=one", "qwerty=two"] }, "body": { "type": "json", "value": { "hello": "world" } } } },
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\ncookies=qwerty=one,qwerty=two\n"
    }
  ]
}
```

*5.2 Format-1.0 cookies and joined headers — multi-value headers map and comma-join*

For payload format 1.0 (no version field), response Set-Cookie values are returned under a multi-value headers map. Any other response header that carries multiple values is comma-joined into a single header value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_response_v1_cookies_and_joined_header.json`

```json
{
  "description": "For protocol v1 (no version field), Set-Cookie values are returned under a multi-value headers map; other multi-valued response headers are comma-joined into a single header value.",
  "cases": [
    {
      "input": {
        "route": { "method": "POST", "path": "/test", "reply": { "headers": { "Set-Cookie": ["qwerty=one", "qwerty=two"], "X-Custom-Header": ["ciao", "salve"] }, "body": { "type": "json", "value": { "hello": "world2" } } } },
        "event": { "httpMethod": "POST", "path": "/test", "headers": { "Content-Type": "application/json" }, "body": "{\"greet\":\"hi\"}" }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world2\"}\nheader.connection=keep-alive\nheader.content-length=18\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\nheader.x-custom-header=ciao,salve\nmultiValueHeaders.set-cookie=qwerty=one,qwerty=two\n"
    }
  ]
}
```

*5.3 Empty body and header coercion — zero length, string coercion, omitted Content-Type*

An empty handler response yields an empty body with a zero Content-Length. Non-string response header values are coerced to strings. Removing the Content-Type in the handler omits it from the result entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_response_empty_and_coercion.json`

```json
{
  "description": "An empty handler response yields an empty body with zero Content-Length; non-string response header values are coerced to strings; removing Content-Type omits it from the result.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "headers": { "Set-Cookie": ["qwerty=one", "qwerty=two"], "x-non-string": 1717171717171 }, "removeContentType": true, "body": { "type": "empty" } } },
        "event": { "requestContext": { "http": { "method": "GET" } }, "rawPath": "/test", "headers": { "X-My-Header": "wuuusaaa" }, "queryStringParameters": "" }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody=\nheader.connection=keep-alive\nheader.content-length=0\nheader.date=<present>\nheader.x-non-string=1717171717171\nmultiValueHeaders.set-cookie=qwerty=one,qwerty=two\n"
    }
  ]
}
```

---

### Feature 6: Binary Response Encoding

**As a developer**, I want the library to decide when a response body must be Base64-encoded, so binary and compressed payloads survive the gateway round-trip.

**Expected Behavior / Usage:**

*6.1 Configured binary MIME types — encode matching content types*

When the response Content-Type matches one of the configured binary MIME types, the body is Base64-encoded and the result is flagged with `isBase64Encoded` true.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_binary_mime_types.json`

```json
{
  "description": "When the response Content-Type matches a configured binary MIME type, the body is Base64-encoded and flagged as such.",
  "cases": [
    {
      "input": {
        "options": { "binaryMimeTypes": ["application/octet-stream"] },
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "bytes", "value": "SGVsbG8gYmluYXJ5IHBheWxvYWQh" } } },
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=true\nbody=SGVsbG8gYmluYXJ5IHBheWxvYWQh\nheader.connection=keep-alive\nheader.content-length=21\nheader.content-type=application/octet-stream\nheader.date=<present>\n"
    }
  ]
}
```

*6.2 Compressed responses — encode non-identity content-encoding by default*

A response whose Content-Encoding is anything other than identity is treated as binary and Base64-encoded by default, even without any configured binary MIME type.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_content_encoding_base64.json`

```json
{
  "description": "A compressed response (non-identity Content-Encoding) is Base64-encoded by default even without a configured binary MIME type.",
  "cases": [
    {
      "input": {
        "options": { "binaryMimeTypes": [] },
        "route": { "method": "GET", "path": "/test", "reply": { "headers": { "content-encoding": "br" }, "body": { "type": "bytes", "value": "SGVsbG8gYmluYXJ5IHBheWxvYWQh" } } },
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=true\nbody=SGVsbG8gYmluYXJ5IHBheWxvYWQh\nheader.connection=keep-alive\nheader.content-encoding=br\nheader.content-length=21\nheader.content-type=application/octet-stream\nheader.date=<present>\n"
    }
  ]
}
```

*6.3 Custom encoding predicate — caller decides from response headers*

A caller-supplied predicate, given the response, decides whether the body should be Base64-encoded. When it returns true, the body is encoded regardless of MIME type or content-encoding.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_custom_base64_predicate.json`

```json
{
  "description": "A caller-supplied predicate decides whether a response should be Base64-encoded based on the response headers.",
  "cases": [
    {
      "input": {
        "options": { "binaryMimeTypes": [] },
        "enforceBase64": { "header": "x-base64-encoded", "equals": "1" },
        "route": { "method": "GET", "path": "/test", "reply": { "headers": { "X-Base64-Encoded": "1" }, "body": { "type": "bytes", "value": "SGVsbG8gYmluYXJ5IHBheWxvYWQh" } } },
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=true\nbody=SGVsbG8gYmluYXJ5IHBheWxvYWQh\nheader.connection=keep-alive\nheader.content-length=21\nheader.content-type=application/octet-stream\nheader.date=<present>\nheader.x-base64-encoded=1\n"
    }
  ]
}
```

---

### Feature 7: Request Decoration

**As a developer**, I want the original invocation event and context attached to the request, so any part of my application can inspect them.

**Expected Behavior / Usage:**

*7.1 Access in the handler — read event and context*

The library decorates the request so the handler can read the original invocation event and the original invocation context.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_request_decoration.json`

```json
{
  "description": "Decorate the request so the handler can read the original invocation event and the original invocation context.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "probe": ["awsLambdaEvent.httpMethod", "awsLambdaContext"],
        "context": { "functionName": "fn" },
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[request]\nrequest.awsLambdaEvent.httpMethod=GET\nrequest.awsLambdaContext={\"functionName\":\"fn\"}\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*7.2 Access in pre-handler hooks — read event before the handler runs*

The decoration is available in lifecycle hooks that run before the handler, not only inside the handler itself.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_decoration_in_hook.json`

```json
{
  "description": "The request decoration is available in lifecycle hooks that run before the handler, not only inside the handler.",
  "cases": [
    {
      "input": {
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "onRequestProbe": ["awsLambdaEvent.httpMethod"],
        "event": { "version": "2.0", "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[request]\nonRequest.awsLambdaEvent.httpMethod=GET\n[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

---

### Feature 8: Invocation Styles & Context Flag

**As a developer**, I want to invoke the handler with either a promise or a callback, and to control the empty-event-loop-wait flag, so the handler fits different runtime conventions.

**Expected Behavior / Usage:**

*8.1 Callback invocation — deliver the result via a callback*

The handler supports node-style callback invocation, delivering the same result object through the callback as it would resolve through a promise.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_callback_invocation.json`

```json
{
  "description": "Support node-style callback invocation: the proxy delivers the same proxy result through a callback as it does through a promise.",
  "cases": [
    {
      "input": {
        "invoke": "callback",
        "context": {},
        "route": { "method": "GET", "path": "/test", "reply": { "headers": { "Set-Cookie": ["qwerty=one", "qwerty=two"] }, "body": { "type": "json", "value": { "hello": "world" } } } },
        "event": { "version": "2.0", "requestContext": { "http": { "method": "GET" } }, "rawPath": "/test", "headers": { "X-My-Header": "wuuusaaa" }, "queryStringParameters": "" }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\ncookies=qwerty=one,qwerty=two\n"
    }
  ]
}
```

*8.2 Empty-event-loop-wait flag — write the option onto the context*

When the option is provided, the empty-event-loop-wait flag is written onto the invocation context before the request is processed, so the runtime observes the requested value.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_callback_waits_option.json`

```json
{
  "description": "When provided, the empty-event-loop-wait flag is written onto the invocation context before the request is processed.",
  "cases": [
    {
      "input": {
        "options": { "callbackWaitsForEmptyEventLoop": false },
        "invoke": "callback",
        "context": {},
        "emitContext": ["callbackWaitsForEmptyEventLoop"],
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n[context]\ncontext.callbackWaitsForEmptyEventLoop=false\n"
    },
    {
      "input": {
        "options": { "callbackWaitsForEmptyEventLoop": true },
        "invoke": "callback",
        "context": {},
        "emitContext": ["callbackWaitsForEmptyEventLoop"],
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "event": { "httpMethod": "GET", "path": "/test", "headers": { "X-My-Header": "wuuusaaa" } }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"hello\":\"world\"}\nheader.connection=keep-alive\nheader.content-length=17\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n[context]\ncontext.callbackWaitsForEmptyEventLoop=true\n"
    }
  ]
}
```

---

### Feature 9: Error Resilience

**As a developer**, I want an unexpected internal failure during request processing to produce a clean error result instead of propagating a raw fault, so a single bad invocation does not crash the function.

**Expected Behavior / Usage:**

If processing the request fails unexpectedly, the handler resolves to a result with status 500, an empty body, and no headers, for both promise and callback invocation. No host-language fault is propagated to the caller and no runtime detail leaks into the result.

**Test Cases:** `rcb_tests/public_test_cases/feature9_error_resilience.json`

```json
{
  "description": "If the underlying request processing fails unexpectedly, the proxy returns a 500 result with an empty body and no headers instead of leaking the failure, for both promise and callback invocation.",
  "cases": [
    {
      "input": {
        "simulateInjectError": true,
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "event": { "requestContext": {}, "rawPath": "/test", "queryStringParameters": "" }
      },
      "expected_output": "[response]\nstatus=500\nisBase64Encoded=<undefined>\nbody=\n"
    },
    {
      "input": {
        "simulateInjectError": true,
        "invoke": "callback",
        "context": null,
        "route": { "method": "GET", "path": "/test", "reply": { "body": { "type": "json", "value": { "hello": "world" } } } },
        "event": { "requestContext": {}, "rawPath": "/test", "queryStringParameters": "" }
      },
      "expected_output": "[response]\nstatus=500\nisBase64Encoded=<undefined>\nbody=\n"
    }
  ]
}
```

---

### Feature 10: Multipart Body Parsing

**As a developer**, I want multipart/form-data bodies parsed by my registered body parser, so file uploads and form fields are available to my handler.

**Expected Behavior / Usage:**

*10.1 File parts — raw and Base64-encoded bodies*

The library forwards a multipart/form-data body (provided either as a raw string or Base64-encoded) so the registered parser extracts the uploaded file part, exposing its field name, file name, encoding, MIME type and content to the handler.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_multipart_file_fields.json`

```json
{
  "description": "Parse a multipart/form-data body (provided either as a raw string or Base64-encoded) and expose the uploaded file part to the handler.",
  "cases": [
    {
      "input": {
        "multipart": true,
        "route": { "method": "POST", "path": "/test", "reply": { "body": { "type": "echoMultipart", "fields": ["uploadFile1"] } } },
        "event": { "version": "2.0", "httpMethod": "POST", "path": "/test", "headers": { "content-type": "multipart/form-data; boundary=----WebKitFormBoundaryDP6Z1qHQSzB6Pf8c" }, "body": "------WebKitFormBoundaryDP6Z1qHQSzB6Pf8c\r\nContent-Disposition: form-data; name=\"uploadFile1\"; filename=\"test.txt\"\r\nContent-Type: text/plain\r\n\r\nHello World!\r\n------WebKitFormBoundaryDP6Z1qHQSzB6Pf8c--", "isBase64Encoded": false }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"uploadFile1\":{\"fieldname\":\"uploadFile1\",\"filename\":\"test.txt\",\"encoding\":\"7bit\",\"mimetype\":\"text/plain\",\"content\":\"Hello World!\"}}\nheader.connection=keep-alive\nheader.content-length=132\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    },
    {
      "input": {
        "multipart": true,
        "route": { "method": "POST", "path": "/test", "reply": { "body": { "type": "echoMultipart", "fields": ["uploadFile1"] } } },
        "event": { "version": "2.0", "httpMethod": "POST", "path": "/test", "headers": { "content-type": "multipart/form-data; boundary=----WebKitFormBoundaryDP6Z1qHQSzB6Pf8c" }, "body": "LS0tLS0tV2ViS2l0Rm9ybUJvdW5kYXJ5RFA2WjFxSFFTekI2UGY4Yw0KQ29udGVudC1EaXNwb3NpdGlvbjogZm9ybS1kYXRhOyBuYW1lPSJ1cGxvYWRGaWxlMSI7IGZpbGVuYW1lPSJ0ZXN0LnR4dCINCkNvbnRlbnQtVHlwZTogdGV4dC9wbGFpbg0KDQpIZWxsbyBXb3JsZCENCi0tLS0tLVdlYktpdEZvcm1Cb3VuZGFyeURQNloxcUhRU3pCNlBmOGMtLQ==", "isBase64Encoded": true }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"uploadFile1\":{\"fieldname\":\"uploadFile1\",\"filename\":\"test.txt\",\"encoding\":\"7bit\",\"mimetype\":\"text/plain\",\"content\":\"Hello World!\"}}\nheader.connection=keep-alive\nheader.content-length=132\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

*10.2 Text fields — expose the decoded value*

A multipart/form-data text field is parsed so its decoded value is exposed to the handler, alongside its field name, encoding and MIME type.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_multipart_value_field.json`

```json
{
  "description": "Parse a multipart/form-data text field and expose its decoded value to the handler.",
  "cases": [
    {
      "input": {
        "multipart": true,
        "route": { "method": "POST", "path": "/test", "reply": { "body": { "type": "echoMultipart", "fields": ["html"] } } },
        "event": { "version": "2.0", "httpMethod": "POST", "path": "/test", "headers": { "content-type": "multipart/form-data; boundary=xYzZY" }, "body": "--xYzZY\r\nContent-Disposition: form-data; name=\"html\"\r\n\r\n<p>Hello World</p>\r\n--xYzZY--\r\n", "isBase64Encoded": false }
      },
      "expected_output": "[response]\nstatus=200\nisBase64Encoded=false\nbody={\"html\":{\"fieldname\":\"html\",\"encoding\":\"7bit\",\"mimetype\":\"text/plain\",\"value\":\"<p>Hello World</p>\"}}\nheader.connection=keep-alive\nheader.content-length=100\nheader.content-type=application/json; charset=utf-8\nheader.date=<present>\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured library implementing the features above: a single factory that accepts a web-framework application plus options and returns an invocation handler. Request-side translation (method, path/URL resolution, stage handling, query parsing, header and cookie normalization, body decoding), response-side rendering (status, body, headers, cookie placement per payload format, binary-encoding decision), and option resolution must be separated into cohesive logical units. The binary-encoding decision must be extensible through a caller-supplied predicate without modifying the core.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core library. It reads a JSON scenario from stdin, builds an application (registering routes, hooks, a multipart parser and reply behavior as described), invokes the handler (promise or callback), and prints the language-neutral line projection to stdout, strictly matching the per-leaf-feature contracts above. Any native error raised internally is caught and re-rendered as the contract's error result; the adapter never emits host-language type names, stack traces, or runtime-specific object renderings. This adapter is physically separate from the core library.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_request_body.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_request_body@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same parameter extraction logic as the form handler
