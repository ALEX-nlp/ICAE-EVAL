## Product Requirement Document

# Structured Key/Value Logging Toolkit - PRD

## Project Goal

Build a structured-logging toolkit whose fundamental unit is a *log event* expressed as a flat, variadic sequence of alternating keys and values. The toolkit lets developers compose loggers that attach persistent context, tag severity, bind values that are recomputed on every event, swap their output sink at runtime, and render each event in a chosen wire format — all behind one tiny logging contract — so applications get consistent, machine-parseable logs without hand-formatting strings.

---

## Background & Problem

Without a structured-logging toolkit, developers concatenate log strings by hand (`"user=" + id + " action=" + a`). This is repetitive, easy to get out of order, impossible to parse reliably downstream, and forces a single hard-coded output format. Adding request-scoped context (a request id, a region) means threading variables through every call site, and recording a per-event timestamp or caller location means recomputing it manually everywhere.

With this toolkit, a logger is just something that accepts a list of alternating key/value pairs. Context can be bolted onto a logger once and then automatically prepended to every later event; a value can be declared *dynamic* so it is re-evaluated on each event; severity tagging, output-format selection, and runtime sink replacement are all composable wrappers around the same minimal contract. The result is uniform structured output (key=value text or one JSON object per line) with zero bespoke formatting code.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (event encoders, context composition, severity tagging, dynamic value binding, runtime sink swapping, and a standard-log-line parser). It MUST NOT be a single "god file"; use a clear multi-file layout that separates these concerns. Do not over-engineer, but do not collapse independent concerns into one module either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract** for the execution adapter, NOT the internal data model. The core logging library must know nothing about stdin/stdout or JSON parsing. A separate execution adapter translates each JSON command into idiomatic calls on the core library and renders the resulting log output.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, routing, encoding, severity tagging, value binding, and output rendering in distinct units.
   - **Open/Closed Principle (OCP):** New encoders or new wrapping behaviors must be addable without modifying the core event contract.
   - **Liskov Substitution Principle (LSP):** Every logger wrapper (context, severity, swappable sink) must be usable anywhere a base logger is expected.
   - **Interface Segregation Principle (ISP):** The core logging contract must be a single, minimal operation that accepts a key/value list.
   - **Dependency Inversion Principle (DIP):** Wrappers depend on the abstract logging contract, never on a concrete encoder or I/O sink.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface must be elegant and idiomatic to the target language, hiding the encoding and composition machinery.
   - **Resilience:** Handle edge cases gracefully — a swappable sink with no active target must silently discard events without erroring; malformed requests must surface as a normalized, language-neutral error category rather than a runtime fault.

---

## Core Features

### Feature 1: Event Encoders

**As a developer**, I want to render a single log event (a flat list of alternating keys and values) into a chosen wire format, so I can emit consistent, parseable log lines without hand-building strings.

**Expected Behavior / Usage:**

A log event is a flat sequence whose even positions are keys and whose odd positions are values. Two encoders are offered. Both terminate each event with a newline. Both interpret a value that is an *error* object specially: the error is rendered as its plain message text, not as a structural dump. An event with an odd number of elements (a key without a value) is invalid and surfaces as the normalized error category `invalid_keyvals`.

*1.1 Key=Value Text Encoder — render an event as space-separated `key=value` pairs*

Pairs are emitted left to right in the order supplied, joined by single spaces, each as `key=value`, where the value uses its natural textual representation and an error value uses its message text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_prefix_encoder.json`

```json
{
    "description": "Encode a single log event as space-separated key=value pairs. Each value is rendered by its natural textual form; an error value renders as its message text. The line is terminated by a newline.",
    "cases": [
        {
            "input": {"op": "encode", "format": "prefix", "keyvals": ["hello", "world"]},
            "expected_output": "hello=world\n"
        },
        {
            "input": {"op": "encode", "format": "prefix", "keyvals": ["a", 1, "err", {"$err": "error"}]},
            "expected_output": "a=1 err=error\n"
        }
    ]
}
```

*1.2 JSON Encoder — render an event as one JSON object per line*

The event is rendered as a single JSON object with keys emitted in sorted order. Nested maps and arrays are rendered as JSON; an error value is rendered as its message string.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_json_encoder.json`

```json
{
    "description": "Encode a single log event as one JSON object on a line. Keys are emitted in sorted order. An error value is rendered as its message string; nested maps and arrays are rendered as JSON. The object is terminated by a newline.",
    "cases": [
        {
            "input": {"op": "encode", "format": "json", "keyvals": ["err", {"$err": "err"}, "m", {"0": 0}, "a", [1, 2, 3]]},
            "expected_output": "{\"a\":[1,2,3],\"err\":\"err\",\"m\":{\"0\":0}}\n"
        },
        {
            "input": {"op": "encode", "format": "json", "keyvals": ["k", "v"]},
            "expected_output": "{\"k\":\"v\"}\n"
        }
    ]
}
```

---

### Feature 2: Contextual Logging

**As a developer**, I want to attach persistent key/value context to a logger once and have it automatically included in every later event, so I don't thread request-scoped fields through every call site.

**Expected Behavior / Usage:**

Context is applied in layers. Each layer contributes a flat key/value list that is remembered by the returned logger and prepended to every subsequent event in front of that event's own pairs. Layers accumulate: applying a second layer keeps the first. The captured context is snapshotted at attach time, so mutating the original input list afterward does not affect what was stored. When the final event is emitted, all accumulated context plus the per-event pairs are merged and rendered by the selected encoder (so under the JSON encoder the merged keys appear in sorted order).

**Test Cases:** `rcb_tests/public_test_cases/feature2_contextual_logging.json`

```json
{
    "description": "Attach persistent context to a logger, then emit an event. Context layers are applied in order and accumulate; each layer's key/value pairs are prepended to every subsequent event. The final emitted record merges all accumulated context with the per-event key/value pairs, rendered by the selected encoder.",
    "cases": [
        {
            "input": {"op": "contextual", "format": "json", "context": [["a", 123], ["b", "c"]], "keyvals": ["msg", "message"]},
            "expected_output": "{\"a\":123,\"b\":\"c\",\"msg\":\"message\"}\n"
        },
        {
            "input": {"op": "contextual", "format": "prefix", "context": [["region", "us"]], "keyvals": ["msg", "hi"]},
            "expected_output": "region=us msg=hi\n"
        }
    ]
}
```

---

### Feature 3: Leveled Logging

**As a developer**, I want to tag events with a severity, so I can filter and route logs by importance without manually adding a level field each time.

**Expected Behavior / Usage:**

A leveled logger is derived from a base logger and exposes three severities: debug, info, and error. Selecting a severity automatically injects a single context pair — a *level key* mapped to that severity's *level value* — ahead of the event's own pairs. The injection reuses the same context mechanism as Feature 2, so it can be combined with additional context layers, and the rendered output obeys the chosen encoder's ordering rules.

*3.1 Default Severity Tags — built-in level key and values*

By default the injected key is `level` and the values are the upper-case severity names `DEBUG`, `INFO`, and `ERROR`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_default_levels.json`

```json
{
    "description": "Emit an event through a severity-tagged logger using the default configuration. Selecting a severity automatically injects a context pair whose key is \"level\" and whose value is the upper-case severity name (DEBUG, INFO, or ERROR) ahead of the event's own pairs.",
    "cases": [
        {
            "input": {"op": "leveled", "format": "prefix", "level": "debug", "keyvals": ["msg", "👨"]},
            "expected_output": "level=DEBUG msg=👨\n"
        },
        {
            "input": {"op": "leveled", "format": "prefix", "level": "info", "keyvals": ["msg", "🚀"]},
            "expected_output": "level=INFO msg=🚀\n"
        },
        {
            "input": {"op": "leveled", "format": "prefix", "level": "error", "keyvals": ["msg", "🍵"]},
            "expected_output": "level=ERROR msg=🍵\n"
        }
    ]
}
```

*3.2 Customized Severity Tags — overridden level key and values, with extra context*

The level key and any of the three per-severity values may be overridden. Additional context layers can be stacked on top of the severity tag before emitting; the merged record is rendered by the chosen encoder (sorted keys under the JSON encoder).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_customized_levels.json`

```json
{
    "description": "Emit an event through a severity-tagged logger whose level key and per-severity values have been customized. The injected severity pair uses the configured key and the configured value for the selected severity, and additional context can be stacked on top before emitting.",
    "cases": [
        {
            "input": {"op": "leveled", "format": "json", "level": "debug", "levelKey": "l", "levelValues": {"debug": "⛄", "info": "🌜", "error": "🌊"}, "context": [["easter_island", "🗿"]], "keyvals": ["msg", "💃💃💃"]},
            "expected_output": "{\"easter_island\":\"🗿\",\"l\":\"⛄\",\"msg\":\"💃💃💃\"}\n"
        }
    ]
}
```

---

### Feature 4: Dynamic Value Binding

**As a developer**, I want a value attached as context to be re-evaluated on every event instead of captured once, so fields like a timestamp reflect the moment each event is emitted.

**Expected Behavior / Usage:**

A value placed into context may be a *dynamic value* — a zero-argument producer that is invoked once per emitted event to yield that event's concrete value. Static values are stored verbatim; dynamic values are recomputed on each call. To make this observable deterministically, the dynamic value here is a mock clock seeded with a start instant and a fixed step: on each evaluation it advances by the step and yields the new instant formatted as an ISO-8601/RFC-3339 timestamp string. Emitting the same logger N times therefore produces N events whose timestamp advances by one step each time, proving the value is bound per event rather than once.

**Test Cases:** `rcb_tests/public_test_cases/feature4_dynamic_value_binding.json`

```json
{
    "description": "Attach a dynamic value to a logger that is re-evaluated on every log event rather than captured once. Here a deterministic mock clock advances by a fixed step on each evaluation, so two successive events bound to the same logger carry different timestamp values, proving the value is recomputed per event.",
    "cases": [
        {
            "input": {"op": "dynamic", "format": "prefix", "start": "[the mock clock start and step values]", "stepSeconds": 1, "calls": 2, "keyvals": ["foo", "bar"]},
            "expected_output": "ts=[the mock clock start and step values] foo=bar\nts=2015-04-25T00:00:02Z foo=bar\n"
        },
        {
            "input": {"op": "dynamic", "format": "prefix", "start": "[the mock clock start and step values]", "stepSeconds": 5, "calls": 3, "keyvals": ["foo", "bar"]},
            "expected_output": "ts=2015-04-25T00:00:05Z foo=bar\nts=2015-04-25T00:00:10Z foo=bar\nts=2015-04-25T00:00:15Z foo=bar\n"
        }
    ]
}
```

---

### Feature 5: Swappable Output Sink

**As a developer**, I want a logger whose active destination can be replaced at runtime, so a globally shared logger can be reconfigured by application code without re-wiring call sites.

**Expected Behavior / Usage:**

A swappable logger forwards each event to whatever sink is currently active. Before any sink is installed (and after the sink is explicitly cleared) it silently discards events and reports no error. At each step the active sink may be replaced — either with a named encoder, or cleared back to the discarding state — and then one event is emitted through whichever sink is active at that moment. The output is the concatenation of every event that reached a real encoder; events emitted while discarding contribute nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature5_swappable_sink.json`

```json
{
    "description": "A swappable logger whose active sink can be replaced between events. Before any sink is set it silently discards events with no error. Each step optionally swaps the active sink (an encoder name, or null to return to discarding) and then emits one event; the concatenated output reflects whichever sink was active at each step. Setting the sink to null again discards subsequent events.",
    "cases": [
        {
            "input": {"op": "rebind", "steps": [
                {"keyvals": ["k", "v"]},
                {"sink": "json", "keyvals": ["k", "v"]},
                {"sink": "prefix", "keyvals": ["k", "v"]},
                {"sink": null, "keyvals": ["k", "v"]}
            ]},
            "expected_output": "{\"k\":\"v\"}\nk=v\n"
        }
    ]
}
```

---

### Feature 6: Standard Log-Line Adapter

**As a developer**, I want to feed a plain standard-library-style log line into the structured pipeline and have its parts extracted into named fields, so legacy or third-party log output becomes structured without changing the emitter.

**Expected Behavior / Usage:**

A raw log line is parsed into up to three fields and re-emitted as `key=value` pairs. An optional leading date in `YYYY/MM/DD` form and an optional time in `HH:MM:SS` form (with optional fractional seconds) are concatenated, separated by a single space when both are present, into one timestamp under key `ts`. An optional file reference in `path:line` form is captured under key `file`. The remaining text after an optional `": "` separator is the message under key `msg`. Fields that are absent are omitted, and the present fields are emitted in the fixed order `ts`, `file`, `msg`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_stdlib_line_adapter.json`

```json
{
    "description": "Parse a single raw standard log line and re-emit it as structured key=value pairs. An optional leading date (YYYY/MM/DD) and time (HH:MM:SS with optional fractional seconds) are joined into a single timestamp under key \"ts\"; an optional file:line reference goes under key \"file\"; the remaining message text goes under key \"msg\". Absent fields are omitted. Fields appear in the order ts, file, msg.",
    "cases": [
        {"input": {"op": "adapt_line", "line": "hello"}, "expected_output": "msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "2009/01/23: hello"}, "expected_output": "ts=2009/01/23 msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "2009/01/23 01:23:23: hello"}, "expected_output": "ts=2009/01/23 01:23:23 msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "01:23:23: hello"}, "expected_output": "ts=01:23:23 msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "2009/01/23 01:23:23.123123: hello"}, "expected_output": "ts=2009/01/23 01:23:23.123123 msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "2009/01/23 01:23:23.123123 /a/b/c/d.go:23: hello"}, "expected_output": "ts=2009/01/23 01:23:23.123123 file=/a/b/c/d.go:23 msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "01:23:23.123123 /a/b/c/d.go:23: hello"}, "expected_output": "ts=01:23:23.123123 file=/a/b/c/d.go:23 msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "2009/01/23 01:23:23 /a/b/c/d.go:23: hello"}, "expected_output": "ts=2009/01/23 01:23:23 file=/a/b/c/d.go:23 msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "2009/01/23 /a/b/c/d.go:23: hello"}, "expected_output": "ts=2009/01/23 file=/a/b/c/d.go:23 msg=hello\n"},
        {"input": {"op": "adapt_line", "line": "/a/b/c/d.go:23: hello"}, "expected_output": "file=/a/b/c/d.go:23 msg=hello\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured logging library implementing the features above — event encoders, context composition, severity tagging, dynamic value binding, swappable sink, and the standard-log-line adapter — with a single minimal logging contract at its center. Its physical structure MUST follow the Scale-Driven Code Organization constraint (multi-file, one concern per unit).

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the appropriate core logic, and prints the rendered log output to stdout, strictly matching the per-leaf-feature contracts above. It must be logically and physically separated from the core library, and it must normalize any failure into a language-neutral `error=<category>` line rather than leaking a host runtime fault.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_prefix_encoder.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_prefix_encoder@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- sink set to null explicitly
- No sink set initially
