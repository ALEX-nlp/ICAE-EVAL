## Product Requirement Document

# Message Broker Tracing Instrumentation — Producer/Consumer Span Contract

## Project Goal

Build a tracing instrumentation layer that transparently wraps a publish/subscribe message broker client (a Kafka-style producer/consumer client) so that every message published and every message consumed automatically produces a structured tracing span, and so that trace context flows from publishers to subscribers through message headers — all without the application author writing any tracing code by hand.

---

## Background & Problem

Without this layer, developers who want end-to-end visibility across an asynchronous messaging system must manually open and close a span around every publish call, manually copy trace identifiers into each outgoing message, and manually re-open the trace on the consuming side by reading those identifiers back out of the message. This is repetitive, easy to get wrong (forgotten spans, leaked error state, broken parent/child links), and couples business code to the tracing system.

With this layer, the producer and consumer factories of the messaging client are patched once at startup. From then on, publishing a message (single, multi-message, or multi-topic batch) emits one span per message; running a consumer handler (per-message or per-batch) emits the appropriate receive/process spans; failures are reflected in span status; optional enrichment callbacks can decorate spans with message-derived data; and trace context plus [a specific baggage key-value relationship — ask the PM for the exact string used in the mock] propagate automatically through the message headers so a consumer span joins the producer's trace.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (client patching, span lifecycle management, context propagation, output rendering, and an execution adapter). It MUST NOT be a single "god file"; use a clear multi-file tree that separates the core instrumentation from the execution/test adapter. Do not over-engineer, but do not collapse distinct responsibilities together.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, not the internal data model of the instrumentation core. The core instrumentation must remain decoupled from stdin/stdout and JSON parsing. The execution adapter alone is responsible for translating JSON scenario commands into idiomatic calls against the messaging client and for rendering resulting spans into the stdout contract.

3. **Adherence to SOLID Design Principles:** Separate scenario parsing, client driving, span collection, error normalization, and output formatting into distinct units. The span lifecycle engine must be open for extension (new operations) but closed for modification. Keep interfaces small and cohesive. High-level rendering must depend on an abstract span shape, not on a concrete I/O implementation.

4. **Robustness & Interface Design:** The public interface of the instrumentation must be idiomatic and hide all span bookkeeping. Edge cases (handler that throws, handler that returns no promise, thrown value with no readable reason, enrichment callback that throws) must be handled gracefully and modeled explicitly. Errors must be surfaced to the caller but, in the stdout contract, normalized to language-neutral category labels — never host-language exception class names or runtime-generated message decorations.

---

## Output Contract (shared by all features)

Every feature is exercised by feeding the execution adapter a single JSON **scenario** on stdin and comparing its stdout. A scenario is `{ "config": {...}, "steps": [...] }`. Each step is one messaging action (`produce`, `produce_batch`, `consume_message`, `consume_batch`). The adapter drives the instrumented client and prints deterministic, identifier-free text:

- One **action line** per step, e.g. `produce topic=<t> status=ok result_records=<n>` (success records are echoed back), `produce topic=<t> status=error error=client_send_failure` (client rejected), or `consume_message topic=<t> delivered=<ok|error> error=<category>`.
- For each message that was handed to the client, one `inject msg=<i> carries=span#<k>` line stating which emitted span's context was stamped into that message's headers (or `<none>`).
- An optional `[a specific baggage key-value relationship — ask the PM for the exact string used in the mock] <k>=<v> ...` line when a consumer handler observed propagated [a specific baggage key-value relationship — ask the PM for the exact string used in the mock].
- A `spans=<n>` count followed by one block per emitted span: `span <i> kind=<producer|consumer> name=<topic> trace=<tLABEL> parent=<root|span#k> status=<unset|error>`, an indented `status_message=<reason|<none>>` line when the status is error, then the span's indented attributes (`messaging.system`, `messaging.destination`, `messaging.destination_kind`, `messaging.operation`, plus any enrichment or version attribute), and an indented `links=span#k,...` line when the span links to other spans.

Trace identifiers are never printed raw; each distinct trace is labelled `t0`, `t1`, … in first-seen order and spans are referenced by their emission index, so the contract captures structure (kind, naming, attributes, status, parent/child, links, trace grouping) without leaking runtime values. Library version values are normalized to the literal token `<version>`.

---

## Core Features

### Feature 1: Producer Span Emission

**As a developer**, I want every published message to automatically produce a tracing span with messaging metadata and an injected trace context, so I can observe my publish path and propagate context downstream without writing tracing code.

**Expected Behavior / Usage:**

*1.1 Single-topic publish — one span per message, result passed through*

Publishing to one topic emits exactly one PRODUCER span per message in the publish, each span named after the topic and carrying `messaging.system=kafka`, `messaging.destination=<topic>`, and `messaging.destination_kind=topic`. The value the underlying client returns from the publish is passed back to the caller unchanged (echoed as `result_records` and per-record fields). Each outgoing message has the trace context of its span injected into its headers, shown as `inject msg=<i> carries=span#<i>`. Each single-message publish starts its own root trace.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_producer_send.json`

```json
{
    "description": "Producing one or more messages to a single topic emits one PRODUCER span per message, each named after the topic and carrying the messaging system/destination attributes; the client send result is passed back unchanged and each outgoing message is stamped with the span trace context.",
    "cases": [
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "testing message content" }],
                        "clientResponse": {
                            "status": "success",
                            "records": [{ "topicName": "topic-name-1", "partition": 0, "offset": "18" }]
                        }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=ok result_records=1\n  record 0 topicName=topic-name-1 partition=0 offset=18\ninject msg=0 carries=span#0\nspans=1\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n"
        },
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "message1" }, { "value": "message2" }],
                        "clientResponse": { "status": "success", "records": [] }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=ok result_records=0\ninject msg=0 carries=span#0\ninject msg=1 carries=span#1\nspans=2\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\nspan 1 kind=producer name=topic-name-1 trace=t1 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n"
        }
    ]
}
```

*1.2 Multi-topic batch publish — one span per message, named by its own topic*

Publishing a batch that groups messages under several topics emits one PRODUCER span per message, in declaration order across the groups, each span named after the topic of its own message. Every message is stamped with its own span context.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_producer_send_batch.json`

```json
{
    "description": "Producing a batch that spans several topics emits one PRODUCER span per message in declaration order, each named after that message’s topic, and stamps every outgoing message with its own span context.",
    "cases": [
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "produce_batch",
                        "topicMessages": [
                            { "topic": "topic-name-1", "messages": [{ "value": "message1-1" }, { "value": "message1-2" }] },
                            { "topic": "topic-name-2", "messages": [{ "value": "message2-1" }] }
                        ],
                        "clientResponse": { "status": "success", "records": [] }
                    }
                ]
            },
            "expected_output": "produce_batch topics=2 status=ok result_records=0\ninject msg=0 carries=span#0\ninject msg=1 carries=span#1\ninject msg=2 carries=span#2\nspans=3\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\nspan 1 kind=producer name=topic-name-1 trace=t1 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\nspan 2 kind=producer name=topic-name-2 trace=t2 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-2\n  messaging.destination_kind=topic\n"
        }
    ]
}
```

*1.3 Publish failure — every span of the failed operation marked error*

When the underlying client rejects a publish (single or batch), every span created for that operation is marked with an error status and its `status_message` is set to the client's failure reason. The failure is still surfaced to the caller (action line reports `status=error error=client_send_failure`). Spans are created before the publish is attempted, so they still exist and still carry the injected context.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_producer_send_failure.json`

```json
{
    "description": "When the underlying client rejects a send or batch-send, every span created for that operation is marked with an error status whose message is the client failure reason, and the failure is surfaced to the caller.",
    "cases": [
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "testing message content" }],
                        "clientResponse": { "status": "error", "message": "error thrown from kafka client send" }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=error error=client_send_failure\ninject msg=0 carries=span#0\nspans=1\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root status=error\n  status_message=error thrown from kafka client send\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n"
        },
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "m1" }, { "value": "m2" }],
                        "clientResponse": { "status": "error", "message": "error thrown from kafka client send" }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=error error=client_send_failure\ninject msg=0 carries=span#0\ninject msg=1 carries=span#1\nspans=2\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root status=error\n  status_message=error thrown from kafka client send\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\nspan 1 kind=producer name=topic-name-1 trace=t1 parent=root status=error\n  status_message=error thrown from kafka client send\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n"
        }
    ]
}
```

*1.4 Producer enrichment callback — decorate span, survive callback failure*

An optional producer enrichment callback runs once per producer span and may copy message-derived data onto the span as a custom attribute (shown as an extra indented attribute line). If the callback itself throws, the span is still created and still finishes with an unset (non-error) status — a faulty enrichment hook must never corrupt the trace.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_producer_hook.json`

```json
{
    "description": "An optional producer enrichment callback runs for each producer span and may copy message data onto the span as a custom attribute; if the callback throws, the span is still created and finishes with an unset (non-error) status.",
    "cases": [
        {
            "input": {
                "config": { "producerHook": { "action": "copy_value_to_attribute", "attribute": "attribute-from-hook" } },
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "testing message content" }],
                        "clientResponse": { "status": "success", "records": [] }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=ok result_records=0\ninject msg=0 carries=span#0\nspans=1\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  attribute-from-hook=testing message content\n"
        },
        {
            "input": {
                "config": { "producerHook": { "action": "throw", "message": "error thrown from producer hook" } },
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "testing message content" }],
                        "clientResponse": { "status": "success", "records": [] }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=ok result_records=0\ninject msg=0 carries=span#0\nspans=1\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n"
        }
    ]
}
```

---

### Feature 2: Consumer Span Emission

**As a developer**, I want every consumed message to automatically produce a tracing span with messaging metadata and correct error reflection, so I can observe my processing path and detect failures without writing tracing code.

**Expected Behavior / Usage:**

*2.1 Per-message consume — one process span*

Delivering a single message to a per-message handler creates exactly one CONSUMER span named after the topic, carrying the messaging attributes plus `messaging.operation=process`. The span is created regardless of whether the handler returns a promise or returns synchronously (a non-promise return must not break instrumentation). Each delivery starts its own root trace when the message carries no upstream context.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_consume_each_message.json`

```json
{
    "description": "Delivering a single message to a per-message consumer handler creates one CONSUMER span named after the topic, with the messaging attributes and a process operation; the span is created whether or not the handler returns a promise.",
    "cases": [
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "partition": 0,
                        "message": { "value": "message content", "offset": "123" },
                        "handler": { "behavior": "resolve" }
                    }
                ]
            },
            "expected_output": "consume_message topic=topic-name-1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name] error=none\nspans=1\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n"
        },
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "partition": 0,
                        "message": { "value": "message content", "offset": "123" },
                        "handler": { "behavior": "return_non_promise" }
                    }
                ]
            },
            "expected_output": "consume_message topic=topic-name-1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name] error=none\nspans=1\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n"
        }
    ]
}
```

*2.2 Per-batch consume — one receive span plus one process span per message*

Delivering a batch to a per-batch handler creates one **receiving** CONSUMER span for the whole batch (`messaging.operation=receive`, a root span starting a new trace) and then one **processing** CONSUMER span per message in the batch (`messaging.operation=process`), each a child of the receiving span and sharing its trace. All spans are created whether the handler returns a promise or returns synchronously.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_consume_each_batch.json`

```json
{
    "description": "Delivering a batch to a per-batch consumer handler creates one receiving CONSUMER span for the batch (operation receive, root of a new trace) plus one processing CONSUMER span per message (operation process) that is a child of the receiving span; the spans are created whether or not the handler returns a promise.",
    "cases": [
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "consume_batch",
                        "topic": "topic-name-1",
                        "partition": 1234,
                        "messages": [
                            { "value": "message content", "offset": "124" },
                            { "value": "message content", "offset": "125" }
                        ],
                        "handler": { "behavior": "resolve" }
                    }
                ]
            },
            "expected_output": "consume_batch topic=topic-name-1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name] error=none\nspans=3\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=receive\nspan 1 kind=consumer name=topic-name-1 trace=t0 parent=span#0 [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\nspan 2 kind=consumer name=topic-name-1 trace=t0 parent=span#0 [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n"
        }
    ]
}
```

*2.3 Per-message handler failure — error reflected and normalized*

When a per-message handler fails, its span is marked with an error status and the failure is re-surfaced to the caller (`delivered=error`). The error is reported on the action line as a neutral category: a thrown value with a readable reason → `handler_failure`; a thrown value carrying no readable reason → `handler_failure_no_message`; an empty/absent thrown value → `handler_failure_empty`. The span's `status_message` is the readable reason when one exists, otherwise `<none>`. No host-language exception identity ever appears.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_consume_handler_failure.json`

```json
{
    "description": "When a per-message consumer handler fails, its span is marked with an error status and the failure is re-surfaced to the caller; the error is reported as a neutral category. A thrown value with a readable reason yields that reason as the status message; a thrown value without a readable reason (including an empty/absent value) yields no status message.",
    "cases": [
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "message": { "value": "message content", "offset": "123" },
                        "handler": { "behavior": "throw_error", "message": "error thrown from eachMessage callback" }
                    }
                ]
            },
            "expected_output": "consume_message topic=topic-name-1 delivered=error error=handler_failure\nspans=1\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root status=error\n  status_message=error thrown from eachMessage callback\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n"
        },
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "message": { "value": "message content", "offset": "123" },
                        "handler": { "behavior": "throw_object_no_message" }
                    }
                ]
            },
            "expected_output": "consume_message topic=topic-name-1 delivered=error error=handler_failure_no_message\nspans=1\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root status=error\n  status_message=<none>\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n"
        },
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "message": { "value": "message content", "offset": "123" },
                        "handler": { "behavior": "throw_undefined" }
                    }
                ]
            },
            "expected_output": "consume_message topic=topic-name-1 delivered=error error=handler_failure_empty\nspans=1\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root status=error\n  status_message=<none>\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n"
        }
    ]
}
```

*2.4 Consumer enrichment callback — decorate span, survive callback failure*

An optional consumer enrichment callback runs once per consumer span and may copy message-derived data onto the span as a custom attribute. If the callback throws, the span is still created (delivery still succeeds).

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_consumer_hook.json`

```json
{
    "description": "An optional consumer enrichment callback runs for each consumer span and may copy message data onto the span as a custom attribute; if the callback throws, the span is still created.",
    "cases": [
        {
            "input": {
                "config": { "consumerHook": { "action": "copy_value_to_attribute", "attribute": "attribute key from hook" } },
                "steps": [
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "message": { "value": "message content", "offset": "123" },
                        "handler": { "behavior": "resolve" }
                    }
                ]
            },
            "expected_output": "consume_message topic=topic-name-1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name] error=none\nspans=1\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n  attribute key from hook=message content\n"
        },
        {
            "input": {
                "config": { "consumerHook": { "action": "throw", "message": "error thrown from consumer hook" } },
                "steps": [
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "message": { "value": "message content", "offset": "123" },
                        "handler": { "behavior": "resolve" }
                    }
                ]
            },
            "expected_output": "consume_message topic=topic-name-1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name] error=none\nspans=1\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n"
        }
    ]
}
```

---

### Feature 3: Cross-Boundary Context Propagation

**As a developer**, I want the trace context and [a specific baggage key-value relationship — ask the PM for the exact string used in the mock] I set when publishing a message to be automatically recovered when that message is consumed, so I can see a single connected trace (and shared [a specific baggage key-value relationship — ask the PM for the exact string used in the mock]) spanning the publish and the processing — even though they run as separate asynchronous operations.

**Expected Behavior / Usage:**

*3.1 Publish → per-message consume — consumer span joins producer trace*

When a message published in one step is later delivered (with its injected headers) to a per-message handler, the consumer span shares the producer span's trace and is its direct child. Any [a specific baggage key-value relationship — ask the PM for the exact string used in the mock] set around the publish call is visible inside the consumer handler and is reported on a `[a specific baggage key-value relationship — ask the PM for the exact string used in the mock] <k>=<v>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_propagation_message.json`

```json
{
    "description": "Trace context and [a specific baggage key-value relationship — ask the PM for the exact string used in the mock] injected into a message when it is produced are recovered when that same message is later delivered to a per-message consumer handler: the consumer span shares the producer span trace and is its child, and any [a specific baggage key-value relationship — ask the PM for the exact string used in the mock] set around the produce call is visible inside the consumer handler.",
    "cases": [
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "testing message content" }],
                        "clientResponse": { "status": "success", "records": [] },
                        "[a specific baggage key-value relationship — ask the PM for the exact string used in the mock]": { "foo": "bar" }
                    },
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "message": { "value": "" },
                        "headersFromMessage": 0,
                        "observeBaggage": true,
                        "handler": { "behavior": "resolve" }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=ok result_records=0\nconsume_message topic=topic-name-1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name] error=none\ninject msg=0 carries=span#0\n[a specific baggage key-value relationship — ask the PM for the exact string used in the mock] [a specific baggage key-value relationship — ask the PM for the exact string used in the mock]\nspans=2\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\nspan 1 kind=consumer name=topic-name-1 trace=t0 parent=span#0 [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n"
        }
    ]
}
```

*3.2 Publish → per-batch consume — link instead of parent*

When a published message is later delivered through a per-batch handler, the per-message processing span does **not** become a child of the original producer span; instead it carries a **link** back to the producer span. The processing span stays a child of the batch's receiving span, and the receiving span starts a brand-new trace distinct from the producer's trace. This reflects the fan-in semantics of batch consumption (many upstream producers, one batch).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_propagation_batch_links.json`

```json
{
    "description": "When a produced message is later delivered through a per-batch consumer handler, its processing span does not become a child of the original producer span but instead carries a link back to it; the processing span remains a child of the batch receiving span, and the receiving span starts a brand-new trace distinct from the producer.",
    "cases": [
        {
            "input": {
                "config": {},
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "testing message content" }],
                        "clientResponse": { "status": "success", "records": [] }
                    },
                    {
                        "action": "consume_batch",
                        "topic": "topic-name-1",
                        "partition": 0,
                        "messages": [{ "value": "", "headersFromMessage": 0 }],
                        "handler": { "behavior": "resolve" }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=ok result_records=0\nconsume_batch topic=topic-name-1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name] error=none\ninject msg=0 carries=span#0\nspans=3\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\nspan 1 kind=consumer name=topic-name-1 trace=t1 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=receive\nspan 2 kind=consumer name=topic-name-1 trace=t1 parent=span#1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n  links=span#0\n"
        }
    ]
}
```

---

### Feature 4: Optional Library-Version Attribute

**As a developer**, I want to optionally tag every emitted span with the version of the instrumented client library under a configurable attribute name, so I can correlate traces with the exact client version in production.

**Expected Behavior / Usage:**

When a version-attribute name is configured, every emitted span — producer and consumer alike — carries an attribute under that exact name whose value is the instrumented client library's version string (a dotted version like `1.16.0`; normalized to the token `<version>` in the contract so the test is environment-independent). When the option is absent, no such attribute is added.

**Test Cases:** `rcb_tests/public_test_cases/feature4_module_version_attribute.json`

```json
{
    "description": "When a module-version attribute name is configured, every emitted span (producer and consumer alike) carries an attribute under that name whose value is the instrumented client library version string.",
    "cases": [
        {
            "input": {
                "config": { "moduleVersionAttribute": "module.version" },
                "steps": [
                    {
                        "action": "produce",
                        "topic": "topic-name-1",
                        "messages": [{ "value": "testing message content" }],
                        "clientResponse": { "status": "success", "records": [] }
                    }
                ]
            },
            "expected_output": "produce topic=topic-name-1 status=ok result_records=0\ninject msg=0 carries=span#0\nspans=1\nspan 0 kind=producer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  module.version=<version>\n"
        },
        {
            "input": {
                "config": { "moduleVersionAttribute": "module.version" },
                "steps": [
                    {
                        "action": "consume_message",
                        "topic": "topic-name-1",
                        "message": { "value": "message content", "offset": "123" },
                        "handler": { "behavior": "resolve" }
                    }
                ]
            },
            "expected_output": "consume_message topic=topic-name-1 [The exact status message string used when a hook throws — check the error propagation spec for the error class name] error=none\nspans=1\nspan 0 kind=consumer name=topic-name-1 trace=t0 parent=root [The exact status message string used when a hook throws — check the error propagation spec for the error class name]\n  messaging.system=kafka\n  messaging.destination=topic-name-1\n  messaging.destination_kind=topic\n  messaging.operation=process\n  module.version=<version>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured instrumentation library that patches the message broker client's producer and consumer factories, manages the producer/consumer span lifecycle (naming, attributes, status, parent/child, links), injects and extracts trace context plus [a specific baggage key-value relationship — ask the PM for the exact string used in the mock] through message headers, supports optional producer/consumer enrichment callbacks and an optional library-version attribute, and is resilient to handler/callback failures. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON scenario from stdin, drives the instrumented client through the requested produce/consume steps, and prints the resulting spans and signals as the language-neutral stdout contract described in "Output Contract" — translating any host-language exception thrown by a handler or callback into a neutral error category. This adapter MUST be logically and physically separated from the core instrumentation.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_producer_send.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_producer_send@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other, and each `.txt` file contains **only** the raw stdout from the program under test so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the attribute naming convention for version metadata
- refer to the error handling strategy for throw-based handlers
