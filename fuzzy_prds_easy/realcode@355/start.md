## Product Requirement Document

# Binary Wire Codec for a SQL Database Protocol — Encode, Decode, and Parameter Binding

## Project Goal

Build a reusable binary codec for the PostgreSQL wire protocol that converts typed values to and from the protocol's binary on-the-wire byte layout, so a database client can send query parameters and read result columns in binary form without each call site hand-rolling byte-order, framing, and type-identifier handling.

---

## Background & Problem

A SQL database driver that talks the PostgreSQL binary protocol must turn in-memory values into exact byte sequences (and back) according to a fixed wire format: integers in big-endian order at fixed widths, floats as IEEE-754 bit patterns, text as raw bytes, arrays with a structured header, and each value optionally framed with its numeric type identifier and length. The driver must also assemble the per-parameter metadata (type identifiers, format codes, lengths, value pointers) the protocol requires when sending a parameterized query, and it must reject mismatched or malformed incoming data with clear, predictable errors.

Without a shared codec, every driver re-implements byte twiddling and framing, which is repetitive and error-prone (endianness bugs, off-by-one sizes, leaking host-language exception types to callers). This library centralizes the encode/decode/bind rules behind one contract: given a typed value you get its exact wire bytes; given wire bytes and the expected type you get the value back; given a parameter you get its protocol metadata; and on bad input you get a small set of normalized error categories.

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

### Feature 1: Binary Value Serialization

**As a developer**, I want typed values rendered into the exact wire bytes the protocol expects, so I can place query parameters and array payloads on the wire without manual byte manipulation.

**Expected Behavior / Usage:**

*1.1 Scalar serialization — encode a single value to its binary wire bytes*

The request names a wire data type and a value. The output reports `size=<n>` (the number of bytes produced) and `bytes=<hex>` (those bytes as space-separated uppercase two-digit hexadecimal, or empty when there are none). Signed integers are written in big-endian (network) byte order at a fixed width keyed to the type: 1 byte (`int1`), 2 bytes (`int2`), 4 bytes (`int4`), 8 bytes (`int8`). A 32-bit float (`float4`) is written as its IEEE-754 big-endian bit pattern. Text is written verbatim as its raw bytes with no length prefix and no terminator. A null value (`null`) produces zero bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_scalar_serialization.json`

```json
{
    "description": "Serialize a single scalar value into its PostgreSQL binary wire representation. The request names the wire data type and the value; the output reports the number of bytes produced and those bytes as space-separated uppercase two-digit hexadecimal. Signed integers are encoded in big-endian (network) byte order using a fixed width determined by the type (1, 2, 4, or 8 bytes). A 32-bit floating point value is encoded as its IEEE-754 big-endian bit pattern. Text is stored verbatim as its raw UTF-8 bytes with no length prefix and no terminator. A null value produces no bytes at all.",
    "cases": [
        {"input": {"op": "serialize", "type": "int4", "value": 42}, "expected_output": "size=4\nbytes=00 00 00 2A\n"},
        {"input": {"op": "serialize", "type": "float4", "value": 42.13}, "expected_output": "size=4\nbytes=42 28 85 1F\n"},
        {"input": {"op": "serialize", "type": "null"}, "expected_output": "size=0\nbytes=\n"}
    ]
}
```

*1.2 Array serialization — encode a one-dimensional array to its binary wire bytes*

The request names the element wire type and lists the element values. The output reports `size=<n>` and `bytes=<hex>`. The encoding is a header of big-endian 32-bit words — dimension count, a data-offset/flags word, the element type's numeric identifier — followed per dimension by the dimension length and a lower-bound word, followed by each element written as a 32-bit big-endian size and then that element's own binary form.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_array_serialization.json`

```json
{
    "description": "Serialize a one-dimensional array of values into the PostgreSQL binary array wire format. The request names the element wire type and lists the element values; the output reports the total byte count and the produced bytes as space-separated uppercase hexadecimal. The encoding begins with a fixed header in big-endian 32-bit words: the number of dimensions, a data-offset/flags word, and the element type's numeric type identifier; then, per dimension, the dimension length and a lower-bound word; then each element is written as a 32-bit big-endian size followed by that element's own binary representation.",
    "cases": [
        {"input": {"op": "serialize_array", "element": "float4", "values": [42.13]}, "expected_output": "[array serialization output format]\nbytes=[array serialization output format] BC 00 00 00 01 00 00 00 00 00 00 00 04 42 28 85 1F\n"}
    ]
}
```

---

### Feature 2: Framed Serialization (Type Identifier + Size + Payload)

**As a developer**, I want a value written as a self-describing frame, so it can be embedded where its type must travel alongside its data (for example as a composite element).

**Expected Behavior / Usage:**

The request names a wire type and a value (raw bytes for `bytea`, a string for `name`). The frame is the value's numeric type identifier as a 32-bit big-endian word, then the payload size as a 32-bit big-endian word, then the raw payload bytes. The output decodes that frame into `oid=<id>`, `size=<payload-size>`, and `data=<hex>` (payload bytes as space-separated uppercase hexadecimal). A raw byte string is framed with its bytes unchanged; an identifier name is framed as its raw text bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature2_framed_serialization.json`

```json
{
    "description": "Serialize a value as a full wire frame, the layout used when an item must carry its own type information (for example as an element of a composite). The frame is the value's numeric type identifier as a 32-bit big-endian word, followed by the value's payload size as a 32-bit big-endian word, followed by the raw payload bytes. The output reports the decoded type identifier, the payload size, and the payload bytes as space-separated uppercase hexadecimal. A raw byte string is framed as its bytes unchanged; a short identifier name is framed as its raw text bytes.",
    "cases": [
        {"input": {"op": "frame", "type": "bytea", "value": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0]}, "expected_output": "[opaque internal frame identifier and payload structure]\n[opaque internal frame identifier and payload structure]\n[opaque internal frame identifier and payload structure]\n"},
        {"input": {"op": "frame", "type": "name", "value": "name"}, "expected_output": "oid=19\nsize=4\ndata=6E 61 6D 65\n"}
    ]
}
```

---

### Feature 3: Binary Value Deserialization

**As a developer**, I want incoming wire bytes turned back into typed values with the incoming type validated, so I can read result columns safely and get predictable errors on bad data.

**Expected Behavior / Usage:**

*3.1 Scalar deserialization — decode a single value from wire bytes*

The request supplies the incoming column's numeric type identifier (`oid`), the target wire type to decode into (`as`), and the raw `bytes`. Decoding proceeds only when the incoming identifier is compatible with the target type. Output is `value=<decoded>`: big-endian integers of width 2/4/8 become their numeric value; a single boolean byte becomes `true` or `false`; text and identifier names become the literal string; a raw byte string is reported as space-separated uppercase hexadecimal.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_scalar_deserialization.json`

```json
{
    "description": "Deserialize a single scalar value from PostgreSQL binary wire bytes back into a typed value. The request supplies the incoming column's numeric type identifier, the target wire type to decode into, and the raw bytes; the output reports the decoded value. Decoding succeeds only when the incoming type identifier is compatible with the target type. Big-endian integers of width 2, 4, and 8 become their numeric value; a single boolean byte becomes true or false; text bytes become the literal string; an identifier name becomes its string; a raw byte string is reported back as space-separated uppercase hexadecimal.",
    "cases": [
        {"input": {"op": "deserialize", "oid": 16, "as": "bool", "bytes": [1]}, "expected_output": "value=true\n"},
        {"input": {"op": "deserialize", "oid": 23, "as": "int4", "bytes": [0, 0, 0, 7]}, "expected_output": "value=7\n"},
        {"input": {"op": "deserialize", "oid": 25, "as": "text", "bytes": [116, 101, 115, 116]}, "expected_output": "value=test\n"}
    ]
}
```

*3.2 Array deserialization — decode a one-dimensional array from wire bytes*

The request supplies the array's numeric type identifier (`oid`), an element decoding mode (`as`), and the raw `bytes` laid out as the binary array header (dimension count, offset/flags word, element type identifier, then per-dimension length and lower bound) followed by each element as a 32-bit big-endian size and payload. Output is `size=<count>` then one indexed line per element (`[i]=<value>`). In a mode that tolerates missing elements, a per-element size of -1 marks the element absent and it renders as `<null>`. A dimension count of zero yields no elements.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_array_deserialization.json`

```json
{
    "description": "Deserialize a one-dimensional array from PostgreSQL binary array bytes into a sequence of elements. The request supplies the array's numeric type identifier, the element decoding mode, and the raw bytes laid out as the binary array header (dimension count, offset/flags word, element type identifier, then per-dimension length and lower bound) followed by each element as a 32-bit big-endian size and payload. The output reports the element count and then each element on its own indexed line. When the element mode tolerates missing values, a per-element size of -1 marks that element as absent and it is rendered as a null marker. An array whose dimension count is zero yields no elements.",
    "cases": [
        {"input": {"op": "deserialize_array", "oid": 1009, "as": "text", "bytes": [0,0,0,1, 0,0,0,0, 0,0,0,25, 0,0,0,3, 0,0,0,1, 0,0,0,4, 116,101,115,116, 0,0,0,3, 102,111,111, 0,0,0,3, 98,97,114]}, "expected_output": "size=3\n[0]=test\n[1]=foo\n[2]=bar\n"},
        {"input": {"op": "deserialize_array", "oid": 1009, "as": "text_nullable", "bytes": [0,0,0,1, 0,0,0,0, 0,0,0,25, 0,0,0,3, 0,0,0,1, 255,255,255,255, 0,0,0,3, 102,111,111, 0,0,0,3, 98,97,114]}, "expected_output": "size=3\n[0]=<null>\n[1]=foo\n[2]=bar\n"}
    ]
}
```

*3.3 Deserialization error categories — normalized failures*

When decoding cannot proceed, the output is a single `error=<category>` line (never the value). `oid_type_mismatch`: the incoming type identifier is not acceptable for the requested target type (including an array whose declared element identifier is wrong). `unexpected_null`: a null is received for a target that cannot represent null (a null value for a non-nullable scalar, or a null element for a non-nullable element sequence). `invalid_data`: a malformed payload, such as a fixed-width value whose byte length disagrees with the type, or an array declaring more than one dimension.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_deserialization_errors.json`

```json
{
    "description": "Report normalized, language-neutral error categories when deserialization cannot proceed. The request is shaped like a normal deserialize/deserialize_array request but describes a faulty situation; instead of a value, the output is a single error line naming the failure category. The categories are: oid_type_mismatch when the incoming type identifier is not acceptable for the requested target type (including an array whose declared element type identifier is wrong); unexpected_null when a null is received for a target that cannot represent null (a null value for a non-nullable scalar, or a null element for a non-nullable element sequence); and invalid_data for malformed payloads such as a fixed-width value whose byte length disagrees with the type, or an array declaring more than one dimension.",
    "cases": [
        {"input": {"op": "deserialize", "oid": 25, "as": "int4", "bytes": [116, 101, 120, 116, 0]}, "expected_output": "error=oid_type_mismatch\n"},
        {"input": {"op": "deserialize", "oid": 25, "as": "text", "null": true}, "expected_output": "error=unexpected_null\n"},
        {"input": {"op": "deserialize", "oid": 16, "as": "bool", "bytes": [1, 0]}, "expected_output": "error=invalid_data\n"}
    ]
}
```

---

### Feature 4: Query Parameter Binding Metadata

**As a developer**, I want a parameterized query assembled into the per-parameter metadata the protocol requires, so I can issue binary queries with correct type identifiers, lengths, and values.

**Expected Behavior / Usage:**

*4.1 Parameter count — bind text and parameters and report the count*

The request supplies a query `text` and a list of `params`. Output is `params_count=<n>` then `text=<text>`: the count equals the number of supplied parameters regardless of their types, and the text is reported unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_parameter_count.json`

```json
{
    "description": "Build a parameterized binary query from a query text and a list of bound parameters, then report how many parameters were bound and the query text that will be sent. The output is the parameter count followed by the query text exactly as provided. The count equals the number of supplied parameters regardless of their individual types; the text is passed through unchanged.",
    "cases": [
        {"input": {"op": "bind_count", "text": "", "params": []}, "expected_output": "params_count=0\ntext=\n"},
        {"input": {"op": "bind_count", "text": "", "params": [{"type": "bool"}, {"type": "int4"}, {"type": "text"}]}, "expected_output": "params_count=3\ntext=\n"}
    ]
}
```

*4.2 Parameter wire metadata — report a single parameter's protocol fields*

The request supplies a query `text` and one `param`. Output is `params_count=1`, `text=<text>`, `oid=<type-id>`, `format=1`, `length=<n>`, and `value=<hex-or-null>`. Parameters are always sent in binary, so the format code is always 1. A present value reports its type's numeric identifier, the byte length of its binary form, and those bytes in uppercase hexadecimal. A typed null reports the underlying type's identifier, a length of -1, and `<null>`. An untyped null reports a type identifier of 0, a length of -1, and `<null>`. An array-typed value reports the array's own numeric type identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_parameter_metadata.json`

```json
{
    "description": "Build a parameterized binary query carrying a single bound parameter and report the per-parameter wire metadata that the protocol requires for that parameter: its numeric type identifier, its wire format code, its serialized byte length, and its serialized bytes. Parameters are always sent in binary, so the format code is always 1. A present value reports its type's numeric identifier, the byte length of its binary form, and those bytes as space-separated uppercase hexadecimal. A typed null value reports the underlying type's identifier, a length of -1, and a null marker for the value. An untyped null reports a type identifier of 0, a length of -1, and a null marker. An array-typed value reports the array's own numeric type identifier.",
    "cases": [
        {"input": {"op": "bind_meta", "text": "", "param": {"type": "text", "value": "std::string"}}, "expected_output": "params_count=1\ntext=\noid=25\nformat=1\nlength=11\nvalue=73 74 64 3A 3A 73 74 72 69 6E 67\n"},
        {"input": {"op": "bind_meta", "text": "", "param": {"type": "int4", "null": true}}, "expected_output": "params_count=1\ntext=\noid=23\nformat=1\nlength=-1\nvalue=<null>\n"}
    ]
}
```

---

### Feature 5: Status-Code Base-36 Conversion

**As a developer**, I want to convert compact alphanumeric status codes to and from their integer encoding, so I can map protocol status strings to numeric error codes and back.

**Expected Behavior / Usage:**

Decoding (`base36_to_long`) reads a status `code` string and interprets it as a base-36 number — digits 0-9 then letters, case-insensitive — and reports `value=<integer>`. Encoding (`long_to_base36`) takes an integer `value` and reports `code=<string>`, the canonical base-36 representation using digits 0-9 and uppercase letters A-Z, most-significant digit first, with no leading zeros.

**Test Cases:** `rcb_tests/public_test_cases/feature5_status_code_base36.json`

```json
{
    "description": "Convert between a compact alphanumeric status code and its integer encoding using base-36. Decoding reads a status code string and interprets it as a base-36 number (digits 0-9 then letters), case-insensitively, producing the integer value. Encoding takes an integer and produces the canonical base-36 string using digits 0-9 and uppercase letters A-Z, most-significant digit first, with no leading zeros.",
    "cases": [
        {"input": {"op": "base36_to_long", "code": "HV001"}, "expected_output": "value=29999809\n"},
        {"input": {"op": "long_to_base36", "value": 29999809}, "expected_output": "code=HV001\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codec library implementing the features above — value serialization, array serialization, framing, deserialization with type validation and normalized errors, parameter-binding metadata, and base-36 status-code conversion. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint and keep the core logic decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON request from stdin, selects behavior by the `op` field (`serialize`, `serialize_array`, `frame`, `deserialize`, `deserialize_array`, `bind_count`, `bind_meta`, `base36_to_long`, `long_to_base36`), invokes the core codec, and prints the line-oriented result (or a normalized `error=<category>` line) to stdout, matching the per-feature contracts above. Numeric type identifiers used in the contract follow the PostgreSQL system catalog (for example bool=16, bytea=17, name=19, int8=20, int2=21, int4=23, text=25, text-array=1009, int4-array=1007). Byte buffers are rendered as space-separated uppercase two-digit hexadecimal.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the metadata layout for serialize_array
- adhere to the deserialization output schema
