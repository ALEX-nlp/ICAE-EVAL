## Product Requirement Document

# Encrypted-Message Header Codec - Binary Serialization, Streaming Decode, and Structural Validation

## Project Goal

Build a codec for the fixed-layout binary header that prefaces an encrypted message. The codec lets developers turn a structured description of a message header (format version, object type, algorithm identifier, a message identifier, an encryption context, one or more wrapped data-key blobs, content framing, and the nonce/tag that authenticate the header) into a compact byte stream, and recover that same structure from bytes — including when the bytes arrive a few at a time over a stream. It guarantees byte-for-byte round-trip stability and rejects malformed input with clear, language-neutral errors.

---

## Background & Problem

Without this codec, developers handling an encrypted-message format must hand-roll big-endian reads and writes for a dozen heterogeneous fields, track the lengths of three independent variable-length sections (encryption context, key provider id/info, encrypted key), and reimplement partial-parse bookkeeping so a header split across network packets can still be assembled. This is repetitive, easy to get wrong (off-by-one length fields, signed/unsigned confusion, missing validation), and a single mistake silently corrupts every message.

With this codec, a developer describes the header fields once and gets a stable wire encoding, a decoder that tolerates input delivered in arbitrarily small chunks, accessors for the decoded metadata, and built-in validation that refuses out-of-range or incomplete headers before they can do harm.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. The core here is a single cohesive value type (the header) plus its codec; a small, well-separated module is appropriate. Keep the wire-format logic, the field-validation logic, and the I/O adapter in distinct logical units; do not collapse everything, including stdin/stdout handling, into one god file.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal data model. The core codec must know nothing about JSON or stdin/stdout. The adapter alone translates a JSON command into idiomatic calls on the core type and renders the result as the line-oriented text contract below.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Separate field parsing, structural validation, encoding, decoded-field access, and output formatting.
   - **OCP:** New algorithm identifiers, content types, or object types should be addable without rewriting the parse loop.
   - **LSP:** Any content-type or algorithm abstraction must be substitutable wherever the base is used.
   - **ISP:** Keep the decode and encode surfaces small and cohesive.
   - **DIP:** The codec depends on abstractions for field primitives, not on the concrete I/O layer.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface should read naturally in the target language and hide the byte-level bookkeeping.
   - **Resilience:** Malformed, out-of-range, or incomplete input must be modeled as explicit, typed error outcomes rather than generic faults or silent corruption.

---

## Core Features

### Feature 1: Round-Trip Binary Encoding

**As a developer**, I want to encode a fully populated header into bytes and decode those bytes back into an equivalent header, so I can persist or transmit a header and reconstruct it losslessly.

**Expected Behavior / Usage:**

The input describes a header: an optional encryption context (a string→string map; absent or empty means no context), a key provider id (a short text label), key provider info (text), the byte length of the wrapped encrypted key, a content type (`frame` or `single_block`), and a frame length (bytes per frame; `0` when not framed). Encoding produces a byte sequence; decoding that sequence and re-encoding it must yield an identical byte sequence.

The output reports `serialized_length` (the total byte length of the encoded header), `round_trip_stable` (`true` when re-encoding the decoded header reproduces the original bytes), and the decoded structural fields: `version`, `content_type`, `frame_length`, `nonce_length`, `encryption_context_length` (byte length of the serialized context), and `encrypted_key_blob_count`. The serialized length is fully determined by the field sizes and is therefore stable across runs even though an internal random message identifier is generated per header. With a 12-byte nonce, a 16-byte tag, one key blob whose provider id is `None` (4 bytes), provider info `TestKeyID` (9 bytes), and a 32-byte key, an empty context yields length 113; a 30-byte context yields length 143.

**Test Cases:** `rcb_tests/public_test_cases/feature1_round_trip_encoding.json`

```json
{
    "description": "Encode a complete message header (version, type, algorithm, message id, encryption context, one key blob, content type, reserved field, nonce length, frame length, header nonce, header tag) into its binary wire form, then decode the bytes back into a header and re-encode it. The two byte sequences must be identical, and the decoded structural fields must match what was supplied. The serialized length is fully determined by the field sizes (fixed-size fields plus the encryption-context length plus the key-blob length plus nonce and tag), so it is stable across runs even though the internal message id is random.",
    "cases": [
        {
            "input": {"action": "encode_round_trip", "encryption_context": {"ENC": "CiphertextHeader Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "serialized_length=143\nround_trip_stable=true\nversion=1\ncontent_type=frame\nframe_length=4096\nnonce_length=12\nencryption_context_length=30\nencrypted_key_blob_count=1\n"
        },
        {
            "input": {"action": "encode_round_trip", "encryption_context": null, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "single_block", "frame_length": 0},
            "expected_output": "serialized_length=113\nround_trip_stable=true\nversion=1\ncontent_type=single_block\nframe_length=0\nnonce_length=12\nencryption_context_length=0\nencrypted_key_blob_count=1\n"
        }
    ]
}
```

---

### Feature 2: Incremental (Streaming) Decode

**As a developer**, I want the decoder to accept header bytes a few at a time and resume where it left off, so I can parse a header that arrives in small pieces over a stream without buffering the whole message first.

**Expected Behavior / Usage:**

The input describes the same header shape as Feature 1. The header is encoded, then fed to a fresh decoder one growing chunk at a time: the decoder consumes whatever complete fields it can from the bytes available so far and reports how many bytes it consumed; the caller advances by that amount and supplies more bytes, repeating until the decoder reports the header is complete. Partial input never corrupts state or throws — it simply consumes zero bytes until enough are available.

The output reports `serialized_length`, `incremental_decode_stable` (`true` when re-encoding the piecewise-decoded header reproduces the original bytes), and the same decoded structural fields as Feature 1. A 40-byte context with one key blob (provider id `None`, provider info `TestKeyID`, 32-byte key) yields a serialized length of 153.

**Test Cases:** `rcb_tests/public_test_cases/feature2_streaming_decode.json`

```json
{
    "description": "Decode a header from a stream where the bytes arrive incrementally, one growing chunk at a time. The decoder must support partial parsing: it consumes whatever complete fields it can from the bytes available so far, reports how many bytes it consumed, and resumes when more bytes arrive, without losing or corrupting any field. After the full header has been consumed in this piecewise manner, re-encoding it must reproduce the original byte sequence exactly.",
    "cases": [
        {
            "input": {"action": "streaming_decode", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "serialized_length=153\nincremental_decode_stable=true\nversion=1\ncontent_type=frame\nframe_length=4096\nnonce_length=12\nencryption_context_length=40\nencrypted_key_blob_count=1\n"
        }
    ]
}
```

---

### Feature 3: Decoded Variable-Length Metadata

**As a developer**, I want to read back the length of the encryption context and the number of wrapped key blobs after decoding, so I can size the variable-length sections without re-scanning the raw bytes.

**Expected Behavior / Usage:**

The input describes a header; it is encoded and then decoded. The output reports `encryption_context_length` (the byte length of the serialized encryption context that was embedded) and `encrypted_key_blob_count` (the number of key blobs embedded). These must equal the values supplied at encode time, confirming the length and count fields survive the round trip. A 40-byte serialized context and a single key blob yield length 40 and count 1.

**Test Cases:** `rcb_tests/public_test_cases/feature3_decode_metadata.json`

```json
{
    "description": "After decoding a header from its bytes, the recovered encryption-context length must equal the byte length of the serialized encryption context that was originally embedded, and the recovered key-blob count must equal the number of key blobs that were embedded. This verifies that the length and count fields survive an encode/decode round trip and report the true sizes of the variable-length sections.",
    "cases": [
        {
            "input": {"action": "decode_metadata", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "encryption_context_length=40\nencrypted_key_blob_count=1\n"
        }
    ]
}
```

---

### Feature 4: Empty-Source Decode Is a No-Op

**As a developer**, I want a decoder asked to read from an absent byte source to consume nothing and report it, so a streaming caller can poll for input that has not yet arrived without special-casing emptiness.

**Expected Behavior / Usage:**

When the input byte source is null/absent, a fresh decoder consumes zero bytes and reports `bytes_consumed=0`, with no error.

**Test Cases:** `rcb_tests/public_test_cases/feature4_decode_null_input.json`

```json
{
    "description": "Asking a fresh decoder to consume a null/absent byte source must be a no-op: it consumes zero bytes and reports that, rather than failing. This lets a streaming caller poll for input that has not yet arrived.",
    "cases": [
        {
            "input": {"action": "decode_empty", "data": null},
            "expected_output": "bytes_consumed=0\n"
        }
    ]
}
```

---

### Feature 5: Empty Header Default State

**As a developer**, I want a freshly created, unpopulated header to report its optional identity and authentication fields as absent, so I have a well-defined empty state distinct from a fully built header.

**Expected Behavior / Usage:**

A new header that has neither been populated nor decoded reports `message_id`, `header_nonce`, and `header_tag` each as `absent`. These become `present` only once the header is constructed or decoded.

**Test Cases:** `rcb_tests/public_test_cases/feature5_empty_header_state.json`

```json
{
    "description": "A newly created, empty header that has not yet been populated or decoded must report all of its optional identity/authentication fields as absent: the message id, the header nonce, and the header tag. This gives callers a well-defined empty state to distinguish from a fully built header.",
    "cases": [
        {
            "input": {"action": "new_header_state"},
            "expected_output": "message_id=absent\nheader_nonce=absent\nheader_tag=absent\n"
        }
    ]
}
```

---

### Feature 6: Encode-Time Guards

**As a developer**, I want encoding to refuse headers that cannot be safely represented, so I never produce a header that would overflow a length field or omit its integrity protection.

**Expected Behavior / Usage:**

*6.1 Oversized Encryption Context — reject a context too large for its length field*

The encryption-context length is stored in an unsigned 16-bit field, so the serialized context may be at most 65535 bytes. Constructing a header whose context exceeds that limit must fail with the neutral error `error=encryption_context_too_large` and report `max=65535`, rather than silently truncating the length.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_oversized_context.json`

```json
{
    "description": "Encoding rejects an encryption context whose serialized size exceeds the maximum value of an unsigned 16-bit length field (65535 bytes). Constructing a header with an over-large context must fail with a neutral too-large error that reports the maximum permitted size, rather than silently truncating the length field.",
    "cases": [
        {
            "input": {"action": "encode_oversized_context", "context_size": 65536},
            "expected_output": "error=encryption_context_too_large\nmax=65535\n"
        }
    ]
}
```

*6.2 Missing Header Authentication — reject serialization without nonce or tag*

The full header serialization embeds a header nonce and a header authentication tag that protect the integrity of the preceding fields. Serializing while either value is still unset must fail with `error=missing_header_authentication` and report which value is missing (`missing=nonce` or `missing=tag`), rather than emitting an unprotected header.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_missing_authentication.json`

```json
{
    "description": "The full header serialization includes a header nonce and a header authentication tag that protect the integrity of the preceding fields. Serializing a header while either of these two authentication values is still unset must fail with a neutral missing-authentication error that names which value is missing, rather than producing an unprotected header.",
    "cases": [
        {
            "input": {"action": "encode_missing_auth", "omit": "nonce"},
            "expected_output": "error=missing_header_authentication\nmissing=nonce\n"
        },
        {
            "input": {"action": "encode_missing_auth", "omit": "tag"},
            "expected_output": "error=missing_header_authentication\nmissing=tag\n"
        }
    ]
}
```

---

### Feature 7: Decode-Time Structural Validation

**As a developer**, I want decoding to reject a header whose fixed fields hold out-of-range values, so corrupted or hostile input is refused with a clear signal instead of being parsed into a bogus header.

**Expected Behavior / Usage:**

Encode a valid header, overwrite exactly one fixed field in the byte stream with an out-of-range value, then decode. Each corruption must fail with the neutral error `[a specific cryptographic algorithm identifier]` and report the offending `field`. The validated fields and their rules: `version` (must equal the current format version; a `0` is invalid), `type` (must be a known object type; `0` is invalid), `algorithm_id` (must be a known algorithm; `0` is invalid), `content_type` (must be a known framing type; an unknown byte such as `10` is invalid), `reserved_field` (must be zero; any non-zero value is invalid), `nonce_length` (must be non-negative; a negative byte is invalid), and `frame_length` (must be non-negative; a negative integer is invalid).

**Test Cases:** `rcb_tests/public_test_cases/feature7_decode_field_validation.json`

```json
{
    "description": "When decoding a header, every fixed structural field is validated against the format's allowed values. Encode a valid header, overwrite one field in the byte stream with an out-of-range value, then decode. Each corruption must be rejected with a neutral malformed-header error that names the offending field. Covered fields: the format version byte (must equal the current version), the object type byte (must be a known type), the algorithm identifier (must be a known algorithm), the content-type byte (must be single-block or framed), the reserved field (must be zero), the nonce-length byte (must be non-negative), and the frame-length integer (must be non-negative).",
    "cases": [
        {
            "input": {"action": "decode_corrupt_field", "field": "version", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "[a specific cryptographic algorithm identifier]\nfield=version\n"
        },
        {
            "input": {"action": "decode_corrupt_field", "field": "type", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "[a specific cryptographic algorithm identifier]\nfield=type\n"
        },
        {
            "input": {"action": "decode_corrupt_field", "field": "algorithm_id", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "[a specific cryptographic algorithm identifier]\n[a specific cryptographic algorithm identifier]\n"
        },
        {
            "input": {"action": "decode_corrupt_field", "field": "content_type", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "[a specific cryptographic algorithm identifier]\nfield=content_type\n"
        },
        {
            "input": {"action": "decode_corrupt_field", "field": "reserved_field", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "[a specific cryptographic algorithm identifier]\nfield=reserved_field\n"
        },
        {
            "input": {"action": "decode_corrupt_field", "field": "nonce_length", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "[a specific cryptographic algorithm identifier]\nfield=nonce_length\n"
        },
        {
            "input": {"action": "decode_corrupt_field", "field": "frame_length", "encryption_context": {"ENC": "CiphertextHeader Streaming Test"}, "key_provider_id": "None", "key_provider_info": "TestKeyID", "encrypted_key_length": 32, "content_type": "frame", "frame_length": 4096},
            "expected_output": "[a specific cryptographic algorithm identifier]\nfield=frame_length\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codec for the binary message header, implementing encoding, incremental decoding, decoded-field access, encode-time guards, and decode-time structural validation as described above. Its physical structure must align with the "Scale-Driven Code Organization" constraint — a focused, well-separated module, not a monolith and not over-engineered.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core codec. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the line-oriented result to stdout, strictly matching the per-feature contracts above. The adapter is the only place that maps native error conditions to the neutral `error=...` categories; the core codec stays free of I/O and JSON concerns.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_round_trip_encoding.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_round_trip_encoding@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains only the raw stdout of the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the status reporting convention used for header initialization
- adhere to the standard serialization sequence defined elsewhere
