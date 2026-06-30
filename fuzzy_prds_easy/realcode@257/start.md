## Product Requirement Document

# Declarative HTTP Client Toolkit - Product Requirements

## Project Goal

Build a reusable HTTP client toolkit that lets application developers describe *what* request to send — method, path, query parameters, headers, body, multipart parts — and receive a typed, decoded response, without hand-writing URL string concatenation, query-string encoding, header merging, body serialization, retry-on-auth logic, or response parsing. The toolkit also ships composable request/response middleware (interceptors) and human-readable request logging.

---

## Background & Problem

Without such a toolkit, every project re-implements the same fragile plumbing: gluing a base URL to a path while juggling stray slashes, percent-encoding nested query structures, deciding whether `null` query values are dropped or kept, serializing a body to JSON or form-encoding and setting the matching `content-type`, re-attaching an auth token and replaying a request after a `401`, and decoding a response payload into the right shape. This boilerplate is repetitive, easy to get subtly wrong (encoding edge cases, slash duplication, header override semantics), and hard to test.

With this toolkit, developers configure a client once (base URL, body converter, interceptors, optional authenticator) and then issue calls that return a structured response object distinguishing success (decoded body) from failure (error payload + status code). All the encoding, URL composition, header merging, retry, multipart assembly, and logging concerns are handled by small, well-defined, independently testable units.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility library (query encoding, URL composition, request modeling, header utilities, body conversion, client dispatch, authentication retry, interceptors/logging, multipart assembly). It MUST be organized as a multi-file repository with clear separation between these concerns rather than a single monolithic file. Do not over-engineer trivial helpers, but keep each responsibility in its own cohesive unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for an execution adapter**, not the internal data model. The core library must expose idiomatic, typed APIs and must not know about stdin/stdout or the JSON command envelope (`op`, etc.). A thin execution adapter is solely responsible for parsing a JSON command, invoking the core API, and rendering the documented stdout contract.

3. **Adherence to SOLID Design Principles:** Separate parsing/routing (adapter), URL/query encoding, request construction, body conversion, dispatch, and output formatting into distinct units. The dispatch engine must be open for extension (pluggable body converters, interceptors, authenticators) but closed for modification. Middleware must be substitutable behind small, cohesive interfaces, and high-level dispatch logic must depend on abstractions (a converter interface, an interceptor interface) rather than concrete encoders.

4. **Robustness & Interface Design:** The public API must be elegant and idiomatic to the target language. Configuration mistakes (e.g. a base URI that already carries query parameters, or an unsupported file-part payload) must be surfaced as well-defined error conditions, not silent misbehavior. The execution adapter MUST normalize every such error into a language-neutral category line (see the error-reporting note below) and MUST NOT leak host-language exception class names or runtime message text.

### Output contract conventions

Every operation prints a small, line-oriented, `key=value` (one per line) textual contract to stdout:

- Map-like outputs (headers, fields) are emitted **sorted by key** for determinism.
- Structured decoded values are rendered as canonical JSON; plain strings are rendered verbatim.
- Errors are emitted as a single neutral category line `error=<category>` (optionally followed by `key=value` detail lines). The categories used by this contract are `base_uri_has_query` and `unsupported_part_type`. No host-language exception type or runtime-generated message text ever appears.

---

## Core Features

### Feature 1: Query-String Serialization

**As a developer**, I want to turn a structured map of parameters into a valid URL query string, so I can build request URLs without hand-encoding values or guessing how collections and nested structures are represented.

**Expected Behavior / Usage:**

The serializer takes a map and produces an `&`-joined query string emitted as `query=<string>`. Two independent boolean options modify the encoding: *use-brackets* (collection key notation) and *include-null* (whether `null` values are emitted as empty entries or dropped). The four leaf points below cover scalar values, list values, bracket notation, and nested maps.

*1.1 Scalar values — flat key/value encoding, null handling, whitespace and primitive rendering*

Each entry becomes `key=value` with the value percent-encoded. A `null` value is omitted by default and emitted as a bare `key=` when include-null is enabled. An empty string always emits `key=`. Whitespace is percent-encoded (space -> `%20`, tab -> `%09`). Numbers and booleans render as their textual form (trailing zeros in a fractional number are dropped, e.g. `123.450` -> `123.45`). When every value in a multi-entry map is `null` and they are dropped, the result is an empty string (`query=`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_query_scalars.json`

```json
{
    "description": "Serialize a flat key/value map into a URL query string. Each entry becomes key=value with the value percent-encoded. By default keys whose value is null are omitted entirely; enabling include-null emits them as bare key= entries. Empty-string values always emit key= ; whitespace is percent-encoded (space -> %20, tab -> %09); booleans and numbers render as their textual form.",
    "cases": [
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": "bar"
                }
            },
            "expected_output": "query=foo=bar\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": null
                }
            },
            "expected_output": "query=\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": null
                },
                "includeNullQueryVars": true
            },
            "expected_output": "query=foo=\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": ""
                }
            },
            "expected_output": "query=foo=\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": " bar "
                }
            },
            "expected_output": "query=foo=%20bar%20\n"
        }
    ]
}
```

---

*1.2 List values — repeated-key encoding with empty/null skipping*

When a value is a list, each element is emitted as its own `key=value` pair repeating the same key (`foo=bar&foo=baz`). Empty-string and `null` elements inside a list are skipped; whitespace-only elements are kept and percent-encoded. Non-list sibling entries follow the same scalar rules.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_query_lists.json`

```json
{
    "description": "Serialize a map whose value is a list. Each list element is emitted as a separate key=value pair that repeats the same key. Empty-string and null elements inside the list are skipped; whitespace-only elements are kept and percent-encoded.",
    "cases": [
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": [
                        "bar",
                        "baz",
                        "etc"
                    ]
                }
            },
            "expected_output": "query=foo=bar&foo=baz&foo=etc\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": [
                        "bar",
                        123,
                        456.789,
                        0,
                        -123,
                        -456.789
                    ]
                }
            },
            "expected_output": "query=foo=bar&foo=123&foo=456.789&foo=0&foo=-123&foo=-456.789\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": [
                        "",
                        "baz",
                        "etc"
                    ]
                }
            },
            "expected_output": "query=foo=baz&foo=etc\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": [
                        "bar",
                        null,
                        "etc"
                    ]
                }
            },
            "expected_output": "query=foo=bar&foo=etc\n"
        }
    ]
}
```

---

*1.3 Bracket notation — collection keys with bracket suffixes*

When bracket mode is enabled, list keys gain a percent-encoded `[]` suffix (`%5B%5D`) and nested-map keys are wrapped as `parent%5Bchild%5D` instead of the default dotted form. Scalar sibling entries are unaffected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_query_brackets.json`

```json
{
    "description": "Serialize collection values using bracket notation. When bracket mode is enabled, list keys gain a percent-encoded [] suffix (%5B%5D) and nested map keys are wrapped as key%5Bsubkey%5D instead of the dotted form.",
    "cases": [
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": [
                        "bar",
                        "baz",
                        "etc"
                    ]
                },
                "useBrackets": true
            },
            "expected_output": "query=foo%5B%5D=bar&foo%5B%5D=baz&foo%5B%5D=etc\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": {
                        "bar": "baz"
                    }
                },
                "useBrackets": true
            },
            "expected_output": "query=foo%5Bbar%5D=baz\n"
        }
    ]
}
```

---

*1.4 Nested maps — dot-flattened keys to arbitrary depth*

A nested map is flattened using a dot separator (`parent.child=value`) to arbitrary depth. A nested list still repeats its flattened key. A `null` leaf is dropped by default and emitted as `flattened.key=` when include-null is enabled.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_query_nested_maps.json`

```json
{
    "description": "Serialize a map that contains nested maps. Nested keys are flattened using a dot separator (parent.child=value) to arbitrary depth. A nested list keeps repeating its flattened key. Null leaf values are omitted unless include-null is enabled, in which case they emit the flattened key with an empty value.",
    "cases": [
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": {
                        "bar": "baz"
                    }
                }
            },
            "expected_output": "query=foo.bar=baz\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": {
                        "bar": null
                    }
                }
            },
            "expected_output": "query=\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": {
                        "bar": null
                    }
                },
                "includeNullQueryVars": true
            },
            "expected_output": "query=foo.bar=\n"
        },
        {
            "input": {
                "op": "serialize_query",
                "map": {
                    "foo": {
                        "bar": "baz",
                        "zap": "abc",
                        "etc": {
                            "abc": "def",
                            "ghi": "jkl",
                            "mno": {
                                "opq": "rst",
                                "uvw": "xyz",
                                "aab": [
                                    "bbc",
                                    "ccd",
                                    "eef"
                                ]
                            }
                        }
                    }
                }
            },
            "expected_output": "query=foo.bar=baz&foo.zap=abc&foo.etc.abc=def&foo.etc.ghi=jkl&foo.etc.mno.opq=rst&foo.etc.mno.uvw=xyz&foo.etc.mno.aab=bbc&foo.etc.mno.aab=ccd&foo.etc.mno.aab=eef\n"
        }
    ]
}
```

---

### Feature 2: Edge Trimming Of Path Segments

**As a developer**, I want to trim whitespace and an optional single delimiter character from either or both ends of a string, so I can normalize path fragments before joining them into URLs.

**Expected Behavior / Usage:**

The operation takes the text, a `mode` (`left`, `right`, or `both`) and an optional single delimiter `character`, and prints `result=<trimmed>`. For each affected side, whitespace on that side is removed first; then, if a delimiter character was supplied and exactly one occurrence sits at that edge, that single occurrence is removed too (only one, so `//foo` left-trimmed by `/` yields `/foo`). With no delimiter character, only whitespace is trimmed.

**Test Cases:** `rcb_tests/public_test_cases/feature2_string_trim.json`

```json
{
    "description": "Trim a string. Mode 'left' removes leading whitespace; 'right' removes trailing whitespace; 'both' removes both. When an optional single delimiter character is supplied, after the whitespace on that side is removed, exactly one occurrence of that character (if present at the edge) is also removed.",
    "cases": [
        {
            "input": {
                "op": "trim_text",
                "text": "     /foo",
                "mode": "left"
            },
            "expected_output": "result=/foo\n"
        },
        {
            "input": {
                "op": "trim_text",
                "text": "     /foo",
                "mode": "left",
                "character": "/"
            },
            "expected_output": "result=foo\n"
        },
        {
            "input": {
                "op": "trim_text",
                "text": "//foo",
                "mode": "left",
                "character": "/"
            },
            "expected_output": "result=/foo\n"
        },
        {
            "input": {
                "op": "trim_text",
                "text": "foo/   ",
                "mode": "right",
                "character": "/"
            },
            "expected_output": "result=foo\n"
        },
        {
            "input": {
                "op": "trim_text",
                "text": "foo//",
                "mode": "right",
                "character": "/"
            },
            "expected_output": "result=foo/\n"
        },
        {
            "input": {
                "op": "trim_text",
                "text": "   /foo/   ",
                "mode": "both",
                "character": "/"
            },
            "expected_output": "result=foo\n"
        },
        {
            "input": {
                "op": "trim_text",
                "text": "//foo//",
                "mode": "both",
                "character": "/"
            },
            "expected_output": "result=/foo/\n"
        }
    ]
}
```

---

### Feature 3: URL Composition

**As a developer**, I want to join a base URL and a request path into one absolute URL and append query parameters, so I never produce duplicated or missing slashes and I get predictable parameter merging.

**Expected Behavior / Usage:**

The operation takes a base URL, a request path/URL, and a parameter map, and prints `url=<composed>`. Exactly one slash separates base and path regardless of trailing/leading slashes on either side. If the path is itself an absolute `http`/`https` URL, the base is ignored entirely. Query parameters already present on the **base** are dropped; query parameters present on the **path** are preserved and merged with the explicit parameter map (path query first, then map). An empty parameter map and no path query yields just the joined path.

**Test Cases:** `rcb_tests/public_test_cases/feature3_url_composition.json`

```json
{
    "description": "Join a base URL and a request path into one absolute URL, then append query parameters. Exactly one slash separates the base and path regardless of trailing/leading slashes on either side. If the path is itself an absolute http/https URL, the base is ignored. Query parameters already present on the base are dropped; query parameters present on the path are kept and merged with the explicit parameter map (path-first, then map).",
    "cases": [
        {
            "input": {
                "op": "resolve_url",
                "baseUrl": "foo",
                "url": "bar",
                "parameters": {}
            },
            "expected_output": "url=foo/bar\n"
        },
        {
            "input": {
                "op": "resolve_url",
                "baseUrl": "foo/",
                "url": "/bar",
                "parameters": {}
            },
            "expected_output": "url=foo/bar\n"
        },
        {
            "input": {
                "op": "resolve_url",
                "baseUrl": "https://foo/",
                "url": "/bar",
                "parameters": {
                    "abc": "xyz"
                }
            },
            "expected_output": "url=https://foo/bar?abc=xyz\n"
        },
        {
            "input": {
                "op": "resolve_url",
                "baseUrl": "https://foo/",
                "url": "/bar?first=123&second=456",
                "parameters": {
                    "third": "789",
                    "fourth": "012"
                }
            },
            "expected_output": "url=https://foo/bar?first=123&second=456&third=789&fourth=012\n"
        },
        {
            "input": {
                "op": "resolve_url",
                "baseUrl": "https://foo?first=123&second=456",
                "url": "/bar",
                "parameters": {
                    "third": "789",
                    "fourth": "012"
                }
            },
            "expected_output": "url=https://foo/bar?third=789&fourth=012\n"
        },
        {
            "input": {
                "op": "resolve_url",
                "baseUrl": "https://foo/bar?first=123&second=456",
                "url": "https://bar/foo?fourth=789&fifth=012",
                "parameters": {}
            },
            "expected_output": "url=https://bar/foo?fourth=789&fifth=012\n"
        }
    ]
}
```

---

### Feature 4: Request Construction

**As a developer**, I want to build a request object from a method, URI, base URI, parameters and headers, so I can inspect the fully-resolved method, URL and headers a client would send.

**Expected Behavior / Usage:**

*4.1 Building a request — resolved method, composed URL, sorted headers*

Construction takes a method, a relative-or-absolute request URI, a base URI, an optional parameter map and headers. It prints `method=<method>`, `url=<composed>`, then one `header.<name>=<value>` line per header sorted by name. Query parameters embedded in the URI are preserved and merged with the explicit parameter map; nested maps flatten with a dot separator and lists repeat their key. An absolute request URI ignores the base URI.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_request_build.json`

```json
{
    "description": "Construct an HTTP request from a method, a relative or absolute request URI, a base URI, an optional parameter map and headers. The output reports the resolved method, the fully composed URL (base+path+merged query) and every header sorted by name. Query parameters embedded in the URI are preserved and merged with the explicit parameter map; nested maps flatten with a dot separator and lists repeat their key.",
    "cases": [
        {
            "input": {
                "op": "assemble_request",
                "method": "GET",
                "uri": "/bar",
                "baseUri": "https://foo/"
            },
            "expected_output": "method=GET\nurl=https://foo/bar\n"
        },
        {
            "input": {
                "op": "assemble_request",
                "method": "GET",
                "uri": "/bar?lorem=ipsum&dolor=123",
                "baseUri": "https://foo/"
            },
            "expected_output": "method=GET\nurl=https://foo/bar?lorem=ipsum&dolor=123\n"
        },
        {
            "input": {
                "op": "assemble_request",
                "method": "GET",
                "uri": "/bar",
                "baseUri": "https://foo/",
                "parameters": {
                    "lorem": "ipsum",
                    "dolor": 123
                }
            },
            "expected_output": "method=GET\nurl=https://foo/bar?lorem=ipsum&dolor=123\n"
        },
        {
            "input": {
                "op": "assemble_request",
                "method": "GET",
                "uri": "https://chopper.dev/test3",
                "baseUri": "",
                "parameters": {
                    "foo": "bar",
                    "foo_list": [
                        "one",
                        "two",
                        "three"
                    ],
                    "user": {
                        "name": "john",
                        "surname": "doe"
                    }
                }
            },
            "expected_output": "method=GET\nurl=https://chopper.dev/test3?foo=bar&foo_list=one&foo_list=two&foo_list=three&user.name=john&user.surname=doe\n"
        },
        {
            "input": {
                "op": "assemble_request",
                "method": "GET",
                "uri": "/bar",
                "baseUri": "https://foo/",
                "headers": {
                    "content-type": "application/json; charset=utf-8",
                    "accept": "application/json; charset=utf-8"
                }
            },
            "expected_output": "method=GET\nurl=https://foo/bar\nheader.accept=application/json; charset=utf-8\nheader.content-type=application/json; charset=utf-8\n"
        }
    ]
}
```

---

*4.2 Rejecting a base URI that carries query parameters*

A base URI must not itself contain query parameters — default query parameters belong in a parameter map or an interceptor, not baked into the base. Attempting to construct a request with such a base URI is a configuration error, surfaced as the neutral category line `error=base_uri_has_query` with no host-language runtime detail.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_request_baseuri_query.json`

```json
{
    "description": "Reject a base URI that itself carries query parameters. Constructing a request with such a base URI is a configuration error: default query parameters must be supplied through a parameter map or interceptor, never baked into the base. The error is reported as a neutral category with no language runtime detail.",
    "cases": [
        {
            "input": {
                "op": "assemble_request",
                "method": "GET",
                "uri": "foo",
                "baseUri": "foo/bar?first=123"
            },
            "expected_output": "error=base_uri_has_query\n"
        },
        {
            "input": {
                "op": "assemble_request",
                "method": "GET",
                "uri": "foo",
                "baseUri": "http://foo/bar?first=123&second=456"
            },
            "expected_output": "error=base_uri_has_query\n"
        }
    ]
}
```

---

### Feature 5: Header Application

**As a developer**, I want to add one header or a batch of headers onto an existing request's header set with controllable override behavior, so I can layer defaults and per-call headers predictably.

**Expected Behavior / Usage:**

Given a starting set of headers, the operation applies either a single `name`/`value` header or a batch `apply` map, producing a new header set printed as `header.<name>=<value>` lines sorted by name. By default an existing header with the same name is overwritten by the incoming value; when override is disabled, the existing value is kept and the incoming one ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature5_header_apply.json`

```json
{
    "description": "Apply one header (name+value) or a batch of headers onto an existing request's header set, producing a new header set. By default an existing header with the same name is overwritten; when override is disabled, the existing value is kept and the incoming one ignored. Output lists the resulting headers sorted by name.",
    "cases": [
        {
            "input": {
                "op": "set_headers",
                "initialHeaders": {},
                "name": "foo",
                "value": "bar"
            },
            "expected_output": "header.foo=bar\n"
        },
        {
            "input": {
                "op": "set_headers",
                "initialHeaders": {
                    "foo": "bar"
                },
                "name": "bar",
                "value": "foo"
            },
            "expected_output": "header.bar=foo\nheader.foo=bar\n"
        },
        {
            "input": {
                "op": "set_headers",
                "initialHeaders": {
                    "foo": "bar"
                },
                "name": "foo",
                "value": "foo"
            },
            "expected_output": "header.foo=foo\n"
        },
        {
            "input": {
                "op": "set_headers",
                "initialHeaders": {
                    "foo": "bar"
                },
                "name": "foo",
                "value": "foo",
                "override": false
            },
            "expected_output": "header.foo=bar\n"
        },
        {
            "input": {
                "op": "set_headers",
                "initialHeaders": {
                    "foo": "bar"
                },
                "apply": {
                    "bar": "foo"
                }
            },
            "expected_output": "header.bar=foo\nheader.foo=bar\n"
        }
    ]
}
```

---

### Feature 6: HTTP Method Dispatch

**As a developer**, I want to issue calls for any HTTP method through a configured client that encodes my body and reports the response outcome, so I can talk to an API declaratively.

**Expected Behavior / Usage:**

*6.1 Issuing calls and observing the outgoing request*

A call specifies a method, base URL, path, optional query, headers, an optional body, an optional body converter (`json` or `form`) and an optional header-injecting interceptor. The output echoes the request as actually handed to the transport: `request_method=`, `request_url=` (fully-qualified, with query), `request_header.<name>=` lines sorted by name (including any `content-type` the converter set), and `request_body=` when a body was sent. The JSON converter sets `content-type: application/json; charset=utf-8` and JSON-encodes the body; the form converter sets `content-type: application/x-www-form-urlencoded; charset=utf-8` and encodes the map as `key=value` pairs. After the request lines the response outcome lines (see 6.2) are also printed.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_http_methods.json`

```json
{
    "description": "Issue an HTTP call through the client for a given method, path and query, optionally encoding a structured body with the JSON or form converter and applying a header-injecting interceptor. Output echoes the outgoing request as actually sent to the transport: method, fully-qualified URL, headers (sorted, including any content-type the converter set), and the serialized body. The JSON converter sets content-type application/json and JSON-encodes the body; the form converter sets content-type application/x-www-form-urlencoded and encodes the map as key=value pairs.",
    "cases": [
        {
            "input": {
                "op": "http_request",
                "baseUrl": "http://localhost:8000",
                "method": "GET",
                "path": "/test/get",
                "query": {
                    "key": "val"
                },
                "headers": {
                    "int": "42"
                },
                "converter": "json",
                "addHeaderInterceptor": {
                    "foo": "bar"
                },
                "response": {
                    "body": "get response",
                    "status": 200
                }
            },
            "expected_output": "request_method=GET\nrequest_url=http://localhost:8000/test/get?key=val\nrequest_header.foo=bar\nrequest_header.int=42\nresponse_status=200\nresponse_successful=true\nresponse_body=get response\n"
        },
        {
            "input": {
                "op": "http_request",
                "baseUrl": "http://localhost:8000",
                "method": "POST",
                "path": "/test/post",
                "query": {
                    "key": "val"
                },
                "headers": {
                    "int": "42"
                },
                "converter": "json",
                "body": {
                    "content": "body"
                },
                "addHeaderInterceptor": {
                    "foo": "bar"
                },
                "response": {
                    "body": "post response",
                    "status": 200
                }
            },
            "expected_output": "request_method=POST\nrequest_url=http://localhost:8000/test/post?key=val\nrequest_header.content-type=application/json; charset=utf-8\nrequest_header.foo=bar\nrequest_header.int=42\nrequest_body={\"content\":\"body\"}\nresponse_status=200\nresponse_successful=true\nresponse_body=post response\n"
        },
        {
            "input": {
                "op": "http_request",
                "baseUrl": "http://localhost:8000",
                "method": "PUT",
                "path": "/test/put",
                "query": {
                    "key": "val"
                },
                "headers": {
                    "int": "42"
                },
                "converter": "json",
                "body": {
                    "content": "body"
                },
                "addHeaderInterceptor": {
                    "foo": "bar"
                },
                "response": {
                    "body": "put response",
                    "status": 200
                }
            },
            "expected_output": "request_method=PUT\nrequest_url=http://localhost:8000/test/put?key=val\nrequest_header.content-type=application/json; charset=utf-8\nrequest_header.foo=bar\nrequest_header.int=42\nrequest_body={\"content\":\"body\"}\nresponse_status=200\nresponse_successful=true\nresponse_body=put response\n"
        },
        {
            "input": {
                "op": "http_request",
                "baseUrl": "http://localhost:8000",
                "method": "DELETE",
                "path": "/test/delete",
                "query": {
                    "key": "val"
                },
                "headers": {
                    "int": "42"
                },
                "converter": "json",
                "addHeaderInterceptor": {
                    "foo": "bar"
                },
                "response": {
                    "body": "delete response",
                    "status": 200
                }
            },
            "expected_output": "request_method=DELETE\nrequest_url=http://localhost:8000/test/delete?key=val\nrequest_header.foo=bar\nrequest_header.int=42\nresponse_status=200\nresponse_successful=true\nresponse_body=delete response\n"
        },
        {
            "input": {
                "op": "http_request",
                "baseUrl": "http://localhost:8000",
                "method": "POST",
                "path": "/test/map",
                "converter": "form",
                "body": {
                    "foo": "test",
                    "default": "hello"
                },
                "response": {
                    "body": "ok",
                    "status": 200
                }
            },
            "expected_output": "request_method=POST\nrequest_url=http://localhost:8000/test/map\nrequest_header.content-type=application/x-www-form-urlencoded; charset=utf-8\nrequest_body=foo=test&default=hello\nresponse_status=200\nresponse_successful=true\nresponse_body=ok\n"
        }
    ]
}
```

---

*6.2 Reporting the response outcome (success vs error)*

The response is reported with `response_status=<code>`, `response_successful=<bool>`, and then either `response_body=<decoded>` on a 2xx success or `response_error=<payload>` on a non-2xx failure. A successful response carries the decoded body and no error; an unsuccessful response carries the error payload and no body.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_response_status.json`

```json
{
    "description": "Surface the outcome of an HTTP call. A 2xx status yields a successful response carrying the decoded body; a non-2xx status yields an unsuccessful response carrying the error payload instead of a body. Output reports the status code, a success flag, and either the body (on success) or the error (on failure).",
    "cases": [
        {
            "input": {
                "op": "http_request",
                "baseUrl": "http://localhost:8000",
                "method": "GET",
                "path": "/test/get",
                "headers": {
                    "int": "42"
                },
                "converter": "json",
                "response": {
                    "body": "get response",
                    "status": 200
                }
            },
            "expected_output": "request_method=GET\nrequest_url=http://localhost:8000/test/get\nrequest_header.int=42\nresponse_status=200\nresponse_successful=true\nresponse_body=get response\n"
        },
        {
            "input": {
                "op": "http_request",
                "baseUrl": "http://localhost:8000",
                "method": "GET",
                "path": "/test/get",
                "headers": {
                    "int": "42"
                },
                "converter": "json",
                "response": {
                    "body": "error",
                    "status": 400
                }
            },
            "expected_output": "request_method=GET\nrequest_url=http://localhost:8000/test/get\nrequest_header.int=42\nresponse_status=400\nresponse_successful=false\nresponse_error=error\n"
        }
    ]
}
```

---

### Feature 7: Response Body Decoding

**As a developer**, I want a JSON response payload decoded into the shape I ask for, so I can work with typed values instead of raw strings.

**Expected Behavior / Usage:**

The operation takes a raw JSON `payload` and a requested `bodyType` (`String`, `ListString`, `ListInt`, or `Map`) and prints `body=<rendered>`. A quoted JSON string decodes to its inner text; a JSON array decodes to a list; a JSON object decodes to a key/value map. The decoded value is rendered as canonical JSON, except a plain string which is rendered verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature7_json_decode.json`

```json
{
    "description": "Decode a JSON response payload into the requested shape. A quoted JSON string decodes to its inner text; a JSON array decodes to a list of elements; a JSON object decodes to a key/value map. The decoded value is rendered back as canonical JSON (or the raw text for a plain string).",
    "cases": [
        {
            "input": {
                "op": "decode_body",
                "payload": "\"foo\"",
                "bodyType": "String"
            },
            "expected_output": "body=foo\n"
        },
        {
            "input": {
                "op": "decode_body",
                "payload": "[\"foo\",\"bar\"]",
                "bodyType": "ListString"
            },
            "expected_output": "body=[\"foo\",\"bar\"]\n"
        },
        {
            "input": {
                "op": "decode_body",
                "payload": "[1,2]",
                "bodyType": "ListInt"
            },
            "expected_output": "body=[1,2]\n"
        },
        {
            "input": {
                "op": "decode_body",
                "payload": "{\"foo\":\"bar\"}",
                "bodyType": "Map"
            },
            "expected_output": "body={\"foo\":\"bar\"}\n"
        }
    ]
}
```

---

### Feature 8: Authentication Retry

**As a developer**, I want a request that is rejected with `401` to be automatically retried once with an attached authorization token, so transient auth challenges are handled transparently.

**Expected Behavior / Usage:**

When the first attempt returns `401 Unauthorized`, an authenticator attaches an authorization token and the request is replayed once. The output reports `first_response_status=401`, `retried_authorization=<token observed on the replayed request>`, `final_response_status=<code>`, and `final_response_body=<decoded body>` from the successful retry. The token attached is the one supplied to the authenticator.

**Test Cases:** `rcb_tests/public_test_cases/feature8_auth_retry.json`

```json
{
    "description": "Automatically retry a request once after an authentication challenge. The first attempt returns 401 Unauthorized; an authenticator then attaches an authorization token and the request is replayed. Output reports the first attempt's status, the authorization token observed on the retried request, and the final status and body after the successful retry.",
    "cases": [
        {
            "input": {
                "op": "auth_retry",
                "method": "GET",
                "path": "/test/get",
                "query": {
                    "key": "val"
                },
                "token": "some_fake_token"
            },
            "expected_output": "first_response_status=401\nretried_authorization=some_fake_token\nfinal_response_status=200\nfinal_response_body=ok\n"
        },
        {
            "input": {
                "op": "auth_retry",
                "method": "POST",
                "path": "/test/post",
                "query": {
                    "key": "val"
                },
                "body": {
                    "name": "john"
                },
                "token": "another_token"
            },
            "expected_output": "first_response_status=401\nretried_authorization=another_token\nfinal_response_status=200\nfinal_response_body=ok\n"
        }
    ]
}
```

---

### Feature 9: Request/Response Logging Middleware

**As a developer**, I want middleware that renders requests and responses in human-readable form, so I can debug traffic without external tooling.

**Expected Behavior / Usage:**

*9.1 curl rendering — an equivalent command line*

Renders an outgoing request as a single `curl` command line: `curl -v -X <METHOD>`, one `-H '<name>: <value>'` per header (including the body encoder's `content-type` for a text body), `-d '<body>'` when a body is present, and the quoted target URL last.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_curl.json`

```json
{
    "description": "Render an outgoing request as an equivalent curl command line, including the method (-X), each header (-H), the body (-d) and the quoted target URL. Headers added by the body encoder (such as content-type for a text body) appear in the command.",
    "cases": [
        {
            "input": {
                "op": "curl",
                "method": "POST",
                "uri": "/",
                "baseUri": "base",
                "body": "test",
                "headers": {
                    "foo": "bar"
                }
            },
            "expected_output": "curl -v -X POST -H 'foo: bar' -H 'content-type: text/plain; charset=utf-8' -d 'test' \"base/\"\n"
        },
        {
            "input": {
                "op": "curl",
                "method": "GET",
                "uri": "/path",
                "baseUri": "base",
                "headers": {
                    "x-token": "abc"
                }
            },
            "expected_output": "curl -v -X GET -H 'x-token: abc' \"base/path\"\n"
        }
    ]
}
```

---

*9.2 Request logging — multi-line request dump*

Emits a multi-line log of an outgoing request: a start line `--> <METHOD> <url>`, one line per header (`name: value`), the body line, and an end line `--> END <METHOD> (<N>-byte body)` stating the body size in bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_log_request.json`

```json
{
    "description": "Emit a human-readable multi-line log of an outgoing request: a start line with method and URL, one line per header, the body, and an end line stating the method and the body size in bytes.",
    "cases": [
        {
            "input": {
                "op": "log_request",
                "method": "POST",
                "uri": "/",
                "baseUri": "base",
                "body": "test",
                "headers": {
                    "foo": "bar"
                }
            },
            "expected_output": "--> POST base/\nfoo: bar\ncontent-type: text/plain; charset=utf-8\ntest\n--> END POST (4-byte body)\n"
        }
    ]
}
```

---

*9.3 Response logging — multi-line response dump*

Emits a multi-line log of a received response: a status line `<-- <status> <url>`, one line per response header (`name: value`), the response body line, and an end line `--> END <METHOD> (<N>-byte body)` stating the originating method and the body size in bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_log_response.json`

```json
{
    "description": "Emit a human-readable multi-line log of a received response: a status line with status code and URL, one line per response header, the response body, and an end line stating the originating method and the body size in bytes.",
    "cases": [
        {
            "input": {
                "op": "log_response",
                "method": "POST",
                "uri": "/",
                "baseUri": "base",
                "body": "test",
                "headers": {
                    "foo": "bar"
                },
                "response": {
                    "body": "responseBodyBase",
                    "status": 200,
                    "headers": {
                        "foo": "bar"
                    }
                }
            },
            "expected_output": "<-- 200 base/\nfoo: bar\nresponseBodyBase\n--> END POST (16-byte body)\n"
        }
    ]
}
```

---

### Feature 10: Multipart Request Assembly

**As a developer**, I want to assemble a `multipart/form-data` request from a list of named parts, so I can upload mixed fields and files in one request.

**Expected Behavior / Usage:**

*10.1 Building parts — fields, file bytes, and null skipping*

The operation takes a list of parts; each part has a `kind` (`value` or `file`) and a `name`. A `value` part becomes a form field whose value is the stringified input. A `file` part carrying a byte list becomes a file upload. Any part whose value is `null` is skipped entirely. Output lists `field.<name>=<value>` lines (sorted by name), then `file_count=<n>`, then a `file.<name>.bytes=<comma-separated bytes>` line for each file part.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_multipart_build.json`

```json
{
    "description": "Build a multipart/form-data request from a list of parts. A value part becomes a form field whose value is the stringified input. A file part carrying a byte list becomes a file upload. Parts whose value is null are skipped entirely. Output lists the resulting fields (sorted by name), the number of file parts, and the raw bytes of each file part.",
    "cases": [
        {
            "input": {
                "op": "multipart",
                "parts": [
                    {
                        "kind": "value",
                        "name": "foo",
                        "value": "bar"
                    },
                    {
                        "kind": "value",
                        "name": "int",
                        "value": 42
                    }
                ]
            },
            "expected_output": "field.foo=bar\nfield.int=42\nfile_count=0\n"
        },
        {
            "input": {
                "op": "multipart",
                "parts": [
                    {
                        "kind": "value",
                        "name": "foo",
                        "value": "bar"
                    },
                    {
                        "kind": "file",
                        "name": "file",
                        "value": [
                            0,
                            1,
                            2,
                            3,
                            4,
                            5,
                            6,
                            7,
                            8,
                            9
                        ]
                    }
                ]
            },
            "expected_output": "field.foo=bar\nfile_count=1\nfile.file.bytes=0,1,2,3,4,5,6,7,8,9\n"
        },
        {
            "input": {
                "op": "multipart",
                "parts": [
                    {
                        "kind": "value",
                        "name": "int",
                        "value": 42
                    },
                    {
                        "kind": "file",
                        "name": "list int",
                        "value": [
                            1,
                            2
                        ]
                    },
                    {
                        "kind": "value",
                        "name": "null value",
                        "value": null
                    },
                    {
                        "kind": "file",
                        "name": "null file",
                        "value": null
                    }
                ]
            },
            "expected_output": "field.int=42\nfile_count=1\nfile.list int.bytes=1,2\n"
        }
    ]
}
```

---

*10.2 Rejecting an unsupported file payload*

A file part must carry a byte list (or an already-built file object). Supplying a bare scalar such as a number is invalid and surfaced as the neutral category line `error=unsupported_part_type`, with no host-language runtime detail leaked.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_multipart_error.json`

```json
{
    "description": "Reject an unsupported file part payload. A file part must carry a byte list (or an already-built file object); supplying a bare scalar such as a number is invalid and reported as a neutral error category, with no language runtime detail leaked.",
    "cases": [
        {
            "input": {
                "op": "multipart",
                "parts": [
                    {
                        "kind": "file",
                        "name": "",
                        "value": 123
                    }
                ]
            },
            "expected_output": "error=unsupported_part_type\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file library implementing the features above (query/URL encoding, request modeling, header utilities, body conversion, client dispatch, authentication retry, interceptors/logging, multipart assembly), with each responsibility in its own cohesive unit and no coupling to stdin/stdout or the JSON command envelope.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command object from stdin, routes on its `op` field to the appropriate core API, and prints the documented line-oriented stdout contract — including normalizing any error into a neutral `error=<category>` line. This adapter is logically separated from the core domain and is the only component aware of the JSON envelope.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_query_scalars.json` under `--cases-dir public_test_cases` -> `rcb_tests/stdout/public_test_cases/feature1_1_query_scalars@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- escape special characters exactly like the http_parser does for headers
