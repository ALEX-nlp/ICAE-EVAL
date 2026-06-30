## Product Requirement Document

# Structured Log Push Adapter - Batch Encoding and Delivery Contract

## Project Goal

Build a structured log batching and push adapter that allows developers to transform application log events into backend ingest payloads, group records by stream labels, and deliver them over HTTP without manually constructing wire formats, batching queues, or retry behavior.

---

## Background & Problem

Without this library/tool, developers are forced to assemble push-request JSON or binary payloads by hand, calculate unique timestamps, split labels, maintain byte-bounded queues, and implement HTTP retry semantics themselves. This leads to repetitive code, broken escaping, inconsistent stream grouping, out-of-order timestamps, and fragile delivery behavior.

With this library/tool, an application can provide log event data and configuration, then receive deterministic payloads and delivery behavior that match the ingest API contract.

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

### Feature 1: Push Payload Serialization

**As a developer**, I want to serialize buffered log records into backend push payloads, so I can send batches in the formats accepted by the ingest API.

**Expected Behavior / Usage:**

*1.1 Push Payload Serialization capabilities — This feature area is split into leaf behaviors below; each leaf block contains its own complete input/output contract.*

*1.1 JSON push payloads — The adapter accepts a JSON command containing an ordered list of records.*

The adapter accepts a JSON command containing an ordered list of records. Each record supplies a millisecond timestamp, nanosecond suffix, ordered labels, and a message line. The output is exactly the JSON push request body: records sharing the same label set are grouped into one stream, timestamps are rendered as a single nanosecond timestamp string, and message text is JSON escaped without altering the original content.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_json_push_payload.json`

```json
{
    "description": "Serializes log records into the JSON push wire format, grouping records by equal label sets and preserving each record timestamp and line.",
    "cases": [
        {
            "input": {
                "operation": "json_batch",
                "capacity": 1000,
                "records": [
                    {
                        "timestamp_ms": 3000,
                        "nanos": 1,
                        "labels": {
                            "level": "DEBUG",
                            "app": "my-app"
                        },
                        "message": "l=DEBUG c=test.TestApp t=thread-2 | Test message 2"
                    },
                    {
                        "timestamp_ms": 1000,
                        "nanos": 2,
                        "labels": {
                            "level": "INFO",
                            "app": "my-app"
                        },
                        "message": "l=INFO c=test.TestApp t=thread-1 | Test message 1"
                    },
                    {
                        "timestamp_ms": 2000,
                        "nanos": 3,
                        "labels": {
                            "level": "INFO",
                            "app": "my-app"
                        },
                        "message": "l=INFO c=test.TestApp t=thread-3 | Test message 4"
                    },
                    {
                        "timestamp_ms": 5000,
                        "nanos": 4,
                        "labels": {
                            "level": "INFO",
                            "app": "my-app"
                        },
                        "message": "l=INFO c=test.TestApp t=thread-1 | Test message 3"
                    }
                ]
            },
            "expected_output": "{\"streams\":[{\"stream\":{\"level\":\"DEBUG\",\"app\":\"my-app\"},\"values\":[[\"3000000001\",\"l=DEBUG c=test.TestApp t=thread-2 | Test message 2\"]]},{\"stream\":{\"level\":\"INFO\",\"app\":\"my-app\"},\"values\":[[\"1000000002\",\"l=INFO c=test.TestApp t=thread-1 | Test message 1\"],[\"2000000003\",\"l=INFO c=test.TestApp t=thread-3 | Test message 4\"],[\"5000000004\",\"l=INFO c=test.TestApp t=thread-1 | Test message 3\"]]}]}"
        },
        {
            "input": {
                "operation": "json_batch",
                "capacity": 1000,
                "records": [
                    {
                        "timestamp_ms": 100,
                        "nanos": 0,
                        "labels": {
                            "level": "INFO",
                            "app": "my-app"
                        },
                        "message": "l=INFO c=test.TestApp t=thread-1 | Test message"
                    }
                ]
            },
            "expected_output": "{\"streams\":[{\"stream\":{\"level\":\"INFO\",\"app\":\"my-app\"},\"values\":[[\"100000000\",\"l=INFO c=test.TestApp t=thread-1 | Test message\"]]}]}"
        }
    ]
}
```

---

*1.2 Binary push payloads — The adapter accepts the same record list plus a buffer mode flag.*

The adapter accepts the same record list plus a buffer mode flag. It must produce a compressed binary push request; for the contract the adapter decodes that binary payload back into neutral text lines showing each stream label block and each timestamp/line entry. On-heap and off-heap buffer choices must not change the decoded payload.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_protobuf_push_payload.json`

```json
{
    "description": "Serializes log records into the compressed binary push format; when decoded, the payload contains the same stream labels, timestamps, and lines.",
    "cases": [
        {
            "input": {
                "operation": "protobuf_batch",
                "capacity": 1000,
                "direct_buffer": false,
                "records": [
                    {
                        "timestamp_ms": 3000,
                        "nanos": 1,
                        "labels": {
                            "level": "DEBUG",
                            "app": "my-app"
                        },
                        "message": "l=DEBUG c=test.TestApp t=thread-2 | Test message 2"
                    },
                    {
                        "timestamp_ms": 1000,
                        "nanos": 2,
                        "labels": {
                            "level": "INFO",
                            "app": "my-app"
                        },
                        "message": "l=INFO c=test.TestApp t=thread-1 | Test message 1"
                    },
                    {
                        "timestamp_ms": 2000,
                        "nanos": 3,
                        "labels": {
                            "level": "INFO",
                            "app": "my-app"
                        },
                        "message": "l=INFO c=test.TestApp t=thread-3 | Test message 4"
                    },
                    {
                        "timestamp_ms": 5000,
                        "nanos": 4,
                        "labels": {
                            "level": "INFO",
                            "app": "my-app"
                        },
                        "message": "l=INFO c=test.TestApp t=thread-1 | Test message 3"
                    }
                ]
            },
            "expected_output": "stream={level=\"DEBUG\",app=\"my-app\"}\ntimestamp=3.1 line=l=DEBUG c=test.TestApp t=thread-2 | Test message 2\nstream={level=\"INFO\",app=\"my-app\"}\ntimestamp=1.2 line=l=INFO c=test.TestApp t=thread-1 | Test message 1\ntimestamp=2.3 line=l=INFO c=test.TestApp t=thread-3 | Test message 4\ntimestamp=5.4 line=l=INFO c=test.TestApp t=thread-1 | Test message 3\n"
        }
    ]
}
```

---


### Feature 2: Label Extraction and Stream Identity

**As a developer**, I want to derive stream labels from rendered event metadata, so I can group records consistently while allowing per-event labels.

**Expected Behavior / Usage:**

*2.1 Label Extraction and Stream Identity capabilities — This feature area is split into leaf behaviors below; each leaf block contains its own complete input/output contract.*

*2.1 Rendered label pair parsing — The adapter accepts rendered label text and separator settings.*

The adapter accepts rendered label text and separator settings. Literal separators split key/value pairs directly, regex separators remove comment and newline sections, and blank pair segments are ignored. Output is one line per label in extraction order using `label=<name> value=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_label_pair_parsing.json`

```json
{
    "description": "Parses rendered label text into ordered key/value fields, honoring configured separators, regex separators, and empty segments.",
    "cases": [
        {
            "input": {
                "operation": "label_pairs",
                "pattern": "level=%level,app=\"my\"app",
                "pair_separator": ",",
                "key_value_separator": "=",
                "rendered_labels": "level=INFO,app=\"my\"app,test=test"
            },
            "expected_output": "label=level value=INFO\nlabel=app value=\"my\"app\nlabel=test value=test\n"
        },
        {
            "input": {
                "operation": "label_pairs",
                "pattern": ",,level=%level,,app=\"my\"app,",
                "pair_separator": ",",
                "key_value_separator": "=",
                "rendered_labels": ",,level=INFO,,app=\"my\"app,test=test,"
            },
            "expected_output": "label=level value=INFO\nlabel=app value=\"my\"app\nlabel=test value=test\n"
        },
        {
            "input": {
                "operation": "label_pairs",
                "pattern": "\n\n// level is label\nlevel=%level\n// another comment\n\napp=\"my\"app\n\n// end comment",
                "pair_separator": "regex:(\n|//[^\n]+)+",
                "key_value_separator": "=",
                "rendered_labels": "\n\n// level is label\nlevel=INFO\n// another comment\n\napp=\"my\"app\n\n// end comment"
            },
            "expected_output": "label=level value=INFO\nlabel=app value=\"my\"app\n"
        }
    ]
}
```

---

*2.2 Malformed label pair reporting — When rendered label text contains a segment that cannot be split into exactly one key and one value with the configured separators, output a normalized domain error.*

When rendered label text contains a segment that cannot be split into exactly one key and one value with the configured separators, output a normalized domain error. The output must contain `error=invalid_label_pair` and the raw rendered label text, with no host-language exception class or runtime wording.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_invalid_label_pair_errors.json`

```json
{
    "description": "Reports malformed rendered label text as a normalized label-pair error without exposing host-language exception names.",
    "cases": [
        {
            "input": {
                "operation": "label_pairs",
                "pattern": "level=%level,app=\"my\"app",
                "pair_separator": "|",
                "key_value_separator": "~",
                "rendered_labels": "level=INFO,app=\"my\"app,test=test"
            },
            "expected_output": "error=invalid_label_pair\nrendered_labels=level=INFO,app=\"my\"app,test=test\n"
        }
    ]
}
```

---

*2.3 Marker-provided labels — The adapter accepts events that may include additional per-event label maps.*

The adapter accepts events that may include additional per-event label maps. When marker labels are present, they are appended to the event stream identity, so records with different marker labels are emitted under separate streams even when their base labels match.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_marker_labels.json`

```json
{
    "description": "Adds per-event marker label fields to the rendered stream so records with different marker labels are grouped separately.",
    "cases": [
        {
            "input": {
                "operation": "marker_labels",
                "events": [
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 1",
                        "marker_labels": {
                            "stcmrk": "stat-val"
                        }
                    },
                    {
                        "timestamp_ms": 103,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 2",
                        "marker_labels": {
                            "mrk": "mrk-val"
                        }
                    },
                    {
                        "timestamp_ms": 105,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 3",
                        "marker_labels": {
                            "stcmrk": "stat-val"
                        }
                    },
                    {
                        "timestamp_ms": 104,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 4",
                        "marker_labels": {
                            "mrk1": "v1",
                            "mrk2": "v2"
                        }
                    }
                ]
            },
            "expected_output": "stream=[l, INFO, mrk, mrk-val]\nrecord=ts=103 INFO | Test message 2\nstream=[l, INFO, stcmrk, stat-val]\nrecord=ts=100 INFO | Test message 1\nrecord=ts=105 INFO | Test message 3\nstream=[l, INFO, mrk1, v1, mrk2, v2]\nrecord=ts=104 INFO | Test message 4\n"
        }
    ]
}
```

---


### Feature 3: Timestamp Ordering Helpers

**As a developer**, I want to derive nanosecond suffixes for millisecond timestamps, so I can avoid duplicate or out-of-order ingest timestamps.

**Expected Behavior / Usage:**

*3.1 Timestamp Ordering Helpers capabilities — This feature area is split into leaf behaviors below; each leaf block contains its own complete input/output contract.*

*3.1 Nanosecond suffix assignment — The adapter accepts a sequence of millisecond timestamps and outputs the nanosecond suffix assigned to each one.*

The adapter accepts a sequence of millisecond timestamps and outputs the nanosecond suffix assigned to each one. Repeated events in the same millisecond increment the suffix, older timestamps are clamped to that millisecond’s final suffix, and more than one thousand events in one millisecond keep using the maximum suffix.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_timestamp_nanos.json`

```json
{
    "description": "Assigns a nanosecond suffix inside each millisecond to preserve event ordering and clamps older or overflowed events to the last suffix for that millisecond.",
    "cases": [
        {
            "input": {
                "operation": "nano_sequence",
                "timestamps_ms": [
                    1123,
                    1123,
                    1123,
                    1123,
                    1122,
                    1124
                ]
            },
            "expected_output": "timestamp_ms=1123 nanos=123000\ntimestamp_ms=1123 nanos=123001\ntimestamp_ms=1123 nanos=123002\ntimestamp_ms=1123 nanos=123003\ntimestamp_ms=1122 nanos=122999\ntimestamp_ms=1124 nanos=124000\n"
        }
    ]
}
```

---


### Feature 4: Appender Batching and Encoding

**As a developer**, I want to buffer application events and flush payloads predictably, so I can send efficient batches without losing valid records.

**Expected Behavior / Usage:**

*4.1 Appender Batching and Encoding capabilities — This feature area is split into leaf behaviors below; each leaf block contains its own complete input/output contract.*

*4.1 Item-count flush — The adapter accepts a batch item threshold and a list of log events.*

The adapter accepts a batch item threshold and a list of log events. It must report that no payload was sent before the final event that reaches the threshold, then print the emitted streams and records from the flushed payload.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_batch_size_flush.json`

```json
{
    "description": "Buffers appended log events until the configured item threshold is reached, then sends one grouped payload.",
    "cases": [
        {
            "input": {
                "operation": "append_batching",
                "batch_max_items": 3,
                "batch_timeout_ms": 1000,
                "events": [
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 1"
                    },
                    {
                        "timestamp_ms": 104,
                        "level": "WARN",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 2"
                    },
                    {
                        "timestamp_ms": 107,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 3"
                    }
                ]
            },
            "expected_output": "sent_before_threshold=false\nstream=[level, INFO, app, my-app]\nrecord=ts=100 l=INFO c=test.TestApp t=thread-1 | Test message 1 \nrecord=ts=107 l=INFO c=test.TestApp t=thread-1 | Test message 3 \nstream=[level, WARN, app, my-app]\nrecord=ts=104 l=WARN c=test.TestApp t=thread-2 | Test message 2 \n"
        }
    ]
}
```

---

*4.2 Batch ordering and static label mode — The adapter accepts events plus two booleans: whether records are sorted by timestamp before output and whether stream labels are evaluated once for the whole batch.*

The adapter accepts events plus two booleans: whether records are sorted by timestamp before output and whether stream labels are evaluated once for the whole batch. Static labels place every record in the first stream; dynamic labels group records by each event’s rendered label value. Sorting changes record order within each stream but not the record content.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_batch_ordering.json`

```json
{
    "description": "Controls whether records are emitted in arrival order or sorted by timestamp, and whether labels are evaluated once for the batch or per event.",
    "cases": [
        {
            "input": {
                "operation": "append_ordering",
                "sort_by_time": false,
                "static_labels": true,
                "events": [
                    {
                        "timestamp_ms": 105,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 1"
                    },
                    {
                        "timestamp_ms": 103,
                        "level": "DEBUG",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 2"
                    },
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 3"
                    },
                    {
                        "timestamp_ms": 104,
                        "level": "WARN",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 4"
                    },
                    {
                        "timestamp_ms": 103,
                        "level": "ERROR",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 5"
                    },
                    {
                        "timestamp_ms": 110,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 6"
                    }
                ]
            },
            "expected_output": "stream=[l, INFO]\nrecord=ts=105 INFO | Test message 1\nrecord=ts=103 DEBUG | Test message 2\nrecord=ts=100 INFO | Test message 3\nrecord=ts=104 WARN | Test message 4\nrecord=ts=103 ERROR | Test message 5\nrecord=ts=110 INFO | Test message 6\n"
        },
        {
            "input": {
                "operation": "append_ordering",
                "sort_by_time": true,
                "static_labels": true,
                "events": [
                    {
                        "timestamp_ms": 105,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 1"
                    },
                    {
                        "timestamp_ms": 103,
                        "level": "DEBUG",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 2"
                    },
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 3"
                    },
                    {
                        "timestamp_ms": 104,
                        "level": "WARN",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 4"
                    },
                    {
                        "timestamp_ms": 103,
                        "level": "ERROR",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 5"
                    },
                    {
                        "timestamp_ms": 110,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 6"
                    }
                ]
            },
            "expected_output": "stream=[l, INFO]\nrecord=ts=100 INFO | Test message 3\nrecord=ts=103 DEBUG | Test message 2\nrecord=ts=103 ERROR | Test message 5\nrecord=ts=104 WARN | Test message 4\nrecord=ts=105 INFO | Test message 1\nrecord=ts=110 INFO | Test message 6\n"
        }
    ]
}
```

---

*4.3 JSON message escaping — The adapter accepts events whose messages contain carriage returns and line feeds, encodes them as a JSON push payload, and prints the raw JSON body.*

The adapter accepts events whose messages contain carriage returns and line feeds, encodes them as a JSON push payload, and prints the raw JSON body. Control characters inside messages must be escaped as JSON string escapes rather than becoming literal line breaks in the payload.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_json_message_escaping.json`

```json
{
    "description": "Preserves carriage returns, line feeds, tabs, and other special characters by escaping them inside JSON payload strings.",
    "cases": [
        {
            "input": {
                "operation": "json_escape_batch",
                "test_label": "testEncodeEscapes",
                "events": [
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "TestApp",
                        "thread": "main",
                        "message": "m1-line1\r\nline2\r\n"
                    },
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "TestApp",
                        "thread": "main",
                        "message": "m2-line1\nline2\n"
                    },
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "TestApp",
                        "thread": "main",
                        "message": "m3-line1\rline2\r"
                    }
                ]
            },
            "expected_output": "{\"streams\":[{\"stream\":{\"test\":\"testEncodeEscapes\",\"level\":\"INFO\",\"app\":\"my-app\"},\"values\":[[\"100100000\",\"l=INFO c=TestApp t=main | m1-line1\\r\\nline2\\r\\n \"],[\"100100001\",\"l=INFO c=TestApp t=main | m2-line1\\nline2\\n \"],[\"100100002\",\"l=INFO c=TestApp t=main | m3-line1\\rline2\\r \"]]}]}"
        }
    ]
}
```

---

*4.4 Oversized event dropping — The adapter accepts a maximum batch byte size and a sequence containing one event that is too large.*

The adapter accepts a maximum batch byte size and a sequence containing one event that is too large. The oversized event is omitted from the emitted payload, while valid events before and after it remain present and grouped normally.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_oversized_event_drop.json`

```json
{
    "description": "Drops an event whose encoded size exceeds the configured batch byte limit while preserving subsequent valid events in the sent payload.",
    "cases": [
        {
            "input": {
                "operation": "drop_large_event",
                "batch_max_items": 3,
                "batch_max_bytes": 500,
                "events": [
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 1"
                    },
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "TestApp",
                        "thread": "main",
                        "message": "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                    },
                    {
                        "timestamp_ms": 104,
                        "level": "WARN",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 2"
                    },
                    {
                        "timestamp_ms": 107,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 3"
                    }
                ]
            },
            "expected_output": "stream=[level, INFO, app, my-app]\nrecord=ts=100 l=INFO c=test.TestApp t=thread-1 | Test message 1 \nrecord=ts=107 l=INFO c=test.TestApp t=thread-1 | Test message 3 \nstream=[level, WARN, app, my-app]\nrecord=ts=104 l=WARN c=test.TestApp t=thread-2 | Test message 2 \n"
        }
    ]
}
```

---


### Feature 5: HTTP Delivery and Retry

**As a developer**, I want to deliver encoded payloads through an HTTP push endpoint, so I can integrate with a real ingest endpoint and transient failures.

**Expected Behavior / Usage:**

*5.1 HTTP Delivery and Retry capabilities — This feature area is split into leaf behaviors below; each leaf block contains its own complete input/output contract.*

*5.1 HTTP push delivery — The adapter starts a real HTTP push endpoint, sends a flushed payload to `/loki/api/v1/push`, and prints observable request signals: status code, request path, optional tenant header, then the decoded payload body.*

The adapter starts a real HTTP push endpoint, sends a flushed payload to `/loki/api/v1/push`, and prints observable request signals: status code, request path, optional tenant header, then the decoded payload body. Different supported HTTP client and buffer modes must preserve these signals.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_http_delivery.json`

```json
{
    "description": "Sends a flushed payload to the configured HTTP push endpoint and preserves the request path, success status, optional tenant header, and payload body.",
    "cases": [
        {
            "input": {
                "operation": "http_send",
                "client": "java",
                "direct_buffer": true,
                "tenant": "tenant1",
                "events": [
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 1"
                    },
                    {
                        "timestamp_ms": 104,
                        "level": "WARN",
                        "logger": "test.TestApp",
                        "thread": "thread-2",
                        "message": "Test message 2"
                    },
                    {
                        "timestamp_ms": 107,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 3"
                    }
                ]
            },
            "expected_output": "http_status=204\nrequest_path=/loki/api/v1/push\ntenant_header=tenant1\nstream=[level, INFO, app, my-app]\nrecord=ts=100 l=INFO c=test.TestApp t=thread-1 | Test message 1 \nrecord=ts=107 l=INFO c=test.TestApp t=thread-1 | Test message 3 \nstream=[level, WARN, app, my-app]\nrecord=ts=104 l=WARN c=test.TestApp t=thread-2 | Test message 2 \n"
        }
    ]
}
```

---

*5.2 Retry and rate-limit policy — The adapter accepts a failure mode, retry delay behavior, and an optional setting to drop rate-limited batches.*

The adapter accepts a failure mode, retry delay behavior, and an optional setting to drop rate-limited batches. It prints how many send attempts occurred and the payload that was attempted. Connection failures and retryable rate limits are retried; configured rate-limit dropping prevents retries after the first attempt.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_retry_policy.json`

```json
{
    "description": "Retries failed sends after the configured retry delay, except rate-limited responses when configured to drop those batches.",
    "cases": [
        {
            "input": {
                "operation": "retry_policy",
                "failure": "connection",
                "drop_rate_limited": false,
                "wait_ms": 520,
                "events": [
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 1"
                    }
                ]
            },
            "expected_output": "send_attempts=3\nstream=[level, INFO, app, my-app]\nrecord=ts=100 l=INFO c=test.TestApp t=thread-1 | Test message 1 \n"
        },
        {
            "input": {
                "operation": "retry_policy",
                "failure": "rate_limited",
                "drop_rate_limited": false,
                "wait_ms": 520,
                "events": [
                    {
                        "timestamp_ms": 100,
                        "level": "INFO",
                        "logger": "test.TestApp",
                        "thread": "thread-1",
                        "message": "Test message 1"
                    }
                ]
            },
            "expected_output": "send_attempts=3\nstream=[level, INFO, app, my-app]\nrecord=ts=100 l=INFO c=test.TestApp t=thread-1 | Test message 1 \n"
        }
    ]
}
```

---


### Feature 6: Binary Send Queue

**As a developer**, I want to manage queued encoded batches under byte pressure, so I can bound memory use while preserving FIFO delivery.

**Expected Behavior / Usage:**

*6.1 Binary Send Queue capabilities — This feature area is split into leaf behaviors below; each leaf block contains its own complete input/output contract.*

*6.1 Queue capacity enforcement — The adapter accepts a maximum queued byte count and a sequence of offer and borrow operations.*

The adapter accepts a maximum queued byte count and a sequence of offer and borrow operations. Offers that would exceed the byte limit return `accepted=false`; borrowing a batch returns its id, item count, byte count, data bytes, and reduces queued bytes so later offers may succeed.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_byte_queue_capacity.json`

```json
{
    "description": "Accepts binary batches while the total queued bytes stay within the configured limit, rejects batches that would exceed it, and releases capacity when a batch is borrowed.",
    "cases": [
        {
            "input": {
                "operation": "byte_queue",
                "max_bytes": 10,
                "operations": [
                    {
                        "action": "offer",
                        "batch_id": 0,
                        "items": 1,
                        "data": [
                            0,
                            1,
                            2,
                            3
                        ]
                    },
                    {
                        "action": "offer",
                        "batch_id": 1,
                        "items": 1,
                        "data": [
                            4,
                            5,
                            6,
                            7
                        ]
                    },
                    {
                        "action": "offer",
                        "batch_id": 2,
                        "items": 1,
                        "data": [
                            8,
                            9,
                            10,
                            11
                        ]
                    },
                    {
                        "action": "borrow",
                        "return": true
                    },
                    {
                        "action": "offer",
                        "batch_id": 2,
                        "items": 1,
                        "data": [
                            8,
                            9,
                            10,
                            11
                        ]
                    },
                    {
                        "action": "borrow",
                        "return": true
                    },
                    {
                        "action": "borrow",
                        "return": true
                    }
                ]
            },
            "expected_output": "offer batch_id=0 accepted=true queued_bytes=4\noffer batch_id=1 accepted=true queued_bytes=8\noffer batch_id=2 accepted=false queued_bytes=8\nborrow batch_id=0 items=1 bytes=4 data=[0,1,2,3] queued_bytes=4\noffer batch_id=2 accepted=true queued_bytes=8\nborrow batch_id=1 items=1 bytes=4 data=[4,5,6,7] queued_bytes=4\nborrow batch_id=2 items=1 bytes=4 data=[8,9,10,11] queued_bytes=0\n"
        }
    ]
}
```

---

*6.2 Borrowed buffer reuse — The adapter accepts queue operations that borrow and return buffers.*

The adapter accepts queue operations that borrow and return buffers. Returned buffers are kept in a one-item reusable pool, and a later compatible offer consumes that pooled buffer; output includes pool size after requested checkpoints.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_byte_queue_reuse.json`

```json
{
    "description": "Returns borrowed binary buffers to an internal reusable pool and reuses a pooled buffer for a later compatible batch.",
    "cases": [
        {
            "input": {
                "operation": "byte_queue",
                "max_bytes": 10,
                "operations": [
                    {
                        "action": "borrow"
                    },
                    {
                        "action": "pool"
                    },
                    {
                        "action": "offer",
                        "batch_id": 0,
                        "items": 1,
                        "data": [
                            0,
                            1,
                            2,
                            3
                        ]
                    },
                    {
                        "action": "offer",
                        "batch_id": 1,
                        "items": 1,
                        "data": [
                            4,
                            5,
                            6,
                            7
                        ]
                    },
                    {
                        "action": "pool"
                    },
                    {
                        "action": "borrow",
                        "return": true
                    },
                    {
                        "action": "pool"
                    },
                    {
                        "action": "borrow",
                        "return": true
                    },
                    {
                        "action": "pool"
                    },
                    {
                        "action": "offer",
                        "batch_id": 2,
                        "items": 1,
                        "data": [
                            0,
                            1,
                            2,
                            3,
                            4,
                            5,
                            6,
                            7
                        ]
                    },
                    {
                        "action": "pool"
                    }
                ]
            },
            "expected_output": "borrow empty=true queued_bytes=0\npool_size=0\noffer batch_id=0 accepted=true queued_bytes=4\noffer batch_id=1 accepted=true queued_bytes=8\npool_size=0\nborrow batch_id=0 items=1 bytes=4 data=[0,1,2,3] queued_bytes=4\npool_size=1\nborrow batch_id=1 items=1 bytes=4 data=[4,5,6,7] queued_bytes=0\npool_size=1\noffer batch_id=2 accepted=true queued_bytes=8\npool_size=0\n"
        }
    ]
}
```

---


### Feature 7: String Utility Behavior

**As a developer**, I want to measure and classify text consistently, so I can support byte-size limits and blank-value handling.

**Expected Behavior / Usage:**

*7.1 String Utility Behavior capabilities — This feature area is split into leaf behaviors below; each leaf block contains its own complete input/output contract.*

*7.1 UTF-8 length and blank checks — The adapter accepts either text values for UTF-8 byte-length measurement or nullable values for blank classification.*

The adapter accepts either text values for UTF-8 byte-length measurement or nullable values for blank classification. It prints byte counts for each text sample and treats null, empty, and whitespace-only values as blank while non-whitespace values are not blank.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_string_utilities.json`

```json
{
    "description": "Computes UTF-8 byte length for text and classifies null, empty, and whitespace-only values as blank.",
    "cases": [
        {
            "input": {
                "operation": "utf8_lengths",
                "strings": [
                    "A",
                    "é",
                    "🏁",
                    "спец"
                ]
            },
            "expected_output": "text=A utf8_bytes=1\ntext=é utf8_bytes=2\ntext=🏁 utf8_bytes=4\ntext=спец utf8_bytes=8\n"
        },
        {
            "input": {
                "operation": "blank_checks",
                "values": [
                    null,
                    "",
                    "    \t\t\n ",
                    "0",
                    "erfqwef9jokfwejfi"
                ]
            },
            "expected_output": "value=<null> blank=true\nvalue= blank=true\nvalue=    \\t\\t\\n  blank=true\nvalue=0 blank=false\nvalue=erfqwef9jokfwejfi blank=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_json_push_payload.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_json_push_payload@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- format the inner arrays using the same timestamp structure as the system.logger module
