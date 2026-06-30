## Product Requirement Document

# Schema-Driven Binary Serialization for Typed Records — Schema Derivation, Encoding & Decoding

## Project Goal

Build a serialization library that derives a self-describing schema from a statically-typed value and encodes that value into a compact binary form (and reads it back), so developers can exchange strongly-typed data across systems without hand-writing schemas or fragile byte-level parsing code.

---

## Background & Problem

Systems that exchange structured data need both a *schema* (a machine-readable description of the data's shape) and a compact *binary encoding* that follows that schema. Writing schemas by hand and keeping them in sync with the program's types is tedious and error-prone, and bespoke binary readers/writers are easy to get subtly wrong.

This library removes that burden: given the static type of a value, it derives the matching schema automatically, encodes values to the format's compact binary layout, and decodes them back into typed values — including correct behavior when the reader's view of a type has evolved away from the writer's.

The schema is rendered as a canonical JSON document. Primitive types map to direct wire types; an optional value is expressed as a union with the null type; structured records list their fields in order; enumerations list their symbols and may declare an alias, documentation, and a fallback default symbol. The binary encoding is length-and-tag free for records (fields are simply concatenated) and uses zig-zag variable-length integers, fixed little-endian floats, and length-prefixed UTF-8 text.

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

### Feature 1: Primitive Type Schema Derivation

**As a developer**, I want a schema derived for any primitive scalar type, so I can describe simple values on the wire without writing schemas by hand.

**Expected Behavior / Usage:**

The request supplies an operation of `schema` and a `kind` naming a primitive category: a logical boolean, the four signed integer widths (8-, 16-, 32- and 64-bit), the two floating-point widths (single and double), text, and a single character. The adapter derives the schema for that scalar and prints its canonical JSON schema document. The two narrow integer widths and the 32-bit width all render as the 32-bit integer type (`"int"`); the 64-bit width renders as `"long"`; the floating-point widths render as `"float"` and `"double"`; the boolean and text kinds render as `"boolean"` and `"string"`. A single character renders as the 32-bit integer type carrying a `char` logical-type marker. Primitive schemas that are a single type are printed as that bare quoted type name; schemas with structure are printed as a pretty multi-line JSON object.

**Test Cases:** `rcb_tests/public_test_cases/feature1_primitive_schema.json`

```json
{
    "description": "Generate the serialization schema for a single scalar value of a given primitive category. The request names a primitive kind (logical boolean, the four signed integer widths, the two floating-point widths, text, and a single character). The adapter resolves the schema for that scalar type and prints its canonical schema document. Narrow integer widths collapse onto the 32-bit integer type, the character type is represented as a 32-bit integer carrying a logical-type marker, and the remaining kinds map to their direct wire types.",
    "cases": [
        {"input": {"op": "schema", "kind": "int"}, "expected_output": "\"int\"\n"},
        {"input": {"op": "schema", "kind": "char"}, "expected_output": "{\n  \"type\" : \"int\",\n  \"logicalType\" : \"char\"\n}\n"}
    ]
}
```

---

### Feature 2: Optional (Nullable) Primitive Schema Derivation

**As a developer**, I want an optional scalar's schema expressed as a union with the null type, so absent values can be represented on the wire.

**Expected Behavior / Usage:**

The request is identical to primitive schema derivation but adds an `nullable` flag set to true. The derived schema is a two-branch union whose first branch is the null type and whose second branch is the underlying primitive's schema, printed as a JSON array of the two branch schemas in that order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_nullable_primitive_schema.json`

```json
{
    "description": "Generate the serialization schema for an optional (nullable) scalar value of a given primitive category. The request names the same primitive kinds as the non-optional case but marks the value as optional. The resulting schema is a two-branch union of the null type and the underlying primitive's schema, in that order, so a missing value can be represented on the wire.",
    "cases": [
        {"input": {"op": "schema", "kind": "int", "nullable": true}, "expected_output": "[ \"null\", \"int\" ]\n"}
    ]
}
```

---

### Feature 3: Record Type Schema Derivation

**As a developer**, I want a schema derived for structured record types, including records that embed other records, so composite data shapes are fully described.

**Expected Behavior / Usage:**

The request supplies an operation of `schema` and a `kind` naming a record shape. Supported shapes are a flat record whose fields cover each primitive category in turn; a record whose second field is itself another record; and a record nested several levels deep where each level holds the next level as its single field. The derived schema is a `record` schema document carrying the record's name and an ordered list of fields, each field rendered as a name plus the schema of its type. A record used as a field's type is expanded inline as a nested `record` schema at its point of use. Field types follow the same primitive mapping as Feature 1 (narrow integer widths collapse to the 32-bit integer type).

**Test Cases:** `rcb_tests/public_test_cases/feature3_record_schema.json`

```json
{
    "description": "Generate the serialization schema for a structured record type. The request names a record shape: a flat record whose fields cover every primitive category, a record that embeds another record as one of its fields, and a record nested several levels deep where each level holds the next level as its only field. The adapter prints the canonical record schema document, with each field rendered as a name plus the schema of its type, and embedded records expanded inline at their point of use.",
    "cases": [
        {"input": {"op": "schema", "kind": "record_nested"}, "expected_output": "{\n  \"type\" : \"record\",\n  \"name\" : \"Record\",\n  \"fields\" : [ {\n    \"name\" : \"foo\",\n    \"type\" : \"string\"\n  }, {\n    \"name\" : \"nested\",\n    \"type\" : {\n      \"type\" : \"record\",\n      \"name\" : \"Inner\",\n      \"fields\" : [ {\n        \"name\" : \"goo\",\n        \"type\" : \"string\"\n      } ]\n    }\n  } ]\n}\n"}
    ]
}
```

---

### Feature 4: Enumeration Schema Derivation & Validation

**As a developer**, I want a schema derived for an enumerated type — with its alias, documentation and fallback default — and an invalid declaration rejected up front, so enum misconfiguration fails fast.

**Expected Behavior / Usage:**

The request supplies an operation of `schema` and a `kind` naming an enumeration. A valid enumeration declares an ordered set of symbols and may attach an alias, a documentation string, and exactly one symbol marked as the fallback default. Its derived schema is an `enum` schema document carrying the type name, the documentation, the symbols in declaration order, the chosen default symbol, and the list of aliases. An enumeration that marks more than one symbol as the fallback default is invalid: schema derivation fails, and the adapter prints a single neutral error line `[a specific error string token]` instead of a schema (no host-language exception identity is leaked).

**Test Cases:** `rcb_tests/public_test_cases/feature4_enum_schema.json`

```json
{
    "description": "Generate the serialization schema for an enumerated type, and reject an invalid one. A valid enumeration declares an ordered set of symbols, may carry an alias and a documentation string, and designates one symbol as the fallback default; its schema lists the symbols in declaration order and records the alias, documentation and default. If a type declares more than one fallback default symbol it is invalid and schema generation fails; the adapter then emits a neutral error line identifying the failure category instead of a schema.",
    "cases": [
        {"input": {"op": "schema", "kind": "enum_with_default"}, "expected_output": "{\n  \"type\" : \"enum\",\n  \"name\" : \"Suit\",\n  \"doc\" : \"documentation\",\n  \"symbols\" : [ \"SPADES\", \"HEARTS\", \"DIAMONDS\", \"CLUBS\" ],\n  \"default\" : \"DIAMONDS\",\n  \"aliases\" : [ \"MySuit\" ]\n}\n"},
        {"input": {"op": "schema", "kind": "enum_invalid_default"}, "expected_output": "[a specific error string token]\n"}
    ]
}
```

---

### Feature 5: Primitive Value Binary Encoding

**As a developer**, I want scalar values encoded to the format's compact binary layout, so I can see the exact bytes that go on the wire.

**Expected Behavior / Usage:**

The request supplies an operation of `encode`, a `kind` naming the primitive category, and the `value` to encode. The adapter encodes the value to the compact binary form and prints the resulting bytes as a single lowercase hexadecimal string (two hex digits per byte, no separators). A boolean encodes to one byte (`01` for true, `00` for false). The signed integer widths encode as a zig-zag variable-length integer. A single character encodes as the zig-zag variable-length integer of its code point (it is supplied as a one-character string). The single- and double-precision floating-point widths encode as 4 and 8 fixed little-endian bytes respectively. Text encodes as the zig-zag variable-length integer of its UTF-8 byte length, immediately followed by those UTF-8 bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature5_primitive_encoding.json`

```json
{
    "description": "Encode a single scalar value into the compact binary wire format and print the resulting bytes as a lowercase hexadecimal string. The request names the primitive category and supplies the value. Booleans encode to a single byte; the signed integer widths and the character (by its code point) use zig-zag variable-length integers; the floating-point widths use fixed little-endian layouts; text encodes as its zig-zag length prefix followed by its UTF-8 bytes.",
    "cases": [
        {"input": {"op": "encode", "kind": "int", "value": 44}, "expected_output": "58\n"},
        {"input": {"op": "encode", "kind": "string", "value": "Hello world"}, "expected_output": "1648656c6c6f20776f726c64\n"},
        {"input": {"op": "encode", "kind": "char", "value": "A"}, "expected_output": "8201\n"}
    ]
}
```

---

### Feature 6: Record Value Binary Encoding

**As a developer**, I want record values encoded to the compact binary layout, so I can verify the framing-free concatenation of field encodings.

**Expected Behavior / Usage:**

The request supplies an operation of `encode`, a `kind` naming a record shape, and a `value` object keyed by field name. The adapter encodes the record and prints the resulting bytes as a single lowercase hexadecimal string. A record adds no framing of its own: its encoding is the concatenation, in declared field order, of each field value encoded with the same per-type rules as standalone scalars (Feature 5).

**Test Cases:** `rcb_tests/public_test_cases/feature6_record_encoding.json`

```json
{
    "description": "Encode a structured record value into the compact binary wire format and print the resulting bytes as a lowercase hexadecimal string. The request names a record shape and supplies the field values as an object keyed by field name. Records carry no framing of their own: the encoding is simply the concatenation of each field's encoded value in declared field order, using the same per-type encodings as for standalone scalars.",
    "cases": [
        {"input": {"op": "encode", "kind": "record_single_int", "value": {"z": 44}}, "expected_output": "58\n"},
        {"input": {"op": "encode", "kind": "record_eight_primitives", "value": {"a": "Hello world", "b": 3.235, "c": true, "d": 3.4, "e": 65653, "f": 44, "g": 3, "h": 3}}, "expected_output": "1648656c6c6f20776f726c64e17a14ae47e10940019a995940ea8108580606\n"}
    ]
}
```

---

### Feature 7: Enumeration Decode With Schema Evolution

**As a developer**, I want an enum value written by one version of a type to be read by another version that shares the enum's name and default, so a reader gracefully tolerates symbols it does not know.

**Expected Behavior / Usage:**

A value is written with a wider enumeration that knows the given symbol, then read back with a narrower enumeration that shares the same enum name and the same fallback default symbol but a smaller symbol set. The request supplies an operation of `decode_enum_evolution` and the `symbol` to write. When the written symbol also exists in the reader's set, it decodes to itself. When the written symbol is unknown to the reader, decoding does not fail; instead it resolves to the reader's fallback default symbol. The adapter prints the decoded symbol's name.

**Test Cases:** `rcb_tests/public_test_cases/feature7_enum_decode_default.json`

```json
{
    "description": "Decode an enumerated value using a reader type whose symbol set differs from the writer's. A value is first written with a wider enumeration (one that knows the given symbol) and then read back with a narrower enumeration that shares the same enum name and default symbol. When the written symbol also exists in the reader, it decodes to itself; when the written symbol is unknown to the reader, decoding falls back to the reader's designated default symbol rather than failing. The adapter prints the decoded symbol's name.",
    "cases": [
        {"input": {"op": "decode_enum_evolution", "symbol": "A"}, "expected_output": "A\n"},
        {"input": {"op": "decode_enum_evolution", "symbol": "B"}, "expected_output": "UNKNOWN\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (schema derivation for primitives, optionals, records and enumerations; compact binary encoding of scalars and records; and enum decoding with reader/writer schema evolution). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `op` selects behavior: `schema` derives and prints the canonical schema document for a primitive `kind` (optionally `nullable`) or a named record/enum shape; `encode` encodes a supplied `value` of the named `kind` and prints the bytes as a lowercase hex string; `decode_enum_evolution` writes the supplied `symbol` with a wider enumeration and reads it back with a narrower one, printing the decoded symbol name. Native exceptions raised by the core must be translated, in the adapter's render layer, into neutral `error=<category>` lines (e.g. `[a specific error string token]`) without leaking host-language runtime type names.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the 'op' constant values defined in the routing gateway module
