## Product Requirement Document

# Binary JSON Document Toolkit - BSON Value Conversion and Wire Encoding

## Project Goal

Build a binary JSON document toolkit that allows developers to convert between ordinary JSON-shaped inputs, Extended JSON, BSON wire bytes, and typed BSON scalar values without hand-writing byte encoders, special numeric wrappers, or ad hoc date and identifier parsers.

---

## Background & Problem

Without this library, developers are forced to manually distinguish BSON integer widths, encode length-prefixed documents, base64-encode binary values, normalize object identifiers, and preserve wire-format representations for timestamps, regular expressions, dates, and decimal values. This leads to repetitive conversion code, incorrect edge-case handling, and data interchange bugs between systems that expect BSON or Extended JSON.

With this library, developers can provide JSON-shaped command input to an execution adapter, invoke the corresponding BSON behavior, and receive deterministic stdout that exposes the observable value, wire length, or normalized error category.

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

### Feature 1: Extended JSON Rendering

**As a developer**, I want to render BSON-compatible values as Extended JSON, so I can exchange typed data through JSON without losing BSON-specific type information.

**Expected Behavior / Usage:**

The execution adapter accepts an input object with `task` selecting the rendering mode and `value` containing a JSON-compatible BSON value. BSON wrappers such as `$numberLong`, `$numberDouble`, `$oid`, and `$date` must be interpreted as typed values before rendering. Output is exactly one JSON string followed by a newline, with no status words.

*1.1 Canonical Extended JSON — Preserve exact type wrappers for BSON values.*

Canonical rendering must output explicit Extended JSON wrappers for BSON-specific scalar widths and values. Plain JSON integers that fit the 32-bit BSON integer range render as `$numberInt`; long integers render as `$numberLong`; special values retain their canonical wrapper representation. Nested arrays and documents must be traversed recursively.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_canonical_extended_json.json`

```json
{
  "description": "Convert externally supplied JSON-compatible BSON values to canonical Extended JSON, preserving exact numeric widths and special BSON wrappers.",
  "cases": [
    {
      "input": {"task":"json_to_canonical_extended","value":{"int32":42,"int64":{"$numberLong":"9223372036854775807"},"double":{"$numberDouble":"1.5"},"string":"hello","bool":true,"null":null}},
      "expected_output": "{\"int32\":{\"$numberInt\":\"42\"},\"int64\":{\"$numberLong\":\"9223372036854775807\"},\"double\":{\"$numberDouble\":\"1.5\"},\"string\":\"hello\",\"bool\":true,\"null\":null}\n"
    },
    {
      "input": {"task":"json_to_canonical_extended","value":{"array":[1,{"$oid":"000000000000000000000000"},{"$date":{"$numberLong":"0"}}]}},
      "expected_output": "{\"array\":[{\"$numberInt\":\"1\"},{\"$oid\":\"000000000000000000000000\"},{\"$date\":{\"$numberLong\":\"0\"}}]}\n"
    }
  ]
}
```

*1.2 Relaxed Extended JSON — Use ordinary JSON scalars when lossless and permitted.*

Relaxed rendering must output ordinary JSON numbers and ISO date strings where the BSON Extended JSON relaxed form permits them. Values that do not have a safe ordinary JSON representation, such as non-finite doubles, must retain Extended JSON wrappers.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_relaxed_extended_json.json`

```json
{
  "description": "Convert externally supplied JSON-compatible BSON values to relaxed Extended JSON, using ordinary JSON scalars where the format allows them.",
  "cases": [
    {
      "input": {"task":"json_to_relaxed_extended","value":{"int32":42,"int64":{"$numberLong":"9007199254740991"},"double":{"$numberDouble":"1.5"},"date":{"$date":{"$numberLong":"0"}}}},
      "expected_output": "{\"int32\":42,\"int64\":9007199254740991,\"double\":1.5,\"date\":{\"$date\":\"1970-01-01T00:00:00Z\"}}\n"
    },
    {
      "input": {"task":"json_to_relaxed_extended","value":{"min_int64":{"$numberLong":"-9223372036854775808"},"nan":{"$numberDouble":"NaN"},"infinity":{"$numberDouble":"Infinity"}}},
      "expected_output": "{\"min_int64\":-9223372036854775808,\"nan\":{\"$numberDouble\":\"NaN\"},\"infinity\":{\"$numberDouble\":\"Infinity\"}}\n"
    }
  ]
}
```

---

### Feature 2: BSON Document Wire Round Trip

**As a developer**, I want to encode a document to BSON bytes and decode it back, so I can verify that the wire representation preserves the document's typed contents.

**Expected Behavior / Usage:**

The execution adapter accepts `task` set to `bson_roundtrip` and a `document` object. It must encode the document as BSON wire bytes, decode those bytes back into a document, and print two lines: `byte_length=<number>` and `canonical=<canonical Extended JSON document>`. The byte length is the actual BSON byte count, including document length and terminator bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature2_bson_document_roundtrip.json`

```json
{
  "description": "Encode a document to the BSON wire byte format and decode it back, reporting the byte length and the canonical value that survived the round trip.",
  "cases": [
    {
      "input": {"task":"bson_roundtrip","document":{"name":"Ada","age":36,"active":true,"scores":[10,20]}},
      "expected_output": "byte_length=64\ncanonical={\"name\":\"Ada\",\"age\":{\"$numberInt\":\"36\"},\"active\":true,\"scores\":[{\"$numberInt\":\"10\"},{\"$numberInt\":\"20\"}]}\n"
    },
    {
      "input": {"task":"bson_roundtrip","document":{"_id":{"$oid":"64b9523b35795e90949872a1"},"created":{"$date":{"$numberLong":"1689866811000"}},"nested":{"x":1}}},
      "expected_output": "byte_length=59\ncanonical={\"_id\":{\"$oid\":\"64b9523b35795e90949872a1\"},\"created\":{\"$date\":{\"$numberLong\":\"1689866811000\"}},\"nested\":{\"x\":{\"$numberInt\":\"1\"}}}\n"
    }
  ]
}
```

---

### Feature 3: Document Path Lookup

**As a developer**, I want to read nested values from BSON documents by field path, so I can distinguish successful lookup, missing fields, and attempts to continue through a non-document value.

**Expected Behavior / Usage:**

The execution adapter accepts `task` set to `document_lookup`, a `document` object, and `path` as an array of field names. If all path segments resolve, stdout must contain `found=true` and the canonical Extended JSON representation of the value. If a field is missing, stdout must contain `found=false` and `missing=<field>`. If traversal reaches a scalar or array before consuming the next field name, stdout must contain `found=false` and `not_document_at=<field>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_document_path_lookup.json`

```json
{
  "description": "Read a value from a document by walking a sequence of field names, distinguishing successful lookup from missing fields and non-document path segments.",
  "cases": [
    {
      "input": {"task":"document_lookup","document":{"user":{"profile":{"name":"Ada","visits":3}}},"path":["user","profile","name"]},
      "expected_output": "found=true\nvalue=\"Ada\"\n"
    },
    {
      "input": {"task":"document_lookup","document":{"user":{"profile":{"name":"Ada"}}},"path":["user","settings","theme"]},
      "expected_output": "found=false\nmissing=settings\n"
    },
    {
      "input": {"task":"document_lookup","document":{"user":{"name":"Ada"}},"path":["user","name","first"]},
      "expected_output": "found=false\nnot_document_at=first\n"
    }
  ]
}
```

---

### Feature 4: Object Identifier Parsing

**As a developer**, I want to parse BSON object identifiers, so I can validate identifier strings and recover their embedded timestamp.

**Expected Behavior / Usage:**

The execution adapter accepts `task` set to `object_id` and `hex` as a string. A valid identifier is exactly the BSON object-id hexadecimal form and prints `hex=<normalized lowercase hexadecimal>` plus `timestamp=<milliseconds since Unix epoch>`. Invalid input must be normalized to `error=invalid_object_id` and echo the raw input on a separate `[a specific error message string for invalid ISO8601]` line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_object_identifier.json`

```json
{
  "description": "Parse a 24-character hexadecimal object identifier, render its normalized hexadecimal form, and expose the timestamp encoded in the identifier.",
  "cases": [
    {
      "input": {"task":"object_id","hex":"000000000000000000000000"},
      "expected_output": "hex=000000000000000000000000\ntimestamp=0\n"
    },
    {
      "input": {"task":"object_id","hex":"64b9523b35795e90949872a1"},
      "expected_output": "hex=64b9523b35795e90949872a1\ntimestamp=1689866811000\n"
    },
    {
      "input": {"task":"object_id","hex":"not-a-valid-id"},
      "expected_output": "error=invalid_object_id\n[a specific error message string for invalid ISO8601]not-a-valid-id\n"
    }
  ]
}
```

---

### Feature 5: BSON Datetime Conversion

**As a developer**, I want to create BSON datetimes from epoch milliseconds or timestamp strings, so I can produce stable Extended JSON date output and normalized parse failures.

**Expected Behavior / Usage:**

The execution adapter accepts `task` set to `datetime` with either `milliseconds` as an integer or `iso8601` as a timestamp string. Successful output must include the epoch millisecond value, canonical Extended JSON date form, and relaxed Extended JSON date form. Invalid timestamp strings must produce `[a specific error message string for invalid ISO8601]` and the raw input on a separate line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_datetime_conversion.json`

```json
{
  "description": "Create a BSON datetime from either milliseconds since the Unix epoch or an RFC 3339 timestamp, then render milliseconds and both canonical and relaxed Extended JSON forms.",
  "cases": [
    {
      "input": {"task":"datetime","milliseconds":0},
      "expected_output": "milliseconds=0\ncanonical={\"$date\":{\"$numberLong\":\"0\"}}\nrelaxed={\"$date\":\"1970-01-01T00:00:00Z\"}\n"
    },
    {
      "input": {"task":"datetime","iso8601":"2023-07-20T17:26:51Z"},
      "expected_output": "milliseconds=1689874011000\ncanonical={\"$date\":{\"$numberLong\":\"1689874011000\"}}\nrelaxed={\"$date\":\"2023-07-20T17:26:51Z\"}\n"
    },
    {
      "input": {"task":"datetime","iso8601":"not-a-date"},
      "expected_output": "[a specific error message string for invalid ISO8601]\n[a specific error message string for invalid ISO8601]not-a-date\n"
    }
  ]
}
```

---

### Feature 6: Decimal128 Conversion

**As a developer**, I want to parse decimal floating-point strings into BSON Decimal128 values, so I can preserve decimal precision and represent special decimal values.

**Expected Behavior / Usage:**

The execution adapter accepts `task` set to `decimal128` and `value` as a string. Successful output must include the normalized decimal string and the canonical Extended JSON decimal representation. Invalid decimal strings must produce `error=invalid_decimal128` and echo the raw input on a separate line.

**Test Cases:** `rcb_tests/public_test_cases/feature6_decimal128_conversion.json`

```json
{
  "description": "Parse decimal floating-point strings into Decimal128 values, preserve the normalized decimal string, and render canonical Extended JSON.",
  "cases": [
    {
      "input": {"task":"decimal128","value":"1234.5678"},
      "expected_output": "string=1234.5678\ncanonical={\"$numberDecimal\":\"1234.5678\"}\n"
    },
    {
      "input": {"task":"decimal128","value":"NaN"},
      "expected_output": "string=NaN\ncanonical={\"$numberDecimal\":\"NaN\"}\n"
    },
    {
      "input": {"task":"decimal128","value":"not-decimal"},
      "expected_output": "error=invalid_decimal128\n[a specific error message string for invalid ISO8601]not-decimal\n"
    }
  ]
}
```

---

### Feature 7: Binary Subtype Rendering

**As a developer**, I want to create BSON binary values from bytes and subtype names, so I can verify base64 data and BSON subtype metadata in Extended JSON.

**Expected Behavior / Usage:**

The execution adapter accepts `task` set to `binary_uuid`, `subtype` as a supported subtype name, and `hex` as hexadecimal bytes. Successful output must report the subtype name, byte count, and canonical Extended JSON binary object containing base64 data and hexadecimal subtype code. Unknown subtype names must produce `error=invalid_binary_subtype` and echo the raw subtype value.

**Test Cases:** `rcb_tests/public_test_cases/feature7_binary_subtypes.json`

```json
{
  "description": "Create binary BSON values from hexadecimal bytes and a named subtype, reporting the subtype, byte length, and canonical Extended JSON representation.",
  "cases": [
    {
      "input": {"task":"binary_uuid","subtype":"generic","hex":"000102ff"},
      "expected_output": "subtype=generic\nbyte_length=4\ncanonical={\"$binary\":{\"base64\":\"AAEC/w==\",\"subType\":\"00\"}}\n"
    },
    {
      "input": {"task":"binary_uuid","subtype":"uuid","hex":"00112233445566778899aabbccddeeff"},
      "expected_output": "subtype=uuid\nbyte_length=16\ncanonical={\"$binary\":{\"base64\":\"ABEiM0RVZneImaq7zN3u/w==\",\"subType\":\"04\"}}\n"
    },
    {
      "input": {"task":"binary_uuid","subtype":"unknown","hex":"00"},
      "expected_output": "error=invalid_binary_subtype\n[a specific error message string for invalid ISO8601]unknown\n"
    }
  ]
}
```

---

### Feature 8: Regular Expression and Timestamp Rendering

**As a developer**, I want to represent BSON regular expressions and timestamps in documents, so I can emit their canonical wire-level Extended JSON forms.

**Expected Behavior / Usage:**

The execution adapter accepts `task` set to `regex_timestamp`, `pattern` and `options` strings for a BSON regular expression, and unsigned integer `time` and `increment` fields for a BSON timestamp. Output is a single `canonical=` line containing a document with `$regularExpression` and `$timestamp` Extended JSON values.

**Test Cases:** `rcb_tests/public_test_cases/feature8_regex_and_timestamp.json`

```json
{
  "description": "Represent regular expressions and BSON timestamps in a document and render their canonical Extended JSON wire-level forms.",
  "cases": [
    {
      "input": {"task":"regex_timestamp","pattern":"^abc","options":"im","time":10,"increment":2},
      "expected_output": "canonical={\"regex\":{\"$regularExpression\":{\"pattern\":\"^abc\",\"options\":\"im\"}},\"timestamp\":{\"$timestamp\":{\"t\":10,\"i\":2}}}\n"
    },
    {
      "input": {"task":"regex_timestamp","pattern":"a.*z","options":"","time":0,"increment":0},
      "expected_output": "canonical={\"regex\":{\"$regularExpression\":{\"pattern\":\"a.*z\",\"options\":\"\"}},\"timestamp\":{\"$timestamp\":{\"t\":0,\"i\":0}}}\n"
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
- follow the error formatting convention used in feature5 datetime conversion for invalid inputs
- reference the sentinel value defined in the ID_FACTORY enumeration for invalid ISO8601
