## Product Requirement Document

# Sortable Binary Identifier Toolkit — Base32 Encoding, Decoding, and Construction

## Project Goal

Build a reusable toolkit for a 128-bit, time-ordered, lexicographically-sortable binary identifier, so developers can encode such identifiers to compact Base32 text, decode that text back to bytes, inspect and split an identifier into its time and randomness parts, and construct identifiers from many input forms — all behind one well-defined contract, without each application reinventing the bit-twiddling and validation.

---

## Background & Problem

The identifier is a 128-bit (16-byte) value laid out big-endian, most-significant bit first. Its first 48 bits (6 bytes) are a timestamp in milliseconds since the Unix epoch, and its last 80 bits (10 bytes) are random data. In text form it is a 26-character string using Crockford's Base32 alphabet ([the project-specific Base32 alphabet — ask the PM for the exact character set]); the timestamp section is the first 10 characters and the randomness section is the last 16.

Without a shared toolkit, developers must hand-roll the Base32 bit packing, the length-based dispatch between the full identifier and its sections, the integer/byte/text conversions, the comparison semantics that make these identifiers sortable, and the validation that rejects malformed input. This is repetitive and error-prone.

With this toolkit, a developer gets: a Base32 encoder and decoder (both a length-detecting variant and strict fixed-width variants), numeric/textual representations of a buffer, ordering and equality across representations, decomposition of an identifier into its timestamp and randomness sections plus a UUID rendering, temporal interpretation of the timestamp section, and constructors that build an identifier from raw bytes, an integer, Base32 text, a UUID, a timestamp value, or a randomness value.

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

All binary buffers in the contract are expressed as lowercase hexadecimal strings under a `hex` field. All Base32 text is expressed under a `text` field. Integers that may exceed native word size are expressed as decimal strings. Every operation prints a small block of `key=value` lines (one per line, trailing newline). Any rejected input is reported as a single neutral line `error=<category>` (categories: `invalid_length`, `unsupported_type`, `unorderable`), never leaking host-language runtime details.

### Feature 1: Base32 Encoding (Binary → Text)

**As a developer**, I want to turn a binary buffer into Crockford Base32 text, so I can store or transmit an identifier (or one of its sections) as a compact ASCII string.

**Expected Behavior / Usage:**

*1.1 Length-dispatching encoder — encodes a buffer whose meaning is inferred from its length*

The request `{"op": "encode", "hex": <buffer>}` encodes the buffer by selecting the width from its length: a 6-byte buffer produces 10 characters, a 10-byte buffer produces 16 characters, and a 16-byte buffer produces 26 characters. Any other length is rejected with `error=invalid_length`. On success the output is `encoded=<text>` followed by `length=<character count>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_encode_auto.json`

```json
{
    "description": "Encode a binary buffer into Base32 text using the length-dispatching encoder. The buffer length selects the encoding width: a 6-byte buffer yields 10 characters, a 10-byte buffer yields 16 characters, and a 16-byte buffer yields 26 characters. Any other length is rejected with a neutral length error. The output reports the encoded text and its character count.",
    "cases": [
        {
            "input": {"op": "encode", "hex": "000102030405060708090a0b0c0d0e0f"},
            "expected_output": "encoded=00041061050R3GG28A1C60T3GF\nlength=26\n"
        },
        {
            "input": {"op": "encode", "hex": "010203040506"},
            "expected_output": "encoded=01081G8186\nlength=10\n"
        },
        {
            "input": {"op": "encode", "hex": "0102030405"},
            "expected_output": "error=invalid_length\n"
        }
    ]
}
```

*1.2 Fixed-width section encoders — encode a named section, requiring an exact length*

The request `{"op": "encode_fixed", "section": <name>, "hex": <buffer>}` encodes using a strict encoder for the named section, where `section` is `identifier` (requires exactly 16 bytes → 26 characters), `timestamp` (exactly 6 bytes → 10 characters), or `randomness` (exactly 10 bytes → 16 characters). Any other length for that section is rejected with `error=invalid_length`, even a length the length-dispatching encoder would otherwise accept (e.g. a 6-byte buffer is invalid for the `identifier` section). On success the output is `section=<name>`, then `encoded=<text>`, then `length=<character count>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_encode_section.json`

```json
{
    "description": "Encode a binary buffer with one of the fixed-width section encoders. Each named section requires an exact buffer length (the full identifier section requires 16 bytes, the timestamp section 6 bytes, the randomness section 10 bytes) and rejects any other length with a neutral length error, even lengths that the auto-detecting encoder would otherwise accept. The output echoes the section name, the encoded text and its character count.",
    "cases": [
        {
            "input": {"op": "encode_fixed", "section": "identifier", "hex": "000102030405060708090a0b0c0d0e0f"},
            "expected_output": "section=identifier\nencoded=00041061050R3GG28A1C60T3GF\nlength=26\n"
        },
        {
            "input": {"op": "encode_fixed", "section": "timestamp", "hex": "015d3ef79800"},
            "expected_output": "section=timestamp\nencoded=01BMZFF600\nlength=10\n"
        },
        {
            "input": {"op": "encode_fixed", "section": "identifier", "hex": "015d3ef79800"},
            "expected_output": "error=invalid_length\n"
        }
    ]
}
```

---

### Feature 2: Base32 Decoding (Text → Binary)

**As a developer**, I want to turn Crockford Base32 text back into the original binary buffer, so I can recover an identifier (or one of its sections) from its string form.

**Expected Behavior / Usage:**

*2.1 Length-dispatching decoder — decodes text whose meaning is inferred from its length*

The request `{"op": "decode", "text": <string>}` decodes by selecting the width from the text length: 10 characters produce 6 bytes, 16 characters produce 10 bytes, and 26 characters produce 16 bytes. Any other length is rejected with `error=invalid_length`. On success the output is `bytes=<lowercase hex>` followed by `length=<byte count>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_decode_auto.json`

```json
{
    "description": "Decode Base32 text into a binary buffer using the length-dispatching decoder. The text length selects the output width: 10 characters yield 6 bytes, 16 characters yield 10 bytes, and 26 characters yield 16 bytes. Any other length is rejected with a neutral length error. The output reports the decoded bytes as lowercase hexadecimal and the byte count.",
    "cases": [
        {
            "input": {"op": "decode", "text": "00041061050R3GG28A1C60T3GF"},
            "expected_output": "bytes=000102030405060708090a0b0c0d0e0f\nlength=16\n"
        },
        {
            "input": {"op": "decode", "text": "01BMZFF600"},
            "expected_output": "bytes=015d3ef79800\nlength=6\n"
        },
        {
            "input": {"op": "decode", "text": "01081"},
            "expected_output": "error=invalid_length\n"
        }
    ]
}
```

*2.2 Fixed-width section decoders — decode a named section, requiring an exact length*

The request `{"op": "decode_fixed", "section": <name>, "text": <string>}` decodes using a strict decoder for the named section, where `section` is `identifier` (requires exactly 26 characters → 16 bytes), `timestamp` (exactly 10 characters → 6 bytes), or `randomness` (exactly 16 characters → 10 bytes). Any other length for that section is rejected with `error=invalid_length`. On success the output is `section=<name>`, then `bytes=<lowercase hex>`, then `length=<byte count>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_decode_section.json`

```json
{
    "description": "Decode Base32 text with one of the fixed-width section decoders. Each named section requires an exact text length (the full identifier section requires 26 characters, the timestamp section 10 characters, the randomness section 16 characters) and rejects any other length with a neutral length error. The output echoes the section name, the decoded bytes as lowercase hexadecimal and the byte count.",
    "cases": [
        {
            "input": {"op": "decode_fixed", "section": "identifier", "text": "00041061050R3GG28A1C60T3GF"},
            "expected_output": "section=identifier\nbytes=000102030405060708090a0b0c0d0e0f\nlength=16\n"
        },
        {
            "input": {"op": "decode_fixed", "section": "timestamp", "text": "01BMZFF600"},
            "expected_output": "section=timestamp\nbytes=015d3ef79800\nlength=6\n"
        },
        {
            "input": {"op": "decode_fixed", "section": "identifier", "text": "01BMZFF600"},
            "expected_output": "error=invalid_length\n"
        }
    ]
}
```

---

### Feature 3: Numeric and Textual Representations

**As a developer**, I want a wrapped buffer to expose its integer and Base32 text forms, so I can move freely between binary, numeric, and string views of the same value.

**Expected Behavior / Usage:**

The request `{"op": "represent", "hex": <buffer>}` wraps the buffer and reports two views: the integer view is the unsigned big-endian interpretation of the bytes, and the text view is the length-dispatched Base32 encoding of the same bytes (so a 16-byte buffer yields 26 characters, a 6-byte buffer 10 characters, a 10-byte buffer 16 characters). The output is `int=<decimal>` followed by `str=<Base32 text>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_representations.json`

```json
{
    "description": "Expose the numeric and textual representations of a wrapped binary buffer. The integer representation is the unsigned big-endian interpretation of the bytes; the textual representation is the length-dispatched Base32 encoding of the same bytes. The output reports both.",
    "cases": [
        {
            "input": {"op": "represent", "hex": "000102030405060708090a0b0c0d0e0f"},
            "expected_output": "int=5233100606242806050955395731361295\nstr=00041061050R3GG28A1C60T3GF\n"
        }
    ]
}
```

---

### Feature 4: Comparisons

**As a developer**, I want a wrapped buffer to compare with values given in different forms, so these identifiers are sortable and equatable regardless of how the other operand is expressed.

**Expected Behavior / Usage:**

A comparison request is `{"op": "compare", "hex": <left buffer>, "operator": <op>, "right": <operand>}` where `operator` is one of `eq`, `ne`, `lt`, `gt`, `le`, `ge`, and `right` is a typed operand: `{"type": "wrapped", "hex": ...}` (another wrapped buffer), `{"type": "bytes", "hex": ...}` (raw bytes), `{"type": "int", "value": ...}` (a big-endian integer), `{"type": "text", "value": ...}` (Base32 text), or `{"type": "unsupported"}` (a value of a type the identifier does not understand, such as a list). Comparison is by the unsigned big-endian integer value of the bytes for wrapped/bytes/int operands, by Base32 text for text operands. The output reports `operator=<op>`, `right_type=<type>`, `left_int=<decimal>`; when the right operand is byte- or integer-shaped it also reports `right_int=<decimal>`; and finally `result=<true|false>`.

*4.1 Equality and inequality across representations*

`eq` is true and `ne` is false exactly when the right operand denotes the same value as the left buffer, regardless of the operand's form; otherwise `eq` is false and `ne` is true.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_equality.json`

```json
{
    "description": "Compare a wrapped buffer for equality and inequality against the same logical value expressed in different forms: another wrapped buffer, raw bytes, the big-endian integer, and the Base32 text. Equality holds when the compared value denotes the same bytes regardless of its form, and fails when it denotes a different value. The output reports the operator, the right operand form, the left operand's integer value (and the right operand's integer value when it is byte- or integer-shaped) and the boolean result.",
    "cases": [
        {
            "input": {"op": "compare", "hex": "000102030405060708090a0b0c0d0e0f", "operator": "eq", "right": {"type": "wrapped", "hex": "000102030405060708090a0b0c0d0e0f"}},
            "expected_output": "operator=eq\nright_type=wrapped\nleft_int=5233100606242806050955395731361295\nright_int=5233100606242806050955395731361295\nresult=true\n"
        },
        {
            "input": {"op": "compare", "hex": "000102030405060708090a0b0c0d0e0f", "operator": "eq", "right": {"type": "int", "value": "5233100606242806050955395731361295"}},
            "expected_output": "operator=eq\nright_type=int\nleft_int=5233100606242806050955395731361295\nright_int=5233100606242806050955395731361295\nresult=true\n"
        },
        {
            "input": {"op": "compare", "hex": "000102030405060708090a0b0c0d0e0f", "operator": "ne", "right": {"type": "wrapped", "hex": "0102030405060708090a0b0c0d0e0f10"}},
            "expected_output": "operator=ne\nright_type=wrapped\nleft_int=5233100606242806050955395731361295\nright_int=1339673755198158349044581307228491536\nresult=true\n"
        }
    ]
}
```

*4.2 Ordering across representations*

The four ordering operators (`lt`, `gt`, `le`, `ge`) compare by the unsigned big-endian integer value for wrapped, bytes, and int operands. A buffer with a smaller integer value is strictly less than one with a larger value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_ordering.json`

```json
{
    "description": "Order a wrapped buffer relative to another value using the four ordering operators (strictly-less, strictly-greater, less-or-equal, greater-or-equal). Ordering is by the unsigned big-endian integer value for wrapped buffers, raw bytes and integers. The output reports the operator, the right operand form, both operands' integer values and the boolean result.",
    "cases": [
        {
            "input": {"op": "compare", "hex": "000102030405060708090a0b0c0d0e0f", "operator": "lt", "right": {"type": "wrapped", "hex": "0102030405060708090a0b0c0d0e0f10"}},
            "expected_output": "operator=lt\nright_type=wrapped\nleft_int=5233100606242806050955395731361295\nright_int=1339673755198158349044581307228491536\nresult=true\n"
        },
        {
            "input": {"op": "compare", "hex": "0102030405060708090a0b0c0d0e0f10", "operator": "gt", "right": {"type": "bytes", "hex": "000102030405060708090a0b0c0d0e0f"}},
            "expected_output": "operator=gt\nright_type=bytes\nleft_int=1339673755198158349044581307228491536\nright_int=5233100606242806050955395731361295\nresult=true\n"
        }
    ]
}
```

*4.3 Unsupported operand types*

Against an operand of an unsupported type, `eq` yields `result=false` and `ne` yields `result=true`, but any ordering operator (`lt`, `gt`, `le`, `ge`) is rejected with `error=unorderable` rather than producing a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_unsupported_operand.json`

```json
{
    "description": "Compare a wrapped buffer against a value of a type it does not understand (for example a list). Equality against an unsupported type yields false and inequality yields true, but any ordering operator against an unsupported type is rejected with a neutral unorderable error rather than producing a boolean.",
    "cases": [
        {
            "input": {"op": "compare", "hex": "000102030405060708090a0b0c0d0e0f", "operator": "eq", "right": {"type": "unsupported"}},
            "expected_output": "operator=eq\nright_type=unsupported\nleft_int=5233100606242806050955395731361295\nresult=false\n"
        },
        {
            "input": {"op": "compare", "hex": "000102030405060708090a0b0c0d0e0f", "operator": "ne", "right": {"type": "unsupported"}},
            "expected_output": "operator=ne\nright_type=unsupported\nleft_int=5233100606242806050955395731361295\nresult=true\n"
        }
    ]
}
```

---

### Feature 5: Identifier Decomposition

**As a developer**, I want to split a full identifier into its constituent parts and render it as a UUID, so I can work with the timestamp and randomness independently and interoperate with UUID-based systems.

**Expected Behavior / Usage:**

*5.1 Timestamp section — the first 48 bits*

The request `{"op": "split_timestamp", "hex": <16-byte buffer>}` extracts the first 6 bytes (48 bits) of the identifier as the timestamp section. The output reports `bytes=<lowercase hex>`, `str=<10-character Base32>`, and `int=<big-endian decimal>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_timestamp_section.json`

```json
{
    "description": "Extract the timestamp section of a 16-byte identifier: the first 6 bytes (48 bits). The output reports those bytes as lowercase hexadecimal, their 10-character Base32 text, and their big-endian integer value.",
    "cases": [
        {
            "input": {"op": "split_timestamp", "hex": "000102030405060708090a0b0c0d0e0f"},
            "expected_output": "bytes=000102030405\nstr=0004106105\nint=4328719365\n"
        }
    ]
}
```

*5.2 Randomness section — the last 80 bits*

The request `{"op": "split_randomness", "hex": <16-byte buffer>}` extracts the last 10 bytes (80 bits) of the identifier as the randomness section. The output reports `bytes=<lowercase hex>`, `str=<16-character Base32>`, and `int=<big-endian decimal>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_randomness_section.json`

```json
{
    "description": "Extract the randomness section of a 16-byte identifier: the last 10 bytes (80 bits). The output reports those bytes as lowercase hexadecimal, their 16-character Base32 text, and their big-endian integer value.",
    "cases": [
        {
            "input": {"op": "split_randomness", "hex": "000102030405060708090a0b0c0d0e0f"},
            "expected_output": "bytes=060708090a0b0c0d0e0f\nstr=0R3GG28A1C60T3GF\nint=28463905110803495063055\n"
        }
    ]
}
```

*5.3 UUID rendering*

The request `{"op": "to_uuid", "hex": <16-byte buffer>}` renders the identifier as a canonical hyphenated UUID string (8-4-4-4-12 lowercase hex groups) built from the same 16 bytes. The output is `uuid=<canonical uuid>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_uuid_form.json`

```json
{
    "description": "Render a 16-byte identifier as a canonical hyphenated UUID string built from the same 16 bytes. The output reports the UUID text.",
    "cases": [
        {
            "input": {"op": "to_uuid", "hex": "000102030405060708090a0b0c0d0e0f"},
            "expected_output": "uuid=00010203-0405-0607-0809-0a0b0c0d0e0f\n"
        }
    ]
}
```

---

### Feature 6: Temporal Interpretation of the Timestamp Section

**As a developer**, I want to read the timestamp section as a Unix time and as a calendar date-time, so I can recover when an identifier was created.

**Expected Behavior / Usage:**

*6.1 Unix time in seconds*

The request `{"op": "unix_seconds", "hex": <6-byte buffer>}` treats the section's big-endian integer as a count of milliseconds since the Unix epoch. The Unix time in seconds is that millisecond value divided by 1000 as a real number. The output is `millis=<integer milliseconds>` followed by `seconds=<real number>` [a specific decimal rendering rule for whole-second timestamps — ask the PM for the exact format].

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_timestamp_seconds.json`

```json
{
    "description": "Interpret a 6-byte timestamp section as a Unix time. The section's big-endian integer is the number of milliseconds since the epoch; the Unix time in seconds is that value divided by 1000 as a real number. The output reports the millisecond integer and the seconds value.",
    "cases": [
        {
            "input": {"op": "unix_seconds", "hex": "015d3ef79800"},
            "expected_output": "millis=1500000000000\nseconds=1500000000.0\n"
        },
        {
            "input": {"op": "unix_seconds", "hex": "0000000004d2"},
            "expected_output": "millis=1234\nseconds=1.234\n"
        }
    ]
}
```

*6.2 UTC calendar date-time*

The request `{"op": "calendar_datetime", "hex": <6-byte buffer>}` converts the millisecond value to a UTC calendar date-time: the whole seconds map to the date-time and the leftover milliseconds become the microsecond component (i.e. leftover milliseconds × 1000 microseconds). The output is `datetime=<ISO-8601 date-time>`; when the microsecond component is zero it is omitted from the ISO rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_timestamp_datetime.json`

```json
{
    "description": "Interpret a 6-byte timestamp section as a UTC calendar date-time. The section's big-endian integer is milliseconds since the epoch; whole seconds map to the UTC date-time and the leftover milliseconds become the microsecond component. The output reports the ISO-8601 date-time.",
    "cases": [
        {
            "input": {"op": "calendar_datetime", "hex": "015d3ef79800"},
            "expected_output": "datetime=2017-07-14T02:40:00\n"
        },
        {
            "input": {"op": "calendar_datetime", "hex": "0000000004d2"},
            "expected_output": "datetime=1970-01-01T00:00:01.234000\n"
        }
    ]
}
```

---

### Feature 7: Construct an Identifier from a Complete Value

**As a developer**, I want to build a full identifier from any single value that fully determines all 16 bytes, so I can ingest identifiers from bytes, integers, text, or UUIDs.

**Expected Behavior / Usage:**

The request `{"op": "build_from_value", "source": <typed value>}` builds a complete identifier from `source`, which is one of: `{"type": "bytes", "hex": ...}` (raw bytes, must be exactly 16 bytes), `{"type": "int", "value": ...}` ([a specific bit-width validity rule for integer inputs — ask the PM for the exact constraint]), `{"type": "text", "value": ...}` (Base32 text, must be exactly 26 characters), or `{"type": "uuid", "value": ...}` (a canonical UUID string, whose 16 bytes are used directly). A buffer that is not 16 bytes, an integer that is not exactly 128 bits wide, or a text that is not 26 characters is rejected with `error=invalid_length`. On success the output reports `bytes=<lowercase hex>`, `str=<26-character Base32>`, and `int=<big-endian decimal>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_construct_from_value.json`

```json
{
    "description": "Construct a complete 16-byte identifier from a single value that fully determines it: raw 16 bytes, a 128-bit unsigned integer, a 26-character Base32 text, or a UUID. A buffer that is not 16 bytes, an integer that is not exactly 128 bits wide, or a text that is not 26 characters is rejected with a neutral length error. The output reports the resulting identifier's bytes (lowercase hexadecimal), its 26-character Base32 text and its big-endian integer value.",
    "cases": [
        {
            "input": {"op": "build_from_value", "source": {"type": "bytes", "hex": "000102030405060708090a0b0c0d0e0f"}},
            "expected_output": "bytes=000102030405060708090a0b0c0d0e0f\nstr=00041061050R3GG28A1C60T3GF\nint=5233100606242806050955395731361295\n"
        },
        {
            "input": {"op": "build_from_value", "source": {"type": "int", "value": "1339673755198158349044581307228491536"}},
            "expected_output": "bytes=0102030405060708090a0b0c0d0e0f10\nstr=01081G81860W40J2GB1G6GW3RG\nint=1339673755198158349044581307228491536\n"
        },
        {
            "input": {"op": "build_from_value", "source": {"type": "bytes", "hex": "0102030405"}},
            "expected_output": "error=invalid_length\n"
        }
    ]
}
```

---

### Feature 8: Construct an Identifier from a Timestamp Value

**As a developer**, I want to build an identifier from a timestamp expressed in any convenient form, so the resulting identifier carries a chosen creation time while its randomness is filled in fresh.

**Expected Behavior / Usage:**

The request `{"op": "build_from_timestamp", "source": <typed value>}` builds an identifier whose timestamp section is derived from `source` and whose randomness is freshly generated. Supported source types are: `{"type": "int", "value": <seconds>}` and `{"type": "float", "value": <seconds>}` (Unix time in seconds, converted to milliseconds), `{"type": "text", "value": <10-char Base32>}` (a timestamp-section text), `{"type": "bytes", "hex": <6-byte buffer>}`, `{"type": "section", "hex": <6-byte buffer>}` (a pre-built timestamp section), `{"type": "identifier", "hex": <16-byte buffer>}` (an existing identifier whose timestamp section is reused), and `{"type": "datetime", "value": "<YYYY-MM-DDThh:mm:ss>"}` (a UTC calendar date-time). Because the randomness is non-deterministic it is not reported; only the deterministic timestamp section is reported, as `timestamp_str=<10-character Base32>` followed by `timestamp_int=<millisecond integer>`. A value of an unsupported type is rejected with `error=unsupported_type`; a value that resolves to a buffer that is not exactly 48 bits (6 bytes) is rejected with `error=invalid_length`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_construct_from_timestamp.json`

```json
{
    "description": "Construct an identifier from a timestamp value of any supported form: a Unix time in seconds as an integer or real number, a 10-character Base32 timestamp text, a 6-byte buffer, a pre-built timestamp section, a full identifier (whose timestamp section is reused), or a UTC calendar date-time. The resulting identifier's randomness is freshly generated and is therefore not reported; only the deterministic timestamp section is reported, as its 10-character Base32 text and its millisecond integer. A value of an unsupported type is rejected with a neutral unsupported-type error, and a buffer that does not represent exactly 48 bits is rejected with a neutral length error.",
    "cases": [
        {
            "input": {"op": "build_from_timestamp", "source": {"type": "int", "value": "1500000000"}},
            "expected_output": "timestamp_str=01BMZFF600\ntimestamp_int=1500000000000\n"
        },
        {
            "input": {"op": "build_from_timestamp", "source": {"type": "text", "value": "01BMZFF600"}},
            "expected_output": "timestamp_str=01BMZFF600\ntimestamp_int=1500000000000\n"
        },
        {
            "input": {"op": "build_from_timestamp", "source": {"type": "datetime", "value": "2017-07-14T02:40:00"}},
            "expected_output": "timestamp_str=01BMZFF600\ntimestamp_int=1500000000000\n"
        },
        {
            "input": {"op": "build_from_timestamp", "source": {"type": "unsupported"}},
            "expected_output": "error=unsupported_type\n"
        },
        {
            "input": {"op": "build_from_timestamp", "source": {"type": "bytes", "hex": "000102030405060708090a0b0c0d0e0f"}},
            "expected_output": "error=invalid_length\n"
        }
    ]
}
```

---

### Feature 9: Construct an Identifier from a Randomness Value

**As a developer**, I want to build an identifier from a chosen randomness value expressed in any convenient form, so the resulting identifier carries that randomness while its timestamp is filled in fresh.

**Expected Behavior / Usage:**

The request `{"op": "build_from_randomness", "source": <typed value>}` builds an identifier whose randomness section is derived from `source` and whose timestamp is freshly generated. Supported source types are: `{"type": "int", "value": ...}` and `{"type": "float", "value": ...}` (an integer/real interpreted as the big-endian randomness value), `{"type": "text", "value": <16-char Base32>}`, `{"type": "bytes", "hex": <10-byte buffer>}`, `{"type": "section", "hex": <10-byte buffer>}` (a pre-built randomness section), and `{"type": "identifier", "hex": <16-byte buffer>}` (an existing identifier whose randomness section is reused). Because the timestamp is non-deterministic it is not reported; only the deterministic randomness section is reported, as `randomness_str=<16-character Base32>` followed by `randomness_int=<big-endian decimal>`. A value of an unsupported type is rejected with `error=unsupported_type`; a value that resolves to a buffer that is not exactly 80 bits (10 bytes) is rejected with `error=invalid_length`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_construct_from_randomness.json`

```json
{
    "description": "Construct an identifier from a randomness value of any supported form: an integer or real number, a 16-character Base32 randomness text, a 10-byte buffer, a pre-built randomness section, or a full identifier (whose randomness section is reused). The resulting identifier's timestamp is freshly generated and is therefore not reported; only the deterministic randomness section is reported, as its 16-character Base32 text and its big-endian integer value. A value of an unsupported type is rejected with a neutral unsupported-type error, and a buffer that does not represent exactly 80 bits is rejected with a neutral length error.",
    "cases": [
        {
            "input": {"op": "build_from_randomness", "source": {"type": "int", "value": "28463905110803495063055"}},
            "expected_output": "randomness_str=0R3GG28A1C60T3GF\nrandomness_int=28463905110803495063055\n"
        },
        {
            "input": {"op": "build_from_randomness", "source": {"type": "text", "value": "0R3GG28A1C60T3GF"}},
            "expected_output": "randomness_str=0R3GG28A1C60T3GF\nrandomness_int=28463905110803495063055\n"
        },
        {
            "input": {"op": "build_from_randomness", "source": {"type": "unsupported"}},
            "expected_output": "error=unsupported_type\n"
        },
        {
            "input": {"op": "build_from_randomness", "source": {"type": "bytes", "hex": "000102030405060708090a0b0c0d0e0f"}},
            "expected_output": "error=invalid_length\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (Base32 encode/decode with both length-dispatching and fixed-width variants; a wrapped-buffer abstraction exposing integer/text/byte views, equality and ordering across representations, and decomposition into timestamp and randomness sections plus UUID and temporal interpretation; and constructors from a complete value, a timestamp value, and a randomness value). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting `key=value` block (or a neutral `error=<category>` line) to stdout, matching the per-feature contracts above. The request's `op` selects the operation; binary buffers are passed as lowercase hex under `hex`, Base32 text under `text`, and large integers as decimal strings. All native exceptions raised by the core must be caught in this adapter and rendered as neutral error categories (`invalid_length`, `unsupported_type`, `unorderable`); no host-language runtime detail may appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- The microsecond conversion follows the same milliseconds-to-sub-second mapping described in the temporal interpretation section.
- Rejected inputs are mapped to neutral error categories following the standard error taxonomy for this toolkit.
