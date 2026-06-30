## Product Requirement Document

# HTTP Request/Response Toolkit — Query Encoding, Header Modeling, Configuration Composition & Body Decoding

## Project Goal

Build a reusable HTTP client toolkit's pure data layer that turns structured request data into wire-format strings, models HTTP headers and request configuration with predictable merge semantics, and decodes response bodies into structured values — so application code can rely on one well-defined contract for serialization and configuration instead of reinventing it per call site.

---

## Background & Problem

An HTTP client has to perform several pieces of deterministic, transport-independent work before and after the bytes ever hit the network: it must percent-encode nested parameter maps into an `application/x-www-form-urlencoded` string (choosing how repeated list values are serialized), it must model a case-insensitive header collection that supports multi-valued headers, it must merge a layered configuration (global defaults, per-call overrides, and the fully-resolved request) with clear precedence rules, and it must decode a response body into a structured value based on the declared response type and content-type.

Without a shared toolkit, each call site hand-rolls these steps, producing inconsistent encodings, ambiguous header handling, and surprising configuration precedence. This toolkit provides one contract for each of those concerns. All behavior described here is pure and deterministic: given the same input it produces the same output, with no real network involved.

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

### Feature 1: Query-String Encoding Of Nested Data

**As a developer**, I want to percent-encode a nested map of parameters into a single `application/x-www-form-urlencoded` string, so I can build request query strings and form bodies without writing my own escaping and flattening logic.

**Expected Behavior / Usage:**

*1.1 Global list format — Encode a nested map under one list format applied to the whole structure*

The input is a request with `op` `url_encode`, a `format` selecting the list serialization, and a `data` map. The map may contain scalars, lists, and nested maps to arbitrary depth. The encoder walks the structure and emits `key=value` pairs joined by `&`. Nested map keys are flattened with bracket notation (a key `x` nested under `c` then `e` becomes `c[e][x]`, with the brackets percent-encoded). Every key and value is percent-encoded as a query component, so non-ASCII text becomes its UTF-8 percent-escapes and reserved separators are escaped. The `format` controls how a list value is serialized: comma-joined (`csv`), space-joined (`ssv`), tab-joined (`tsv`), pipe-joined (`pipes`), repeated bare keys (`multi`, e.g. `b=5&b=6`), or repeated bracketed keys (`multiCompatible`, e.g. `b[]=5&b[]=6`). For the separator formats, the separator character itself is part of the (encoded) value. The result is the encoded string followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_global_list_format.json`

```json
{
    "description": "Percent-encode a nested data structure into an application/x-www-form-urlencoded query string. The structure mixes a top-level scalar, a top-level list, and nested maps several levels deep. A single global list format selects how repeated list values are serialized: comma-separated, space-separated, tab-separated, pipe-separated, repeated bare keys, or repeated bracketed keys. Nested map keys are flattened using bracket notation, and every key and value is percent-encoded (including non-ASCII characters and the list separators themselves where they are reserved).",
    "cases": [
        {
            "input": {"op": "url_encode", "format": "multi", "data": {"a": "你好", "b": [5, "6"], "c": {"d": 8, "e": {"a": 5, "b": [66, 8]}}}},
            "expected_output": "a=%E4%BD%A0%E5%A5%BD&b=5&b=6&c%5Bd%5D=8&c%5Be%5D%5Ba%5D=5&c%5Be%5D%5Bb%5D=66&c%5Be%5D%5Bb%5D=8\n"
        },
        {
            "input": {"op": "url_encode", "format": "multiCompatible", "data": {"a": "你好", "b": [5, "6"], "c": {"d": 8, "e": {"a": 5, "b": [66, 8]}}}},
            "expected_output": "a=%E4%BD%A0%E5%A5%BD&b%5B%5D=5&b%5B%5D=6&c%5Bd%5D=8&c%5Be%5D%5Ba%5D=5&c%5Be%5D%5Bb%5D%5B%5D=66&c%5Be%5D%5Bb%5D%5B%5D=8\n"
        }
    ]
}
```

*1.2 Per-parameter list format — Override the list format for individual list values within one pass*

A single encoding pass may mix list formats: any list value can be wrapped to carry its own format, overriding the global `format` for just that value. In the input a wrapped value is an object with a marker key `@list` holding the value list and a sibling `format` naming the desired list format. Wrapped values may appear at any depth. Unwrapped lists continue to use the global format. The output is the single encoded string (trailing newline), in which each wrapped list is serialized using its own format while the rest of the structure follows the global format.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_per_param_format.json`

```json
{
    "description": "Percent-encode a nested data structure where individual list-valued entries each request their own serialization format, overriding the global format. A value may be wrapped (marker key indicating the value list plus the desired list format) so that one list uses pipe separation, another comma separation, another space separation, another tab separation, and another the repeated-key form, all within a single encoding pass. Nested keys are flattened with bracket notation and every component is percent-encoded.",
    "cases": [
        {
            "input": {"op": "url_encode", "format": "multiCompatible", "data": {"a": "你好", "b": {"@list": [5, 6], "format": "pipes"}, "c": {"d": 8, "e": {"a": 5, "b": {"@list": ["foo", "bar"], "format": "csv"}, "c": {"@list": ["foo", "bar"], "format": "ssv"}, "d": {"@list": ["foo", "bar"], "format": "multi"}, "e": {"@list": ["foo", "bar"], "format": "tsv"}}}}},
            "expected_output": "a=%E4%BD%A0%E5%A5%BD&b=5%7C6&c%5Bd%5D=8&c%5Be%5D%5Ba%5D=5&c%5Be%5D%5Bb%5D=foo%2Cbar&c%5Be%5D%5Bc%5D=foo+bar&c%5Be%5D%5Bd%5D%5B%5D=foo&c%5Be%5D%5Bd%5D%5B%5D=bar&c%5Be%5D%5Be%5D=foo%5Ctbar\n"
        }
    ]
}
```

---

### Feature 2: JSON Media-Type Detection

**As a developer**, I want to classify whether a content-type string denotes JSON, so I can decide whether to parse a body as JSON regardless of vendor-specific media types.

**Expected Behavior / Usage:**

The input is a request with `op` `is_json_mime` and a `contentType` string. Following the WHATWG MIME-sniffing rule, the classifier returns [JSON MIME logic output value] when the essence is the canonical JSON type, when it is the text JSON type, or when the subtype carries the `+json` structured-syntax suffix — independent of any media-type parameters. The output echoes the input content-type and reports the boolean decision, each on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_json_mime_type.json`

```json
{
    "description": "Classify whether a given content-type string denotes a JSON media type, following the WHATWG MIME-sniffing rule. The classifier returns [JSON MIME logic output value] when the essence is the canonical JSON type, when it is the text JSON type, or when the subtype carries the structured-syntax suffix marking it as JSON, regardless of any media-type parameters. The adapter echoes the input content-type and reports the boolean decision.",
    "cases": [
        {
            "input": {"op": "is_json_mime", "contentType": "application/json"},
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]\nisJsonMimeType=[JSON MIME logic output value]\n"
        }
    ]
}
```

---

### Feature 3: HTTP Header Collection

**As a developer**, I want a case-insensitive, multi-valued header collection with predictable read/write/render semantics, so I can manipulate request and response headers reliably.

**Expected Behavior / Usage:**

The input is a request with `op` `headers`, an optional `init` map (header name to a list of string values), and an ordered list of `actions`. Header names are case-insensitive, so a name added or read under any casing maps to the same entry. The supported actions are: `add` (append a value to a name's list, creating it if absent), `set` (replace a name's values with a single string or a provided list), `remove` (drop one specific value from a name), `removeAll` (drop a whole name), `clear` (empty the collection), and the observation actions `value`, `get`, `len`, `foreachCount`, `toString`, and `isEmpty`. `value` reads a single-valued header and emits `value[name]=<v>`; if the name holds more than one value it is reported as a normalized error (`error=multiple_header_values` then `name=<name>`) rather than a raw value. `get` emits `get[name]=<comma-joined values>` or `null`. `len` emits `len[name]=<count>` or `null`. `foreachCount` iterates all entries and emits `foreach_count=<total number of values>`. `toString` emits the canonical wire-format text block: one `name: value` line per value, in insertion order, each terminated by a newline. `isEmpty` emits `isEmpty=<bool>`. Each observation prints exactly its described line(s); mutation actions print nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature3_header_collection.json`

```json
{
    "description": "Drive a case-insensitive HTTP header collection through a scripted sequence of operations and observe the results. The collection is built from an initial map of header name to a list of string values, then operations are applied in order: appending a value under a differently-cased name, reading a single-valued header, attempting to read a header that holds multiple values (reported as a normalized error rather than a raw value), listing the number of values under a name, removing one specific value, removing an entire header, counting all values via iteration, rendering the whole collection to its canonical wire-format text, replacing a header's values with a single value and then with a list, setting and reading a value on a freshly relevant name, and finally clearing the collection and checking emptiness. Each read or observe step prints one labelled line (the multi-value read prints a normalized error category and the offending name); the text rendering prints the wire-format block; unknown or missing names read back as a null marker.",
    "cases": [
        {
            "input": {
                "op": "headers",
                "init": {"set-cookie": ["k=v", "k1=v1"], "content-length": ["200"], "test": ["1", "2"]},
                "actions": [
                    {"action": "add", "name": "SET-COOKIE", "value": "k2=v2"},
                    {"action": "value", "name": "content-length"},
                    {"action": "value", "name": "test"},
                    {"action": "len", "name": "set-cookie"},
                    {"action": "remove", "name": "set-cookie", "value": "k=v"},
                    {"action": "len", "name": "set-cookie"},
                    {"action": "removeAll", "name": "set-cookie"},
                    {"action": "get", "name": "set-cookie"},
                    {"action": "foreachCount"},
                    {"action": "toString"},
                    {"action": "set", "name": "content-length", "value": "300"},
                    {"action": "value", "name": "content-length"},
                    {"action": "set", "name": "content-length", "value": ["400"]},
                    {"action": "value", "name": "content-length"},
                    {"action": "set", "name": "xx", "value": "v"},
                    {"action": "value", "name": "xx"},
                    {"action": "clear"},
                    {"action": "isEmpty"}
                ]
            },
            "expected_output": "value[content-length]=200\nerror=multiple_header_values\nname=test\nlen[set-cookie]=3\nlen[set-cookie]=2\nget[set-cookie]=null\nforeach_count=3\ncontent-length: 200\ntest: 1\ntest: 2\nvalue[content-length]=300\nvalue[content-length]=400\nvalue[xx]=v\nisEmpty=[JSON MIME logic output value]\n"
        }
    ]
}
```

---

### Feature 4: Request Configuration Composition

**As a developer**, I want layered request configuration with predictable copy-on-override and composition semantics, so per-call options merge onto global defaults in a way I can reason about.

**Expected Behavior / Usage:**

*4.1 Copy-with-override — Derive a configuration from an existing one, overriding selected fields*

The input is a request with `op` `copy_with`, a `kind` selecting the configuration tier (`base` global config, `options` per-call config, or `request` resolved request config), an `init` map describing the starting object, and a `with` map naming the overrides. Fields named in `with` take the new value; unnamed fields are inherited unchanged. Header and extra maps supplied in `with` fully replace the inherited maps. Header access is case-insensitive (a value stored under `b` is readable as `B`, and writing `B` updates `b`). Durations are given as whole seconds and rendered as `<n>s`. The output reports the resolved fields for the tier, one labelled line each; the `request` tier additionally reads a header key in a different case and then writes through that case to demonstrate case-insensitive access.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_copy_with_merge.json`

```json
{
    "description": "Create a new configuration object from an existing one by copying it while overriding a selected subset of fields. Fields named in the override take the new value; fields not named are inherited unchanged. This applies across three configuration tiers: a global/base configuration (which also carries a base URL, common query parameters and a connect timeout), a per-call override configuration, and a fully-resolved request configuration (which also carries a request body and path). Header and extra maps supplied in the override fully replace the inherited maps. Header lookup is case-insensitive, so a value stored under one casing is readable and writable under another. The adapter reports the resolved fields after the copy; the request tier additionally demonstrates the case-insensitive header access by reading a key in a different case and then writing through that case.",
    "cases": [
        {
            "input": {
                "op": "copy_with",
                "kind": "base",
                "init": {"connectTimeout": 2, "receiveTimeout": 2, "sendTimeout": 2, "baseUrl": "http://localhost", "queryParameters": {"a": "5"}, "extra": {"a": "5"}, "headers": {"a": "5"}, "contentType": "application/json", "followRedirects": false, "persistentConnection": false},
                "with": {"method": "post", "receiveTimeout": 3, "sendTimeout": 3, "baseUrl": "https://pub.dev", "extra": {"b": "6"}, "headers": {"b": "6"}, "contentType": "text/html"}
            },
            "expected_output": "method=post\nconnectTimeout=2s\nreceiveTimeout=3s\nfollowRedirects=false\npersistentConnection=false\nbaseUrl=https://pub.dev\nheader_b=6\nextra_b=6\n[specific null string format expected by tests]\ncontentType=text/html\n"
        }
    ]
}
```

*4.2 Content-type field/header equivalence — A base configuration's content-type field and its content-type header mirror each other*

The input is a request with `op` `content_type_field`, an optional `contentType` string, and an optional `headers` map. When a base configuration is constructed with an explicit content-type, that value is also visible as the content-type header. When it is constructed with a content-type only in the header map, that value is also visible through the dedicated content-type field. When neither is supplied, both read back as absent. The output reports the content-type field and the content-type header, one line each (absent renders as `null`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_content_type_field.json`

```json
{
    "description": "Show the equivalence between the dedicated content-type field of a base configuration and the content-type entry of its header map. When a base configuration is constructed with an explicit content-type, that value is also visible as the content-type header. When it is constructed with a content-type only in the header map, that value is also visible through the content-type field. When neither is supplied, both read back as absent. The adapter reports the content-type field and the content-type header.",
    "cases": [
        {
            "input": {"op": "content_type_field", "contentType": "text/html"},
            "expected_output": "contentType=text/html\nheader_content_type=text/html\n"
        },
        {
            "input": {"op": "content_type_field"},
            "expected_output": "contentType=null\nheader_content_type=null\n"
        }
    ]
}
```

*4.3 Compose precedence & URL assembly — Resolve a request by composing a per-call override onto base defaults for a path*

The input is a request with `op` `compose`, a `base` map (global defaults: `baseUrl`, `headers`, `contentType`, and a `setRequestContentTypeWhenNoPayload` flag), an `options` map (per-call override: `method`, `headers`, `contentType`), a `path`, optionally a `data` payload, and optionally a `copyWith` map applied to the composed result. Content-type precedence: a content-type from the per-call override (its dedicated field or its header entry) wins over the base content-type. A default JSON content-type is implied only when none is otherwise present and either a payload is supplied or the base requests a content-type even with no payload. A subsequent copy-with override on the composed request can further replace the content-type via its header map or its dedicated field. The composed request also assembles a final URL by joining the base URL and path. The output reports the resolved content-type (absent renders `null`) and the assembled URL, one line each.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_compose_content_type.json`

```json
{
    "description": "Resolve the effective request configuration by composing a per-call override onto a base configuration for a given path. The content-type is resolved with a clear precedence: a content-type supplied by the per-call override (either as its dedicated field or inside its header map) takes priority over the base content-type. When the request carries a payload, or when the base is configured to always set a content-type even without a payload, a default JSON content-type is implied only if none was otherwise provided. A subsequent copy-with override on the composed request can further replace the content-type, either through its header map or its dedicated field. The composed request also assembles a final request URL by joining the base URL and path. The adapter reports the resolved content-type and the assembled URL.",
    "cases": [
        {
            "input": {"op": "compose", "base": {"contentType": "text/html"}, "options": {"contentType": "appliction/json"}, "path": ""},
            "expected_output": "contentType=appliction/json\nuri=\n"
        },
        {
            "input": {"op": "compose", "base": {"baseUrl": "https://www.example.com", "setRequestContentTypeWhenNoPayload": [JSON MIME logic output value]}, "options": {"method": "GET"}, "path": "/test", "copyWith": {"headers": {"content-type": "text/plain"}}},
            "expected_output": "contentType=text/plain\nuri=https://www.example.com/test\n"
        }
    ]
}
```

---

### Feature 5: Response Body Decoding

**As a developer**, I want a response body decoded into a structured value based on the response type and content-type, so I receive ready-to-use objects instead of raw text.

**Expected Behavior / Usage:**

The input is a request with `op` `transform_response`, a `body` string, a `contentType`, and a `responseType`. When the response type requests JSON and the content-type denotes a JSON media type, the textual body is parsed into the corresponding structured value (object or array, including nested structures, with JSON scalars, booleans, and nulls). The output reports the kind of the resulting value (`map`, `list`, `string`, `scalar`, or `null`) and a canonical compact re-serialization of it, one line each.

**Test Cases:** `rcb_tests/public_test_cases/feature5_response_decoding.json`

```json
{
    "description": "Transform a raw HTTP response body into a deserialized value according to the requested response type and the response content-type. When the response type requests JSON and the response content-type denotes a JSON media type, the textual body is parsed into the corresponding structured value (object or array, including nested structures). The adapter reports the kind of the resulting value and a canonical re-serialization of it.",
    "cases": [
        {
            "input": {"op": "transform_response", "body": "{\"foo\": \"bar\"}", "contentType": "application/json", "responseType": "json"},
            "expected_output": "type=map\nvalue={\"foo\":\"bar\"}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (query-string encoding with global and per-value list formats, a case-insensitive multi-valued header collection, a layered request configuration with copy-with-override and composition semantics, JSON media-type detection, and response body decoding). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects behavior by the `op` field (`url_encode`, `is_json_mime`, `headers`, `copy_with`, `content_type_field`, `compose`, `transform_response`), invokes the appropriate core logic, and prints the result to stdout matching the per-leaf-feature contracts above. Native exceptions surfaced by the core (such as reading a multi-valued header as single) MUST be normalized by the adapter into the neutral error lines described above; the host language identity of any exception MUST NOT appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same pattern as other requested headers mapping
- apply the same prefix transformation to extra fields
