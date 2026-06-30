## Product Requirement Document

# Message Transport Adapter - Event Envelope, Routing, and Retry Contracts

## Project Goal

Build a message transport adapter that allows developers to serialize application payloads, wrap and unwrap event envelopes, configure publisher/subscriber routes, and classify queue retry behavior without writing repetitive transport glue code.

---

## Background & Problem

Without this library/tool, developers are forced to manually serialize payloads, copy event metadata between transport envelopes, parse provider-specific queue wrappers, register message routes, and implement retry decisions for polling failures. This leads to repetitive code, inconsistent metadata propagation, and error-prone configuration.

With this library/tool, application messages can be encoded, enveloped, routed, unwrapped, and retried through a consistent black-box contract with predictable stdout rendering for test automation.

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

### Feature 1: Application Message JSON Conversion

**As a developer, I want to convert application message objects to and from JSON text**, so I can exchange typed payloads through message transports without hand-writing field mapping.

**Expected Behavior / Usage:**

This feature is divided into the leaf functional points below; each leaf is independently testable through its listed JSON contract.

*1.1 JSON encoding for application messages — A message input contains scalar person fields, an enum-like gender value, and a nested address*

A message input contains scalar person fields, an enum-like gender value, and a nested address. The adapter must print one `json=` line containing compact JSON that preserves the public field names, nested address object, numeric values, and string enum value exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_message_json_encode.json`

```json
{
    "description": "Encode an application message containing scalar fields, an enum-like value, and a nested address into compact JSON text.",
    "cases": [
        {
            "input": {
                "operation": "message_json_encode",
                "person": {
                    "firstName": "Bob",
                    "lastName": "Stone",
                    "age": 30,
                    "gender": "Male",
                    "address": {
                        "unit": 12,
                        "street": "Prince St",
                        "zipCode": "00001"
                    }
                }
            },
            "expected_output": "json={\"FirstName\":\"Bob\",\"LastName\":\"Stone\",\"Age\":30,\"Gender\":\"Male\",\"Address\":{\"Unit\":12,\"Street\":\"Prince St\",\"ZipCode\":\"00001\"}}[one newline terminator]"
        }
    ]
}
```

*1.2 JSON decoding for application messages — A JSON text input containing a person payload must be decoded into its public fields*

A JSON text input containing a person payload must be decoded into its public fields. The adapter must print one line per field, including nested address fields, so the result can be compared without relying on host-language object rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_message_json_decode.json`

```json
{
    "description": "Decode JSON text for an application message and expose each scalar and nested address field in the resulting object.",
    "cases": [
        {
            "input": {
                "operation": "message_json_decode",
                "json": "{[one newline terminator]  \"FirstName\":\"Bob\",[one newline terminator]  \"LastName\":\"Stone\",[one newline terminator]  \"Age\":30,[one newline terminator]  \"Gender\":\"Male\",[one newline terminator]  \"Address\":{\"Unit\":12,\"Street\":\"Prince St\",\"ZipCode\":\"00001\"}[one newline terminator]}"
            },
            "expected_output": "first_name=Bob[one newline terminator]last_name=Stone[one newline terminator]age=30[one newline terminator]gender=Male[one newline terminator]address_unit=12[one newline terminator]address_street=Prince St[one newline terminator]address_zip=00001[one newline terminator]"
        }
    ]
}
```

---

### Feature 2: Event Envelope Construction and Parsing

**As a developer, I want application payloads to be wrapped in standard event envelopes and parsed back**, so messages can carry source, type, time, metadata, and data consistently across transports.

**Expected Behavior / Usage:**

This feature is divided into the leaf functional points below; each leaf is independently testable through its listed JSON contract.

*2.1 Parse structured event envelopes — An event envelope input uses standard event keys for id, source, version, type, time, and data, plus queue metadata and unknown extension metadata*

An event envelope input uses standard event keys for id, source, version, type, time, and data, plus queue metadata and unknown extension metadata. The adapter must print the decoded standard fields, data fields, selected extension metadata, and queue metadata as separate lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_cloud_event_parse.json`

```json
{
    "description": "Parse a structured event envelope that uses standard event field names, application data, queue metadata, and unknown extension metadata.",
    "cases": [
        {
            "input": {
                "operation": "cloud_event_parse",
                "json": "{[one newline terminator] \"id\":\"A1234\",[one newline terminator] \"source\":\"/backend-service/order-placed\",[one newline terminator] \"specversion\":\"1.0\",[one newline terminator] \"type\":\"order-info\",[one newline terminator] \"time\":\"2018-04-05T17:31:00\",[one newline terminator] \"data\":{\"name\":\"Bob\",\"city\":\"my-city\",\"merchandise\":\"t-shirt\"},[one newline terminator] \"SQSMetadata\":{\"MessageDeduplicationId\":\"dedup-id\",\"MessageGroupId\":\"group-id\",\"MessageAttributes\":{\"MyNameAttribute\":{\"StringValue\":\"John Doe\"}}},[one newline terminator] \"some-metadata\":\"random-string\"[one newline terminator]}"
            },
            "expected_output": "id=A1234[one newline terminator]source=/backend-service/order-placed[one newline terminator]version=1.0[one newline terminator]type=order-info[one newline terminator]time=2018-04-05T17:31:00[one newline terminator]data_name=Bob[one newline terminator]data_city=my-city[one newline terminator]data_merchandise=t-shirt[one newline terminator]metadata_some=random-string[one newline terminator]sqs_group=group-id[one newline terminator]sqs_dedup=dedup-id[one newline terminator]sqs_attr_MyNameAttribute=John Doe[one newline terminator]"
        }
    ]
}
```

*2.2 Create event envelopes from payloads — An address payload input plus a configured event source must produce an event envelope with version `1*

An address payload input plus a configured event source must produce an event envelope with version `1.0`, the configured source, the configured message type identifier, the current timestamp supplied by the execution environment, and the original address fields.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_cloud_event_create.json`

```json
{
    "description": "Wrap an address payload into an event envelope using configured source, type identifier, event version, and current timestamp.",
    "cases": [
        {
            "input": {
                "operation": "cloud_event_create",
                "source": "/aws/messaging",
                "address": {
                    "unit": 123,
                    "street": "Prince St",
                    "zipCode": "00001"
                }
            },
            "expected_output": "source=/aws/messaging[one newline terminator]version=1.0[one newline terminator]type=addressInfo[one newline terminator]time=2000-12-05T10:30:55+00:00[one newline terminator]unit=123[one newline terminator]street=Prince St[one newline terminator]zip=00001[one newline terminator]"
        }
    ]
}
```

*2.3 Encode event envelopes as JSON — An event envelope input must be encoded as compact JSON using standard event field names*

An event envelope input must be encoded as compact JSON using standard event field names. The application payload must be serialized as a JSON string in the envelope data field, preserving the address fields and the supplied id, source, type, version, and time.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_cloud_event_json_encode.json`

```json
{
    "description": "Encode an event envelope as compact JSON, preserving standard event field names and serializing application data as a JSON string inside the envelope.",
    "cases": [
        {
            "input": {
                "operation": "cloud_event_json_encode",
                "id": "id-123",
                "source": "/backend/service",
                "version": "1.0",
                "messageTypeIdentifier": "addressInfo",
                "time": "2000-12-05T10:30:55+00:00",
                "address": {
                    "unit": 123,
                    "street": "Prince St",
                    "zipCode": "00001"
                }
            },
            "expected_output": "json={\"id\":\"id-123\",\"source\":\"/backend/service\",\"specversion\":\"1.0\",\"type\":\"addressInfo\",\"time\":\"2000-12-05T10:30:55+00:00\",\"data\":\"{\\u0022Unit\\u0022:123,\\u0022Street\\u0022:\\u0022Prince St\\u0022,\\u0022ZipCode\\u0022:\\u002200001\\u0022}\"}[one newline terminator]"
        }
    ]
}
```

---

### Feature 3: Queue Payload Unwrapping

**As a developer, I want queue-delivered payloads to be unwrapped from different transport envelopes**, so handlers receive the original event payload together with transport metadata.

**Expected Behavior / Usage:**

This feature is divided into the leaf functional points below; each leaf is independently testable through its listed JSON contract.

*3.1 Direct queue body event unwrapping — A queue message whose body is already an event envelope must decode to the inner event payload and attach queue receipt, FIFO group, deduplication, and message attribute metadata*

A queue message whose body is already an event envelope must decode to the inner event payload and attach queue receipt, FIFO group, deduplication, and message attribute metadata. The output must also identify the configured message mapping selected for the event type.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_queue_payload_direct_unwrap.json`

```json
{
    "description": "Unwrap a queue message whose body is already an event envelope and carry queue receipt, FIFO, and message attribute metadata onto the decoded envelope.",
    "cases": [
        {
            "input": {
                "operation": "queue_payload_unwrap",
                "wrapper": "none",
                "id": "66659d05-e4ff-462f-81c4-09e560e66a5c",
                "source": "/aws/messaging",
                "messageTypeIdentifier": "addressInfo",
                "time": "2000-12-05T10:30:55+00:00",
                "address": {
                    "unit": 123,
                    "street": "Prince St",
                    "zipCode": "00001"
                },
                "receiptHandle": "receipt-handle",
                "messageGroupId": "group-123",
                "messageDeduplicationId": "dedup-123",
                "queueAttributeName": "attr1",
                "queueAttributeDataType": "String",
                "queueAttributeValue": "val1"
            },
            "expected_output": "id=66659d05-e4ff-462f-81c4-09e560e66a5c[one newline terminator]source=/aws/messaging[one newline terminator]version=1.0[one newline terminator]type=addressInfo[one newline terminator]time=2000-12-05T10:30:55+00:00[one newline terminator]unit=123[one newline terminator]street=Prince St[one newline terminator]zip=00001[one newline terminator]mapping_identifier=addressInfo[one newline terminator]mapping_message=address[one newline terminator]mapping_handler=registered_address_handler[one newline terminator]sqs_receipt=receipt-handle[one newline terminator]sqs_group=group-123[one newline terminator]sqs_dedup=dedup-123[one newline terminator]sqs_attr_attr1_type=String[one newline terminator]sqs_attr_attr1_value=val1[one newline terminator]"
        }
    ]
}
```

*3.2 Notification envelope unwrapping — A queue message whose body is a notification envelope must decode the nested event message, preserve the application payload, expose the selected handler mapping, and print notification metadata such as message id, topic, subject, unsubscribe URL, timestamp, and attributes*

A queue message whose body is a notification envelope must decode the nested event message, preserve the application payload, expose the selected handler mapping, and print notification metadata such as message id, topic, subject, unsubscribe URL, timestamp, and attributes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_queue_payload_notification_unwrap.json`

```json
{
    "description": "Unwrap a queue message that contains a notification envelope, decode the inner event, and expose notification metadata and attributes.",
    "cases": [
        {
            "input": {
                "operation": "queue_payload_unwrap",
                "wrapper": "sns",
                "id": "66659d05-e4ff-462f-81c4-09e560e66a5c",
                "source": "/aws/messaging",
                "messageTypeIdentifier": "addressInfo",
                "time": "2000-12-05T10:30:55+00:00",
                "address": {
                    "unit": 123,
                    "street": "Prince St",
                    "zipCode": "00001"
                },
                "outerId": "abcd-123",
                "topicArn": "arn:aws:sns:us-east-2:111122223333:ExampleTopic1",
                "subject": "TestSubject",
                "unsubscribeUrl": "https://www.click-here.com",
                "outerTime": "2000-12-05T10:30:55+00:00"
            },
            "expected_output": "id=66659d05-e4ff-462f-81c4-09e560e66a5c[one newline terminator]source=/aws/messaging[one newline terminator]version=1.0[one newline terminator]type=addressInfo[one newline terminator]time=2000-12-05T10:30:55+00:00[one newline terminator]unit=123[one newline terminator]street=Prince St[one newline terminator]zip=00001[one newline terminator]mapping_identifier=addressInfo[one newline terminator]mapping_message=address[one newline terminator]mapping_handler=registered_address_handler[one newline terminator]sqs_receipt=[one newline terminator]sqs_group=[one newline terminator]sqs_dedup=[one newline terminator]sns_message_id=abcd-123[one newline terminator]sns_topic=arn:aws:sns:us-east-2:111122223333:ExampleTopic1[one newline terminator]sns_subject=TestSubject[one newline terminator]sns_unsubscribe=https://www.click-here.com[one newline terminator]sns_time=2000-12-05T10:30:55+00:00[one newline terminator]sns_attr_attr1_type=String[one newline terminator]sns_attr_attr1_value=val1[one newline terminator]sns_attr_attr2_type=Number[one newline terminator]sns_attr_attr2_value=3[one newline terminator]"
        }
    ]
}
```

*3.3 Event-routing envelope unwrapping — A queue message whose body is an event-routing envelope must decode the nested event detail, preserve the application payload, expose the selected handler mapping, and print outer routing metadata such as event id, source, detail type, account, region, time, and resources*

A queue message whose body is an event-routing envelope must decode the nested event detail, preserve the application payload, expose the selected handler mapping, and print outer routing metadata such as event id, source, detail type, account, region, time, and resources.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_queue_payload_event_unwrap.json`

```json
{
    "description": "Unwrap a queue message that contains an event-routing outer envelope, decode the inner event detail, and expose outer routing metadata.",
    "cases": [
        {
            "input": {
                "operation": "queue_payload_unwrap",
                "wrapper": "eventbridge",
                "id": "66659d05-e4ff-462f-81c4-09e560e66a5c",
                "source": "/aws/messaging",
                "messageTypeIdentifier": "addressInfo",
                "time": "2000-12-05T10:30:55+00:00",
                "address": {
                    "unit": 123,
                    "street": "Prince St",
                    "zipCode": "00001"
                },
                "outerId": "abcd-123",
                "outerSource": "some-source",
                "detailType": "address",
                "account": "123456789123",
                "region": "us-west-2",
                "outerTime": "2000-12-05T10:30:55+00:00",
                "resources": [
                    "arn1",
                    "arn2"
                ]
            },
            "expected_output": "id=66659d05-e4ff-462f-81c4-09e560e66a5c[one newline terminator]source=/aws/messaging[one newline terminator]version=1.0[one newline terminator]type=addressInfo[one newline terminator]time=2000-12-05T10:30:55+00:00[one newline terminator]unit=123[one newline terminator]street=Prince St[one newline terminator]zip=00001[one newline terminator]mapping_identifier=addressInfo[one newline terminator]mapping_message=address[one newline terminator]mapping_handler=registered_address_handler[one newline terminator]sqs_receipt=[one newline terminator]sqs_group=[one newline terminator]sqs_dedup=[one newline terminator]event_id=abcd-123[one newline terminator]event_source=some-source[one newline terminator]event_detail_type=address[one newline terminator]event_account=123456789123[one newline terminator]event_region=us-west-2[one newline terminator]event_time=2000-12-05T10:30:55+00:00[one newline terminator]event_resources=arn1,arn2[one newline terminator]"
        }
    ]
}
```

---

### Feature 4: Message Processing Outcome

**As a developer, I want message handlers to return a clear processing outcome**, so downstream polling logic can distinguish successful processing from failed processing.

**Expected Behavior / Usage:**

*4.1 Success and failure flags — A processing outcome input of success or failure must print both boolean flags*

A processing outcome input of success or failure must print both boolean flags. Success must set `is_success=true` and `is_failed=false`; failure must set `is_success=false` and `is_failed=true`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_processing_outcome.json`

```json
{
    "description": "Represent a message handling outcome as mutually exclusive success and failure flags.",
    "cases": [
        {
            "input": {
                "operation": "processing_outcome",
                "status": "success"
            },
            "expected_output": "is_success=true[one newline terminator]is_failed=false[one newline terminator]"
        },
        {
            "input": {
                "operation": "processing_outcome",
                "status": "failed"
            },
            "expected_output": "is_success=false[one newline terminator]is_failed=true[one newline terminator]"
        }
    ]
}
```

---

### Feature 5: Queue Retry Backoff

**As a developer, I want queue polling errors to be classified for retry backoff**, so transient failures can be retried while fatal queue errors stop retrying.

**Expected Behavior / Usage:**

*5.1 Retry decision and maximum delay — A retry-backoff input selects a policy, an error category, and a retry count*

A retry-backoff input selects a policy, an error category, and a retry count. The adapter must print whether backoff should occur, the maximum delay allowed by that policy for the input, and whether the observed delay generated by the policy stayed within that maximum. Fatal queue error categories must not request backoff; generic queue errors must request backoff for interval and capped exponential policies; the no-backoff policy must never request backoff.

**Test Cases:** `rcb_tests/public_test_cases/feature5_retry_backoff.json`

```json
{
    "description": "For queue polling errors, decide whether retry backoff should occur and report the computed delay in seconds for the selected retry policy.",
    "cases": [
        {
            "input": {
                "operation": "retry_backoff",
                "policy": "none",
                "errorCategory": "generic_queue_error",
                "retryCount": 5
            },
            "expected_output": "should_backoff=false[one newline terminator]max_backoff_seconds=0[one newline terminator]observed_within_max=true[one newline terminator]"
        },
        {
            "input": {
                "operation": "retry_backoff",
                "policy": "interval",
                "fixedInterval": 2,
                "errorCategory": "generic_queue_error",
                "retryCount": 3
            },
            "expected_output": "should_backoff=true[one newline terminator]max_backoff_seconds=2[one newline terminator]observed_within_max=true[one newline terminator]"
        },
        {
            "input": {
                "operation": "retry_backoff",
                "policy": "interval",
                "fixedInterval": 2,
                "errorCategory": "queue_missing",
                "retryCount": 3
            },
            "expected_output": "should_backoff=false[one newline terminator]max_backoff_seconds=2[one newline terminator]observed_within_max=true[one newline terminator]"
        },
        {
            "input": {
                "operation": "retry_backoff",
                "policy": "capped_exponential",
                "capBackoffTime": 60,
                "errorCategory": "generic_queue_error",
                "retryCount": 4
            },
            "expected_output": "should_backoff=true[one newline terminator]max_backoff_seconds=16[one newline terminator]observed_within_max=true[one newline terminator]"
        }
    ]
}
```

---

### Feature 6: Settings-Based Messaging Configuration

**As a developer, I want messaging routes and retry settings to load from configuration JSON**, so deployments can define publishers, subscribers, pollers, and backoff policies without imperative setup code.

**Expected Behavior / Usage:**

This feature is divided into the leaf functional points below; each leaf is independently testable through its listed JSON contract.

*6.1 Publisher definitions from settings — A settings JSON input may define queue, notification, or event-bus publishers*

A settings JSON input may define queue, notification, or event-bus publishers. The adapter must print the number of publisher mappings and, for each one, its target kind, endpoint, and message identifier, followed by the other configuration collection counts and default backoff settings.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_settings_publishers.json`

```json
{
    "description": "Load publisher definitions from settings JSON for queue, notification, and event-bus targets, preserving target type, endpoint, and optional message identifier.",
    "cases": [
        {
            "input": {
                "operation": "settings_load",
                "settings_json": "{\"Messaging\":{\"SQSPublishers\":[{\"MessageType\":\"chat_message\",\"QueueUrl\":\"https://sqs.us-west-2.amazonaws.com/012345678910/MPF\",\"MessageTypeIdentifier\":\"chatmessage\"}]}}"
            },
            "expected_output": "publishers=1[one newline terminator]publisher_target=SQS[one newline terminator]publisher_endpoint=https://sqs.us-west-2.amazonaws.com/012345678910/MPF[one newline terminator]publisher_identifier=chatmessage[one newline terminator]subscribers=0[one newline terminator]pollers=0[one newline terminator]backoff_policy=CappedExponential[one newline terminator]interval_fixed=1[one newline terminator][specific value based on backoff policy context]60[one newline terminator]"
        },
        {
            "input": {
                "operation": "settings_load",
                "settings_json": "{\"Messaging\":{\"SNSPublishers\":[{\"MessageType\":\"chat_message\",\"TopicUrl\":\"arn:aws:sns:us-west-2:012345678910:MPF\",\"MessageTypeIdentifier\":\"chatmessage\"}]}}"
            },
            "expected_output": "publishers=1[one newline terminator]publisher_target=SNS[one newline terminator]publisher_endpoint=arn:aws:sns:us-west-2:012345678910:MPF[one newline terminator]publisher_identifier=chatmessage[one newline terminator]subscribers=0[one newline terminator]pollers=0[one newline terminator]backoff_policy=CappedExponential[one newline terminator]interval_fixed=1[one newline terminator][specific value based on backoff policy context]60[one newline terminator]"
        },
        {
            "input": {
                "operation": "settings_load",
                "settings_json": "{\"Messaging\":{\"EventBridgePublishers\":[{\"MessageType\":\"chat_message\",\"EventBusName\":\"arn:aws:events:us-west-2:012345678910:event-bus/default\",\"MessageTypeIdentifier\":\"chatmessage\"}]}}"
            },
            "expected_output": "publishers=1[one newline terminator]publisher_target=EventBridge[one newline terminator]publisher_endpoint=arn:aws:events:us-west-2:012345678910:event-bus/default[one newline terminator]publisher_identifier=chatmessage[one newline terminator]subscribers=0[one newline terminator]pollers=0[one newline terminator]backoff_policy=CappedExponential[one newline terminator]interval_fixed=1[one newline terminator][specific value based on backoff policy context]60[one newline terminator]"
        }
    ]
}
```

*6.2 Subscriber and poller definitions from settings — A settings JSON input may define subscriber handler mappings or queue pollers*

A settings JSON input may define subscriber handler mappings or queue pollers. Subscriber mappings must print their message identifier. Queue pollers must print endpoint and tuning values for concurrency, visibility timeout, wait time, heartbeat interval, and extension threshold.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_settings_subscribers_and_pollers.json`

```json
{
    "description": "Load subscriber handler mappings and queue poller settings from JSON, including optional message identifiers and poller tuning values.",
    "cases": [
        {
            "input": {
                "operation": "settings_load",
                "settings_json": "{\"Messaging\":{\"MessageHandlers\":[{\"HandlerType\":\"chat_handler\",\"MessageType\":\"chat_message\",\"MessageTypeIdentifier\":\"chatmessage\"}]}}"
            },
            "expected_output": "publishers=0[one newline terminator]subscribers=1[one newline terminator]subscriber_identifier=chatmessage[one newline terminator]pollers=0[one newline terminator]backoff_policy=CappedExponential[one newline terminator]interval_fixed=1[one newline terminator][specific value based on backoff policy context]60[one newline terminator]"
        },
        {
            "input": {
                "operation": "settings_load",
                "settings_json": "{\"Messaging\":{\"SQSPollers\":[{\"QueueUrl\":\"https://sqs.us-west-2.amazonaws.com/012345678910/MPF\",\"Options\":{\"MaxNumberOfConcurrentMessages\":10,\"VisibilityTimeout\":20,\"WaitTimeSeconds\":20,\"VisibilityTimeoutExtensionHeartbeatInterval\":1,\"VisibilityTimeoutExtensionThreshold\":5}}]}}"
            },
            "expected_output": "publishers=0[one newline terminator]subscribers=0[one newline terminator]pollers=1[one newline terminator]poller_endpoint=https://sqs.us-west-2.amazonaws.com/012345678910/MPF[one newline terminator]poller_concurrency=10[one newline terminator]poller_visibility=20[one newline terminator]poller_wait=20[one newline terminator]poller_heartbeat=1[one newline terminator]poller_threshold=5[one newline terminator]backoff_policy=CappedExponential[one newline terminator]interval_fixed=1[one newline terminator][specific value based on backoff policy context]60[one newline terminator]"
        }
    ]
}
```

*6.3 Backoff policy definitions from settings — A settings JSON input may select no backoff, interval backoff, or capped exponential backoff*

A settings JSON input may select no backoff, interval backoff, or capped exponential backoff. The adapter must print the selected policy and any policy-specific option values that were loaded.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_settings_backoff_policy.json`

```json
{
    "description": "Load retry backoff policy selection and policy-specific options from settings JSON.",
    "cases": [
        {
            "input": {
                "operation": "settings_load",
                "settings_json": "{\"Messaging\":{\"BackoffPolicy\":\"None\"}}"
            },
            "expected_output": "publishers=0[one newline terminator]subscribers=0[one newline terminator]pollers=0[one newline terminator]backoff_policy=None[one newline terminator]interval_fixed=1[one newline terminator][specific value based on backoff policy context]60[one newline terminator]"
        },
        {
            "input": {
                "operation": "settings_load",
                "settings_json": "{\"Messaging\":{\"BackoffPolicy\":\"Interval\",\"IntervalBackoffOptions\":{\"FixedInterval\":2}}}"
            },
            "expected_output": "publishers=0[one newline terminator]subscribers=0[one newline terminator]pollers=0[one newline terminator]backoff_policy=Interval[one newline terminator]interval_fixed=2[one newline terminator][specific value based on backoff policy context]60[one newline terminator]"
        },
        {
            "input": {
                "operation": "settings_load",
                "settings_json": "{\"Messaging\":{\"BackoffPolicy\":\"CappedExponential\",\"CappedExponentialBackoffOptions\":{\"CapBackoffTime\":2}}}"
            },
            "expected_output": "publishers=0[one newline terminator]subscribers=0[one newline terminator]pollers=0[one newline terminator]backoff_policy=CappedExponential[one newline terminator]interval_fixed=1[one newline terminator][specific value based on backoff policy context]2[one newline terminator]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- convert keys to snake_case
- apply naming rules per output_rule section
