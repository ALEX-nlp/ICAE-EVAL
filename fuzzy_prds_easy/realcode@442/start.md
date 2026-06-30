## Product Requirement Document

# HTTP Request Toolkit & Service-Client Utilities - Building requests, modeling name/value data, and serializing domain records

## Project Goal

Build a reusable client-side toolkit that lets developers assemble HTTP requests, model simple name/value data, filter parameter maps, validate arguments, serialize a few domain records to a compact wire format, and resolve service credentials from a configuration directory — all without hand-writing the fiddly, error-prone boilerplate each of those tasks normally requires.

---

## Background & Problem

Without this toolkit, developers integrating with web services must repeatedly reimplement the same low-level plumbing: percent-encoding query strings, choosing the right content type and charset for a payload, joining form fields, guarding against null/empty arguments, and translating a credentials blob into an authorization header. Each reimplementation is a fresh chance to introduce subtle encoding or pairing bugs.

With this toolkit, those operations become small, well-defined building blocks with predictable, inspectable outputs, so application code can focus on its own logic instead of transport details.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This project spans several distinct responsibilities (request building, value modeling, map filtering, validation, serialization, credential resolution); it MUST be organized as a clear multi-file tree (e.g. `src/`, `tests/`) reflecting a production-grade repository rather than a single monolithic file. Do not over-engineer, but avoid a "god file".

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract** for an execution adapter, NOT the internal data model. The core logic must stay decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core domain and rendering results to stdout.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting (SRP); keep the core engine open for extension but closed for modification (OCP); ensure substitutability (LSP); keep interfaces small and cohesive (ISP); and depend on abstractions rather than concrete I/O (DIP).

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language, hiding internal complexity. Edge cases must be handled gracefully and errors modeled properly (specific error types or Result patterns) rather than via generic faults.

---

## Core Features

### Feature 1: HTTP Request Construction

**As a developer**, I want to assemble an HTTP request from a verb, URL, query parameters, headers, and a body, so I can issue well-formed calls without manually encoding each part.

**Expected Behavior / Usage:**

A request is built by choosing an HTTP verb (GET, POST, PUT, DELETE) and a target URL, then optionally attaching query parameters, headers, and a payload. After building, selected facets of the request can be reported: its method, its final URL, whether it is relative, its path, its serialized body, and the resolved content type, or a named header value. The reporting interface used by the cases below takes a `report` list naming which facets to emit; each requested facet is printed on its own `key=value` line in the order requested. Header values are requested with the form `header:<name>` and reported as `header.<name>=<value>`.

*1.1 Method and fully-qualified URL — verb recording and URL pass-through*

Construct a request for a given verb and a fully-qualified URL and report the method and final URL. The recorded method is the upper-case verb name. A URL that already carries a query string is preserved verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_method_and_url.json`

```json
{
    "description": "Construct an HTTP request for a given verb (GET, POST, PUT, or DELETE) and a target URL, then report the resulting request's HTTP method and its final URL. The URL passed in may already contain a query string, which must be preserved verbatim in the built request. This verifies the verb is recorded correctly and that a fully-qualified URL passes through unchanged.",
    "cases": [
        {"input": {"op": "request_builder", "method": "get", "url": "http://www.example.com/?foo=bar&p2=p2", "report": ["method", "url"]}, "expected_output": "[acceptable HTTP verbs — to be determined by the backend team]\nurl=http://www.example.com/?foo=bar&p2=p2\n"},
        {"input": {"op": "request_builder", "method": "post", "url": "http://www.example.com/", "report": ["method", "url"]}, "expected_output": "[acceptable HTTP verbs — to be determined by the backend team]\nurl=http://www.example.com/\n"}
    ]
}
```

*1.2 Query parameters — appending and percent-encoding*

Attach query parameters to a base URL that has no query string, then report the final URL. Each parameter is a name paired with either a single value or a list of values; a single value is appended once, a list value repeats the name once per element preserving order. Names and values with reserved or non-ASCII characters are percent-encoded.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_query_params.json`

```json
{
    "description": "Attach query parameters to a request whose base URL has no query string, then report the final URL. Each parameter is given as a name paired with either a single value or a list of values. A single value is appended once; a list value is expanded so the same parameter name is repeated for every element, preserving order. Parameter names and values that contain reserved or non-ASCII characters must be percent-encoded in the resulting URL.",
    "cases": [
        {"input": {"op": "request_builder", "method": "post", "url": "http://www.example.com/", "query": [["foo", "bar"], ["p2", "p2"]], "report": ["url"]}, "expected_output": "url=http://www.example.com/?foo=bar&p2=p2\n"},
        {"input": {"op": "request_builder", "method": "post", "url": "http://www.example.com/", "query": [["foo", ["bar", "bar2"]]], "report": ["url"]}, "expected_output": "url=http://www.example.com/?foo=bar&foo=bar2\n"}
    ]
}
```

*1.3 Relative URL — placeholder endpoint and path retention*

Build a request from a path-only URL (no scheme or host). It is treated as relative: a placeholder endpoint is applied internally so the request is well-formed, the request can be recognized as relative, and the caller's path is retained exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_relative_url.json`

```json
{
    "description": "Build a request from a path-only URL (one that has no scheme or host, e.g. a leading-slash path). Such a request is treated as relative: a placeholder endpoint is applied internally so the request is well-formed, and the request can be recognized as relative. Report the HTTP method, whether the request is relative, and the path component of the request. The path supplied by the caller must be retained exactly.",
    "cases": [
        {"input": {"op": "request_builder", "method": "get", "url": "/v1/ping", "report": ["method", "relative", "path"]}, "expected_output": "[acceptable HTTP verbs — to be determined by the backend team]\nrelative=true\npath=/v1/ping\n"}
    ]
}
```

*1.4 Custom headers — recording and read-back*

Attach one or more custom headers (each a name and a value) while building, then report a chosen header value by name. Arbitrary caller-supplied headers are recorded and readable back.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_headers.json`

```json
{
    "description": "Attach one or more custom request headers (each a name and a value) while building a request, then report the HTTP method and the value stored under a chosen header name. Confirms that arbitrary headers supplied by the caller are recorded on the request and can be read back by name.",
    "cases": [
        {"input": {"op": "request_builder", "method": "post", "url": "http://www.example.com/?foo=bar&p2=p2", "body": {"content": "body1", "content_type": "text/plain"}, "header": [["x-token", "token1"]], "report": ["method", "header:x-token"]}, "expected_output": "[acceptable HTTP verbs — to be determined by the backend team]\nheader.x-token=token1\n"}
    ]
}
```

*1.5 Request body — raw, JSON, and form payloads*

Attach a payload of one of three kinds and report the serialized body and resolved content type. A raw string body with an explicit media type is sent as-is, and if that media type carries no charset a UTF-8 charset is appended to the content type. A JSON-object body is serialized to compact JSON and sent as JSON (UTF-8 charset appended). Form fields (an even-length flat list of name, value, ...) are encoded as `application/x-www-form-urlencoded`, joining each pair with `=` and separating pairs with `&`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_body.json`

```json
{
    "description": "Attach a request payload of one of three kinds and report the serialized body together with its resolved content type. A raw string body paired with an explicit media type is sent as-is, and when the media type carries no charset a UTF-8 charset is appended to the content type. A JSON-object body is serialized to its compact JSON text and sent as JSON (charset UTF-8 appended). A set of form fields (an even-length flat list of name, value, name, value, ...) is encoded as an application/x-www-form-urlencoded body joining each pair with '=' and separating pairs with '&'.",
    "cases": [
        {"input": {"op": "request_builder", "method": "post", "url": "http://www.example.com/?foo=bar&p2=p2", "body": {"content": "test2", "content_type": "text/plain"}, "report": ["body", "content_type"]}, "expected_output": "body=test2\ncontent_type=text/plain; charset=utf-8\n"},
        {"input": {"op": "request_builder", "method": "post", "url": "http://www.example.com/?foo=bar&p2=p2", "form": ["foo", "bar", "test1", "test2"], "report": ["body", "content_type"]}, "expected_output": "body=foo=bar&test1=test2\ncontent_type=application/x-www-form-urlencoded\n"}
    ]
}
```

*1.6 Invalid usage — normalized errors*

Reject malformed construction requests with a neutral, categorized error line and produce no request. A null URL is rejected as `error=null_url`. Form fields given as an odd-length list (so name/value pairing is incomplete) are rejected as `error=odd_argument_count`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_invalid_usage.json`

```json
{
    "description": "Reject malformed request-construction requests with a neutral, categorized error. Supplying no URL (a null URL) is rejected as a null-URL error. Supplying form fields as an odd-length list (so the name/value pairing is incomplete) is rejected as an odd-argument-count error. Each failure is reported as a single normalized error line and produces no request.",
    "cases": [
        {"input": {"op": "request_builder", "method": "get", "url": null, "report": ["method"]}, "expected_output": "error=null_url\n"},
        {"input": {"op": "request_builder", "method": "put", "url": "http://www.example.com/", "form": ["1", "2", "3"], "report": ["body"]}, "expected_output": "error=odd_argument_count\n"}
    ]
}
```

---

### Feature 2: Name/Value Pair

**As a developer**, I want a small immutable pair that holds a name and an optional value, so I can model headers, parameters, and similar data with predictable string and equality semantics.

**Expected Behavior / Usage:**

*2.1 Accessors and string form*

Create a pair from a name and an optional value, then report the stored name, the stored value, and the pair's string form. The value may be absent (null). The string form is `name=value` when a value is present, or just `name` when absent; an absent value is reported with a null marker.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_name_value_accessors.json`

```json
{
    "description": "Create a name/value pair from a name and an optional value, then report the stored name, the stored value, and the pair's string form. The value may be absent (null). The string form is name followed by '=' followed by value when a value is present; when the value is absent the string form is just the name, and the reported value is shown as a null marker.",
    "cases": [
        {"input": {"op": "name_value", "name": "foo", "value": "bar"}, "expected_output": "name=foo\nvalue=bar\nstring=foo=bar\n"},
        {"input": {"op": "name_value", "name": "foo", "value": null}, "expected_output": "name=foo\nvalue=(null)\nstring=foo\n"}
    ]
}
```

*2.2 Equality and hash consistency*

Compare two pairs and report whether they are equal and whether their hash codes match. Two pairs are equal exactly when both names and both values are equal (absent values treated consistently), and equal pairs share a hash code. Pairs differing only in value are not equal, and a pair with an absent value is not equal to one with a present value under the same name.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_name_value_equality.json`

```json
{
    "description": "Compare two name/value pairs for equality and report both whether they are considered equal and whether their hash codes match. Two pairs are equal exactly when both their names and their values are equal (with absent values treated consistently). Equal pairs must also share the same hash code. Pairs differing only in their value are not equal, and a pair with an absent value is not equal to one with the same name but a present value.",
    "cases": [
        {"input": {"op": "name_value", "left": {"name": "foo", "value": "bar"}, "right": {"name": "foo", "value": "bar"}}, "expected_output": "equal=true\nhash_equal=true\n"},
        {"input": {"op": "name_value", "left": {"name": "foo", "value": "bar"}, "right": {"name": "foo", "value": "buzz"}}, "expected_output": "equal=false\nhash_equal=false\n"}
    ]
}
```

*2.3 Required name*

Creating a pair with a null name is rejected with a neutral, categorized error (`error=null_name`) and produces no pair.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_name_value_required.json`

```json
{
    "description": "Require a non-null name when creating a name/value pair. Attempting to create a pair with a null name is rejected with a neutral, categorized error and produces no pair.",
    "cases": [
        {"input": {"op": "name_value", "name": null, "value": null}, "expected_output": "error=null_name\n"}
    ]
}
```

---

### Feature 3: Parameter-Map Filtering

**As a developer**, I want to derive a copy of a string-keyed map by either dropping or retaining a chosen set of keys, so I can shape parameter maps without mutating the original.

**Expected Behavior / Usage:**

Both operations return a fresh copy and leave the original map untouched. Requested keys that are not present are ignored. When the input map itself is absent (null), the result is also absent and is rendered as `null`. Surviving entries are emitted one `key=value` per line, ordered by key for determinism.

*3.1 Omit listed keys*

Return a copy with the listed keys removed. With no keys requested the copy equals the input.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_param_omit.json`

```json
{
    "description": "Return a copy of a string-keyed map with the listed keys removed, leaving the original untouched. Keys requested for removal that are not present are ignored. When no keys are requested the copy is identical to the input. When the input map itself is absent (null), the result is also absent. The output lists each surviving key and value, one per line, ordered by key for determinism.",
    "cases": [
        {"input": {"op": "param_filter", "mode": "omit", "params": {"A": 1, "B": 2, "C": 3, "D": 4}, "keys": ["A"]}, "expected_output": "B=2\nC=3\nD=4\n"},
        {"input": {"op": "param_filter", "mode": "omit", "params": null, "keys": ["A"]}, "expected_output": "null\n"}
    ]
}
```

*3.2 Pick listed keys*

Return a copy keeping only the listed keys. With no keys requested every entry is kept. When no entries are kept the output is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_param_pick.json`

```json
{
    "description": "Return a copy of a string-keyed map keeping only the listed keys, leaving the original untouched. Keys requested for selection that are not present are ignored. When no keys are requested the copy keeps every entry of the input. When the input map itself is absent (null), the result is also absent. The output lists each kept key and value, one per line, ordered by key for determinism; when no entries are kept the output is empty.",
    "cases": [
        {"input": {"op": "param_filter", "mode": "pick", "params": {"A": 1, "B": 2, "C": 3, "D": 4}, "keys": ["A"]}, "expected_output": "A=1\n"},
        {"input": {"op": "param_filter", "mode": "pick", "params": {"A": 1, "B": 2, "C": 3, "D": 4}, "keys": ["F"]}, "expected_output": ""}
    ]
}
```

---

### Feature 4: Argument Validation

**As a developer**, I want simple guard clauses that reject invalid arguments, so I can fail fast on bad input with a uniform, categorized error.

**Expected Behavior / Usage:**

A truth check fails when its condition is false. A presence check fails when the value is absent (null). A non-emptiness check fails when the sequence or text is empty. Each failure is reported as a neutral, categorized error naming which kind of check was violated (`error=invalid_argument` plus a `check=<kind>` line); no other output is produced.

**Test Cases:** `rcb_tests/public_test_cases/feature4_validation.json`

```json
{
    "description": "Guard clauses that reject invalid arguments. A truth check fails when its condition is false. A presence check fails when the value is absent (null). A non-emptiness check fails when the sequence or text is empty. Each failure is reported as a neutral, categorized error naming which kind of check was violated; no other output is produced.",
    "cases": [
        {"input": {"op": "validate", "check": "is_true", "value": false}, "expected_output": "error=invalid_argument\ncheck=is_true\n"},
        {"input": {"op": "validate", "check": "not_empty", "value": []}, "expected_output": "error=invalid_argument\ncheck=not_empty\n"}
    ]
}
```

---

### Feature 5: Domain-Record Serialization

**As a developer**, I want a few domain records serialized to a compact, positional wire format, so consumers can read them without field-name overhead.

**Expected Behavior / Usage:**

Each record serializes to a compact JSON array (no spaces) terminated by a newline.

*5.1 Word-timing record*

Serialize a word-timing record to a three-element array in fixed order: word, start time, end time. Times are emitted as numbers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_timestamp_serialization.json`

```json
{
    "description": "Serialize a word-timing record to a compact JSON array of exactly three elements in fixed order: the word, its start time, and its end time. Times are emitted as numbers.",
    "cases": [
        {"input": {"op": "serialize", "kind": "timestamp", "word": "test", "start_time": 1.1, "end_time": 2.3}, "expected_output": "[\"test\",1.1,2.3]\n"}
    ]
}
```

*5.2 Word-confidence record*

Serialize a word-confidence record to a two-element array in fixed order: word, confidence. The confidence is emitted as a number.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_word_confidence_serialization.json`

```json
{
    "description": "Serialize a word-confidence record to a compact JSON array of exactly two elements in fixed order: the word and its confidence. The confidence is emitted as a number.",
    "cases": [
        {"input": {"op": "serialize", "kind": "word_confidence", "word": "test", "confidence": 0.6}, "expected_output": "[\"test\",0.6]\n"}
    ]
}
```

*5.3 Epoch-date list*

Serialize a list whose elements are each either an absent value or an epoch-milliseconds integer. The result is a compact JSON array preserving order, with absent elements rendered as a null marker.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_epoch_date_serialization.json`

```json
{
    "description": "Serialize a list of timestamps where each element is either an absent value or an epoch-milliseconds integer. The result is a compact JSON array preserving order, with absent elements rendered as a null marker.",
    "cases": [
        {"input": {"op": "serialize", "kind": "date_list", "epochs": [null]}, "expected_output": "[null]\n"}
    ]
}
```

---

### Feature 6: Service-Credential Resolution

**As a developer**, I want to resolve a service credential from a service-directory configuration, so I can produce an authorization token from a deployment's bound services.

**Expected Behavior / Usage:**

Given a service-directory configuration (a map from service name to a list of bound instances, each carrying credentials with a username and password), a requested service name, and an optional plan, locate the matching instance and return its credential token: HTTP basic authentication built as `Basic ` followed by the base64 of `username:password`. When the requested service name is absent or empty, no credential is returned and an absent marker (`(null)`) is produced. When a plan is given, the instance with that plan is selected; with no plan, the first matching instance is selected.

**Test Cases:** `rcb_tests/public_test_cases/feature6_credential_resolution.json`

```json
{
    "description": "Resolve a service credential from a service-directory configuration. Given a service name and an optional plan, locate the matching service instance and return its credential token (HTTP basic authentication built from the instance's username and password). When the requested service name is absent or empty, no credential is returned (an absent marker is produced). When a plan is given, the instance with that plan is selected; when no plan is given, the first matching instance is selected.",
    "cases": [
        {"input": {"op": "credentials", "service": null, "plan": null, "config": {"personality_insights": [{"name": "pi", "label": "personality_insights", "plan": "free", "credentials": {"url": "https://example/api", "username": "not-a-free-username", "password": "not-a-free-password"}}, {"name": "pi", "label": "personality_insights", "plan": "standard", "credentials": {"url": "https://example/api", "username": "not-a-username", "password": "not-a-password"}}]}}, "expected_output": "(null)\n"},
        {"input": {"op": "credentials", "service": "personality_insights", "plan": "standard", "config": {"personality_insights": [{"name": "pi", "label": "personality_insights", "plan": "free", "credentials": {"url": "https://example/api", "username": "not-a-free-username", "password": "not-a-free-password"}}, {"name": "pi", "label": "personality_insights", "plan": "standard", "credentials": {"url": "https://example/api", "username": "not-a-username", "password": "not-a-password"}}]}}, "expected_output": "Basic bm90LWEtdXNlcm5hbWU6bm90LWEtcGFzc3dvcmQ=\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above (request building, name/value modeling, map filtering, validation, serialization, credential resolution), with its physical structure aligned to the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, dispatches on its `op` field to the appropriate core logic, and prints the result to stdout exactly matching the per-feature contracts above (including normalized `error=<category>` lines for invalid usage). This adapter must be separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{idx:03d}.txt` containing **only** the raw stdout from the program under test, so it can be compared directly against `expected_output`.
