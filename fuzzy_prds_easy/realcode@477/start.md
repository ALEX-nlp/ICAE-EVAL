## Product Requirement Document

# HTTP Request Builder for a Search-Count API — Conditional Request Body Construction

## Project Goal

Build a request-construction layer for a document search service that turns a high-level "count documents" request object into a concrete HTTP request (method, routed path, [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]-string parameters, and request body) **without** forcing the caller to hand-assemble URLs, encode parameters, or decide when a request body should be sent. The defining behavior is that the body is included **only when it carries meaningful content**, so empty or parameter-only requests go out cleanly with no payload.

---

## Background & Problem

Without this layer, every caller that wants to count matching documents has to manually decide: does this request need an HTTP body or not? A naive implementation always serializes the request object, which produces an empty `{}` JSON body even when the caller supplied nothing — many servers treat an empty body differently from an absent body, and shipping `{}` for a "count everything" request is both wasteful and semantically wrong. Callers also have to know which inputs belong on the [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] string (lightweight string parameters) versus which belong in the JSON body (structured queries), and how to route the path when a target collection is named. Getting any of this wrong leads to subtle, hard-to-debug request mismatches.

With this layer, the caller simply describes *what* they want counted using a fluent request object. The system decides the HTTP method, builds the correct path, places lightweight parameters on the [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] string, and — crucially — emits a JSON body **only** when the serialized request actually contains at least one property. An empty serialization produces *no* body at all rather than an empty object.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. The request-construction logic (method/path/parameter/body resolution) belongs in the core domain and must be cleanly separated from the execution adapter that renders requests to stdout. Do not collapse everything into one file if responsibilities are genuinely distinct, but do not over-engineer a focused request builder either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract** for the execution adapter, NOT the internal data model. The core request-building logic must remain decoupled from stdin/stdout and JSON command parsing. The execution adapter is solely responsible for translating a JSON command into idiomatic request-builder calls and rendering the resulting wire request.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Separate command parsing, request building, the body-inclusion decision, and output formatting into distinct units.
   - **OCP:** The body-inclusion strategy (suppress-when-empty) must be reusable across endpoints without modifying the core engine.
   - **LSP:** A "no body" request and a "with body" request must be interchangeable wherever a request is consumed.
   - **ISP:** Keep the request and response abstractions small and cohesive.
   - **DIP:** The request builder depends on transport abstractions, not on a concrete HTTP client.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public request-building interface must be fluent and elegant, hiding the body-inclusion mechanics from the caller.
   - **Resilience:** Malformed input must be handled gracefully and reported through a normalized, language-neutral error category rather than a raw runtime fault.

---

## Core Features

### Feature 1: Conditional Request Body for a Document-Count Request

**As a developer**, I want a count request to send an HTTP body only when it carries a structured [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name], so I can avoid shipping meaningless empty payloads and let lightweight parameters ride the [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] string instead.

**Expected Behavior / Usage:**

The input is a JSON command describing a count request. Recognized fields are: `index` (an array of collection names to target), `q` (a free-text [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] string that travels as a [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]-string parameter), and `[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]` (a structured [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] object that must be serialized into the request body). The request is always issued with HTTP method `POST`. When no collection is targeted, the path is `/_count`; when one or more collections are named, the path becomes `/<comma-joined-names>/_count`.

The execution adapter renders the constructed wire request as line-oriented text. The first line is `method=<HTTP method>`. The second line is `path=<routed path>`. Then, for each [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]-string parameter, one line `[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name].<name>=<value>` is emitted, with parameters sorted alphabetically by name. The final line describes the body: `[the exact sentinel string to indicate a missing body status —— ask the PM for the literal output line]` when the request was sent with no HTTP payload, or `body=<json>` when a JSON payload was sent (where `<json>` is the exact bytes placed on the wire). The decisive contract is that an empty or parameter-only request yields `[the exact sentinel string to indicate a missing body status —— ask the PM for the literal output line]` (NOT an empty `{}` object), while a request with a structured [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] yields a real JSON body.

*1.1 No body for an empty or parameter-only request — the body must be omitted entirely when there is nothing structured to send*

When the count request is completely empty, or when it only sets fields that travel on the [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] string (such as the free-text `q` parameter), the serialized request body has no properties and therefore MUST be suppressed: the request goes out with no HTTP payload. The adapter emits the method line, the path line, any `[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name].<name>=<value>` lines (sorted by name), and a final `[the exact sentinel string to indicate a missing body status —— ask the PM for the literal output line]` line. A free-text [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] value such as `foo:bar` appears verbatim as `[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name].q=foo:bar` and does NOT appear in any body.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_no_body_for_empty_request.json`

```json
{
    "description": "When a document-count request carries no structured request body (either it is completely empty, or it only sets parameters that travel on the [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] string), the constructed wire request must contain NO HTTP request body. The adapter emits the HTTP method, the routed path, any [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]-string parameters (one `[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name].<name>=<value>` line, sorted by name), and a final `[the exact sentinel string to indicate a missing body status —— ask the PM for the literal output line]` line indicating the request was sent with no payload.",
    "cases": [
        {
            "input": {},
            "expected_output": "method=POST\npath=/_count\n[the exact sentinel string to indicate a missing body status —— ask the PM for the literal output line]\n"
        },
        {
            "input": {"q": "foo:bar"},
            "expected_output": "method=POST\npath=/_count\n[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name].q=foo:bar\n[the exact sentinel string to indicate a missing body status —— ask the PM for the literal output line]\n"
        }
    ]
}
```

*1.2 JSON body for a structured [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] — a structured [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] must be serialized into the request body*

When the count request includes a structured `[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]`, that [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] has serializable content and therefore MUST be placed in the HTTP request body as JSON. The adapter emits the method line, the path line, and a `body=<json>` line whose value is the exact JSON payload sent over the wire. A term [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] — matching a named field against a value — serializes with the matched value nested under the field name as `{"value": <v>}`, wrapped as `{"[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]":{"term":{<field>:{"value":<v>}}}}`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_body_for_structured_[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name].json`

```json
{
    "description": "When a document-count request includes a structured [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] (e.g. a term [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] that matches a field against a value), that [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] must be serialized into a JSON HTTP request body. The adapter emits the HTTP method, the routed path, and a `body=<json>` line whose value is the exact JSON payload sent over the wire. A term [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name] nests the matched value under the field name as `{\"value\": <v>}`.",
    "cases": [
        {
            "input": {"[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]": {"term": {"field": "foo", "value": "bar"}}},
            "expected_output": "method=POST\npath=/_count\nbody={\"[a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]\":{\"term\":{\"foo\":{\"value\":\"bar\"}}}}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured request-construction layer that resolves the HTTP method, routed path, [a specific internal configuration flag name for structured queries —— ask the PM for the exact variable name]-string parameters, and the conditional request body for a document-count request. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The suppress-empty-body decision must live in a reusable strategy, not be hard-coded per call site.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON command from stdin, builds the corresponding count request via the core layer, drives it through the request/transport abstraction so a genuine wire request is produced, and prints the rendered request to stdout exactly matching the per-leaf-feature contracts above. The adapter must be logically (and ideally physically) separated from the core domain, and must normalize any failure into a language-neutral error category line (e.g. `error=invalid_input`) — never leak host-language runtime details.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_no_body_for_empty_request.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_no_body_for_empty_request@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the same path construction method used for the resource list paths
