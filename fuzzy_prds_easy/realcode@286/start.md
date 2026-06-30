## Product Requirement Document

# Real-Time Event Protocol Codec — Engine.IO / Socket.IO Wire Format

## Project Goal

Build a protocol codec library that turns high-level real-time messaging intents (connect to a namespace, emit an event, reply with an acknowledgement, decode an incoming frame) into the exact bytes of the Engine.IO/Socket.IO transport wire format, and back again. Application developers can speak in terms of *event names, namespaces, argument lists and binary attachments* and let the codec handle the textual frame grammar, attachment placeholder bookkeeping, and handshake URL construction — without ever hand-assembling protocol strings.

---

## Background & Problem

The Engine.IO/Socket.IO transport encodes every message as a short text frame whose meaning is determined by a numeric prefix (`2`=ping, `3`=pong, `0`=transport open, `40`=connected, `41`=disconnected, `42`=event, `43`=ack, `44`=error, with a `4`-prefixed binary variant `45`/`46` carrying out-of-band attachments). Namespaces, acknowledgement ids and JSON argument arrays are packed into specific positions within that frame, and binary arguments must be lifted out into separate ordered attachment payloads and replaced inline by placeholder objects.

Without this library, developers are forced to concatenate and parse these frame strings by hand: counting attachments, inserting the `-` separator, deciding when a default port should be dropped from a URL, remembering that protocol v3 and v4 disagree about whether the default namespace gets a connect frame and where auth/query data live. This is repetitive, easy to get subtly wrong, and tightly coupled to protocol-version quirks.

With this library, the developer describes *what* to send or asks *what was received*, and the codec produces or interprets the precise wire frames — including correct handshake URLs, attachment placeholdering, namespace/id placement and protocol-version differences.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The codec spans several distinct responsibilities (URL construction, outbound encoding, inbound decoding, attachment handling, payload rendering). It MUST NOT be a single "god file". Output a clear multi-file layout that separates the codec core from the execution adapter; do not over-engineer, but reflect a production-grade repository.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, not the internal data model of the codec. The codec core must be decoupled from stdin/stdout and from the adapter's command JSON. The adapter is solely responsible for translating each JSON command into idiomatic calls on the codec and rendering the result.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core encode/decode and output formatting into distinct units (SRP). The codec must be open to new message kinds without modifying existing ones (OCP). Message representations must be substitutable behind a common message abstraction (LSP). Keep the codec interface small and cohesive (ISP). The adapter depends on the codec abstraction, not on concrete I/O (DIP).

4. **Robustness & Interface Design:** The public codec interface must be idiomatic to the target language and hide framing details. Edge cases (empty/unrecognized frames, incomplete binary messages awaiting attachments, unsupported URL scheme) must be modeled explicitly rather than producing corrupt frames. Errors surfaced to stdout must be normalized to language-neutral categories.

---

## Core Features

### Feature 1: Handshake / Connection URL Construction

**As a developer**, I want to turn a server endpoint plus my transport and protocol choices into the exact handshake URL, so I can open a connection without manually assembling query strings or worrying about default ports.

**Expected Behavior / Usage:**

Given a base server URI (`http`/`https`/`ws`/`wss`), a transport flag (websocket vs long-polling), a protocol version number, an optional mount path, and an optional set of query parameters, produce the full handshake URL. The output scheme follows the transport flag: with the websocket transport an `http(s)` base maps to `ws(s)`, otherwise it stays `http(s)`. A port equal to the scheme's default (80 for the plaintext schemes, 443 for the TLS schemes) is omitted; a port that is *not* the scheme's default is kept verbatim (e.g. plaintext on 80 is dropped, but TLS on 80 is kept). When no mount path is given the path defaults to `/socket.io`; otherwise the provided path is used. The fixed query `EIO=<version>` and `transport=polling|websocket` are always appended, followed by each supplied query parameter as `&key=value`. The result is emitted as `url=<full url>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_handshake_url.json`

```json
[a specific JSON string to replace byte arrays]
    "description": "Build the Engine.IO handshake/connection URL from a server endpoint, transport choice (long-polling vs websocket), protocol version, optional mount path and query parameters. Default ports for the scheme are dropped; a non-default port for the scheme is preserved.",
    "cases": [
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "handshake_url", "ws": false, "uri": "http://localhost", "eio": 4, "path": "", "query": [a specific JSON string to replace byte arrays]"token": "test"}},
            "expected_output": "url=http://localhost/socket.io/?EIO=4&transport=polling&token=test\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "handshake_url", "ws": false, "uri": "https://localhost:443", "eio": 4, "path": "/sio", "query": [a specific JSON string to replace byte arrays]"token": "test"}},
            "expected_output": "url=https://localhost/sio/?EIO=4&transport=polling&token=test\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "handshake_url", "ws": true, "uri": "ws://localhost:80", "eio": 4, "path": "", "query": [a specific JSON string to replace byte arrays]}},
            "expected_output": "url=ws://localhost/socket.io/?EIO=4&transport=websocket\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "handshake_url", "ws": false, "uri": "https://localhost:80", "eio": 4, "path": "", "query": [a specific JSON string to replace byte arrays]"token": "test"}},
            "expected_output": "url=https://localhost:80/socket.io/?EIO=4&transport=polling&token=test\n"
        }
    ]
}
```

---

### Feature 2: Outbound Message Encoding

**As a developer**, I want to encode connection, event and acknowledgement intents into wire frames, so I can hand structured data to the codec and let it produce protocol-correct text and attachment frames.

**Expected Behavior / Usage:**

All encoders emit one `frame=<text>` line for the text frame. When any argument is binary, the codec lifts each binary value out into an ordered out-of-band attachment, replaces it inline with a placeholder object `[a specific JSON string to replace byte arrays]"_placeholder":true,"num":N}` (N counts from 0 in argument order), switches the frame's numeric prefix to the binary variant, prefixes the text with `<count>-`, and emits one `attachment=<comma-separated byte values>` line per attachment in order.

*2.1 Encode an event — emit an event-name + arguments frame*

Encode an outbound event from an event name, an optional namespace, and an argument list. The text frame is `42` followed by `<namespace>,` when a namespace is present, then a JSON array whose first element is the event name and whose remaining elements are the arguments. With binary arguments the prefix becomes `45<count>-`. A null/empty namespace is omitted entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_encode_event.json`

```json
[a specific JSON string to replace byte arrays]
    "description": "Encode an outbound event message with an event name, optional namespace and an arbitrary argument list. Plain values are inlined as a JSON array prefixed by the event name; binary arguments are replaced by placeholder objects ([a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":N}) and emitted as separate ordered attachment payloads, switching the frame prefix to the binary form.",
    "cases": [
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_event", "eio": 4, "event": "test", "namespace": "", "data": []},
            "expected_output": "frame=42[\"test\"]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_event", "eio": 4, "event": "test", "namespace": "/nsp", "data": [true, false, 123]},
            "expected_output": "frame=42/nsp,[\"test\",true,false,123]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_event", "eio": 4, "event": "test", "namespace": "", "data": [[a specific JSON string to replace byte arrays]"$bytes": [1, 2, 3]}]},
            "expected_output": "frame=451-[\"test\",[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]\nattachment=1,2,3\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_event", "eio": 4, "event": "event", "namespace": "/test", "data": [123456.789, [a specific JSON string to replace byte arrays]"User": "test", "Password": "hello"}, [a specific JSON string to replace byte arrays]"Size": 2023, "Name": "test.txt", "Bytes": [a specific JSON string to replace byte arrays]"$bytes": [240, 159, 144, 174, 240, 159, 141, 186]}}]},
            "expected_output": "frame=451-/test,[\"event\",123456.789,[a specific JSON string to replace byte arrays]\"User\":\"test\",\"Password\":\"hello\"},[a specific JSON string to replace byte arrays]\"Size\":2023,\"Name\":\"test.txt\",\"Bytes\":[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}}]\nattachment=240,159,144,174,240,159,141,186\n"
        }
    ]
}
```

*2.2 Encode an event awaiting acknowledgement — same as 2.1 but with an ack id*

Encode an outbound event that also requests an acknowledgement. Identical to a plain event, except a numeric acknowledgement id is inserted immediately before the JSON argument array (after the namespace, when one is present). Binary arguments behave exactly as in 2.1.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_encode_event_ack.json`

```json
[a specific JSON string to replace byte arrays]
    "description": "Encode an outbound event message that also requests an acknowledgement: the same event encoding as a plain event, but the numeric acknowledgement id is inserted directly before the JSON argument array (after the namespace, when present). Binary arguments still become placeholders plus ordered attachments.",
    "cases": [
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_event_ack", "eio": 4, "event": "event", "packet_id": 0, "namespace": null, "data": ["string", 1, true, null]},
            "expected_output": "frame=420[\"event\",\"string\",1,true,null]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_event_ack", "eio": 4, "event": "event", "packet_id": 23, "namespace": "/test", "data": ["string", 1, true, null]},
            "expected_output": "frame=42/test,23[\"event\",\"string\",1,true,null]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_event_ack", "eio": 4, "event": "event", "packet_id": 8964, "namespace": "/test", "data": [123456.789, [a specific JSON string to replace byte arrays]"User": "test", "Password": "hello"}, [a specific JSON string to replace byte arrays]"Size": 2023, "Name": "test.txt", "Bytes": [a specific JSON string to replace byte arrays]"$bytes": [240, 159, 144, 174, 240, 159, 141, 186]}}]},
            "expected_output": "frame=451-/test,8964[\"event\",123456.789,[a specific JSON string to replace byte arrays]\"User\":\"test\",\"Password\":\"hello\"},[a specific JSON string to replace byte arrays]\"Size\":2023,\"Name\":\"test.txt\",\"Bytes\":[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}}]\nattachment=240,159,144,174,240,159,141,186\n"
        }
    ]
}
```

*2.3 Encode an acknowledgement reply — emit an id-bearing argument frame with no event name*

Encode an outbound acknowledgement that replies to a previously received id-bearing request. There is no event name: the text frame is `43` followed by `<namespace>,` when present, then the acknowledgement id, then the JSON argument array. With binary arguments the prefix becomes `46<count>-`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_encode_ack.json`

```json
[a specific JSON string to replace byte arrays]
    "description": "Encode an outbound acknowledgement message replying to a previously received id-bearing request. There is no event name; the argument array is emitted directly, preceded by the acknowledgement id (and namespace when present). Binary arguments become placeholders plus ordered attachments and switch the frame to the binary-ack prefix.",
    "cases": [
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_ack", "eio": 4, "packet_id": 0, "namespace": null, "data": ["string", 1, true, null]},
            "expected_output": "frame=430[\"string\",1,true,null]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_ack", "eio": 4, "packet_id": 23, "namespace": "/test", "data": ["string", 1, true, null]},
            "expected_output": "frame=43/test,23[\"string\",1,true,null]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_ack", "eio": 4, "packet_id": 8964, "namespace": "/test", "data": [123456.789, [a specific JSON string to replace byte arrays]"User": "test", "Password": "hello"}, [a specific JSON string to replace byte arrays]"Size": 2023, "Name": "test.txt", "Bytes": [a specific JSON string to replace byte arrays]"$bytes": [240, 159, 144, 174, 240, 159, 141, 186]}}]},
            "expected_output": "frame=461-/test,8964[123456.789,[a specific JSON string to replace byte arrays]\"User\":\"test\",\"Password\":\"hello\"},[a specific JSON string to replace byte arrays]\"Size\":2023,\"Name\":\"test.txt\",\"Bytes\":[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}}]\nattachment=240,159,144,174,240,159,141,186\n"
        }
    ]
}
```

*2.4 Encode a namespace connection — protocol-version-dependent connect frame*

Encode the frame that joins a namespace, which differs by protocol version. Under version 3: the default namespace produces no frame at all (output `frame=null`); a named namespace produces `40<namespace>` optionally followed by `?key=value(&key=value...)` built from the connection query, then a trailing `,`. Under version 4: the default namespace always produces `40`; a named namespace produces `40<namespace>,`; an auth object is serialized inline as JSON appended after the prefix/namespace; the connection query is NOT embedded in this frame (it is carried only by the handshake URL of Feature 1).

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_encode_connect.json`

```json
[a specific JSON string to replace byte arrays]
    "description": "Encode the namespace-connection frame. Under protocol v3 the default namespace produces no frame (none is sent), while a named namespace yields a connect frame that carries the namespace and, optionally, the connection query string. Under protocol v4 the default namespace always produces a connect frame, an auth object is serialized inline as JSON, and connection queries are not embedded in this frame.",
    "cases": [
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_connect", "eio": 3, "namespace": null, "auth": null, "query": null},
            "expected_output": "frame=null\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_connect", "eio": 3, "namespace": "/test", "auth": null, "query": null},
            "expected_output": "frame=40/test,\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_connect", "eio": 3, "namespace": "/test", "auth": null, "query": [a specific JSON string to replace byte arrays]"key": "value"}},
            "expected_output": "frame=40/test?key=value,\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_connect", "eio": 4, "namespace": null, "auth": null, "query": null},
            "expected_output": "frame=40\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_connect", "eio": 4, "namespace": null, "auth": [a specific JSON string to replace byte arrays]"userId": 1}, "query": null},
            "expected_output": "frame=40[a specific JSON string to replace byte arrays]\"userId\":1}\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "encode_connect", "eio": 4, "namespace": "/test", "auth": [a specific JSON string to replace byte arrays]"userId": 1}, "query": null},
            "expected_output": "frame=40/test,[a specific JSON string to replace byte arrays]\"userId\":1}\n"
        }
    ]
}
```

---

### Feature 3: Inbound Frame Decoding

**As a developer**, I want to decode received frames back into structured messages, so I can react to events, acknowledgements, errors and lifecycle signals without parsing protocol strings myself.

**Expected Behavior / Usage:**

Decode one or more received frames into structured messages. Every decoded message is rendered as a `type=<kind>` line followed by kind-specific fields, one `key=value` per line. A `namespace=` line appears only for a non-default namespace; an `id=` line appears only when the frame carried an acknowledgement id. When multiple messages are produced, they are separated by a line containing `---`. Frames that carry no decodable message produce `message=none`.

*3.1 Decode a text frame — single self-contained frame*

Decode a single text frame. The numeric prefix selects the kind: `2`→`ping`, `3`→`pong`, `0`→`opened` (carrying `sid`, `ping_interval`, `ping_timeout`, comma-joined `upgrades`), `40`→`connected` (optional namespace, optional `sid`), `41`→`disconnected` (optional namespace), `42`→`event` (event name, optional namespace, optional id, JSON `data` array with the event-name element removed), `43`→`ack` (optional namespace, id, JSON `data`), `44`→`error` (optional namespace, normalized `error_message`; the v3 form is a bare quoted string, the v4 form is a `[a specific JSON string to replace byte arrays]"message":...}` object). Empty or unrecognized frames produce `message=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_decode_text.json`

```json
[a specific JSON string to replace byte arrays]
    "description": "Decode a single inbound text frame into a structured message. The numeric prefix selects the kind (heartbeat ping/pong, transport opened handshake, namespace connected/disconnected, event, acknowledgement, connect error). Optional namespace, acknowledgement id, event name and JSON argument payload are extracted from their wire positions; unrecognized or empty frames yield no message.",
    "cases": [
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "2"}]},
            "expected_output": "type=ping\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "0[a specific JSON string to replace byte arrays]\"sid\":\"wOuAvDB9Jj6yE0VrAL8N\",\"upgrades\":[\"websocket\"],\"pingInterval\":25000,\"pingTimeout\":30000}"}]},
            "expected_output": "type=opened\nsid=wOuAvDB9Jj6yE0VrAL8N\nping_interval=25000\nping_timeout=30000\nupgrades=websocket\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "40[a specific JSON string to replace byte arrays]\"sid\":\"aMA_EmVTuzpgR16PAc4w\"}"}]},
            "expected_output": "type=connected\nsid=aMA_EmVTuzpgR16PAc4w\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "40/test,[a specific JSON string to replace byte arrays]\"sid\":\"aMA_EmVTuzpgR16PAc4w\"}"}]},
            "expected_output": "type=connected\nnamespace=/test\nsid=aMA_EmVTuzpgR16PAc4w\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "42/test,[\"hi\",\"V3: onAny\"]"}]},
            "expected_output": "type=event\nevent=hi\nnamespace=/test\ndata=[\"V3: onAny\"]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "42/test,17[\"cool\"]"}]},
            "expected_output": "type=event\nevent=cool\nnamespace=/test\nid=17\ndata=[]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "431[\"nice\"]"}]},
            "expected_output": "type=ack\nid=1\ndata=[\"nice\"]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "44[a specific JSON string to replace byte arrays]\"message\":\"Authentication error2\"}"}]},
            "expected_output": "type=error\nerror_message=Authentication error2\n"
        }
    ]
}
```

*3.2 Decode a binary message — leading text frame plus attachment frames*

Decode a binary message that spans a leading text frame (prefix `45`/`46`) plus one or more raw attachment frames. The text frame declares `<count>-`, optional namespace, optional acknowledgement id and the JSON payload containing binary placeholders. The structured message — kind `binary_event` (event name present) or `binary_ack` (no event name), with `attachment_count` and the placeholder-bearing `data` — is produced ONLY after all declared attachment frames have been received; until the count is satisfied, decoding yields no message (`message=none`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_decode_binary.json`

```json
[a specific JSON string to replace byte arrays]
    "description": "Decode an inbound binary message that spans a leading text frame plus one or more raw attachment frames. The text frame declares the attachment count, optional namespace, optional acknowledgement id and the JSON payload (with binary placeholders). The message is only produced once all declared attachment frames have arrived; until then nothing is emitted.",
    "cases": [
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "451-[\"1 params\",[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]"}, [a specific JSON string to replace byte arrays]"bytes": [0]}]},
            "expected_output": "type=binary_event\nevent=1 params\nattachment_count=1\ndata=[[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "451-/test,[\"1 params\",[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]"}, [a specific JSON string to replace byte arrays]"bytes": [0]}]},
            "expected_output": "type=binary_event\nevent=1 params\nnamespace=/test\nattachment_count=1\ndata=[[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "451-30[\"1 params\",[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]"}, [a specific JSON string to replace byte arrays]"bytes": [0]}]},
            "expected_output": "type=binary_event\nevent=1 params\nid=30\nattachment_count=1\ndata=[[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "decode", "eio": 4, "frames": [[a specific JSON string to replace byte arrays]"text": "461-6[[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]"}, [a specific JSON string to replace byte arrays]"bytes": [0]}]},
            "expected_output": "type=binary_ack\nid=6\nattachment_count=1\ndata=[[a specific JSON string to replace byte arrays]\"_placeholder\":true,\"num\":0}]\n"
        }
    ]
}
```

---

### Feature 4: Decoded Payload Rendering

**As a developer**, I want to render the argument payload of a decoded message back to a compact JSON string, so I can forward or inspect just the data without the framing.

**Expected Behavior / Usage:**

Given a decoded message kind and its received JSON text, render the stored arguments array as a compact (no whitespace) JSON string on a `payload=` line. For an `event` message the leading event-name element has already been consumed, so only the remaining arguments are rendered. For an `ack` message the full stored array is rendered as-is.

**Test Cases:** `rcb_tests/public_test_cases/feature4_extract_payload.json`

```json
[a specific JSON string to replace byte arrays]
    "description": "Render the JSON arguments array carried by a decoded message back to a compact JSON string. For an event message the leading event-name element has already been consumed, so only the remaining arguments are rendered; for an acknowledgement message the full stored array is rendered as-is.",
    "cases": [
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "extract_payload", "type": "Event", "text": "[\"event\",1]"},
            "expected_output": "payload=[1]\n"
        },
        [a specific JSON string to replace byte arrays]
            "input": [a specific JSON string to replace byte arrays]"op": "extract_payload", "type": "Ack", "text": "[\"event\",\"hello\",[a specific JSON string to replace byte arrays]\"user\":\"admin\",\"password\":\"test\"}]"},
            "expected_output": "payload=[\"event\",\"hello\",[a specific JSON string to replace byte arrays]\"user\":\"admin\",\"password\":\"test\"}]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codec implementing handshake-URL construction, outbound encoding (event, event-with-ack, ack, namespace connect), inbound decoding (text and multi-frame binary) and payload rendering, with the wire-format details and protocol-version differences fully encapsulated. Its physical structure must align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, dispatches to the matching codec operation, and prints the result to stdout exactly matching the per-leaf-feature contracts above (including byte-exact frames, attachment byte lists and normalized error categories). This adapter must be logically and physically separated from the codec core.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/[a specific JSON string to replace byte arrays]filename.stem}@[a specific JSON string to replace byte arrays]case_index.zfill(3)}.txt` (e.g. the first case of `feature1_handshake_url.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_handshake_url@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test, so it can be compared directly against `expected_output`.
