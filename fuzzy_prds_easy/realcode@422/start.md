## Product Requirement Document

# Crash & Event Reporting Client - A Lightweight Telemetry SDK for Long-Running Applications

## Project Goal

Build a small client library that lets an application report runtime events — log-style messages, captured exceptions, and navigational "breadcrumbs" — to a remote event-ingest backend over HTTP. The library turns a single connection string into a ready-to-use reporting client, assembles a structured event payload with stable metadata, and hands it to the network transport, so developers get production telemetry without hand-rolling payload formats, endpoint URLs, or identifier/timestamp generation.

---

## Background & Problem

Without such a client, developers running long-lived services must manually craft the JSON envelope every monitoring backend expects, parse and validate the backend connection string, derive the correct ingest endpoint, generate unique event identifiers, format timestamps two different ways, and wire all of this into the application's exception paths. This is repetitive, easy to get subtly wrong (a malformed endpoint or a millisecond-vs-second timestamp silently breaks ingestion), and clutters business code with transport concerns.

With this library, the developer supplies one connection string, then reports messages and exceptions through a tiny API. The library validates the connection string up front, derives the ingest endpoint, attaches a generated identifier and correctly formatted timestamps to every event, threads a trail of breadcrumbs onto the next event, and exposes the backend-assigned id of the most recent event.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a focused SDK with a handful of cohesive responsibilities (connection-string parsing, event assembly, metadata generation, HTTP transport). A compact module layout is acceptable, but transport, event modeling, and metadata helpers MUST remain logically separated rather than entangled in one routine.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract** for an execution adapter, NOT the internal data model of the library. The core reporting logic must remain decoupled from stdin/stdout and from the JSON command shape used by the test adapter. The adapter alone translates JSON commands into idiomatic calls on the library and renders results.

3. **Adherence to SOLID Design Principles (scaled to project size):**
   - **SRP:** Keep connection-string validation, event assembly, metadata generation, transport, and output formatting in distinct units.
   - **OCP:** New event kinds or contexts should be addable without rewriting the core engine.
   - **LSP:** Any transport implementation (real HTTP vs. an in-memory test sink) must be substitutable behind one interface.
   - **ISP:** Keep the public reporting surface small and cohesive.
   - **DIP:** The reporting core depends on a transport abstraction, not a concrete network implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public reporting surface must be elegant and idiomatic to the target language.
   - **Resilience:** Invalid input (e.g. a malformed connection string) must be modeled as a proper error condition, not a silent fault. Optional parameters (extra context, breadcrumb type/data) must have sensible defaults.

---

## Core Features

### Feature 1: Client Configuration from a Connection String

**As a developer**, I want to configure a reporting client from a single connection string, so I can point my application at a monitoring backend without manually building endpoint URLs or hand-validating credentials.

**Expected Behavior / Usage:**

*1.1 Endpoint Derivation — a valid connection string resolves to the canonical ingest endpoint*

A valid connection string has the shape `scheme://public_key:secret_key@host/project_id`, where `scheme` is `http` or `https` and `project_id` is numeric. From it the client derives the event-ingest endpoint URL `scheme://host/api/<project_id>/store/`, preserving the original scheme. The input is a connection string; the output reports the derived endpoint URL.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_endpoint_derivation.json`

```json
{
    "description": "A valid connection string of the form scheme://public:secret@host/project is accepted and resolved into the canonical event-ingest endpoint URL (scheme://host/api/<project>/store/). Both http and https schemes are supported and preserved.",
    "cases": [
        {
            "input": {"dsn": "https://abc:def@sentry.io/123"},
            "expected_output": "store_url=https://sentry.io/api/123/store/\n"
        },
        {
            "input": {"dsn": "http://abc:def@sentry.io/123"},
            "expected_output": "store_url=http://sentry.io/api/123/store/\n"
        }
    ]
}
```

*1.2 Connection-String Validation — a malformed string is rejected with a normalized error*

A connection string that does not match the required shape is rejected when the client is constructed. Rejected forms include: a missing scheme, an unsupported scheme (anything other than http/https), a missing public key, a missing secret key, missing credentials entirely, and a missing or empty numeric project segment. The failure is surfaced as a normalized validation error category together with the offending raw string, with no host-language runtime details.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_invalid_dsn.json`

```json
{
    "description": "A malformed connection string is rejected at client construction time and surfaced as a normalized validation error that echoes the offending raw string. Rejection covers a missing scheme, an unsupported scheme, a missing public key, a missing secret key, missing credentials entirely, and a missing/empty project segment.",
    "cases": [
        {
            "input": {"dsn": "://abc:def@sentry.io/123"},
            "expected_output": "error=invalid_dsn\ndsn=://abc:def@sentry.io/123\n"
        },
        {
            "input": {"dsn": "gopher://abc:def@sentry.io/123"},
            "expected_output": "error=invalid_dsn\ndsn=gopher://abc:def@sentry.io/123\n"
        },
        {
            "input": {"dsn": "https://abc:def@sentry.io"},
            "expected_output": "error=invalid_dsn\ndsn=https://abc:def@sentry.io\n"
        }
    ]
}
```

---

### Feature 2: Reporting Message Events

**As a developer**, I want to report a text message as an event, so I can surface noteworthy runtime conditions to my monitoring backend.

**Expected Behavior / Usage:**

*2.1 Plain Message — a single message becomes one outbound event*

Reporting a plain text message produces exactly one outbound event addressed to the derived ingest endpoint. The event carries a `platform` tag, the original message text, a generated 32-character event identifier, and the backend-assigned id of the most recent event. The transport assigns sequential ids starting at `0` within a fresh session, so the first event reported is id `0`. The output reports the endpoint URL, the platform tag, the message text, the length of the generated identifier, and the last event id.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_plain_message.json`

```json
{
    "description": "Reporting a plain text message produces exactly one outbound event addressed to the resolved ingest endpoint. The event carries the platform tag, the original message text, a generated 32-character event identifier, and the sink-assigned id of the most recent event (the first event in a fresh session is id 0).",
    "cases": [
        {
            "input": {"dsn": "https://abc:def@sentry.io/123", "event": {"message": "message text"}},
            "expected_output": "url=https://sentry.io/api/123/store/\nplatform=c\nmessage=message text\nevent_id_length=32\nlast_event_id=0\n"
        }
    ]
}
```

*2.2 Message with Extra Context — caller-supplied keys merge into the event root*

When a message is reported together with an extra context object, every key of that object is merged into the root of the outbound event alongside the standard fields, so each supplied key becomes directly readable on the event. The output reports the standard message fields plus each merged key and value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_message_with_context.json`

```json
{
    "description": "Reporting a message together with an extra context object merges every key of that object into the root of the outbound event, alongside the standard message fields. Each supplied key becomes directly readable on the event.",
    "cases": [
        {
            "input": {"dsn": "https://abc:def@sentry.io/123", "event": {"message": "message text", "context": {"key": "value"}}},
            "expected_output": "url=https://sentry.io/api/123/store/\nplatform=c\nmessage=message text\nmerged.key=value\nevent_id_length=32\nlast_event_id=0\n"
        }
    ]
}
```

---

### Feature 3: Reporting Exception Events

**As a developer**, I want to report an exception with its handling status, so my monitoring backend can distinguish errors my application recovered from versus errors that escaped.

**Expected Behavior / Usage:**

*3.1 Handled Exception — recorded with a handled mechanism*

Reporting an exception that the application already caught produces one outbound event whose exception list holds a single entry. The entry records the exception's textual value and a handling mechanism flagged as handled with the description `handled exception`. The output reports the endpoint URL, the platform tag, the exception count, the exception value, the handled flag, the mechanism description, the identifier length, and the last event id.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_handled_exception.json`

```json
{
    "description": "Reporting an exception that the application already caught produces one outbound event whose exception list holds a single entry. The entry records the exception's textual value and a handling mechanism flagged as handled with a 'handled exception' description.",
    "cases": [
        {
            "input": {"dsn": "https://abc:def@sentry.io/123", "event": {"value": "exception text", "handled": true}},
            "expected_output": "url=https://sentry.io/api/123/store/\nplatform=c\nexception_count=1\nexception.value=exception text\nexception.handled=true\nexception.mechanism=handled exception\nevent_id_length=32\nlast_event_id=0\n"
        }
    ]
}
```

*3.2 Unhandled Exception — recorded with an unhandled mechanism*

Reporting an exception that escaped handling produces one outbound event whose single exception entry records the exception's textual value and a handling mechanism flagged as not handled with the description `unhandled exception`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_unhandled_exception.json`

```json
{
    "description": "Reporting an exception that escaped handling produces one outbound event whose single exception entry records the exception's textual value and a handling mechanism flagged as not handled with an 'unhandled exception' description.",
    "cases": [
        {
            "input": {"dsn": "https://abc:def@sentry.io/123", "event": {"value": "exception text", "handled": false}},
            "expected_output": "url=https://sentry.io/api/123/store/\nplatform=c\nexception_count=1\nexception.value=exception text\nexception.handled=false\nexception.mechanism=unhandled exception\nevent_id_length=32\nlast_event_id=0\n"
        }
    ]
}
```

---

### Feature 4: Breadcrumb Trail

**As a developer**, I want to record breadcrumbs leading up to an event, so I can see the sequence of actions that preceded a message or error.

**Expected Behavior / Usage:**

Breadcrumbs recorded before an event accumulate in order and are attached to the next reported event. Each breadcrumb keeps its message and a type that defaults to `default` when unspecified. An optional structured data object is preserved verbatim on the breadcrumb. The output reports the standard event fields, the breadcrumb count, and for each breadcrumb its message, type, and (when present) its data object rendered as compact JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature4_breadcrumbs.json`

```json
{
    "description": "Breadcrumbs recorded before an event accumulate in order and are attached to the next reported event. Each breadcrumb keeps its message and a type that defaults to 'default' when unspecified; an optional structured data object is preserved verbatim on the breadcrumb.",
    "cases": [
        {
            "input": {"dsn": "https://abc:def@sentry.io/123", "breadcrumbs": [{"message": "breadcrumb 1"}, {"message": "breadcrumb 2", "type": "navigation", "data": {"from": "origin", "to": "destination"}}], "event": {"message": "message text"}},
            "expected_output": "url=https://sentry.io/api/123/store/\nplatform=c\nmessage=message text\nbreadcrumb_count=2\nbreadcrumb[0].message=breadcrumb 1\nbreadcrumb[0].type=default\nbreadcrumb[1].message=breadcrumb 2\nbreadcrumb[1].type=navigation\nbreadcrumb[1].data={\"from\":\"origin\",\"to\":\"destination\"}\nevent_id_length=32\nlast_event_id=0\n"
        }
    ]
}
```

---

### Feature 5: Event Identifiers & Timestamps

**As a developer**, I want every event to carry a unique identifier and correctly formatted timestamps, so the backend can deduplicate and order events without me generating these values by hand.

**Expected Behavior / Usage:**

*5.1 Event Identifier — a 32-character hexadecimal id with a fixed version marker*

The library generates an event identifier that is a 32-character string drawn entirely from lowercase hexadecimal digits, with a fixed version marker `4` at index 12. The input requests an identifier sample; the output reports its length, the character at index 12, and that the character set is hexadecimal.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_identifier.json`

```json
{
    "description": "Every event is tagged with a freshly generated identifier: a 32-character string drawn entirely from lowercase hexadecimal digits, with a fixed version marker '4' at index 12.",
    "cases": [
        {
            "input": {"metadata": "identifier"},
            "expected_output": "length=32\nversion_char=4\ncharset=hex\n"
        }
    ]
}
```

*5.2 Human-Readable Timestamp — extended ISO-8601 UTC date-time*

Human-readable event timestamps are emitted as a 20-character UTC date-time string in extended ISO-8601 form: a four-digit year, hyphen-separated month and day, a `T` separator, colon-separated zero-padded hours, minutes and seconds, and a trailing `Z`. The output reports the string length and a mask in which every digit position is shown as `#` and every fixed separator is shown literally.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_datetime.json`

```json
{
    "description": "Human-readable event timestamps are emitted as a 20-character UTC date-time string in extended ISO-8601 form: four-digit year, month and day separated by hyphens, a 'T' separator, zero-padded hours, minutes and seconds separated by colons, and a trailing 'Z'. The mask shows digit positions as '#'.",
    "cases": [
        {
            "input": {"metadata": "datetime"},
            "expected_output": "length=20\n[a specific regex pattern for extended ISO timestamps]\n"
        }
    ]
}
```

*5.3 Machine-Readable Timestamp — whole seconds since the Unix epoch*

Machine-readable timestamps (used for breadcrumbs) are expressed as a whole number of seconds since the Unix epoch — a 10-digit value for the current era — never milliseconds. The output reports the unit and the digit count.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_epoch_seconds.json`

```json
{
    "description": "Machine-readable timestamps (used for breadcrumbs) are expressed as a whole number of seconds since the Unix epoch, i.e. a 10-digit value for the current era, never milliseconds.",
    "cases": [
        {
            "input": {"metadata": "timestamp"},
            "expected_output": "unit=seconds\ndigits=10\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured client library implementing the features above — connection-string parsing and validation, event assembly (messages, exceptions, breadcrumbs, extra context), metadata generation (identifiers and timestamps), and an HTTP transport behind an abstraction. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint: compact but with transport, event modeling, and metadata kept logically separate.

2. **The Execution/Test Adapter:** A runnable program that acts as a client of the core library. It reads a single JSON command from stdin, drives the library through its public surface, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. Native validation failures (e.g. a bad connection string) MUST be translated into the normalized `error=...` contract. The adapter must be logically separated from the core domain, and network egress must be routed to an in-memory sink so events can be inspected deterministically.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_endpoint_derivation.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_endpoint_derivation@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the versioning module for the marker at index 12
- reference the DSN validation utility for invalid schemes
