## Product Requirement Document

# Structured JSON Logging Serializer - Schema-Compliant Log Event Formatter

## Project Goal

Build a structured-logging serialization library that turns a log event (timestamp, severity, message, contextual key/values, tags, and optional error) into a single line of schema-compliant JSON, ready to be written to a file and ingested by a log pipeline without any grok/regex parsing. The library serializes events deterministically and field-by-field, so the produced line is byte-stable and directly machine-parseable.

---

## Background & Problem

Without this library, developers either log plain text and then maintain fragile parsing rules downstream, or they pull in a general-purpose JSON serializer and hand-roll the field names, the field ordering, and the escaping for every log event. That is repetitive, error-prone, and easy to get subtly wrong (an unescaped quote or newline corrupts the whole line; an inconsistent timestamp format breaks time-range queries; ad-hoc field names break shared dashboards).

With this library, the developer hands over the raw event data and gets back one canonical JSON line whose first fields are always `@timestamp`, `log.level`, and `message`, whose timestamps are always fixed-width UTC ISO-8601, whose string values are always correctly escaped, and whose contextual data is namespaced consistently. The output schema is stable across services, so a single set of downstream dashboards and queries works everywhere.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities — timestamp formatting, string escaping, log-line assembly, and error rendering — so it MUST NOT be a single "god file". Provide a small, clear module/directory layout (e.g. a core serialization module plus a separate execution adapter), not a monolith. Do not over-engineer: a handful of cohesive units is sufficient.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, NOT the internal data model of the core serializer. The core serialization logic MUST be usable directly from code via idiomatic calls and MUST NOT know anything about stdin/stdout or JSON command parsing. The execution adapter is solely responsible for translating a JSON command into idiomatic calls on the core and printing the produced wire output.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep timestamp formatting, escaping, line assembly, error rendering, command parsing, and output writing in distinct units.
   - **Open/Closed Principle (OCP):** The set of serialized fields must be extensible (new optional fields, new context keys) without rewriting the core assembler.
   - **Liskov Substitution Principle (LSP):** Any concrete formatter must be substitutable for its abstraction.
   - **Interface Segregation Principle (ISP):** Keep the serialization entry points small and focused.
   - **Dependency Inversion Principle (DIP):** The core must not depend on the I/O adapter; the adapter depends on the core.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core serializer must be elegant and idiomatic to the target language, hiding escaping and ordering details from callers.
   - **Resilience:** Absent optional inputs must be omitted cleanly (never emit a half-formed field). Malformed commands must be reported through a normalized, language-neutral error contract (see below), never by leaking a host-language stack trace or runtime object dump to stdout.

**Normalized error contract (applies to all features):** When the adapter cannot honor a command, it prints a two-line, language-neutral block: a first line `error=<category>` and a second line `<field>=<value>` carrying the offending datum. Categories used: `missing_field` (a required field is absent — `field=<name>`), `unknown_operation` (the requested op is not recognized — `op=<name>`), and `invalid_input` (the payload was not a JSON object — `payload=<raw>`). No host exception class names, no runtime message suffixes, no object reprs ever appear in stdout.

---

## Core Features

### Feature 1: UTC ISO-8601 Timestamp Serialization

**As a developer**, I want every log event stamped with a fixed-width UTC ISO-8601 timestamp, so I can run reliable time-range queries and sort log lines lexicographically by time.

**Expected Behavior / Usage:**

The input is a command object with `op` set to `format_timestamp` and an integer field `epoch_millis` holding milliseconds elapsed since the Unix epoch (1970-01-01T00:00:00Z). The output is a single timestamp string followed by a trailing newline, in the exact form `YYYY-MM-DDThh:mm:ss.SSSZ`. Every component is zero-padded to a constant width: 4-digit year, 2-digit month, 2-digit day, 2-digit hour, 2-digit minute, 2-digit second, and 3-digit millisecond. The date portion is computed in UTC and the zone is always the literal character `Z`; there is no local-time offset and no variation in width. Epoch `0` yields `[a specific millisecond marker representing the Unix epoch]`. If `epoch_millis` is missing or not an integer, the normalized error contract is used with `field=epoch_millis`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_iso_timestamp.json`

```json
{
    "description": "Serialize an epoch timestamp given in milliseconds into a fixed-width UTC ISO-8601 date-time string of the form YYYY-MM-DDThh:mm:ss.SSSZ. Every component is zero-padded to constant width (4-digit year, 2-digit month/day/hour/minute/second, 3-digit millisecond) and the zone is always literal 'Z' (UTC). The input is a JSON object with op 'format_timestamp' and an integer field epoch_millis (milliseconds since the Unix epoch). The output is the formatted string followed by a trailing newline.",
    "cases": [
        {"input": "{\"op\":\"format_timestamp\",\"epoch_millis\":0}", "expected_output": "[a specific millisecond marker representing the Unix epoch]\n"},
        {"input": "{\"op\":\"format_timestamp\",\"epoch_millis\":1565093352375}", "expected_output": "2019-08-06T12:09:12.375Z\n"},
        {"input": "{\"op\":\"format_timestamp\",\"epoch_millis\":1577836799999}", "expected_output": "2019-12-31T23:59:59.999Z\n"}
    ]
}
```

---

### Feature 2: Canonical Log Line Assembly

**As a developer**, I want each event rendered as one canonical JSON line whose leading fields are always in the same order and spacing, so downstream tooling can rely on a stable schema and humans can scan the start of every line consistently.

**Expected Behavior / Usage:**

The input is a command object with `op` set to `build_log_line` and the fields `timestamp_millis` (epoch ms), `level` (the severity name), and `message`. Optional fields `service_name`, `thread_name`, and `logger_name` may also be supplied. The output is exactly one JSON line terminated by a newline character.

The first three fields always appear in this fixed order with this fixed spacing: `@timestamp` (the value formatted exactly as in Feature 1), then `log.level`, then `message`. The level value is right-aligned to a width of five characters: a level name shorter than five characters is left-padded with spaces *inside* the quotes-region so that all level labels line up in a column (for example a four-character level gains one leading space before the opening quote of its value), while a level name of five or more characters gets no padding. After those three fields, when present and in this order, come `service.name`, `process.thread.name`, and `log.logger`. Any optional field whose source value is absent is omitted entirely (no empty placeholder). The required fields `timestamp_millis` and `level` trigger the normalized error contract (`field=timestamp_millis` or `field=level`) when missing.

**Test Cases:** `rcb_tests/public_test_cases/feature2_log_line_core.json`

```json
{
    "description": "Assemble a single structured log record into one line of ECS-compatible JSON. The input is a JSON object with op 'build_log_line' and the fields timestamp_millis (epoch ms), level (severity name), message, and optional service_name, thread_name, logger_name. The output is exactly one JSON line terminated by a newline. The first three fields always appear in fixed order and with fixed spacing: @timestamp (formatted as a UTC ISO-8601 string), log.level (right-aligned to a width of five characters by left-padding short level names with spaces, then quoted), and message. After those come, when present, service.name, process.thread.name and log.logger. Fields whose source value is absent are simply omitted.",
    "cases": [
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"DEBUG\",\"message\":\"test\",\"service_name\":\"test\",\"thread_name\":\"main\",\"logger_name\":\"com.example.App\"}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\":\"DEBUG\", \"message\":\"test\", \"service.name\":\"test\",\"process.thread.name\":\"main\",\"log.logger\":\"com.example.App\"}\n"},
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"WARN\",\"message\":\"hi\",\"service_name\":\"test\",\"thread_name\":\"main\",\"logger_name\":\"L\"}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\": \"WARN\", \"message\":\"hi\", \"service.name\":\"test\",\"process.thread.name\":\"main\",\"log.logger\":\"L\"}\n"},
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":0,\"level\":\"TRACE\",\"message\":\"x\",\"logger_name\":\"L\"}", "expected_output": "{\"@timestamp\":\"[a specific millisecond marker representing the Unix epoch]\", \"log.level\":\"TRACE\", \"message\":\"x\", \"log.logger\":\"L\"}\n"}
    ]
}
```

---

### Feature 3: Contextual Key/Value Labels

**As a developer**, I want to attach arbitrary contextual key/value pairs to a log event, so I can correlate and filter logs by request, user, or trace without polluting the reserved top-level fields.

**Expected Behavior / Usage:**

*3.1 Namespaced Labels — context keys are emitted under a reserved namespace prefix*

The input is a `build_log_line` command with an optional `labels` object (a map of string keys to string values). Each label becomes its own JSON field, emitted after `log.logger`, in the same insertion order as given. By default every label key is namespaced with a `labels.` prefix so that user-supplied context can never collide with or overwrite a reserved top-level field. The value is escaped like any other string. When the `labels` object is absent or empty, no label fields appear.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_labels_prefixed.json`

```json
{
    "description": "Attach arbitrary key/value context (a labels map) to a log record. Each label is emitted as its own JSON field after the logger field. By default every label key is namespaced with a 'labels.' prefix so that user context cannot collide with reserved top-level fields. The input provides the labels under the optional 'labels' object; insertion order of the labels is preserved in the output. The output is the full log line with one prefixed field per label.",
    "cases": [
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"DEBUG\",\"message\":\"test\",\"service_name\":\"test\",\"thread_name\":\"main\",\"logger_name\":\"L\",\"labels\":{\"foo\":\"bar\"}}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\":\"DEBUG\", \"message\":\"test\", \"service.name\":\"test\",\"process.thread.name\":\"main\",\"log.logger\":\"L\",\"labels.foo\":\"bar\"}\n"},
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"INFO\",\"message\":\"m\",\"service_name\":\"svc\",\"thread_name\":\"worker-1\",\"logger_name\":\"a.b.C\",\"labels\":{\"user\":\"alice\",\"region\":\"eu\"}}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\": \"INFO\", \"message\":\"m\", \"service.name\":\"svc\",\"process.thread.name\":\"worker-1\",\"log.logger\":\"a.b.C\",\"labels.user\":\"alice\",\"labels.region\":\"eu\"}\n"}
    ]
}
```

*3.2 Promoted Top-Level Keys — selected correlation keys bypass the namespace prefix*

The input is a `build_log_line` command with a `labels` object, and optionally a `top_level_labels` array overriding the default allow-list. A configurable allow-list of key names (defaulting to correlation identifiers such as the trace id, transaction id, span id, error id, and service name) is emitted as a bare top-level field *without* the `labels.` prefix; every other key keeps the prefix. This lets known correlation fields land at their reserved schema location while still flowing through the same labels input. A single input map may mix promoted and namespaced keys; each key is decided independently and emission order follows the input order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_labels_top_level.json`

```json
{
    "description": "Promote selected context keys to reserved top-level fields instead of namespacing them under 'labels.'. A configurable allow-list of key names (defaulting to correlation identifiers such as trace, transaction, span, error id and service name) is emitted without the 'labels.' prefix, while any other key keeps the prefix. The input supplies the labels under 'labels' and may override the allow-list via the optional 'top_level_labels' array. The output shows the promoted key as a bare top-level field.",
    "cases": [
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"DEBUG\",\"message\":\"test\",\"service_name\":\"test\",\"thread_name\":\"main\",\"logger_name\":\"L\",\"labels\":{\"transaction.id\":\"0af7651916cd43dd8448eb211c80319c\"}}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\":\"DEBUG\", \"message\":\"test\", \"service.name\":\"test\",\"process.thread.name\":\"main\",\"log.logger\":\"L\",\"transaction.id\":\"0af7651916cd43dd8448eb211c80319c\"}\n"},
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"DEBUG\",\"message\":\"test\",\"service_name\":\"test\",\"thread_name\":\"main\",\"logger_name\":\"L\",\"labels\":{\"trace.id\":\"abc\",\"custom\":\"v\"}}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\":\"DEBUG\", \"message\":\"test\", \"service.name\":\"test\",\"process.thread.name\":\"main\",\"log.logger\":\"L\",\"trace.id\":\"abc\",\"labels.custom\":\"v\"}\n"}
    ]
}
```

---

### Feature 4: Hierarchical Tags

**As a developer**, I want to attach a set of named tags (a flattened marker hierarchy) to a log event, so I can categorize events and filter them by membership in any tag.

**Expected Behavior / Usage:**

The input is a `build_log_line` command with an optional `tags` array of tag names, given in the order they should appear (a parent/child/grandchild marker tree is supplied already flattened, parents before descendants). When at least one tag is present, the record gains a single `tags` JSON array field holding those names in order; this field is placed immediately after `message` and before `service.name`. When the `tags` array is absent or empty, no `tags` field is emitted at all.

**Test Cases:** `rcb_tests/public_test_cases/feature4_tags.json`

```json
{
    "description": "Render a hierarchy of named markers/tags as a JSON array field named 'tags'. The input supplies an ordered list of tag names under the optional 'tags' array (a flattened parent/child/grandchild marker tree). When at least one tag is present, the record gains a 'tags' field holding the names in order, placed after the message and before the service field. When no tags are supplied the field is omitted entirely.",
    "cases": [
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"DEBUG\",\"message\":\"test\",\"service_name\":\"test\",\"thread_name\":\"main\",\"logger_name\":\"L\",\"tags\":[\"parent\",\"child\",\"grandchild\"]}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\":\"DEBUG\", \"message\":\"test\", \"tags\":[\"parent\",\"child\",\"grandchild\"],\"service.name\":\"test\",\"process.thread.name\":\"main\",\"log.logger\":\"L\"}\n"},
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"INFO\",\"message\":\"hello\",\"service_name\":\"test\",\"thread_name\":\"main\",\"logger_name\":\"L\",\"tags\":[\"foo\"]}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\": \"INFO\", \"message\":\"hello\", \"tags\":[\"foo\"],\"service.name\":\"test\",\"process.thread.name\":\"main\",\"log.logger\":\"L\"}\n"}
    ]
}
```

---

### Feature 5: Error / Exception Serialization

**As a developer**, I want errors serialized into a small, fixed set of structured fields, so failures are queryable and the full diagnostic trace is preserved as machine-readable text rather than being dumped as free-form output.

**Expected Behavior / Usage:**

*5.1 Standalone Error Object — three fixed error fields*

The input is a command with `op` set to `format_error` and an `error` object carrying `type` (the error category/class name as opaque text), `message`, and `stack_trace` (the already-rendered trace as a single multi-line string). The output is a one-line JSON object containing exactly three fields, in this fixed order: `error.code` (the type), `error.message` (the message), and `error.stack_trace` (the trace as one quoted string). All three values are escaped according to JSON string rules: a double-quote becomes `\"`, a backslash becomes `\\`, and an embedded newline becomes the two-character escape `\n` (so the whole trace stays on one physical line). The `type`, `message`, and `stack_trace` are treated as opaque domain-supplied text — the serializer does not interpret or rewrite them. If the `error` object is missing the normalized error contract is used with `field=error`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_error_fields.json`

```json
{
    "description": "Serialize an error into the three ECS error fields in fixed order: error.code (the error type name), error.message (the human-readable message), and error.stack_trace (the rendered stack trace as a single quoted string with embedded newlines preserved as the escape sequence backslash-n). The input is a JSON object with op 'format_error' and an 'error' object carrying type, message and stack_trace. The type, message and stack trace are treated as opaque domain-supplied text. The output is a one-line JSON object holding exactly these three fields, terminated by a newline.",
    "cases": [
        {"input": "{\"op\":\"format_error\",\"error\":{\"type\":\"java.lang.RuntimeException\",\"message\":\"boom\",\"stack_trace\":\"java.lang.RuntimeException: boom\\nat A.b(A.java:1)\\nat C.d(C.java:2)\"}}", "expected_output": "{\"error.code\":\"java.lang.RuntimeException\",\"error.message\":\"boom\",\"error.stack_trace\":\"java.lang.RuntimeException: boom\\nat A.b(A.java:1)\\nat C.d(C.java:2)\"}\n"},
        {"input": "{\"op\":\"format_error\",\"error\":{\"type\":\"PaymentDeclinedError\",\"message\":\"card declined\",\"stack_trace\":\"PaymentDeclinedError: card declined\\n\\tat charge(billing.mod:88)\"}}", "expected_output": "{\"error.code\":\"PaymentDeclinedError\",\"error.message\":\"card declined\",\"error.stack_trace\":\"PaymentDeclinedError: card declined\\n\\tat charge(billing.mod:88)\"}\n"}
    ]
}
```

*5.2 Error Attached to a Log Line — error fields appended to a full record*

The input is a `build_log_line` command whose optional `error` object supplies the same `type`, `message`, and `stack_trace`. The output is one complete log line: the standard leading fields (Feature 2), then any label fields, then the three error fields `error.code`, `error.message`, and `error.stack_trace` appended at the end, all within the same single JSON line terminated by a newline. The error fields obey the same fixed order and the same escaping rules as in 5.1.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_error_in_log_line.json`

```json
{
    "description": "Emit a complete ERROR-level log line that carries an attached error. The error.code, error.message and error.stack_trace fields are appended after the logger and label fields, within the same single JSON line. The input is a 'build_log_line' command whose optional 'error' object supplies the error type, message and stack_trace. The output is one JSON line: the standard leading fields followed by the three error fields, terminated by a newline.",
    "cases": [
        {"input": "{\"op\":\"build_log_line\",\"timestamp_millis\":1565093352375,\"level\":\"ERROR\",\"message\":\"failed\",\"service_name\":\"test\",\"thread_name\":\"main\",\"logger_name\":\"L\",\"error\":{\"type\":\"OrderProcessingError\",\"message\":\"insufficient funds\",\"stack_trace\":\"OrderProcessingError: insufficient funds\\n\\tat checkout(checkout.mod:42)\\n\\tat main(app.mod:7)\"}}", "expected_output": "{\"@timestamp\":\"2019-08-06T12:09:12.375Z\", \"log.level\":\"ERROR\", \"message\":\"failed\", \"service.name\":\"test\",\"process.thread.name\":\"main\",\"log.logger\":\"L\",\"error.code\":\"OrderProcessingError\",\"error.message\":\"insufficient funds\",\"error.stack_trace\":\"OrderProcessingError: insufficient funds\\n\\tat checkout(checkout.mod:42)\\n\\tat main(app.mod:7)\"}\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured serialization library implementing Features 1–5, with timestamp formatting, string escaping, log-line assembly, and error rendering separated into cohesive units. Its physical structure MUST follow the "Scale-Driven Code Organization" constraint — a small multi-unit layout, not a single god file and not an over-engineered framework.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client of the core serializer. It reads a single JSON command from stdin, dispatches on the `op` field to the appropriate core call, prints the produced wire output to stdout, and renders any failure through the normalized, language-neutral error contract. This adapter MUST be logically (and ideally physically) separated from the core domain and must never leak host-language runtime traces to stdout.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_iso_timestamp.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_iso_timestamp@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the timezone convention from the date-channel
