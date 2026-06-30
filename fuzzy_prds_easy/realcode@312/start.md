## Product Requirement Document

# JSON-RPC 2.0 Server Engine

## Project Goal

Build a server-side engine that implements the JSON-RPC 2.0 protocol: it accepts a JSON-RPC
request (single or batched), dispatches it to a matching service operation, and produces a
correctly-shaped JSON-RPC response. The engine must support both a raw byte-stream transport
and an HTTP transport, and it must map service outcomes to standardized error categories and
HTTP status codes.

To make the engine's externally-observable behavior verifiable, the deliverable also includes a
thin **adapter** program. The adapter reads exactly one *case-input* JSON object from standard
input, drives the engine, and prints a **normalized, line-based view** of the resulting protocol
response to standard output. All evaluation is performed against this normalized stdout, so the
contract below is defined entirely in terms of request inputs and normalized outputs — never in
terms of any host-language type, class, or framework internal.

## Background & Problem

JSON-RPC 2.0 is a transport-agnostic remote-procedure-call protocol. A request names a `method`,
carries `params` (a positional array or a named object), and carries an `id` used to correlate the
response. The server returns either a `result` (success) or an `error` object with a numeric
`code`. A request without an `id` is a *notification* and yields no response on success. Multiple
requests can be sent as a JSON array (a *batch*), producing an array of correlated responses.

A correct engine must make many subtle decisions consistently: how to bind positional vs. named
arguments to an operation, how to choose among overloaded operations, how to coerce argument types,
what to do when too few or too many arguments arrive, how to surface service-thrown errors as
protocol errors without leaking host-language details, and how to translate protocol outcomes into
HTTP status codes. These behaviors are the substance of this specification.

The standardized JSON-RPC error codes used throughout are:

| category               | code    |
|------------------------|---------|
| `ok`                   | `0`     |
| `parse_error`          | `-32700`|
| `invalid_request`      | `-32600`|
| `method_not_found`     | `-32601`|
| `method_params_invalid`| `-32602`|
| `internal_error`       | `-32603`|
| `error_not_handled`    | `-32001`|
| `bulk_error`           | `-32002`|

Any other code is reported with the category `custom`.

## Architecture & Engineering Constraints

**Service surface under test.** The engine is exercised through a fixed demonstration service that
exposes the following operations. Implementations must reproduce these exact externally-visible
semantics (the result strings encode which variant was selected, so dispatch decisions are
observable):

- `echo(text: string) -> string` — returns `text` unchanged.
- `addInts(a: int, b: int) -> int` — returns `a + b`.
- `voidMethod(value: int) -> void` — returns no value (null result).
- `overloadedMethod()` / `overloadedMethod(string)` / `overloadedMethod(string, string)` /
  `overloadedMethod(int)` / `overloadedMethod(int, int)` — five overloads returning, respectively,
  `"overloaded:0"`, `"overloaded:string:<a>"`, `"overloaded:string,string:<a>,<b>"`,
  `"overloaded:int:<i>"`, `"overloaded:int,int:<a+b>"`.
- `methodWithoutRequiredParam(param1: string, param2: string) -> string` — returns
  `"withoutRequired:<param1>|<param2>"`, where a missing second argument renders as `<none>`.
- `methodWithDifferentTypes(param1: boolean, param2: double, param3: uuid) -> string` — returns
  `"types:<boolean>,<double>,<uuid>"`; used to exercise type coercion.
- `customEcho(text: string)` published under the external alias `custom.echo` — returns
  `"custom:<text>"`.
- `throwsUnmapped()` — always raises an error that is **not** mapped to a specific code.
- `throwsMapped()` — raises an error mapped to code `1234`.
- `throwsMappedFull()` — raises an error mapped to code `-5678` with message `"The message"` and
  data `"The data"`.
- `throwsMappedWithExceptionMessage()` — raises an error mapped to code `1234` whose own message is
  `"exception message"`.

**Argument binding policy.** By default a call must supply exactly as many arguments as the chosen
operation declares; otherwise it is rejected as `method_params_invalid`. Two switches relax this:
`allowExtraParams` permits and ignores surplus arguments, and `allowLessParams` permits missing
trailing arguments (bound to their type default / null).

**Error normalization (mandatory).** Service-thrown errors must be surfaced as JSON-RPC errors with
a numeric code and an optional message/data. The normalized output must express only
language-neutral signals: the numeric `error_code`, the derived `error_category`, and any
engine-level `error_message`/`error_data` strings. Host-language artifacts — exception class names,
fully-qualified type names, stack traces, runtime-specific message suffixes — must **never** appear
in the output.

**HTTP status mapping.** Over the HTTP transport the response additionally carries an HTTP status
derived from the result code: `ok` → 200, `method_not_found` → 404, `parse_error`/`invalid_request`
→ 400, and `method_params_invalid`/`internal_error`/`error_not_handled`/`bulk_error`/custom-server
codes → 500. A batch in which any sub-request fails is reported as 500. A pluggable status-code
provider may remap every category to arbitrary numbers.

**Adapter input schema.** The adapter consumes a single JSON object on stdin:

```
{
  "transport":       "raw" | "http_post" | "http_get",   // default "raw"
  "request":         <json>,        // the JSON-RPC request object or batch array
  "request_raw":     "<string>",    // optional: exact request bytes (for malformed input)
  "query":           {"method": "...", "id": "...", "params": "..."},  // http_get only
  "allowExtraParams": <bool>,       // optional, default false
  "allowLessParams":  <bool>,       // optional, default false
  "statusProvider":   "custom"      // optional (http transports): use the remapping provider
}
```

**Adapter output schema.** The adapter writes only the engine's normalized response to stdout, as
newline-terminated `key=value` lines:

- A successful single response:
  `jsonrpc=2.0`, `id=<json-id>`, `outcome=success`, `result=<compact-json>`.
- A failed single response:
  `jsonrpc=2.0`, `id=<json-id>`, `outcome=error`, `error_code=<int>`, `error_category=<name>`,
  and — only when present — `error_message=<text>`, `error_data=<text>` (when the error data is a
  string), or `error_data_message=<text>` (when the error data is a structured value carrying a
  message).
- A successful notification (no `id`) produces the single token `no_response`.
- A batch produces `batch_size=<n>` followed by each entry, sorted by `id`, each prefixed by a `--`
  separator line and rendered with the single-response fields above.
- For HTTP transports the body is preceded by `http_status=<int>` and `content_type=<string>`; an
  empty body is rendered as `body=empty`.

**Determinism.** Output must depend only on the input. Batch entries are emitted in ascending `id`
order. Field ordering within a response is fixed as listed above.

**Build/runtime constraints.** The engine and adapter run on the JVM. The evaluation harness
(`rcb_tests/test.sh`) resolves the project's runtime classpath offline, compiles the adapter against
the engine, runs one adapter process per case, and compares stdout to each case's
`expected_output`. No network access is assumed.

## Core Features

### Feature 1: Positional dispatch, result types, id handling, notifications

A request whose `params` is an array is routed to the operation with the matching positional arity.
The response echoes the request `id` faithfully whether it is an integer, a string, or a large
integer. A void operation yields a `null` result. A request with no `id` (a notification) that
succeeds produces no response at all.

```json
{
  "description": "Positional dispatch: a request with an array of params is routed to the matching method by position; the result envelope echoes the request id (integer, string, or large integer), a void method yields a null result, and a request without an id (a notification) that succeeds produces no response at all.",
  "cases": [
    {
      "description": "echo a string value positionally",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "[a specific semantic version string]", "id": 1, "method": "echo", "params": ["hello"] }
      },
      "expected_output": "jsonrpc=[a specific semantic version string]\nid=1\noutcome=[a specific sentinel output state]\nresult=\"hello\"\n"
    },
    {
      "description": "integer result from a two-argument call",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "[a specific semantic version string]", "id": 1, "method": "addInts", "params": [2, 3] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=[a specific sentinel output state]\nresult=5\n"
    }
  ]
}
```

### Feature 2: Parameter arity validation

Supplying too few or too many positional arguments is rejected with the `method_params_invalid`
error, unless the engine is configured to allow missing (`allowLessParams`) or extra
(`allowExtraParams`) arguments, in which case the call proceeds.

```json
{
  "description": "Parameter arity validation for positional calls: supplying too few or too many positional arguments is rejected with the method-parameters-invalid error, unless the server is configured to allow missing (allowLessParams) or extra (allowExtraParams) arguments, in which case the call proceeds.",
  "cases": [
    {
      "description": "too few positional arguments is rejected",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "addInts", "params": [1] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=error\nerror_code=-32602\nerror_category=method_params_invalid\nerror_message=method parameters invalid\n"
    },
    {
      "description": "too many positional arguments is rejected",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "echo", "params": ["a", "b"] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=error\nerror_code=-32602\nerror_category=method_params_invalid\nerror_message=method parameters invalid\n"
    }
  ]
}
```

### Feature 3: Overload resolution by arity and type

When several operations share a name, the engine selects the variant whose parameter count and
types match the supplied positional arguments (no arguments, one string, one integer, two strings,
or two integers). The returned value reveals which variant was chosen.

```json
{
  "description": "Overload resolution by argument count and type: when several methods share a name, the engine selects the variant whose parameter count and types match the supplied positional arguments (no args, one string, one integer, two strings, or two integers).",
  "cases": [
    {
      "description": "no-argument overload",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "overloadedMethod", "params": [] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=[a specific sentinel output state]\nresult=\"overloaded:0\"\n"
    },
    {
      "description": "single string-argument overload",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "overloadedMethod", "params": ["x"] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=success\nresult=\"overloaded:string:x\"\n"
    }
  ]
}
```

### Feature 4: Named-parameter dispatch and type coercion

A request whose `params` is an object is matched to an operation by parameter names, including
overload selection by the named set and types. Argument values are coerced to the declared
parameter types; a value that cannot be coerced is rejected with `method_params_invalid`, and the
message identifies the offending argument position.

```json
{
  "description": "Named-parameter dispatch: a request whose params is an object is matched to a method by parameter names, including overload selection by the named set and type; argument values are coerced to the declared parameter types, and a value that cannot be coerced is rejected with the method-parameters-invalid error identifying the offending argument position.",
  "cases": [
    {
      "description": "named object selects the single-string overload",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "overloadedMethod", "params": { "param1": "x" } }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=success\nresult=\"overloaded:string:x\"\n"
    },
    {
      "description": "named object selects the single-integer overload",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "overloadedMethod", "params": { "param1": 7 } }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=success\nresult=\"overloaded:int:7\"\n"
    }
  ]
}
```

### Feature 5: Custom external method names

An operation may be published under an alias. The alias dispatches to the implementation, and the
operation also remains invocable by its original declared name.

```json
{
  "description": "Custom external method names: a method may be published under an alias; the alias dispatches to the implementation, and the method also remains invocable by its original declared name.",
  "cases": [
    {
      "description": "invoking by the registered alias succeeds",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "custom.echo", "params": ["yo"] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=success\nresult=\"custom:yo\"\n"
    },
    {
      "description": "the original declared name remains invocable",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "customEcho", "params": ["yo"] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=success\nresult=\"custom:yo\"\n"
    }
  ]
}
```

### Feature 6: Protocol-level error reporting

Malformed JSON input is reported as a `parse_error`; an empty-line payload is likewise a
`parse_error`; and a request naming an unknown operation is reported as `method_not_found`.

```json
{
  "description": "Protocol-level error reporting: malformed JSON input is reported as a parse error, an empty-line payload is also a parse error, and a request naming an unknown method is reported as method-not-found.",
  "cases": [
    {
      "description": "malformed JSON yields a parse error",
      "input": { "transport": "raw", "request_raw": "{ not valid json" },
      "expected_output": "jsonrpc=2.0\nid=\"null\"\noutcome=error\nerror_code=-32700\nerror_category=parse_error\nerror_message=JSON parse error\n"
    },
    {
      "description": "empty-line payload yields a parse error",
      "input": { "transport": "raw", "request_raw": "\n" },
      "expected_output": "jsonrpc=2.0\nid=\"null\"\noutcome=error\nerror_code=-32700\nerror_category=parse_error\nerror_message=JSON parse error\n"
    }
  ]
}
```

### Feature 7: Service-error mapping

An unmapped error thrown by an operation becomes a generic `error_not_handled` response. Errors
explicitly mapped to a code are reported with that code; an explicit message and data override the
defaults, and when no message override is configured the thrown error's own message is surfaced.
Host-language class names are never exposed in any field.

```json
{
  "description": "Service-error mapping: an unmapped exception thrown by a method becomes a generic error-not-handled response, while exceptions explicitly mapped to a code are reported with that code; an explicit message and data override the defaults, and when no message override is given the thrown exception's own message is surfaced. Host-language class names are never exposed.",
  "cases": [
    {
      "description": "unmapped exception becomes error-not-handled",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "throwsUnmapped", "params": [] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=error\nerror_code=-32001\nerror_category=error_not_handled\n"
    },
    {
      "description": "mapped exception reports the configured code",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "throwsMapped", "params": [] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=error\nerror_code=1234\nerror_category=custom\n"
    },
    {
      "description": "explicit message and data override the defaults",
      "input": {
        "transport": "raw",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "throwsMappedFull", "params": [] }
      },
      "expected_output": "jsonrpc=2.0\nid=1\noutcome=error\nerror_code=-5678\nerror_category=custom\nerror_message=The message\nerror_data=The data\n"
    }
  ]
}
```

### Feature 8: Batch processing

An array of requests produces an array of correlated responses, each keyed to its request `id`.
Successful and failing sub-requests coexist in one batch, each carrying its own result or error.

```json
{
  "description": "Batch processing: an array of requests produces an array of correlated responses, each keyed to its request id; successful and failing sub-requests coexist in one batch, each carrying its own result or error.",
  "cases": [
    {
      "description": "all sub-requests succeed",
      "input": {
        "transport": "raw",
        "request": [
          { "jsonrpc": "2.0", "id": 1, "method": "echo", "params": ["a"] },
          { "jsonrpc": "2.0", "id": 2, "method": "overloadedMethod", "params": [5] }
        ]
      },
      "expected_output": "batch_size=2\n--\njsonrpc=2.0\nid=1\noutcome=success\nresult=\"a\"\n--\njsonrpc=2.0\nid=2\noutcome=success\nresult=\"overloaded:int:5\"\n"
    },
    {
      "description": "mixed success and error in one batch",
      "input": {
        "transport": "raw",
        "request": [
          { "jsonrpc": "2.0", "id": 1, "method": "overloadedMethod", "params": ["a"] },
          { "jsonrpc": "2.0", "id": 2, "method": "throwsUnmapped", "params": [] },
          { "jsonrpc": "2.0", "id": 3, "method": "echo", "params": ["c"] }
        ]
      },
      "expected_output": "batch_size=3\n--\njsonrpc=2.0\nid=1\noutcome=success\nresult=\"overloaded:string:a\"\n--\njsonrpc=2.0\nid=2\noutcome=error\nerror_code=-32001\nerror_category=error_not_handled\n--\njsonrpc=2.0\nid=3\noutcome=success\nresult=\"c\"\n"
    }
  ]
}
```

### Feature 9: HTTP transport and status-code mapping

Over HTTP the response carries a status code derived from the JSON-RPC outcome: success is 200, an
unknown method is 404, malformed input is 400, and a service or parameter error is 500; a batch
containing any error reports 500. GET requests build the call from `method`/`id`/`params` query
parameters, and a custom status-code provider can remap every category.

```json
{
  "description": "HTTP transport status mapping: over HTTP the response carries a status code derived from the JSON-RPC outcome - success is 200, an unknown method is 404, malformed input is 400, and a service or parameter error is 500; a batch containing any error reports 500. GET requests build the call from method/id/params query parameters, and a custom status-code provider can remap every category.",
  "cases": [
    {
      "description": "successful call over HTTP is 200",
      "input": {
        "transport": "http_post",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "echo", "params": ["hi"] }
      },
      "expected_output": "http_status=200\ncontent_type=[a specific media type constant]\njsonrpc=2.0\nid=1\noutcome=success\nresult=\"hi\"\n"
    },
    {
      "description": "unknown method over HTTP is 404",
      "input": {
        "transport": "http_post",
        "request": { "jsonrpc": "2.0", "id": 1, "method": "nope", "params": [] }
      },
      "expected_output": "http_status=404\ncontent_type=[a specific media type constant]\njsonrpc=2.0\nid=1\noutcome=error\nerror_code=-32601\nerror_category=method_not_found\nerror_message=method not found\n"
    },
    {
      "description": "malformed input over HTTP is 400",
      "input": { "transport": "http_post", "request_raw": "{bad" },
      "expected_output": "http_status=400\ncontent_type=[a specific media type constant]\njsonrpc=2.0\nid=\"null\"\noutcome=error\nerror_code=-32700\nerror_category=parse_error\nerror_message=JSON parse error\n"
    }
  ]
}
```

## Deliverables

- A JSON-RPC 2.0 server engine implementing the dispatch, argument-binding, overload-resolution,
  type-coercion, error-mapping, batch, and HTTP-status behaviors specified above.
- The demonstration service surface exactly as described in **Architecture & Engineering
  Constraints**, with the stated externally-visible result semantics.
- An adapter program that reads one case-input JSON object from stdin and emits the normalized,
  line-based response described in the adapter output schema — performing all error normalization so
  that no host-language identifiers ever reach stdout.
- A single test entry point `rcb_tests/test.sh` accepting `--cases-dir <subdir>` (default
  `test_cases`), which runs every case, writes each invocation's raw stdout to
  `rcb_tests/stdout/<cases-dir>/<stem>@<NNN>.txt`, compares it against the case's `expected_output`,
  and prints a final `test_cases: <pass>/<total> pass` line.
- The hidden evaluation set under `rcb_tests/test_cases/` and its public mirror under
  `rcb_tests/public_test_cases/` (the cases embedded in this document), grouped by feature.


---
**Implementation notes:**
- rely on the signature matching heuristic used in the resolver module
- apply the default fallback mapping registered in the error mapper configuration
