## Product Requirement Document

# Embedded MQTT 3.1.1 Client Library — Packet Encoding, Message Delivery & Keepalive

## Project Goal

Build a small, embeddable MQTT client library that lets device firmware talk to an MQTT broker over an arbitrary byte-stream transport, so developers can connect, publish, subscribe and receive messages without hand-writing the MQTT 3.1.1 wire protocol. The library owns protocol framing (control-packet encoding/decoding, packet identifiers, keepalive timing) and hands application messages to a user callback, while delegating the actual bytes to a pluggable network connection.

---

## Background & Problem

Without such a library, every project that needs MQTT on a constrained device must re-implement the binary control-packet format by hand: building the fixed header and remaining-length encoding, serialising UTF-8 string fields with two-byte length prefixes, tracking packet identifiers, acknowledging QoS 1 messages, and sending periodic keepalive pings. This is fiddly and error-prone, and bugs only surface as a broker silently dropping the connection.

With this library, the developer supplies a network connection object (anything that can open a socket and read/write bytes) and an optional message callback, then calls high-level operations — connect, publish, subscribe, unsubscribe, loop — and the library translates them to and from the MQTT byte stream. The contract below is expressed purely in terms of bytes on the wire and observable outcomes, independent of any particular implementation.

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

## Protocol Conventions (shared by all features)

All features below operate the client through a scripted scenario expressed as JSON. The top-level object configures the session and lists a sequence of `steps`:

- `server`: the broker endpoint, either `{"ip": "a.b.c.d"}` or `{"host": "name"}`, with optional `port` (default `1883`).
- `allow_connect` (default `true`): whether the underlying transport is allowed to open. `false` simulates a transport that refuses to connect.
- `stream` (default `false`): when `true`, the client is configured with an external payload sink instead of buffering payloads internally.
- `auto_advance_ms` (default `0`): amount by which the virtual millisecond clock auto-advances on every reading; used only to exercise timeout windows.

Each entry in `steps` has an `op`:

- `{"op":"inbound","bytes":"<hex>"}` — queue raw bytes as if the broker sent them (space-separated lowercase/uppercase hex). Produces no output.
- `{"op":"advance","ms":<n>}` — advance the virtual clock by `n` milliseconds. Produces no output.
- `{"op":"buffer","size":<n>}` — resize the client's packet buffer. Produces no output.
- `{"op":"connect","id":...,"user":...,"pass":...,"will_topic":...,"will_qos":...,"will_retain":...,"will_message":...}` — open a session. Only `id` is required; `quiet:true` performs the handshake without emitting output (used to set up later steps).
- `{"op":"publish","topic":...,"payload":"<text>"|"payload_bytes":"<hex>","retained":<bool>}`
- `{"op":"subscribe","topic":...,"qos":<n>}` / `{"op":"unsubscribe","topic":...}`
- `{"op":"loop"}` — service the connection once (process one inbound packet and/or emit keepalive).
- `{"op":"disconnect"}` / `{"op":"state"}` / `{"op":"connected"}`

Output is line-oriented and raw. For each emitting step the adapter prints the boolean outcome (`1`/`0`) of the operation, any wire bytes it transmitted on a `sent=<hex>` line (empty when nothing was sent), the session `state=<int>` where relevant, and, for serviced inbound messages, a `message ...` line. Session-state integers are protocol-neutral: `0` connected, `-1` disconnected, `-2` connect-failed, `-4` timeout, and a positive value mirrors a broker CONNACK return code. All transmitted/received bytes follow the MQTT 3.1.1 control-packet wire format (protocol level `0x04`, protocol name `MQTT`, default keepalive `15` seconds, default packet buffer `128` bytes).

---

## Core Features

### Feature 1: Establishing a Session (CONNECT / CONNACK)

**As a developer**, I want to open and tear down an MQTT session against a broker, so I can authenticate, declare a last-will, and detect connection failures up front.

**Expected Behavior / Usage:**

*1.1 Encoding the CONNECT packet — successful connection with optional credentials and will*

Opening a session transmits a single CONNECT control packet, then waits for the broker's CONNACK. The CONNECT packet begins with fixed header `0x10`, a remaining-length byte, the protocol name (`0x00 0x04 'M' 'Q' 'T' 'T'`), protocol level `0x04`, a connect-flags byte, the two-byte keepalive (`0x00 0x0f`), and the UTF-8 client identifier (two-byte length prefix + bytes). The connect-flags byte encodes which optional fields follow: a username sets bit `0x80`, a password (only honoured when a username is present) sets bit `0x40`, and a last-will sets bit `0x04` plus its QoS (`<<3`) and retain (`<<5`); the default flags value with none of these is `0x02` (clean session). Optional fields are appended in order: will-topic, will-message, username, password — each a length-prefixed UTF-8 string. When the broker replies with a success CONNACK (`0x20 0x02 0x00 0x00`) the call returns `1` and the session state becomes `0`. A password supplied without a username is ignored (the packet is identical to the no-credentials packet). A host-name endpoint connects identically to an IP endpoint.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_connect_packets.json`

```json
{
    "description": "A client opens an MQTT session by sending a CONNECT control packet and then waiting for the broker's CONNACK. Given an identifier and optional credentials and/or last-will settings, the client serialises the CONNECT packet on the wire and, on a success CONNACK, reports a connected return and a connected session state. Each case supplies the connection parameters and the broker's CONNACK and observes the exact CONNECT bytes transmitted, the boolean outcome and the resulting session state.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1"}]},
            "expected_output": "connect=1\nstate=0\nsent=10 18 00 04 [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] 04 02 00 0f 00 0c 63 6c 69 65 6e 74 5f 74 65 73 74 31\n"
        },
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "user": "user", "pass": "pass"}]},
            "expected_output": "connect=1\nstate=0\nsent=10 24 00 04 [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] 04 c2 00 0f 00 0c 63 6c 69 65 6e 74 5f 74 65 73 74 31 00 04 75 73 65 72 00 04 70 61 73 73\n"
        }
    ]
}
```

*1.2 Connection failure modes*

A connection that cannot complete reports a specific failure state and (where applicable) transmits nothing. If the transport refuses to open, the call returns `0`, state becomes `-2` (connect-failed) and no bytes are sent. If the transport opens but the broker never sends a CONNACK, the client gives up after a fixed socket-timeout window, returning `0` with state `-4` (timeout) — note the CONNECT packet was still transmitted before the wait. If the broker answers with a non-zero CONNACK return code (e.g. `0x20 0x02 0x00 0x01`), the call returns `0` and the state exposes that broker return code (here `1`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_connect_failures.json`

```json
{
    "description": "Connection attempts that cannot complete report failure with a specific session state rather than a generic error. If the underlying transport refuses to open, the client reports a connect-failed state and transmits nothing. If the transport opens but the broker never answers, the client gives up after a fixed timeout window and reports a timeout state. If the broker answers with a non-zero CONNACK return code, the client reports failure and exposes that broker return code as the session state.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "allow_connect": false, "steps": [{"op": "connect", "id": "client_test1"}]},
            "expected_output": "connect=0\nstate=-2\nsent=\n"
        },
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 01"}, {"op": "connect", "id": "client_test1"}]},
            "expected_output": "connect=0\nstate=1\nsent=10 18 00 04 [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] 04 02 00 0f 00 0c 63 6c 69 65 6e 74 5f 74 65 73 74 31\n"
        }
    ]
}
```

*1.3 Clean disconnect and reconnect*

Disconnecting a live session transmits a DISCONNECT control packet (`0xe0 0x00`), closes the transport (so `connected` becomes `0`) and returns the session to state `-1`. The same client can subsequently open a fresh session, transmitting a new CONNECT packet and reaching state `0` on a success CONNACK.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_disconnect_reconnect.json`

```json
{
    "description": "A connected client can be cleanly disconnected, which transmits a DISCONNECT control packet, closes the transport and returns the session to a disconnected state with no live connection. After disconnecting, the same client can open a fresh session again, transmitting a new CONNECT packet and reaching the connected state on a success CONNACK.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1"}, {"op": "disconnect"}, {"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1"}]},
            "expected_output": "connect=1\nstate=0\nsent=10 18 00 04 [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] 04 02 00 0f 00 0c 63 6c 69 65 6e 74 5f 74 65 73 74 31\ndisconnect\nconnected=0\nstate=-1\nsent=e0 00\nconnect=1\nstate=0\nsent=10 18 00 04 [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] [a hex-encoded four-character string] 04 02 00 0f 00 0c 63 6c 69 65 6e 74 5f 74 65 73 74 31\n"
        }
    ]
}
```

---

### Feature 2: Publishing Messages (PUBLISH)

**As a developer**, I want to publish application messages to topics, so I can send sensor data or commands to the broker.

**Expected Behavior / Usage:**

*2.1 Encoding the PUBLISH packet*

A publish on a live session transmits a PUBLISH control packet: fixed header `0x30` (or `0x31` when the retain flag is set), a remaining-length byte, the length-prefixed UTF-8 topic, then the raw payload bytes. The payload may be a text string or an arbitrary byte sequence (binary, including embedded `0x00` bytes); it is copied verbatim with no terminator. The call returns `1` on success.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_publish.json`

```json
{
    "description": "A connected client publishes an application message to a topic by transmitting a PUBLISH control packet. The packet carries the topic and the raw payload bytes; the payload may be supplied as a text string or as an arbitrary byte sequence (including embedded zero bytes). An optional retained flag is encoded into the packet's fixed-header flags. Each case observes the exact PUBLISH bytes transmitted and the boolean outcome.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "publish", "topic": "topic", "payload": "payload"}]},
            "expected_output": "publish=1\nsent=30 0e 00 05 74 6f 70 69 63 70 61 79 6c 6f 61 64\n"
        },
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "publish", "topic": "topic", "payload_bytes": "01 02 03 00 05", "retained": true}]},
            "expected_output": "publish=1\nsent=31 0c 00 05 74 6f 70 69 63 01 02 03 00 05\n"
        }
    ]
}
```

*2.2 Publish rejection*

A publish is rejected — returns `0` and transmits nothing — when there is no live session, or when the topic plus payload would not fit in the client's packet buffer (default `128` bytes).

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_publish_rejected.json`

```json
{
    "description": "A publish attempt is rejected (no packet is transmitted and the outcome is false) when the preconditions are not met: publishing on a client that has no live session is refused, and publishing a message whose topic plus payload would not fit in the client's send buffer is refused.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "publish", "topic": "topic", "payload": "payload"}]},
            "expected_output": "publish=0\nsent=\n"
        },
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "publish", "topic": "topic", "payload": "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"}]},
            "expected_output": "publish=0\nsent=\n"
        }
    ]
}
```

---

### Feature 3: Subscriptions (SUBSCRIBE / UNSUBSCRIBE)

**As a developer**, I want to subscribe to and unsubscribe from topic filters, so I can choose which messages the broker delivers to me.

**Expected Behavior / Usage:**

*3.1 Encoding the SUBSCRIBE packet*

A subscribe on a live session transmits a SUBSCRIBE control packet: fixed header `0x82`, a remaining-length byte, a two-byte packet identifier (incremented per outbound request, starting from `1` so the first request after connecting is `0x00 0x02`), the length-prefixed UTF-8 topic filter, and a one-byte requested maximum QoS (defaulting to `0`). The call returns `1` as long as the resulting packet fits in the buffer; the largest topic filter that fits at the default buffer size is accepted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_subscribe.json`

```json
{
    "description": "A connected client subscribes to a topic filter by transmitting a SUBSCRIBE control packet carrying an incrementing packet identifier, the topic filter and the requested maximum QoS byte (defaulting to 0). A topic filter is accepted as long as the resulting packet fits in the send buffer. Each case observes the exact SUBSCRIBE bytes transmitted and the boolean outcome.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "subscribe", "topic": "topic"}]},
            "expected_output": "subscribe=1\nsent=82 0a 00 02 00 05 74 6f 70 69 63 00\n"
        },
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "subscribe", "topic": "topic", "qos": 1}]},
            "expected_output": "subscribe=1\nsent=82 0a 00 02 00 05 74 6f 70 69 63 01\n"
        }
    ]
}
```

*3.2 Subscribe rejection*

A subscribe is rejected (returns `0`, transmits nothing) when the requested QoS is outside the supported range (only `0` and `1` are valid; e.g. `2` or `2[a hex-encoded four-character string]` are refused), when there is no live session, or when the topic filter is too large for the buffer.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_subscribe_rejected.json`

```json
{
    "description": "A subscribe attempt is rejected (no packet is transmitted, outcome false) when its arguments are invalid or preconditions fail: a requested QoS outside the supported range is refused, subscribing without a live session is refused, and a topic filter too large for the send buffer is refused.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "subscribe", "topic": "topic", "qos": 2}]},
            "expected_output": "subscribe=0\nsent=\n"
        },
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "subscribe", "topic": "topic"}]},
            "expected_output": "subscribe=0\nsent=\n"
        }
    ]
}
```

*3.3 Encoding the UNSUBSCRIBE packet*

An unsubscribe on a live session transmits an UNSUBSCRIBE control packet: fixed header `0xa2`, a remaining-length byte, a two-byte packet identifier, and the length-prefixed UTF-8 topic filter. Unsubscribing without a live session is refused (returns `0`, transmits nothing).

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_unsubscribe.json`

```json
{
    "description": "A connected client cancels a subscription by transmitting an UNSUBSCRIBE control packet carrying an incrementing packet identifier and the topic filter. Unsubscribing without a live session is refused (no packet transmitted, outcome false).",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "unsubscribe", "topic": "topic"}]},
            "expected_output": "unsubscribe=1\nsent=a2 09 00 02 00 05 74 6f 70 69 63\n"
        },
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "unsubscribe", "topic": "topic"}]},
            "expected_output": "unsubscribe=0\nsent=\n"
        }
    ]
}
```

---

### Feature 4: Receiving Messages (inbound PUBLISH dispatch)

**As a developer**, I want incoming messages parsed and handed to my callback, so I can react to data the broker sends me.

**Expected Behavior / Usage:**

*4.1 Delivering a message to the callback*

When the connection is serviced and an inbound QoS 0 PUBLISH packet (fixed header `0x30`) is available, it is parsed and delivered to the message handler with the topic decoded as text, the raw payload bytes, and the payload length. Servicing returns `1`. Messages up to the buffer's maximum size are delivered in full. The output renders the delivered message as `message topic=<topic> payload=<hex bytes> length=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_receive_callback.json`

```json
{
    "description": "While servicing the connection, an incoming QoS 0 PUBLISH packet is parsed and delivered to the application's message handler with the topic (as text), the raw payload bytes and the payload length. Messages up to the buffer's maximum size are delivered in full. Each case feeds inbound PUBLISH bytes, services the connection once and observes the delivered topic, payload and length.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "inbound", "bytes": "30 0e 00 05 74 6f 70 69 63 70 61 79 6c 6f 61 64"}, {"op": "loop"}]},
            "expected_output": "loop=1\nmessage topic=topic payload=70 61 79 6c 6f 61 64 length=7\nsent=\n"
        }
    ]
}
```

*4.2 QoS 1 delivery and acknowledgement*

An inbound QoS 1 PUBLISH (fixed header `0x32`) carries a two-byte packet identifier after the topic. It is delivered to the message handler exactly like a QoS 0 message, and the client additionally transmits a PUBACK control packet (`0x40 0x02` followed by the echoed two-byte packet identifier) to acknowledge it.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_receive_qos1.json`

```json
{
    "description": "An incoming QoS 1 PUBLISH packet (which carries a packet identifier) is delivered to the message handler with topic, payload and length, and the client acknowledges it by transmitting a PUBACK control packet echoing that packet identifier. The case observes the delivered message and the PUBACK bytes transmitted.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "inbound", "bytes": "32 10 00 05 74 6f 70 69 63 12 34 70 61 79 6c 6f 61 64"}, {"op": "loop"}]},
            "expected_output": "loop=1\nmessage topic=topic payload=70 61 79 6c 6f 61 64 length=7\nsent=40 02 12 34\n"
        }
    ]
}
```

*4.3 Oversized messages are dropped*

An inbound PUBLISH whose total size exceeds the client's packet buffer is silently dropped: it is not delivered to the message handler and no acknowledgement is sent. Servicing the connection still returns `1`. The output renders `message=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_oversized_dropped.json`

```json
{
    "description": "An incoming PUBLISH packet whose total size exceeds the client's receive buffer is silently dropped: it is not delivered to the message handler. Servicing the connection still succeeds. The case feeds an over-large PUBLISH and observes that no message is delivered.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "inbound", "bytes": "30 7f 00 05 74 6f 70 69 63 70 61 79 6c 6f 61 64 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41"}, {"op": "loop"}]},
            "expected_output": "loop=1\nmessage=none\nsent=\n"
        }
    ]
}
```

*4.4 Enlarging the buffer for bigger messages*

The packet buffer can be resized at runtime. After enlarging it to fit a bigger packet, an inbound PUBLISH that would otherwise be dropped is delivered in full to the message handler.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_resize_buffer.json`

```json
{
    "description": "The receive/send buffer can be enlarged at runtime. After growing the buffer to accommodate a larger packet, an incoming PUBLISH that would otherwise be too big is delivered in full to the message handler. The case grows the buffer, feeds a larger PUBLISH and observes the delivered topic, payload and length.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "buffer", "size": 129}, {"op": "inbound", "bytes": "30 7f 00 05 74 6f 70 69 63 70 61 79 6c 6f 61 64 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41"}, {"op": "loop"}]},
            "expected_output": "loop=1\nmessage topic=topic payload=70 61 79 6c 6f 61 64 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 length=120\nsent=\n"
        }
    ]
}
```

*4.5 Streaming payloads to an external sink*

When the client is configured with an external payload sink (`stream:true`), an inbound PUBLISH still delivers the topic and payload length to the message handler while the payload bytes are streamed out to the sink. In stream mode a payload larger than the packet buffer is still delivered (topic and length) rather than dropped. In stream mode the output renders the message without the payload bytes: `message topic=<topic> length=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_stream.json`

```json
{
    "description": "When the client is configured with an external payload sink (stream), an incoming PUBLISH still delivers the topic and payload length to the message handler, while the payload bytes are streamed out to the sink. In stream mode, payloads larger than the receive buffer are still delivered (topic and length) rather than dropped. Each case feeds inbound PUBLISH bytes and observes the delivered topic and length.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "stream": true, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "inbound", "bytes": "30 0e 00 05 74 6f 70 69 63 70 61 79 6c 6f 61 64"}, {"op": "loop"}]},
            "expected_output": "loop=1\nmessage topic=topic length=7\nsent=\n"
        }
    ]
}
```

---

### Feature 5: Keepalive (loop-driven liveness)

**As a developer**, I want the client to keep the session alive and detect dead connections, so the broker does not drop me and I learn when the link is gone.

**Expected Behavior / Usage:**

*5.1 Idle keepalive ping*

When the keepalive interval (`15` seconds) elapses with no traffic, servicing the connection transmits a PINGREQ control packet (`0xc0 0x00`). When the broker answers with a PINGRESP (`0xd0 0x00`), the outstanding ping is cleared, so after another idle interval the client issues a fresh PINGREQ rather than disconnecting.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_keepalive_ping.json`

```json
{
    "description": "To keep an idle session alive, once the keepalive interval elapses with no traffic the client transmits a PINGREQ control packet when servicing the connection. When the broker answers with a PINGRESP, the outstanding ping is cleared so that, after another idle interval, the client issues a fresh PINGREQ instead of disconnecting. The case advances a virtual clock past the keepalive interval, services the connection, supplies a PINGRESP, then advances again and observes a second PINGREQ.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "advance", "ms": 16000}, {"op": "loop"}, {"op": "inbound", "bytes": "d0 00"}, {"op": "loop"}, {"op": "advance", "ms": 16000}, {"op": "loop"}]},
            "expected_output": "loop=1\nmessage=none\nsent=c0 00\nloop=1\nmessage=none\nsent=\nloop=1\nmessage=none\nsent=c0 00\n"
        }
    ]
}
```

*5.2 Hung-connection disconnect*

If a transmitted PINGREQ goes unanswered, the client detects the dead connection: at the next keepalive interval with a ping still outstanding, servicing the connection returns `0`, the transport is closed, and the session enters state `-4` (timeout).

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_keepalive_timeout.json`

```json
{
    "description": "If a transmitted PINGREQ goes unanswered, the client detects the dead connection: at the next keepalive interval with a ping still outstanding, servicing the connection fails, the transport is closed and the session enters a timeout state. The case sends a ping, withholds any PINGRESP, advances past the next interval, services the connection (which now fails) and observes the timeout state.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "advance", "ms": 16000}, {"op": "loop"}, {"op": "advance", "ms": 16000}, {"op": "loop"}, {"op": "state"}]},
            "expected_output": "loop=1\nmessage=none\nsent=c0 00\nloop=0\nmessage=none\nsent=\nstate=-4\n"
        }
    ]
}
```

*5.3 Acknowledged traffic refreshes the keepalive window*

Activity on the connection refreshes the keepalive timers. Receiving and acknowledging a QoS 1 PUBLISH updates both the inbound and outbound activity timestamps (the latter via the PUBACK it sends); if the connection is next serviced within a keepalive interval of that activity, no PINGREQ is transmitted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_keepalive_traffic_resets.json`

```json
{
    "description": "Acknowledged inbound traffic refreshes the keepalive window so no spurious ping is emitted. Receiving and acknowledging a QoS 1 PUBLISH updates the activity timers; if the next service occurs within a keepalive interval of that activity, no PINGREQ is transmitted. The case delivers a QoS 1 message before the interval elapses, then services the connection again shortly after and observes that no ping is sent.",
    "cases": [
        {
            "input": {"server": {"ip": "172.16.0.2"}, "steps": [{"op": "inbound", "bytes": "20 02 00 00"}, {"op": "connect", "id": "client_test1", "quiet": true}, {"op": "advance", "ms": 10000}, {"op": "inbound", "bytes": "32 10 00 05 74 6f 70 69 63 12 34 70 61 79 6c 6f 61 64"}, {"op": "loop"}, {"op": "advance", "ms": 10000}, {"op": "loop"}]},
            "expected_output": "loop=1\nmessage topic=topic payload=70 61 79 6c 6f 61 64 length=7\nsent=40 02 12 34\nloop=1\nmessage=none\nsent=\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured MQTT client library implementing the features above. The core protocol logic (control-packet encoding/decoding, packet-identifier tracking, keepalive timing, message dispatch) must be decoupled from standard I/O and JSON parsing, and must talk to the network only through a small connection abstraction (open, read bytes, write bytes, close) and an optional payload sink. The physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable program — logically (and ideally physically) separated from the core — that reads a single JSON scenario from stdin, drives the client through the scripted `steps` against an in-memory scripted network peer and a virtual clock, and prints the observable results (transmitted bytes, return codes, session state, delivered messages) to stdout, matching the per-feature contracts above. All transmitted/received bytes are MQTT 3.1.1 control packets; `sent=` lines list bytes as space-separated two-digit hex; session-state integers are protocol-neutral (`0` connected, `-1` disconnected, `-2` connect-failed, `-4` timeout, positive = broker CONNACK return code).

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- structure must align with other fixed-size headers in the protocol spec
