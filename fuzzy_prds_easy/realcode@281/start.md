## Product Requirement Document

# Binary Message-Protocol Codec & Frame Engine — Wire Serialization, Content Framing, and Authentication

## Project Goal

Build a client-side codec and framing engine for a binary publish/subscribe messaging protocol, so developers can turn structured method calls and messages into the exact bytes the protocol defines on the wire — and parse those bytes back — without hand-writing fragile byte manipulation for every field type, frame, and message header.

---

## Background & Problem

A binary messaging protocol defines a small set of primitive field types (bits, fixed-width integers, floats, length-prefixed strings, byte arrays, timestamps) and two composite types (a key/value *field table* and an ordered *array*). Methods sent to and received from the broker are sequences of such fields; messages additionally carry a property header and a body. Everything travels inside *frames*: a typed envelope with a channel number, a length, a payload, and an end marker.

Without a dedicated codec, every application re-implements this byte layout by hand — getting endianness, bit packing, length prefixes, and the property-flag bitmap subtly wrong, and leaking protocol details into business code. This project provides one well-defined contract for: serializing/parsing argument lists and composite values; encoding/decoding message property headers; reassembling chunked message bodies; producing authentication responses; emitting and parsing whole frames; and modeling protocol errors as typed conditions. Because the contract is the wire format itself, all byte-level outputs in this document are given as lowercase hexadecimal so they are unambiguous across languages.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This is a multi-responsibility domain (primitive codec, composite codec, property/header codec, body reassembly, authentication, frame I/O, error model); it MUST be organized as a clear multi-file tree (e.g. `src/`, `tests/`) rather than a single "god file", without over-engineering any single part.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases in the "Core Features" section are a **black-box contract** for an execution adapter, NOT the internal data model. The core codec/framing logic MUST be completely decoupled from stdin/stdout and JSON parsing. A thin execution adapter translates JSON commands into idiomatic calls to the core and renders results to the contract.

3. **Adherence to SOLID Design Principles:** Separate primitive-field coding, composite coding, header coding, framing, authentication, and error modeling into distinct cohesive units; keep the core open for extension (new field types / mechanisms) but closed for modification; depend on abstractions rather than on I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding byte-level complexity.
   - **Resilience:** Malformed or unsupported inputs must be modeled as explicit typed errors, not generic faults.

---

## Core Features

### Feature 1: Serialize An Argument List To Wire Bytes

**As a developer**, I want to serialize a positional list of typed method arguments into the exact protocol byte stream, so I can send well-formed methods without hand-coding byte layout.

**Expected Behavior / Usage:**

The request carries a `format` string with one type code per argument and a `values` list of typed values. The codes are: `b` bit, `o` octet (unsigned 8-bit), `B` short (unsigned 16-bit), `l` long (unsigned 32-bit), `L` long-long (unsigned 64-bit), `f` single-precision float, `s` short string (1-byte length prefix), `S` long string (4-byte length prefix), `x` byte array (4-byte length prefix), `T` timestamp, `F` field table, `A` array. Every fixed-width type is laid out in network (big-endian) byte order. Consecutive `b` (bit) arguments are packed together into shared octets, least-significant-bit first, and a run of bits is flushed to a whole number of bytes when a non-bit field follows or at the end. String/byte values may be supplied as text or raw bytes; text is encoded as UTF-8. The output is the resulting byte stream as a lowercase hex string on a `wire=` line.

Each typed value is a tagged object: `{"t":"bool","v":true}`, `{"t":"int","v":N}`, `{"t":"float","v":F}`, `{"t":"str","v":"..."}`, `{"t":"bytes","v":"<hex>"}`, `{"t":"datetime","v":"<ISO-8601>"}`, `{"t":"decimal","v":"<number>"}`, `{"t":"none"}`, `{"t":"table","v":{key:tagged,...}}`, `{"t":"array","v":[tagged,...]}`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_serialize_fields.json`

```json
{
    "description": "Serialize a positional list of AMQP method arguments into the protocol wire byte stream. The request supplies a type-code format string (one code per argument: bit, octet, short, long, long-long, float, short string, long string, byte array, timestamp) and the matching list of typed values. Consecutive bit arguments are packed together into shared octets, least-significant-bit first, while every other type is laid out in network byte order. The output is the resulting byte stream rendered as a lowercase hex string.",
    "cases": [
        {
            "input": {"op": "encode", "format": "bobBlLbsbSTx", "values": [
                {"t": "bool", "v": true}, {"t": "int", "v": 32}, {"t": "bool", "v": false},
                {"t": "int", "v": 3415}, {"t": "int", "v": 4513134}, {"t": "int", "v": 13241923419},
                {"t": "bool", "v": true}, {"t": "bytes", "v": "746865717569636b62726f776e666f78"},
                {"t": "bool", "v": false}, {"t": "str", "v": "jumpsoverthelazydog"},
                {"t": "datetime", "v": "2015-03-13T10:23:00"}, {"t": "bytes", "v": "746865717569636bff"}
            ]},
            "expected_output": "wire=0120000d570044dd6e000000031547b75b0110746865717569636b62726f776e666f7800000000136a756d70736f7665727468656c617a79646f67000000005502ba8400000009746865717569636bff"
        }
    ]
}
```

---

### Feature 2: Round-Trip Of Field Tables And Arrays

**As a developer**, I want to serialize a composite value and parse it back, so I can trust the encoder and decoder are exact inverses for nested data.

**Expected Behavior / Usage:**

A field table maps string keys to typed values; an array is an ordered sequence of typed values. In both, each element is self-describing on the wire (a type tag byte followed by the value). Element types include strings, signed integers (a value outside the signed 32-bit range must be promoted to the wider 64-bit integer code), booleans, doubles, fixed-point decimals, timestamps, void/null, and nested tables/arrays. The request has `format` (`F` for a single table, `A` for a single array) and a `values` list holding the one composite value. The output renders each recovered top-level value with an explicit type tag; for tables the keys are rendered in sorted order so output is order-independent.

**Test Cases:** `rcb_tests/public_test_cases/feature2_table_array_roundtrip.json`

```json
{
    "description": "Serialize a composite value (a field table or an array) and then parse it back, reporting the recovered value so the encoder and decoder can be checked as inverses. Tables map string keys to typed values; arrays hold an ordered sequence of typed values. Element types covered include strings, signed integers (including values beyond the 32-bit range, which must promote to a wider integer code), booleans, doubles, fixed-point decimals, timestamps, and nested tables/arrays, plus a void/null element. The output renders each recovered top-level value with an explicit type tag; table keys are reported in sorted order.",
    "cases": [
        {
            "input": {"op": "roundtrip", "format": "F", "values": [
                {"t": "table", "v": {
                    "foo": {"t": "int", "v": 32}, "bar": {"t": "str", "v": "baz"}, "nil": {"t": "none"},
                    "array": {"t": "array", "v": [{"t": "int", "v": 1}, {"t": "bool", "v": true}, {"t": "str", "v": "bar"}]}
                }}
            ]},
            "expected_output": "table:{array=array:[int:1,bool:true,str:bar],bar=str:baz,foo=int:32,nil=none}"
        },
        {
            "input": {"op": "roundtrip", "format": "A", "values": [
                {"t": "array", "v": [
                    {"t": "str", "v": "A"}, {"t": "int", "v": 1}, {"t": "bool", "v": true}, {"t": "float", "v": 33.3},
                    {"t": "decimal", "v": "55.5"}, {"t": "decimal", "v": "-3.4"}, {"t": "datetime", "v": "2015-03-13T10:23:00"},
                    {"t": "table", "v": {"quick": {"t": "str", "v": "fox"}, "amount": {"t": "int", "v": 1}}},
                    {"t": "array", "v": [{"t": "int", "v": 3}, {"t": "str", "v": "hens"}]}, {"t": "none"}
                ]}
            ]},
            "expected_output": "array:[str:A,int:1,bool:true,float:33.3,decimal:55.5,decimal:-3.4,datetime:2015-03-13T10:23:00,table:{amount=int:1,quick=str:fox},array:[int:3,str:hens],none]"
        }
    ]
}
```

---

### Feature 3: Decode A Single Self-Describing Table Entry

**As a developer**, I want to decode one tagged value from raw bytes, so I can read individual table/array entries that carry their own type information.

**Expected Behavior / Usage:**

The input is `wire`, the hex of a buffer whose first byte is a type tag and whose following bytes carry one value. Supported tags include short string `s` and long string `S`; byte array `x`; signed/unsigned 8-bit (`b`/`B`), signed/unsigned 16-bit (`U`/`u`), signed/unsigned 32-bit (`I`/`i`); signed/unsigned 64-bit (`L`/`l`); single-precision float `f`; and the void/null marker `V`. A long-string payload that is not valid UTF-8 is returned as raw bytes rather than text. Any bytes beyond the single decoded value are ignored. The output renders the decoded value with an explicit type tag.

**Test Cases:** `rcb_tests/public_test_cases/feature3_read_tagged_value.json`

```json
{
    "description": "Decode a single self-describing table entry from raw bytes. The first byte is a type tag selecting the value's wire encoding; the bytes that follow carry the value. Supported tags cover short and long strings, byte arrays, signed and unsigned 8/16/32-bit integers, 64-bit integers, single-precision floats, and the void/null marker. A long-string payload that is not valid UTF-8 is returned as raw bytes rather than text. Any trailing bytes beyond the value are ignored. The output renders the decoded value with an explicit type tag.",
    "cases": [
        {"input": {"op": "read_item", "wire": "7338746865717569636b"}, "expected_output": "str:thequick"},
        {"input": {"op": "read_item", "wire": "6201"}, "expected_output": "int:1"}
    ]
}
```

---

### Feature 4: Single-Precision Float Round-Trip

**As a developer**, I want a float field to survive serialization and parsing within single-precision tolerance, so numeric payloads are preserved.

**Expected Behavior / Usage:**

The request serializes a `f` (single-precision float) field followed by a `b` (bit) field and parses them back. The output renders the recovered values with explicit type tags; the float is rendered with six significant digits.

**Test Cases:** `rcb_tests/public_test_cases/feature4_float_roundtrip.json`

```json
{
    "description": "Serialize and parse back a single-precision float field followed by a bit field, confirming the float value survives the round-trip within single-precision tolerance. The output renders the recovered values with explicit type tags.",
    "cases": [
        {
            "input": {"op": "roundtrip", "format": "fb", "values": [{"t": "float", "v": 32.31}, {"t": "bool", "v": false}]},
            "expected_output": "float:32.31\nbool:false"
        }
    ]
}
```

---

### Feature 5: Reject Unsupported Or Unknown Field Types

**As a developer**, I want malformed serialization requests rejected with a clear typed error, so bad data fails fast instead of producing corrupt bytes.

**Expected Behavior / Usage:**

Two conditions must be rejected: (1) parsing a stream whose `format` carries an unknown type code; (2) serializing a table (`F`) or array (`A`) that contains a value of an unsupported type (represented here by `{"t":"unsupported"}`). Either condition fails with a normalized frame-syntax error rather than emitting partial output. The output is a neutral error: an `[an undefined type code verification error with location detail]` line plus a `where=` line indicating the rejection point (`decode`, `encode_table`, or `encode_array`). The error MUST NOT leak any host-language runtime detail.

**Test Cases:** `rcb_tests/public_test_cases/feature5_invalid_types.json`

```json
{
    "description": "Reject malformed serialization requests. Parsing a stream whose format string carries an unknown type code, or serializing a table or array that contains a value of an unsupported type, must fail with a normalized frame-syntax error rather than producing partial output. The output is a neutral error line naming the error category, with a field indicating where the rejection occurred.",
    "cases": [
        {"input": {"op": "decode", "format": "y", "wire": "617364736164"}, "expected_output": "[an undefined type code verification error with location detail]\nwhere=decode"},
        {
            "input": {"op": "encode", "format": "F", "values": [
                {"t": "table", "v": {"foo": {"t": "unsupported"}, "bar": {"t": "str", "v": "baz"}, "nil": {"t": "none"},
                    "array": {"t": "array", "v": [{"t": "int", "v": 1}, {"t": "bool", "v": true}, {"t": "str", "v": "bar"}]}}}
            ]},
            "expected_output": "[an undefined type code verification error with location detail]\nwhere=encode_table"
        }
    ]
}
```

---

### Feature 6: Message Property Header Round-Trip

**As a developer**, I want to serialize a message's property set into the property-flags/property-list block and parse it back, so message metadata travels correctly in the content header.

**Expected Behavior / Usage:**

A message has a fixed, ordered set of named properties, each with a wire type: short strings for `content_type`, `content_encoding`, `correlation_id`, `reply_to`, `expiration`, `message_id`, `type`, `user_id`, `app_id`, `cluster_id`; octets for `delivery_mode` and `priority`; an unsigned long for `timestamp`; and a nested field table for `application_headers`. Presence is encoded as a 16-bit property-flags bitmap (most-significant bit first, in property order); a property whose value is absent is not emitted and therefore does not reappear after parsing. The request gives the `properties`; the output reports the serialized block as a `wire=` hex line followed by each recovered property (sorted by name) rendered with an explicit type tag.

**Test Cases:** `rcb_tests/public_test_cases/feature6_message_properties.json`

```json
{
    "description": "Serialize a message's property set into the property-flags/property-list block of a content header and then parse it back. Each known property has a fixed slot and wire type (short strings for textual fields, octets for delivery mode and priority, an unsigned long for the timestamp, and a nested field table for application headers). Properties whose value is absent are not emitted and therefore do not reappear after parsing. The output reports the serialized block as hex followed by each recovered property (sorted by name) rendered with an explicit type tag.",
    "cases": [
        {
            "input": {"op": "properties", "properties": {
                "content_type": "application/json", "content_encoding": "utf-8",
                "application_headers": {"foo": 1, "id": "id#1"}, "delivery_mode": 1, "priority": 255,
                "correlation_id": "df31-142f-34fd-g42d", "reply_to": "cosmo", "expiration": "2015-12-23",
                "message_id": "3312", "timestamp": 3912491234, "type": "generic", "user_id": "george",
                "app_id": "vandelay", "cluster_id": "NYC"
            }},
            "expected_output": "wire=fffc106170706c69636174696f6e2f6a736f6e057574662d380000001503666f6f490000000102696453000000046964233101ff13646633312d313432662d333466642d6734326405636f736d6f0a323031352d31322d3233043333313200000000e933e0e20767656e657269630667656f7267650876616e64656c6179034e5943\napp_id=str:vandelay\napplication_headers=table:{foo=int:1,id=str:id#1}\ncluster_id=str:NYC\ncontent_encoding=str:utf-8\ncontent_type=str:application/json\ncorrelation_id=str:df31-142f-34fd-g42d\ndelivery_mode=int:1\nexpiration=str:2015-12-23\nmessage_id=str:3312\npriority=int:255\nreply_to=str:cosmo\ntimestamp=int:3912491234\ntype=str:generic\nuser_id=str:george"
        }
    ]
}
```

---

### Feature 7: Content-Frame Header Parsing

**As a developer**, I want to parse a content-frame header to learn the body size and properties and whether the message is already complete, so I know how to handle the frames that follow.

**Expected Behavior / Usage:**

A content header is a class id (2 bytes), two reserved bytes, an unsigned-long body size (8 bytes), then the serialized property block. The header may start at a non-zero `pad` offset within the buffer. When the body size is zero the message is immediately ready (no body frames follow); otherwise it is not yet ready. The output reports `body_size=`, `ready=`, and each recovered property (sorted by name) with an explicit type tag.

**Test Cases:** `rcb_tests/public_test_cases/feature7_content_header.json`

```json
{
    "description": "Parse a content-frame header to recover the announced body size and the message properties, and report whether the message is already complete. The header begins with a class id, two reserved bytes, and an unsigned long body size, followed by the serialized property block. When the body size is zero the message is immediately ready (no body frames follow); otherwise it is not yet ready. The header may begin at a non-zero offset within the buffer. The output reports the body size, the readiness flag, and each recovered property (sorted by name).",
    "cases": [
        {
            "input": {"op": "content_header", "body_size": 19, "pad": 30, "properties": {"content_type": "application/json", "content_encoding": "utf-8"}},
            "expected_output": "body_size=19\nready=false\ncontent_encoding=str:utf-8\ncontent_type=str:application/json"
        }
    ]
}
```

---

### Feature 8: Content Body Reassembly

**As a developer**, I want to reassemble a message body that arrives as several chunks, so a large body split across body frames becomes one buffer.

**Expected Behavior / Usage:**

The consumer tracks how many body bytes have arrived against the announced `body_size`, starting from an optional already-`received` count and an optional list of already-buffered `pending` chunks. Each incoming chunk is buffered; the message becomes ready only once the accumulated length reaches the announced size, at which point all buffered chunks are concatenated in arrival order into the final body. Chunks are supplied as hex (byte data) or as `{"str": "..."}` (text). The output reports `ready=` after each chunk, then the final assembled body as `body_hex=` (bytes) or `body_str=` (text).

**Test Cases:** `rcb_tests/public_test_cases/feature8_content_body.json`

```json
{
    "description": "Reassemble a message body delivered as a sequence of chunks. The consumer tracks how many body bytes have arrived against the announced body size, buffering partial chunks; the message becomes ready only once the accumulated length reaches the announced size, at which point the buffered chunks are concatenated in arrival order into the final body. The output reports the readiness flag after each chunk is fed and then the final assembled body.",
    "cases": [
        {
            "input": {"op": "content_body", "body_size": 16, "received": 8, "pending": ["746865", "717569636b"], "chunks": ["62726f776e", "666f78"]},
            "expected_output": "ready=false\nready=true\nbody_hex=746865717569636b62726f776e666f78"
        }
    ]
}
```

---

### Feature 9: Authentication Initial Responses

**As a developer**, I want each authentication mechanism to produce its correct initial client response, so I can authenticate over the protocol.

**Expected Behavior / Usage:**

*9.1 PLAIN — username/password packed with NUL separators*

The PLAIN response is the NUL byte, the UTF-8 username, a NUL byte, then the UTF-8 password, concatenated. If either credential is absent the mechanism declines (no response). The output reports the response bytes as hex on a `response=` line, or `response=not_provided`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_sasl_plain.json`

```json
{
    "description": "Produce the initial client response for the PLAIN authentication mechanism. The response is the NUL byte, the UTF-8 username, a NUL byte, and the UTF-8 password, concatenated. If either credential is absent, the mechanism declines to produce a response. The output reports the response bytes as hex, or a marker indicating no response was produced.",
    "cases": [
        {"input": {"op": "sasl", "mechanism": "PLAIN", "username": "foo", "password": "bar"}, "expected_output": "response=00666f6f00626172"}
    ]
}
```

*9.2 AMQPLAIN — a length-stripped field table of LOGIN/PASSWORD*

The AMQPLAIN response is a field table containing `LOGIN` and `PASSWORD` entries serialized in the standard table wire format, but with the leading 4-byte table-length prefix removed. If either credential is absent the mechanism declines. The output is `response=<hex>` or `response=not_provided`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_sasl_amqplain.json`

```json
{
    "description": "Produce the initial client response for the AMQPLAIN authentication mechanism. The response is a field table containing the LOGIN and PASSWORD entries serialized in the standard table wire format, but with the leading 4-byte table length prefix removed. If either credential is absent, the mechanism declines to produce a response. The output reports the response bytes as hex, or a marker indicating no response was produced.",
    "cases": [
        {"input": {"op": "sasl", "mechanism": "AMQPLAIN", "username": "foo", "password": "bar"}, "expected_output": "response=054c4f47494e5300000003666f6f0850415353574f52445300000003626172"}
    ]
}
```

*9.3 EXTERNAL — empty response*

The EXTERNAL mechanism carries no authentication data of its own; its response is empty. The output is `response=` (empty hex).

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_sasl_external.json`

```json
{
    "description": "Produce the initial client response for the EXTERNAL authentication mechanism, which carries no authentication data of its own. The output reports the response bytes as hex (which is empty).",
    "cases": [
        {"input": {"op": "sasl", "mechanism": "EXTERNAL"}, "expected_output": "response="}
    ]
}
```

*9.4 Abstract base — unsupported*

The abstract base mechanism has no concrete behavior; requesting its initial response is unsupported and is reported as a normalized not-implemented error.

**Test Cases:** `rcb_tests/public_test_cases/feature9_4_sasl_base.json`

```json
{
    "description": "The abstract base authentication mechanism has no concrete behavior: requesting its initial response is unsupported and must be reported as a normalized not-implemented error rather than returning data.",
    "cases": [
        {"input": {"op": "sasl", "mechanism": "BASE"}, "expected_output": "error=not_implemented"}
    ]
}
```

---

### Feature 10: Protocol Error Modeling

**As a developer**, I want protocol errors modeled as typed conditions with a numeric reply code and a readable string, so failures are explicit and inspectable.

**Expected Behavior / Usage:**

*10.1 Base error string rendering*

A base protocol error renders its string in one of three ways: with no details, a generic `<TypeName: unknown error>`; with only a method signature `(class id, method id)`, the signature followed by its reply code and reply text; with a reply text, that text verbatim. The output reports the rendered `str=`, the `type=` name, and the numeric `reply_code=`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_error_string.json`

```json
{
    "description": "Render the human-readable string of a base protocol error. With no details, the error renders a generic '<TypeName: unknown error>' form. When only a method signature (class id, method id) is given, the error renders the signature, its reply code, and its reply text. When a reply text is given, the error renders that text verbatim. The output reports the rendered string, the error type name, and the numeric reply code.",
    "cases": [
        {"input": {"op": "amqp_error", "class": "AMQPError"}, "expected_output": "str=<AMQPError: unknown error>\ntype=AMQPError\nreply_code=0"},
        {"input": {"op": "amqp_error", "class": "AMQPError", "method_sig": [50, 60]}, "expected_output": "str=(50, 60): (0) None\ntype=AMQPError\nreply_code=0"}
    ]
}
```

*10.2 Concrete error categories and their codes*

Each concrete protocol error category has a stable type name and a numeric reply code (zero for the abstract grouping categories, the assigned protocol code for the concrete conditions, e.g. a "not found" condition has code 404). Constructed with no details, each renders the generic `<TypeName: unknown error>` form. The output reports `str=`, `type=`, and `reply_code=`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_error_subclasses.json`

```json
{
    "description": "Render the string of each concrete protocol error type when constructed with no details. Each renders the generic '<TypeName: unknown error>' form. The output also reports the type name and the type's numeric reply code (zero for the abstract categories, the assigned AMQP code for the concrete conditions).",
    "cases": [
        {"input": {"op": "amqp_error", "class": "NotFound"}, "expected_output": "str=<NotFound: unknown error>\ntype=NotFound\nreply_code=404"}
    ]
}
```

---

### Feature 11: Outbound Frame Encoding

**As a developer**, I want to encode methods and messages into whole frames on the transport byte stream, so the broker receives correctly delimited frames.

**Expected Behavior / Usage:**

A frame is a 1-byte frame type, a 2-byte channel, a 4-byte payload length, the payload, then a `0xCE` frame-end byte. A method frame's payload is the 2-byte class id, 2-byte method id, and the serialized arguments. A content message also emits a content-header frame (carrying body length and serialized properties) and one or more body frames; when the total size would exceed the negotiated `frame_max`, the body is split across multiple body frames of at most `frame_max - 8` bytes each. A string body is encoded using the message's content encoding, defaulting to UTF-8 when none is set (the resulting encoding becomes observable on the message). The request gives `type`, `channel`, `method_sig`, `args_hex`, optional `content` (with `body_hex` or `body_str` and optional `properties`), and `frame_max`. The output reports the full transport byte stream as a `wire=` hex line, `bytes_sent=` (number of frames written), and, for content frames, `content_encoding=`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_frame_writer.json`

```json
{
    "description": "Encode an outbound frame (or sequence of frames) onto the transport byte stream. A method frame carries a 1-byte frame type, a 2-byte channel, a 4-byte payload length, the method signature plus arguments, and a 0xCE frame-end byte. A content message additionally emits a content-header frame (carrying the body length and serialized properties) and one or more body frames; when the total size exceeds the negotiated frame max the body is split across multiple body frames. A string body is encoded using the message's content encoding, defaulting to UTF-8 when none is set. The output reports the full transport byte stream as hex, the number of frames sent, and (for content frames) the resulting content encoding.",
    "cases": [
        {
            "input": {"op": "frame_writer", "frame_max": 512, "type": 1, "channel": 1, "method_sig": [50, 10], "args_hex": "787878787878787878787878787878787878787878787878787878787878", "content": null},
            "expected_output": "wire=010001000000220032000a787878787878787878787878787878787878787878787878787878787878ce\nbytes_sent=1"
        },
        {
            "input": {"op": "frame_writer", "frame_max": 512, "type": 2, "channel": 1, "method_sig": [60, 40], "args_hex": "78787878787878787878", "content": {"body_hex": "79797979797979797979", "properties": {"content_type": "utf-8"}}},
            "expected_output": "wire=02000100000000ce02000100000014003c0000000000000000000a8000057574662d38ce0300010000000a79797979797979797979ce\nbytes_sent=1\ncontent_encoding=none"
        }
    ]
}
```

---

### Feature 12: Inbound Frame Assembly State Machine

**As a developer**, I want inbound frames assembled into dispatchable units, so a method and its content frames are delivered together and protocol violations are caught.

**Expected Behavior / Usage:**

Frames arrive as `{type, channel, payload_hex}`. A standalone method frame for a non-content method is dispatched immediately. A content-bearing method (such as a delivery) is held until its content-header frame arrives; if the announced body size is zero the message is dispatched right away, otherwise the assembler waits for body frames and dispatches once the whole body is collected. A heartbeat frame is consumed without dispatching anything. On a given channel, receiving a frame whose type is not the one currently expected is a protocol violation, reported as a normalized error. For each frame the output reports `complete=` (whether it completed a dispatchable unit); for each dispatch it reports `dispatch channel=<n> method=<class>,<method>` and either `content=no` or `body=<rendered value>`. A protocol violation yields `error=unexpected_frame`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_frame_handler.json`

```json
{
    "description": "Feed a sequence of inbound frames through the frame assembler and report what it dispatches. A standalone method frame for a non-content method is dispatched immediately. A content-bearing method (such as a delivery) is held until its content-header frame arrives; if the announced body size is zero the message is dispatched right away, otherwise the assembler waits for body frames and dispatches once the whole body has been collected. A heartbeat frame is consumed without dispatching anything. Receiving a frame whose type is not the one currently expected on a channel is a protocol violation, reported as a normalized error. For each frame the output reports whether it completed a dispatchable unit, and for each dispatch the channel, the method signature, and the message body (or that there was no content).",
    "cases": [
        {
            "input": {"op": "frame_handler", "frames": [{"type": 1, "channel": 1, "payload_hex": "003c0033"}]},
            "expected_output": "complete=true\ndispatch channel=1 method=60,51 content=no"
        },
        {
            "input": {"op": "frame_handler", "frames": [
                {"type": 1, "channel": 1, "payload_hex": "003c003c"},
                {"type": 2, "channel": 1, "payload_hex": "003c000000000000000000100000"},
                {"type": 3, "channel": 1, "payload_hex": "746865717569636b"},
                {"type": 3, "channel": 1, "payload_hex": "62726f776e666f78"}
            ]},
            "expected_output": "complete=false\ncomplete=false\ncomplete=false\ncomplete=true\ndispatch channel=1 method=60,60 body=bytes:746865717569636b62726f776e666f78"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the primitive-field codec, composite (table/array) codec, message property/header codec, body reassembly, authentication mechanisms, frame writer, inbound frame assembler, and typed error model described above. The core must be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON request from stdin, selects behavior by its `op` field (`encode`, `decode`, `read_item`, `roundtrip`, `properties`, `content_header`, `content_body`, `sasl`, `amqp_error`, `frame_writer`, `frame_handler`), invokes the core, and prints the result to stdout exactly matching the per-feature contracts above. All byte outputs are lowercase hex; all errors are normalized to neutral `error=<category>` lines and MUST NOT leak host-language runtime details. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout from the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same sorting convention used in the property list generator
- match the standard AMQP error output template for frame syntax violations
