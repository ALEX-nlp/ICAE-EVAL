## Product Requirement Document

# Notification Delivery Toolkit - Multi-Channel Notification Contracts

## Project Goal

Build a notification delivery library that allows developers to construct one notification payload and deliver it through persistence, queued jobs, email, realtime broadcasts, HTTP integrations, and mobile push helpers without duplicating delivery plumbing for every channel.

---

## Background & Problem

Without this library, developers are forced to hand-write payload validation, recipient iteration, database persistence, queue scheduling, callback orchestration, serialization, and channel-specific request handling for each notification. This leads to repetitive code, inconsistent delivery behavior, and difficult maintenance when adding or changing delivery channels.

With this library, developers define notification inputs once, attach delivery channels and options, and rely on a shared engine to validate, execute, schedule, persist, serialize, broadcast, and report observable delivery effects consistently.

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

### Feature 1: Parameter Payloads

**As a developer**, I want to create a notification with arbitrary payload fields, so I can carry caller-supplied data into every delivery path.

**Expected Behavior / Usage:**

The adapter accepts a JSON command with payload fields. It must construct a notification request and print the number of payload entries plus each normalized key/value pair that remains available to delivery code.

**Test Cases:** `rcb_tests/public_test_cases/feature1_parameter_payloads.json`

```json
{
    "description": "Notification instances preserve supplied payload fields for delivery.",
    "cases": [
        {
            "input": {
                "command": "notification_params",
                "params": {
                    "foo": "bar"
                }
            },
            "expected_output": "param_count=1\nparam_foo=bar\n"
        }
    ]
}
```

---

### Feature 2: Configuration and Payload Validation

**As a developer**, I want to receive normalized validation failures, so I can detect missing required inputs without exposing runtime-specific exceptions.

**Expected Behavior / Usage:**

The adapter must validate required payload fields and delivery-channel options before executing delivery. Validation failures print `error=validation` and a language-neutral `message` field such as a missing parameter or missing option.

**Test Cases:** `rcb_tests/public_test_cases/feature2_validation_errors.json`

```json
{
    "description": "Required payload fields and delivery options are validated before delivery.",
    "cases": [
        {
            "input": {
                "command": "required_param"
            },
            "expected_output": "error=validation\nmessage=missing_param=user_id\n"
        }
    ]
}
```

---

### Feature 3: Immediate Multi-Channel Delivery

**As a developer**, I want to send a notification immediately, so I can persist records and invoke immediate channels in one operation.

**Expected Behavior / Usage:**

The adapter accepts recipients and payload, performs immediate delivery, and prints framework-observable effects: recipient result kind, number of records created, number of test deliveries, last persisted record metadata, and whether the delivered in-memory notification was linked to the persisted record and recipient.

**Test Cases:** `rcb_tests/public_test_cases/feature3_immediate_delivery.json`

```json
{
    "description": "Immediate delivery creates records and invokes non-database channels for recipients.",
    "cases": [
        {
            "input": {
                "command": "deliver_now",
                "recipients": "first",
                "params": {
                    "foo": "bar"
                }
            },
            "expected_output": "result_kind=recipient_results\nrecords_created=1\ntest_deliveries=1\nlast_record_type=notification\nlast_recipient_email=first@example.com\nlast_param_foo=bar\ndelivered_record_matches=true\ndelivered_recipient_email=first@example.com\n"
        }
    ]
}
```

---

### Feature 4: Queued and Delayed Delivery

**As a developer**, I want to schedule notification work, so I can defer channel execution while preserving queues and run times.

**Expected Behavior / Usage:**

The adapter schedules delivery jobs and prints the number of enqueued jobs, each channel identifier, queue name, scheduled timestamp when delayed, and the number of records created synchronously. Database persistence happens immediately before queued non-database channels when a database channel is present.

**Test Cases:** `rcb_tests/public_test_cases/feature4_async_scheduling.json`

```json
{
    "description": "Queued delivery records job count, queue names, and scheduled timestamps.",
    "cases": [
        {
            "input": {
                "command": "deliver_later",
                "kind": "default"
            },
            "expected_output": "enqueued_jobs=2\njob_0_channel=test\njob_0_queue=default\njob_1_channel=realtime\njob_1_queue=default\nrecords_created=1\n"
        }
    ]
}
```

---

### Feature 5: Conditional Channel Execution

**As a developer**, I want to attach predicates to delivery channels, so I can skip channels when business conditions say not to send.

**Expected Behavior / Usage:**

The adapter runs condition-controlled delivery and prints the number of channel deliveries. Positive predicates deliver only when true, negative predicates deliver only when false, and predicates can access the current recipient.

**Test Cases:** `rcb_tests/public_test_cases/feature5_conditional_delivery.json`

```json
{
    "description": "Conditional delivery predicates can suppress or allow channel execution while seeing the recipient.",
    "cases": [
        {
            "input": {
                "command": "conditional_delivery",
                "kind": "if",
                "params": {
                    "enabled": false
                }
            },
            "expected_output": "test_deliveries=0\n"
        }
    ]
}
```

---

### Feature 6: Delivery Callbacks

**As a developer**, I want to run lifecycle callbacks, so I can observe and extend delivery without changing channel code.

**Expected Behavior / Usage:**

The adapter executes notification-level callbacks around a database delivery and channel-level callbacks around test delivery. It prints ordered callback names or callback count deltas.

**Test Cases:** `rcb_tests/public_test_cases/feature6_callbacks.json`

```json
{
    "description": "Notification and channel callbacks execute around delivery.",
    "cases": [
        {
            "input": {
                "command": "callbacks",
                "kind": "notification"
            },
            "expected_output": "callbacks=before_channel,around_channel,after_channel,after_all\n"
        }
    ]
}
```

---

### Feature 7: Database Persistence

**As a developer**, I want to store notifications as database records, so I can query durable notification state later.

**Expected Behavior / Usage:**

The adapter performs database delivery and prints created-record counts, recipient association counts, payload values, custom stored attributes, returned record kind, and normalized configuration errors for unsupported delayed database delivery.

**Test Cases:** `rcb_tests/public_test_cases/feature7_database_delivery.json`

```json
{
    "description": "Database delivery persists notification records with payload and returns created records.",
    "cases": [
        {
            "input": {
                "command": "database_delivery",
                "kind": "default"
            },
            "expected_output": "records_created=1\nrecipient_records_created=1\nlast_param_foo=bar\n"
        }
    ]
}
```

---

### Feature 8: Read State Management

**As a developer**, I want to mark stored notifications read or unread, so I can maintain unread counts for notification UIs.

**Expected Behavior / Usage:**

The adapter creates a stored notification, optionally marks it read, applies a bulk read-state operation, and prints initial state, final state, read count, and unread count.

**Test Cases:** `rcb_tests/public_test_cases/feature8_read_state.json`

```json
{
    "description": "Stored notifications expose read and unread state transitions and scopes.",
    "cases": [
        {
            "input": {
                "command": "notification_read_state",
                "read_initial": false,
                "operation": "mark_all_read"
            },
            "expected_output": "initial_read=false\nfinal_read=true\nread_count=1\nunread_count=0\n"
        }
    ]
}
```

---

### Feature 9: Record-Based Notification Associations

**As a developer**, I want to find notifications that reference an application record, so I can clean up dependent notifications consistently.

**Expected Behavior / Usage:**

The adapter stores notifications whose payload references an application record and prints association count deltas for default and custom reference names. It also prints whether deleting the referenced record removes matching notifications when cleanup is enabled or leaves them when cleanup is disabled.

**Test Cases:** `rcb_tests/public_test_cases/feature9_record_associations.json`

```json
{
    "description": "Application records can query and clean up notifications that reference them in payload params.",
    "cases": [
        {
            "input": {
                "command": "notification_association",
                "kind": "default_association"
            },
            "expected_output": "association_count_delta=1\n"
        }
    ]
}
```

---

### Feature 10: Payload Serialization

**As a developer**, I want to round-trip application records inside payloads, so I can support durable payload storage across column formats.

**Expected Behavior / Usage:**

The adapter stores an application record reference in payload data for text, JSON, and JSON-like column formats, reloads it, and prints the storage kind, restored record email, and coder category.

**Test Cases:** `rcb_tests/public_test_cases/feature10_payload_serialization.json`

```json
{
    "description": "Payload serialization round-trips application records across supported column storage types.",
    "cases": [
        {
            "input": {
                "command": "param_serialization",
                "model": "text"
            },
            "expected_output": "column_kind=text\nroundtrip_user_email=first@example.com\ncoder_kind=text\n"
        }
    ]
}
```

---

### Feature 11: Email Delivery

**As a developer**, I want to send or enqueue email notifications, so I can integrate notification delivery with an email subsystem.

**Expected Behavior / Usage:**

The adapter sends email immediately, returns a mail-message result from direct channel execution, enqueues mail when configured, and normalizes missing mailer configuration errors. Output includes email counts, message kind, recipient email, and queued email counts.

**Test Cases:** `rcb_tests/public_test_cases/feature11_email_delivery.json`

```json
{
    "description": "Email channel sends immediately, can enqueue mail, validates configuration, and returns mail messages.",
    "cases": [
        {
            "input": {
                "command": "email_delivery",
                "kind": "send"
            },
            "expected_output": "emails_sent=1\nemail_kind=mail_message\nrecipient_email=first@example.com\n"
        }
    ]
}
```

---

### Feature 12: Realtime Broadcast Delivery

**As a developer**, I want to broadcast notification payloads to realtime subscribers, so I can update clients without polling.

**Expected Behavior / Usage:**

The adapter broadcasts a payload to a recipient-specific realtime channel and prints the broadcast channel, count delta, and payload field. It also resolves channel selectors supplied as text, object, or callback and reports a normalized realtime channel kind.

**Test Cases:** `rcb_tests/public_test_cases/feature12_websocket_delivery.json`

```json
{
    "description": "Realtime channel broadcasts payloads and resolves channel selectors.",
    "cases": [
        {
            "input": {
                "command": "websocket_delivery",
                "kind": "broadcast"
            },
            "expected_output": "[a base64-encoded normalized resource ID]\nbroadcast_count_delta=1\nlast_payload_foo=bar\n"
        }
    ]
}
```

---

### Feature 13: HTTP Webhook and SMS Delivery

**As a developer**, I want to send notification payloads through HTTP integrations, so I can connect notifications to chat and SMS services.

**Expected Behavior / Usage:**

The adapter stubs outbound POST requests for supported HTTP services. For successful responses it prints request host, status, response body, and debug logs when enabled. For failed responses it prints a normalized HTTP failure with status and response body.

**Test Cases:** `rcb_tests/public_test_cases/feature13_http_delivery.json`

```json
{
    "description": "Webhook and SMS HTTP channels send POST requests, expose responses, log debug output, and normalize failures.",
    "cases": [
        {
            "input": {
                "command": "http_delivery",
                "service": "slack",
                "outcome": "success"
            },
            "expected_output": "[the standard webhooks endpoint hosted by the messaging service]\nstatus=200\nresponse_body=ok\n"
        }
    ]
}
```

---

### Feature 14: Mobile Push Helpers

**As a developer**, I want to resolve push credentials and message payloads, so I can send platform push notifications with validated setup.

**Expected Behavior / Usage:**

The adapter resolves push credentials from hash, file path, string path, or callback, extracts project IDs and access tokens, formats a device-token message, and prints normalized iOS configuration or missing-callback errors.

**Test Cases:** `rcb_tests/public_test_cases/feature14_push_delivery_helpers.json`

```json
{
    "description": "Mobile push helpers resolve credentials, tokens, message payloads, and configuration errors.",
    "cases": [
        {
            "input": {
                "command": "push_credentials",
                "kind": "hash"
            },
            "expected_output": "credential_keys=foo\nfoo=bar\n"
        }
    ]
}
```

---

### Feature 15: Localized Notification Text

**As a developer**, I want to look up notification text by key and scope, so I can keep notification copy in translation files.

**Expected Behavior / Usage:**

The adapter resolves plain translation keys, namespace-scoped keys, custom-scope keys, and HTML-safe translations. It prints the lookup key or rendered message and whether HTML safety is preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature15_translations.json`

```json
{
    "description": "Notification text lookup supports plain keys, scoped keys, custom scopes, and HTML-safe values.",
    "cases": [
        {
            "input": {
                "command": "translation",
                "kind": "plain"
            },
            "expected_output": "lookup_key=hello\nmessage=Hello world\n"
        }
    ]
}
```

---

### Feature 16: Persistence Model Generator

**As a developer**, I want to generate persistence model artifacts, so I can bootstrap storage setup quickly.

**Expected Behavior / Usage:**

The adapter runs the generator for a notification storage model and prints whether the model file exists and how many matching migration files were created.

**Test Cases:** `rcb_tests/public_test_cases/feature16_model_generator.json`

```json
{
    "description": "The model generator creates a notification model file and matching migration.",
    "cases": [
        {
            "input": {
                "command": "generate_model",
                "name": "TestNotification"
            },
            "expected_output": "model_file_exists=true\n[the default output file artifact from the generator command]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_parameter_payloads.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_parameter_payloads@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- inspect the failed_status_response map
