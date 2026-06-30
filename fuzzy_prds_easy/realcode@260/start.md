## Product Requirement Document

# Declarative HTTP Client Generator - Interface-Driven Request Binding

## Project Goal

Build a compile-time code generator and runtime that lets developers describe a remote HTTP API as a plain host-language interface, annotated with declarative metadata, and have a fully working client implementation generated automatically. Developers declare *what* request each method represents (verb, path, query, headers, body, encoding) and the generated client takes care of *how* the request is assembled, addressed, and dispatched, so no hand-written networking boilerplate is needed.

---

## Background & Problem

Without this tool, developers calling a remote API must hand-write, for every endpoint, the same mechanical plumbing: pick the HTTP verb, concatenate a base address with a relative path, substitute dynamic path segments, append query parameters with correct encoding, assemble headers, choose and serialize the body (raw, form-url-encoded, or multipart), and wire all of that into an HTTP engine. This is repetitive, easy to get subtly wrong (double-encoding, missing slashes, wrong content type), and drifts out of sync as the API evolves.

With this tool, the API surface is expressed once as an annotated interface. A code generator reads the interface at build time, validates that the declarations are internally consistent, and emits an implementation that produces correctly-formed requests at runtime. Misuse (such as two verbs on one method, a body on a verb that forbids it, or a malformed base address) is caught and reported as a precise, neutral diagnostic rather than producing a broken client.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a complex domain with several distinct responsibilities — interface/metadata parsing, generation-time validation, request assembly, URL resolution, body/encoding handling, parameter conversion, and a runtime dispatch layer. The codebase MUST NOT be a single monolithic file. Provide a clear multi-module/multi-file tree separating the generator (compile-time validation + emission) from the runtime (request building + dispatch) from the execution adapter. Do not over-engineer, but reflect the real separation of concerns.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" define a **black-box contract for the execution adapter only**, not the internal data model. The core generator and runtime MUST be completely decoupled from stdin/stdout and from JSON parsing. The execution adapter is the sole component that translates a JSON request into idiomatic calls against the generator and runtime (it synthesizes an interface from the request spec, drives the real generator over it, loads the generated implementation, invokes it against a capturing transport, and formats the observed result).

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility:** Keep parsing, validation, generation, runtime request assembly, and output formatting in distinct units.
   - **Open/Closed:** New parameter roles, encodings, or converters must be addable without rewriting the dispatch core.
   - **Liskov Substitution:** Transport/engine abstractions must be substitutable (the adapter substitutes a capturing transport for a real network engine).
   - **Interface Segregation:** Converter, transport, and request-builder abstractions must each stay small and cohesive.
   - **Dependency Inversion:** The runtime depends on a transport abstraction and a converter registry, not on a concrete network stack.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The annotated-interface surface must read naturally in the target language; generated code must be invisible to the caller.
   - **Resilience:** Every invalid declaration must be modeled as a specific, categorizable failure rather than a generic crash. Generation-time violations are reported as neutral error categories; runtime configuration failures (e.g. base address validation, missing converter) likewise map to neutral categories. Host-language stack traces must never leak into the contract output.

### Neutral request schema (adapter input)

The execution adapter reads a single JSON object from stdin describing one scenario. Fields:

- `op` (string, optional, default `"request"`): `"request"` synthesizes and drives an interface method; `"convert"` exercises the standalone parameter-conversion path.
- `lang` (string, optional, default host language): `"java"` requests a foreign-language interface (used to exercise interface-shape validation).
- `withPackage` (bool, optional, default `true`): whether the synthesized interface resides in a package.
- `generic` (bool, optional, default `false`): whether the synthesized interface carries a type parameter.
- `baseUrl` (string, optional, default a valid `http://localhost/`): the configured base address.
- `checkUrl` (bool, optional, default `true`): whether base-address relative-resolution checking is enabled.
- `suspend` (bool, optional, default `true`): whether the synthesized method is asynchronous.
- `streaming` (bool, optional, default `false`): whether the method is declared as a streaming/deferred-handle method.
- `return` (string, optional): an explicit return type override for the synthesized method.
- `http` (array, for `op=request`): one or more `{ "verb": <string>, "path": <string>, "hasBody": <bool optional>, "value": <string optional> }` verb declarations. More than one entry exercises the multiple-verb rule.
- `encoding` (array of string, optional): zero or more of `"form"`, `"multipart"`.
- `headers` (array of string, optional): fixed static headers, each `"Name:Value"`.
- `params` (array, optional): parameter declarations, each `{ "kind": <role>, "key": <string optional>, "name": <string>, "type": <string optional>, "encoded": <bool optional>, "requestType": <string optional>, "header": <string optional> }`. `kind` is one of: `path`, `url`, `body`, `field`, `fieldMap`, `part`, `partMap`, `query`, `queryName`, `queryMap`, `header`, `headerMap`, `reqBuilder`.
- `args` (array, optional): runtime argument values supplied positionally to the synthesized method.
- For `op=convert`: `from` (string), `to` (string), `value` (string), `converter` (bool — whether a converter supporting the requested conversion is registered).

### Output contract (adapter stdout)

On success the adapter prints newline-separated `key=value` lines in this order, omitting lines that do not apply:

- `method=<VERB>`
- `url=<fully resolved absolute URL>`
- `body=none|text|form|multipart`
- `text=<payload>` (only when `body=text`)
- `field=<name>=<value>` per field, sorted by name (only when `body=form`)
- `header=<name>=<value>` per user-supplied header, sorted by name (static `Accept`/`Accept-Charset` excluded)
- For `op=convert`: `converted=<value>` then `type=<simple type name>`.

On any failure the adapter prints one or more `error=<category>` lines (sorted, newline-joined when several apply) and nothing else. Categories are neutral and language-agnostic; the full set is the union of those appearing in the feature cases below.

---

## Core Features

### Feature 1: HTTP method binding

**As a developer**, I want to bind an interface method to an HTTP verb and relative path, so I can declare an endpoint without writing request-construction code.

**Expected Behavior / Usage:**

A method-level declaration names an HTTP verb and a relative path; the generated client issues a request whose method and URL match. A generic verb form may additionally declare that the request carries a body. Declaring more than one verb on the same method is rejected at generation time with `error=[a specific sentinel error category]`. The adapter prints the issued request's method, resolved URL and body kind, or the error category.

**Test Cases:** `rcb_tests/public_test_cases/feature01_http_method.json`

```json
{
  "description": "Binding of an interface method to an HTTP request line. A declarative method-level annotation names the HTTP verb and a relative path; the generated client must issue a request whose method and URL match. A dedicated generic verb form may additionally declare that the request carries a body. Declaring more than one verb annotation on the same method is rejected at generation time. The adapter prints the issued request's method, resolved URL and body kind, or a neutral error category when generation fails.",
  "cases": [
    {"input": {"http": [{"verb": "GET", "path": "user"}]}, "expected_output": "method=GET\nurl=http://localhost/user\nbody=none"},
    {"input": {"http": [{"verb": "GET", "path": "user/followers"}, {"verb": "POST", "path": "repos/foso/experimental/issues"}]}, "expected_output": "error=[a specific sentinel error category]"}
  ]
}
```

---

### Feature 2: URL resolution

**As a developer**, I want the final request URL resolved from the configured base address, the static path, and any dynamic full-URL parameter, so I can address endpoints flexibly.

**Expected Behavior / Usage:**

A method may carry a dynamic full-URL parameter that supplies the target when the verb's static path is empty. When neither a non-empty static path nor a dynamic full-URL parameter is present the request cannot be addressed and generation is rejected (`error=[a specific internal error identifier]`). More than one dynamic full-URL parameter is rejected (`error=multiple_url_annotations`). At runtime the resolved absolute URL combines the base address with the relative target; a parameter whose value is itself absolute overrides the base. The adapter prints method, resolved URL and body kind, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature02_url_resolution.json`

```json
{
  "description": "Resolution of the final request URL. A method may carry a dynamic full-URL parameter that supplies the request target when the verb's static path is empty. When neither a non-empty static path nor a dynamic full-URL parameter is present the request cannot be addressed and generation is rejected. Declaring more than one dynamic full-URL parameter is also rejected. At runtime the resolved absolute URL combines the configured base address with the relative target, and a parameter whose value is itself an absolute URL overrides the base entirely. The adapter prints the issued request's method, resolved URL and body kind, or a neutral error category.",
  "cases": [
    {"input": {"http": [{"verb": "GET", "path": ""}], "params": [{"kind": "url", "name": "url"}], "args": ["posts/9"]}, "expected_output": "method=GET\nurl=http://localhost/posts/9\nbody=none"},
    {"input": {"http": [{"verb": "GET", "path": ""}]}, "expected_output": "error=[a specific internal error identifier]"}
  ]
}
```

---

### Feature 3: Base address validation

**As a developer**, I want the configured base address validated before any request is built, so misconfiguration fails fast with a clear category.

**Expected Behavior / Usage:**

The base address must be present, must end with a path separator, and must use a recognised URL scheme; otherwise client construction fails before any request is issued, producing `error=base_url_required`, `error=base_url_must_end_with_slash`, or `error=base_url_invalid_scheme` respectively. The adapter prints the neutral error category.

**Test Cases:** `rcb_tests/public_test_cases/feature03_base_url_validation.json`

```json
{
  "description": "Validation of the configured base address. The base address must be present, must end with a path separator, and must use a recognised URL scheme; otherwise client construction fails before any request is issued. The adapter prints a neutral error category for each invalid configuration.",
  "cases": [
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "baseUrl": "http://www.example.com"}, "expected_output": "error=base_url_must_end_with_slash"}
  ]
}
```

---

### Feature 4: Path-segment substitution

**As a developer**, I want a parameter to fill a named placeholder in the path, so I can build dynamic endpoint URLs.

**Expected Behavior / Usage:**

A parameter marked as a path variable replaces a named placeholder in the relative path. A variant flag marks the supplied value as already URL-encoded so it is inserted verbatim. A path-variable parameter may not be nullable (`error=path_must_not_be_nullable`), and a placeholder-substitution parameter is only meaningful when the verb declares a non-empty relative path (`error=path_requires_relative_url`). The adapter prints method, resolved URL and body kind, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature04_path.json`

```json
{
  "description": "Path-segment substitution. A method parameter marked as a path variable replaces a named placeholder inside the relative path. A variant flag marks the supplied value as already URL-encoded so it is inserted verbatim. A path-variable parameter may not be nullable, and a placeholder-substitution parameter is only meaningful when the verb declares a non-empty relative path. The adapter prints the issued request's method, resolved URL and body kind, or a neutral error category.",
  "cases": [
    {"input": {"http": [{"verb": "GET", "path": "user/{id}"}], "params": [{"kind": "path", "key": "id", "name": "id"}], "args": ["abc"]}, "expected_output": "method=GET\nurl=http://localhost/user/abc\nbody=none"},
    {"input": {"http": [{"verb": "GET", "path": "user/{id}"}], "params": [{"kind": "path", "key": "id", "name": "id", "type": "String?"}], "args": ["x"]}, "expected_output": "error=path_must_not_be_nullable"}
  ]
}
```

---

### Feature 5: Query-string construction

**As a developer**, I want parameters to contribute query values in several roles, so I can build flexible query strings.

**Expected Behavior / Usage:**

Parameters can contribute a single named query value, a per-element repeated value when the parameter is a list, a bare query name without a value, or a set of named values supplied as a map. Each role has an encoded variant that appends to the already-encoded query section. Map-valued query parameters must be maps keyed by string; other container or key types are rejected at generation time (`error=query_map_must_be_map`, `error=query_map_keys_must_be_string`). The adapter prints method, resolved URL and body kind, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature05_query.json`

```json
{
  "description": "Query-string construction. Parameters can contribute a single named query value, a per-element repeated value when the parameter is a list, a bare query name without a value, or a set of named values supplied as a map. Each role has an encoded variant that appends the value to the already-encoded query section. Map-valued query parameters must be maps keyed by string; other key or container types are rejected at generation time. The adapter prints the issued request's method, resolved URL and body kind, or a neutral error category.",
  "cases": [
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "params": [{"kind": "query", "key": "name", "name": "q1"}, {"kind": "query", "key": "user", "encoded": true, "name": "q2", "type": "Int"}], "args": ["bob", 5]}, "expected_output": "method=GET\nurl=http://localhost/posts?name=bob&user=5\nbody=none"},
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "params": [{"kind": "queryMap", "name": "m", "type": "String"}], "args": ["x"]}, "expected_output": "error=query_map_must_be_map"}
  ]
}
```

---

### Feature 6: Request header construction

**As a developer**, I want to declare static and parameter-driven headers, so I can attach metadata to requests.

**Expected Behavior / Usage:**

A method may declare a fixed list of static headers, a single named header from a parameter, a repeated named header from a list parameter, or a set of named headers supplied as a map; static and parameter-driven headers may be combined. Map-valued header parameters must be maps keyed by string; other container or key types are rejected (`error=header_map_must_be_map`, `error=header_map_keys_must_be_string`). The adapter prints method, resolved URL, body kind, and every user-supplied header sorted by name, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature06_header.json`

```json
{
  "description": "Request header construction. A method may declare a fixed list of static headers, a single named header taken from a parameter, a repeated named header taken from a list parameter, or a set of named headers supplied as a map. Static and parameter-driven headers may be combined on one method. Map-valued header parameters must be maps keyed by string; other key or container types are rejected at generation time. The adapter prints the issued request's method, resolved URL, body kind, and every user-supplied header sorted by name, or a neutral error category.",
  "cases": [
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "headers": ["x:y", "a:b"]}, "expected_output": "method=GET\nurl=http://localhost/posts\nbody=none\nheader=a=b\nheader=x=y"},
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "params": [{"kind": "headerMap", "name": "h", "type": "Map<String, String>"}], "args": [{"H1": "a", "H2": "b"}]}, "expected_output": "method=GET\nurl=http://localhost/posts\nbody=none\nheader=H1=a\nheader=H2=b"}
  ]
}
```

---

### Feature 7: Request body attachment

**As a developer**, I want to mark a parameter as the request body, so its value is sent as the payload.

**Expected Behavior / Usage:**

A method may mark a single parameter as the request body, sent as the payload. A body parameter may not be nullable (`error=body_must_not_be_nullable`), may only appear on a verb that permits a body (`error=body_not_allowed_on_non_body_method`), and may not be combined with a form or multipart encoding declaration (`error=body_not_allowed_with_form_encoding`). The adapter prints method, resolved URL, body kind and, for a textual payload, the body text, or the error category for each violation.

**Test Cases:** `rcb_tests/public_test_cases/feature07_body.json`

```json
{
  "description": "Request body attachment. A method may mark a single parameter as the request body, which is sent as the request payload. A body parameter may not be nullable, may only appear on a verb that permits a request body, and may not be combined with a form or multipart encoding declaration. The adapter prints the issued request's method, resolved URL, body kind and, for a textual payload, the body text, or a neutral error category for each violation.",
  "cases": [
    {"input": {"http": [{"verb": "POST", "path": "user"}], "params": [{"kind": "body", "name": "id"}], "args": ["theBody"]}, "expected_output": "method=POST\nurl=http://localhost/user\nbody=text\ntext=theBody"},
    {"input": {"http": [{"verb": "GET", "path": "user"}], "params": [{"kind": "body", "name": "id"}], "return": "String?"}, "expected_output": "error=body_not_allowed_on_non_body_method"}
  ]
}
```

---

### Feature 8: Form-url-encoded field bodies

**As a developer**, I want form-field parameters to contribute name/value pairs to a form body, so I can submit form-encoded data.

**Expected Behavior / Usage:**

When a method opts into form encoding, parameters marked as form fields contribute name/value pairs; a map-valued field parameter contributes its entries. A field parameter outside a form-encoded method is rejected (`error=field_requires_form_encoding`). A null field value, and null entries inside a field map, are omitted from the body. Map-valued field parameters must be maps keyed by string (`error=field_map_must_be_map`, `error=field_map_keys_must_be_string`). The adapter prints method, resolved URL, body kind and each form field sorted by name, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature08_form_field.json`

```json
{
  "description": "Form-url-encoded field bodies. When a method opts into form encoding, parameters marked as form fields contribute name/value pairs to a form-encoded body; a map-valued field parameter contributes its entries. A field parameter outside a form-encoded method is rejected. A null field value, and null entries inside a field map, are omitted from the body. Map-valued field parameters must be maps keyed by string; other key or container types are rejected at generation time. The adapter prints the issued request's method, resolved URL, body kind and each form field sorted by name, or a neutral error category.",
  "cases": [
    {"input": {"http": [{"verb": "POST", "path": "posts"}], "encoding": ["form"], "params": [{"kind": "field", "key": "name", "name": "f"}], "args": ["v1"]}, "expected_output": "method=POST\nurl=http://localhost/posts\nbody=form\nfield=name=v1"},
    {"input": {"http": [{"verb": "POST", "path": "posts"}], "encoding": ["form"], "params": [{"kind": "field", "key": "name", "name": "f"}, {"kind": "fieldMap", "name": "m", "type": "Map<String, String>"}], "args": ["v1", {"k2": "v2"}]}, "expected_output": "method=POST\nurl=http://localhost/posts\nbody=form\nfield=k2=v2\nfield=name=v1"}
  ]
}
```

---

### Feature 9: Encoding declarations and constraints

**As a developer**, I want encoding declarations validated, so a form body is well-formed and mutually-exclusive encodings are caught.

**Expected Behavior / Usage:**

A form-encoding declaration is only valid on a verb that permits a body (`error=form_requires_body_method`) and requires at least one form field (`error=form_requires_field`). At most one encoding declaration (form or multipart) may be applied (`error=multiple_encoding_annotations`). A valid form-encoded method with a field produces a form body. The adapter prints method, resolved URL, body kind and form fields, or the error category for each violation.

**Test Cases:** `rcb_tests/public_test_cases/feature09_form_encoding.json`

```json
{
  "description": "Encoding declarations and their constraints. A form-encoding declaration is only valid on a verb that permits a request body and requires at least one form field to be present. At most one encoding declaration (form or multipart) may be applied to a method. A valid form-encoded method with a field produces a form body. The adapter prints the issued request's method, resolved URL, body kind and form fields, or a neutral error category for each violation.",
  "cases": [
    {"input": {"http": [{"verb": "POST", "path": "user"}], "encoding": ["form"], "params": [{"kind": "field", "key": "id", "name": "id"}], "return": "String?", "args": ["7"]}, "expected_output": "method=POST\nurl=http://localhost/user\nbody=form\nfield=id=7"},
    {"input": {"http": [{"verb": "POST", "path": "user"}], "encoding": ["multipart", "form"], "params": [{"kind": "field", "key": "id", "name": "id"}]}, "expected_output": "error=multiple_encoding_annotations"}
  ]
}
```

---

### Feature 10: Multipart part bodies

**As a developer**, I want part parameters to make the request a multipart payload, so I can upload composite data.

**Expected Behavior / Usage:**

Parameters marked as parts, individually or as a map of parts, cause the request body to be sent as a multipart payload. A part parameter may not be nullable (`error=part_must_not_be_nullable`), and a map-of-parts parameter must be a map (`error=part_map_must_be_map`). The adapter prints method, resolved URL and body kind, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature10_multipart_part.json`

```json
{
  "description": "Multipart part bodies. Parameters marked as parts, individually or as a map of parts, cause the request body to be sent as a multipart payload. A part parameter may not be nullable, and a map-of-parts parameter must be a map; other types are rejected at generation time. The adapter prints the issued request's method, resolved URL and body kind, or a neutral error category.",
  "cases": [
    {"input": {"http": [{"verb": "POST", "path": "posts"}], "params": [{"kind": "part", "key": "name", "name": "p"}], "args": ["v"]}, "expected_output": "method=POST\nurl=http://localhost/posts\nbody=multipart"},
    {"input": {"http": [{"verb": "POST", "path": "posts"}], "suspend": false, "params": [{"kind": "part", "name": "name", "type": "String?"}]}, "expected_output": "error=part_must_not_be_nullable"}
  ]
}
```

---

### Feature 11: Streaming responses

**As a developer**, I want to declare a method as streaming, so it returns a deferred handle and the request fires when executed.

**Expected Behavior / Usage:**

A method may be declared as streaming, in which case it must return a deferred HTTP-statement handle rather than a decoded value; the underlying request is issued when the handle is executed. Declaring streaming on a method whose return type is not the streaming handle is rejected (`error=streaming_requires_statement_return`). The adapter prints method, resolved URL and body kind, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature11_streaming.json`

```json
{
  "description": "Streaming responses. A method may be declared as streaming, in which case it must return a deferred HTTP-statement handle rather than a decoded value; the underlying request is issued when the handle is executed. Declaring streaming on a method whose return type is not the streaming handle is rejected at generation time. The adapter prints the issued request's method, resolved URL and body kind, or a neutral error category.",
  "cases": [
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "streaming": true}, "expected_output": "method=GET\nurl=http://localhost/posts\nbody=none"},
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "streaming": true, "return": "String"}, "expected_output": "error=streaming_requires_statement_return"}
  ]
}
```

---

### Feature 12: Per-request builder injection

**As a developer**, I want to pass a builder block that mutates the outgoing request, so I can imprint per-call customizations.

**Expected Behavior / Usage:**

A method may accept a parameter that is a builder block applied to the outgoing request, letting the caller imprint arbitrary mutations such as an extra header. At most one builder parameter is allowed (`error=multiple_request_builders`), and the parameter must have the builder block type (`error=req_builder_wrong_type`). The adapter exercises the positive case with a builder that appends one header and prints method, resolved URL, body kind and headers, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature12_request_builder.json`

```json
{
  "description": "Per-request builder injection. A method may accept a parameter that is a builder block applied to the outgoing request, letting the caller imprint arbitrary request mutations such as an extra header. At most one builder parameter is allowed, and the parameter must have the builder block type; other forms are rejected at generation time. The adapter exercises the positive case with a builder that appends one header and prints the issued request's method, resolved URL, body kind and headers, or a neutral error category.",
  "cases": [
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "params": [{"kind": "reqBuilder", "name": "builder", "header": "X-Custom"}]}, "expected_output": "method=GET\nurl=http://localhost/posts\nbody=none\nheader=X-Custom=1"},
    {"input": {"http": [{"verb": "GET", "path": "posts"}], "params": [{"kind": "reqBuilder", "name": "b1"}, {"kind": "reqBuilder", "name": "b2"}]}, "expected_output": "error=multiple_request_builders"}
  ]
}
```

---

### Feature 13: Parameter type conversion

**As a developer**, I want supplied values converted to a declared target type via a registered converter, so parameters can be type-adapted before use.

**Expected Behavior / Usage:**

The client can convert a supplied parameter value to a declared target type using a registered converter before the value is placed into the request; if no converter supports the requested conversion the call fails (`error=no_request_converter`). A parameter may also declare a target request type so its value is converted before being substituted into the request. The adapter prints the converted value and its resulting type, the issued request for the substitution case, or the error.

**Test Cases:** `rcb_tests/public_test_cases/feature13_parameter_conversion.json`

```json
{
  "description": "Parameter type conversion. The client can convert a supplied parameter value to a declared target type using a registered converter before the value is placed into the request; if no converter supports the requested conversion the call fails. A parameter may also declare a target request type so that its value is converted before being substituted into the request. The adapter prints the converted value and its resulting type, the issued request for the substitution case, or a neutral error category.",
  "cases": [
    {"input": {"op": "convert", "from": "String", "to": "Int", "value": "4", "converter": true}, "expected_output": "converted=4\ntype=Int"},
    {"input": {"op": "convert", "from": "String", "to": "Int", "value": "4", "converter": false}, "expected_output": "error=no_request_converter"}
  ]
}
```

---

### Feature 14: Interface-shape validation

**As a developer**, I want the declarative API source validated as a well-formed interface, so unsupported shapes are rejected with a clear category.

**Expected Behavior / Usage:**

The declarative API source must be a host-language interface that resides in a package and carries no type parameters. A foreign-language interface (`error=java_interface_unsupported`), an interface without a package (`error=missing_package`), or an interface with type parameters (`error=type_parameters_unsupported`) is rejected at generation time. The adapter prints the neutral error category for each violation.

**Test Cases:** `rcb_tests/public_test_cases/feature14_interface_validation.json`

```json
{
  "description": "Interface-shape validation. The declarative API source must be a host-language interface that resides in a package and carries no type parameters. A foreign-language interface, an interface without a package, or an interface with type parameters is rejected at generation time. The adapter prints a neutral error category for each violation.",
  "cases": [
    {"input": {"lang": "java", "http": [{"verb": "GET", "path": "posts"}]}, "expected_output": "error=java_interface_unsupported"}
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — a compile-time generator that parses the annotated interface and its declarations, validates them (emitting precise diagnostics for every violation category), and emits a working client implementation; and a runtime that resolves URLs, assembles query strings/headers/bodies (raw, form, multipart), applies per-request builder blocks, performs parameter conversion through a converter registry, and dispatches through a transport abstraction. The generator and runtime must be decoupled from each other and from any I/O concern.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON request (schema above) from stdin, synthesizes the corresponding annotated interface, drives the real generator over it, loads the generated implementation, invokes it against a capturing transport (so the issued request is observable without a network), and prints the normalized output contract — or one or more neutral `error=<category>` lines on any generation-time or runtime failure. It must contain no business logic of its own and must never leak host-language stack traces into the contract output.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature01_http_method.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature01_http_method@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- adhere to the same validation rules as described in the path constraint section regarding nullable values
- invoke the builder component as defined in the request builder pattern examples
