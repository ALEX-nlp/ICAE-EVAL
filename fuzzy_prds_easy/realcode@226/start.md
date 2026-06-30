## Product Requirement Document

# Event Capture & Scope Enrichment SDK - Contract Specification

## Project Goal

Build an error- and event-monitoring SDK that lets application developers report log messages and thrown errors to an observability backend, and enrich every report with contextual data (tags, severity level, user identity, structured contexts, and breadcrumbs), without hand-assembling event payloads or wiring up transport themselves. The SDK exposes a small, idiomatic facade for initialization and capture, plus a pre-send inspection hook so that every event can be observed and post-processed before it leaves the process.

---

## Background & Problem

Without such a library, developers who want crash and error visibility must manually build event objects, attach metadata, serialize them, and ship them to a backend on every error path. This produces repetitive, error-prone boilerplate scattered across the codebase, makes it hard to attach consistent contextual data (who the user was, what severity applied, what happened just before the failure), and gives no single place to intercept or scrub an event before it is sent.

With this library, the developer initializes the SDK once with a configuration block, then captures messages and errors through a few one-line calls. Contextual data is layered through a "scope": data placed on the global scope is automatically attached to every later event, while data placed on a per-capture local scope applies only to that one event. A pre-send hook receives a fully assembled, normalized event object, allowing inspection or suppression. The same model applies to breadcrumbs (trail-of-events leading up to a failure) through a dedicated pre-processing hook.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. The core is a multi-responsibility system (initialization/options, the capture facade, the scope/enrichment model, the event/breadcrumb data model, and the pre-send hook pipeline) and MUST NOT collapse into a single "god file"; organize it into clear modules. The execution adapter that translates external commands into SDK calls MUST be separate from the core.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, not the internal data model of the SDK. The core capture/scope/event logic MUST remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic SDK calls and for rendering captured events into the textual contract.

3. **Adherence to SOLID Design Principles:** Separate parsing, command routing, scope mutation, capture execution, and output formatting into distinct logical units. The capture engine must be open for extension (new enrichment kinds) but closed for modification. Enrichment value kinds must be substitutable behind a common abstraction. Keep public interfaces small and cohesive. High-level capture logic must depend on abstractions, not on concrete I/O.

4. **Robustness & Interface Design:** The public facade must be elegant and idiomatic to the target language, hiding transport and serialization details. Invalid commands (unknown operation, missing required field, unknown enrichment kind) must be modeled as proper errors and surfaced through the neutral error contract described below, never as raw runtime stack traces.

---

## Core Features

### Feature 1: Capture a Log Message

**As a developer**, I want to capture a free-text message as an event, so I can record noteworthy occurrences that are not exceptions.

**Expected Behavior / Usage:**

Submitting a single `capture_message` operation with a `message` string produces exactly one captured event. The event's formatted message text equals the supplied string. When a message is captured without an explicit severity, the SDK assigns the default informational severity level. The output first reports the total number of captured events as `captured_events=<n>`, then, for the event, its `message` and its `level`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_capture_message.json`

```json
{
    "description": "Capturing a plain log message records exactly one event whose formatted text equals the supplied string and whose severity defaults to the informational level.",
    "cases": [
        {
            "input": {"operations": [{"op": "capture_message", "message": "test[specific JSON string serialization logic for context types]]},
            "expected_output": "captured_events=1\nevent[0].message=test\nevent[0].level=INFO\n"
        }
    ]
}
```

---

### Feature 2: Capture Thrown Errors

**As a developer**, I want to capture thrown errors as events, so I can monitor failures with their type and message preserved.

**Expected Behavior / Usage:**

Each `capture_exception` operation captures the supplied error as its own event, in submission order. For every captured error the event records the error's type name (`exception[0].type`) and the error's message text (`exception[0].value`). Submitting no capture operations results in `captured_events=0` and no event lines. The leading `captured_events=<n>` count lets a reader confirm exactly how many events the framework emitted, so a stub that silently drops or duplicates events cannot pass.

**Test Cases:** `rcb_tests/public_test_cases/feature2_capture_exception.json`

```json
{
    "description": "Capturing one or more thrown errors produces one event per capture, in order, each recording the error's type name and its message text; capturing nothing produces zero events.",
    "cases": [
        {
            "input": {"operations": [{"op": "capture_exception", "message": "test[specific JSON string serialization logic for context types], {"op": "capture_exception", "message": "test2[specific JSON string serialization logic for context types]]},
            "expected_output": "captured_events=2\nevent[0].exception[0].type=RuntimeException\nevent[0].exception[0].value=test\nevent[1].exception[0].type=RuntimeException\nevent[1].exception[0].value=test2\n"
        },
        {
            "input": {"operations": []},
            "expected_output": "captured_events=0\n"
        }
    ]
}
```

---

### Feature 3: Breadcrumb Pre-Processing

**As a developer**, I want breadcrumbs I add to be routed through a pre-processing hook before they are retained, so I can observe, filter, or transform the trail of events that precedes a failure.

**Expected Behavior / Usage:**

An `add_breadcrumb` operation registers a breadcrumb (carrying at least a `message`). The breadcrumb is delivered to the breadcrumb pre-processing hook with its message intact, recorded in the output as `breadcrumb[<i>].message=<text>`. A later `capture_exception` is reported as its own event independently of the breadcrumb. This verifies the breadcrumb actually flows through the framework's hook pipeline rather than being silently stored.

**Test Cases:** `rcb_tests/public_test_cases/feature3_breadcrumb.json`

```json
{
    "description": "A breadcrumb added before an error is captured is delivered to the breadcrumb pre-processing hook with its message intact; the subsequently captured error is reported as its own event.",
    "cases": [
        {
            "input": {"operations": [{"op": "add_breadcrumb", "message": "test[specific JSON string serialization logic for context types], {"op": "capture_exception", "message": "test[specific JSON string serialization logic for context types]]},
            "expected_output": "captured_events=1\nevent[0].exception[0].type=RuntimeException\nevent[0].exception[0].value=test\nbreadcrumb[0].message=test\n"
        }
    ]
}
```

---

### Feature 4: Scope Enrichment

**As a developer**, I want to attach contextual data to captured events through a scope, so that reports carry the metadata needed to diagnose them.

**Expected Behavior / Usage:**

Enrichment data lives in a scope. A `configure_scope` operation mutates the **global** scope, whose data is automatically attached to every subsequently captured event. A `scope` block attached directly to a capture operation mutates a **local** scope that applies only to that one capture. Each enrichment kind (tag, level, user, structured context) is rendered into the captured event under a stable, namespaced key prefixed by the event index.

*4.1 Tags — Setting key/value tags on global and local scopes*

*4.1.1 Local Scope Tag — A tag set on a per-capture scope applies only to that capture*

A tag provided on a capture operation's local `scope` is attached only to that event, rendered as `event[<i>].tag.<key>=<value>`. Performing two independent captures, each setting the same tag key on its own local scope, shows that each event carries its own copy and that local scope data does not bleed from one capture into the next.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_1_local_scope_tag.json`

```json
{
    "description": "A tag set on a per-capture local scope is attached only to that event. A second capture that sets the same key on its own local scope carries its own value, demonstrating that local scope data does not leak between captures.",
    "cases": [
        {
            "input": {"operations": [{"op": "capture_exception", "message": "test", "scope": {"set_tag": {"key": "testABC", "value": "valueABC[specific JSON string serialization logic for context types]}}]},
            "expected_output": "captured_events=1\nevent[0].exception[0].type=RuntimeException\nevent[0].exception[0].value=test\nevent[0].tag.testABC=valueABC\n"
        },
        {
            "input": {"operations": [{"op": "capture_exception", "message": "test", "scope": {"set_tag": {"key": "testABC", "value": "valueABC[specific JSON string serialization logic for context types]}}, {"op": "capture_exception", "message": "test2", "scope": {"set_tag": {"key": "testABC", "value": "valueABC[specific JSON string serialization logic for context types]}}]},
            "expected_output": "captured_events=2\nevent[0].exception[0].type=RuntimeException\nevent[0].exception[0].value=test\nevent[0].tag.testABC=valueABC\nevent[1].exception[0].type=RuntimeException\nevent[1].exception[0].value=test2\nevent[1].tag.testABC=valueABC\n"
        }
    ]
}
```

*4.1.2 Global Scope Tag — A tag set on the global scope is attached to later events*

A tag set on the global scope via `configure_scope` persists and is attached to an event captured afterward, without being re-supplied at capture time. It is rendered as `event[<i>].tag.<key>=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_2_global_scope_tag.json`

```json
{
    "description": "A tag set on the global scope persists and is attached to a later captured event without being supplied at capture time.",
    "cases": [
        {
            "input": {"operations": [{"op": "configure_scope", "set_tag": {"key": "testABC", "value": "valueABC[specific JSON string serialization logic for context types]}, {"op": "capture_exception", "message": "test[specific JSON string serialization logic for context types]]},
            "expected_output": "captured_events=1\nevent[0].exception[0].type=RuntimeException\nevent[0].exception[0].value=test\nevent[0].tag.testABC=valueABC\n"
        }
    ]
}
```

*4.2 Severity Level — Setting the event severity on the global scope*

A severity level set on the global scope via `configure_scope` (`set_level`) is applied to a subsequently captured event and rendered as `event[<i>].level=<LEVEL>`. Valid levels are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `FATAL`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_global_scope_level.json`

```json
{
    "description": "A severity level set on the global scope is applied to a subsequently captured event.",
    "cases": [
        {
            "input": {"operations": [{"op": "configure_scope", "set_level": "DEBUG[specific JSON string serialization logic for context types], {"op": "capture_exception", "message": "test[specific JSON string serialization logic for context types]]},
            "expected_output": "captured_events=1\nevent[0].exception[0].type=RuntimeException\nevent[0].exception[0].value=test\nevent[0].level=DEBUG\n"
        }
    ]
}
```

*4.3 User Identity — Setting the user on the global scope*

A user identity set on the global scope via `configure_scope` (`set_user`) is attached to a subsequently captured event. The SDK exposes the user's `email`, `id`, `ipAddress`, and `username` fields, rendered as `event[<i>].user.<field>=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_global_scope_user.json`

```json
{
    "description": "A user identity set on the global scope is attached to a subsequently captured event, exposing the email, id, ip address and username fields.",
    "cases": [
        {
            "input": {"operations": [{"op": "configure_scope", "set_user": {"email": "test@example.com", "id": "123", "ipAddress": "127.0.0.1", "username": "testuser[specific JSON string serialization logic for context types]}, {"op": "capture_exception", "message": "test[specific JSON string serialization logic for context types]]},
            "expected_output": "captured_events=1\nevent[0].exception[0].type=RuntimeException\nevent[0].exception[0].value=test\nevent[0].user.email=test@example.com\nevent[0].user.id=123\nevent[0].user.ipAddress=127.0.0.1\nevent[0].user.username=testuser\n"
        }
    ]
}
```

*4.4 Structured Contexts — Setting typed context entries on the global scope*

Structured context entries set on the global scope via `configure_scope` (`set_contexts`) are attached to a subsequently captured event. Each entry has a `key`, a `type` (`string`, `boolean`, `number`, or `collection`), and a `value`; a collection may mix value kinds. The SDK normalizes every context entry into an object that wraps the original value under a single `value` field. Each entry is rendered as `event[<i>].context.<key>=<json-object>`, where the object is the normalized wrapper serialized as JSON (e.g. `{"value":true}`, `{"value":["abc",123,true]}`). Context lines for the event are emitted in ascending key order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_global_scope_contexts.json`

```json
{
    "description": "Structured context entries of different value kinds (string, boolean, number, and heterogeneous collection) set on the global scope are attached to a captured event, each normalized into an object that wraps the original value under a single value field.",
    "cases": [
        {
            "input": {"operations": [{"op": "configure_scope", "set_contexts": [{"key": "stringKey", "type": "string", "value": "stringValue[specific JSON string serialization logic for context types], {"key": "booleanKey", "type": "boolean", "value": true}, {"key": "numberKey", "type": "number", "value": "123[specific JSON string serialization logic for context types], {"key": "collectionKey", "type": "collection", "value": ["abc", 123, true]}]}, {"op": "capture_exception", "message": "test[specific JSON string serialization logic for context types]]},
            "expected_output": "captured_events=1\nevent[0].exception[0].type=RuntimeException\nevent[0].exception[0].value=test\nevent[0].context.booleanKey={\"value\":true}\nevent[0].context.collectionKey={\"value\":[\"abc\",123,true]}\nevent[0].context.numberKey={\"value\":123}\nevent[0].context.stringKey={\"value\":\"stringValue\[specific JSON string serialization logic for context types]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing initialization/options, the capture facade (message and error capture), the scope/enrichment model (global and local scopes; tags, level, user, structured contexts), the breadcrumb pipeline, and the pre-send/pre-breadcrumb inspection hooks. Its physical structure must follow the Scale-Driven Code Organization constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client of the core system. It reads a single JSON command object from stdin (an `operations` array describing a sequence of captures, scope configurations, and breadcrumb additions), drives the core SDK through its public API, intercepts the assembled events and breadcrumbs via the SDK's hooks, and prints the language-neutral textual contract described above to stdout. Invalid commands are rendered as a neutral error line of the form `error=<category>` optionally followed by a single detail line (e.g. `field=<name>`), never as a host-language stack trace. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it feeds the `input` object to the adapter on stdin and writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_capture_message.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_capture_message@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the standard log level hierarchy defined in the global_scope module
