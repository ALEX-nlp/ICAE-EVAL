## Product Requirement Document

# Cloud Event Payload Codec — Typed Value Decoding, Epoch Timestamps, and Compressed Log Batches

## Project Goal

Build a reusable codec library that translates the wire formats used by managed cloud services into native, strongly-typed values (and back), so application developers can consume incoming event payloads directly without hand-writing fragile, repetitive parsing logic for every payload shape.

---

## Background & Problem

Managed cloud services deliver events as JSON, but several fields use specialized encodings rather than plain values: document-store attributes are wrapped in self-describing type envelopes, timestamps arrive as numeric UNIX epochs at differing resolutions, and high-volume log batches are gzip-compressed and base64-encoded into a single opaque string. Without a shared codec, every consumer re-implements these conversions by hand, producing inconsistent edge-case handling, silent type coercion bugs, and brittle code that breaks when a field's representation is misread.

With this library, a developer hands the raw payload to the codec and receives well-typed values with predictable rules: type envelopes resolve to a logical type plus value, numeric strings convert to integers or reals on demand, epoch numbers round-trip to calendar instants, compressed log batches expand into structured records, and requesting a value as the wrong type fails loudly with a normalized error instead of corrupting data.

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

### Feature 1: Typed Attribute Value Codec

**As a developer**, I want to decode the self-describing, type-tagged attribute envelopes used by a NoSQL document store and convert their payloads into native values, so I can read records without manually inspecting type tags everywhere.

**Expected Behavior / Usage:**

An attribute value is a JSON object with exactly one key. That key names the value's logical type and its associated value is the encoded payload. The supported type tags are: `S` (a text string), `N` (a number carried as a decimal string), `BOOL` (a boolean), `B` (binary carried as standard base64 text), `NULL` (a null value), `SS` (a set of strings), `NS` (a set of number strings), `BS` (a set of base64 binary strings), `L` (an ordered list whose elements are themselves attribute values), and `M` (a map from string keys to attribute values).

*1.1 Decode A Wire-Format Attribute Value — resolve the type tag and report the value*

Given one attribute envelope, decode it and report its resolved logical type and value. A scalar reports its value directly: a string and a number report their textual value, a boolean reports `true`/`false`, and binary reports its standard base64 text. The null type reports a null indicator rather than a value. A collection reports its element count and then one line per element: a string/number/binary set lists each member; a list reports, per element, that element's own resolved type and its scalar value; a map reports, per entry, the entry key, the entry value's resolved type, and its scalar value, with entries ordered by key. An empty set reports a count of zero and no member lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_decode_attribute_value.json`

```json
{
    "description": "Decode a single attribute value given in the wire format used by a NoSQL document store, where every value is a JSON object with exactly one key naming its type and the matching encoded payload. The decoder reports the resolved logical type and the value. Scalars report their value directly; binary payloads are reported as their standard base64 text; collection types report their element count followed by one line per element (sets list their members, a heterogeneous list reports each element's own type and scalar value, and a map reports each entry keyed by name with its element type and scalar value, entries ordered by key); the null type reports a null indicator.",
    "cases": [
        {"input": {"action": "dynamodb_decode", "value": {"S": "Hello"}}, "expected_output": "type=String\nvalue=Hello\n"},
        {"input": {"action": "dynamodb_decode", "value": {"M": {"Name": {"S": "Joe"}, "Age": {"N": "35"}}}}, "expected_output": "type=Map\ncount=2\nAge: type=Number value=35\nName: type=String value=Joe\n"}
    ]
}
```

*1.2 Numeric Conversion Of A Number Attribute — interpret a decimal string as an integer or a real*

A number attribute carries its value as a decimal string. On request, convert it to a native numeric form. When an integer is requested, the string is parsed as a signed integer; if the string actually contains a fractional decimal, it is parsed as a real number and then truncated toward zero to an integer. When a real (floating-point) value is requested, the string is parsed as a real number. The output reports the requested numeric form and the resulting value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_number_conversion.json`

```json
{
    "description": "Convert a numeric attribute value (which arrives on the wire as a decimal string) into a native numeric form on request. When an integer is requested, the value is parsed as a signed integer; if the string holds a fractional decimal, it is first parsed as a floating-point number and then truncated toward zero to an integer. When a floating-point value is requested, the string is parsed as a real number. The output reports the requested numeric form and the resulting value.",
    "cases": [
        {"input": {"action": "dynamodb_number", "value": {"N": "123"}, "as": "integer"}, "expected_output": "integer=123\n"},
        {"input": {"action": "dynamodb_number", "value": {"N": "123.45"}, "as": "float"}, "expected_output": "float=123.45\n"}
    ]
}
```

*1.3 Type-Mismatch Access Error — reject reading a value as a type it does not hold*

When a typed accessor is requested for a value whose actual decoded type differs from the requested type, the operation must be rejected rather than silently coercing the value. The output is a normalized error contract: a line naming the error category, a line naming the requested type, and a line naming the actual type of the value. The contract carries only domain type names and must not leak any host-language runtime details.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_type_mismatch_error.json`

```json
{
    "description": "Request a typed accessor on an attribute value whose actual decoded type differs from the requested one. Accessing a value as a type it does not hold is a contract violation and must be rejected rather than silently coerced. The output is a normalized error contract that names the error category together with the requested type and the actual type of the value, so callers can diagnose the mismatch without depending on any host-language runtime details.",
    "cases": [
        {"input": {"action": "dynamodb_access", "value": {"B": "AAEqQQ=="}, "as": "number"}, "expected_output": "error=incompatible_type\nrequested=Number\nactual=Binary\n"}
    ]
}
```

---

### Feature 2: Epoch Timestamp Codec

**As a developer**, I want to convert between numeric UNIX epoch timestamps and calendar instants at the resolution the payload uses, so I can work with real dates instead of raw epoch numbers.

**Expected Behavior / Usage:**

*2.1 Seconds-Resolution Epoch — round-trip an epoch measured in seconds (fractional allowed)*

Decoding takes an epoch value measured in seconds (which may include a fractional part for sub-second precision) and yields the corresponding calendar instant in UTC, reported as its individual components: year, month, day, hour, minute, second, and millisecond. Encoding takes a calendar instant supplied as an ISO-8601 UTC timestamp and yields the epoch-seconds number, retaining the fractional digits needed to represent any sub-second precision.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_seconds_epoch.json`

```json
{
    "description": "Serialize and deserialize an instant of time expressed as a UNIX epoch measured in seconds, where fractional seconds are permitted. Decoding takes the epoch-seconds number (possibly fractional) and yields the corresponding calendar instant in UTC, reported as its individual components down to the millisecond. Encoding takes a calendar instant given as an ISO-8601 UTC timestamp and yields the epoch-seconds number, keeping the fractional part needed to represent sub-second precision.",
    "cases": [
        {"input": {"action": "epoch_seconds_decode", "value": 1480641523.476}, "expected_output": "year=2016\nmonth=12\nday=2\nhour=1\nminute=18\nsecond=43\nmillisecond=476\n"},
        {"input": {"action": "epoch_seconds_encode", "iso": "2016-12-02T01:18:43.476Z"}, "expected_output": "epoch=1480641523.476\n"}
    ]
}
```

*2.2 Milliseconds-Resolution Epoch — round-trip an epoch measured in whole milliseconds*

Decoding takes an epoch value measured in whole milliseconds and yields the corresponding calendar instant in UTC, reported with the same component breakdown as the seconds variant. Encoding takes a calendar instant supplied as an ISO-8601 UTC timestamp and yields the epoch value as an integer count of milliseconds.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_milliseconds_epoch.json`

```json
{
    "description": "Serialize and deserialize an instant of time expressed as a UNIX epoch measured in whole milliseconds. Decoding takes the epoch-milliseconds integer and yields the corresponding calendar instant in UTC, reported as its individual components down to the millisecond. Encoding takes a calendar instant given as an ISO-8601 UTC timestamp and yields the epoch-milliseconds integer.",
    "cases": [
        {"input": {"action": "epoch_millis_decode", "value": 1480641523476}, "expected_output": "year=2016\nmonth=12\nday=2\nhour=1\nminute=18\nsecond=43\nmillisecond=476\n"},
        {"input": {"action": "epoch_millis_encode", "iso": "2016-12-02T01:18:43.476Z"}, "expected_output": "epoch=1480641523476\n"}
    ]
}
```

---

### Feature 3: Compressed Log-Batch Decoding

**As a developer**, I want to expand the compact, compressed log-batch payload delivered by a managed logging pipeline into structured records, so I can process individual log entries without writing my own decompression and parsing pipeline.

**Expected Behavior / Usage:**

The payload wraps the log batch in a single opaque field whose value is the batch document first serialized to JSON, then gzip-compressed, then base64-encoded. Decoding reverses that pipeline: base64-decode the field, gzip-decompress it, and parse the recovered JSON. The recovered document carries batch metadata — the owning account identifier, the log group name, the log stream name, the list of configured subscription filters, and the message type — together with an ordered list of log entries, each with an identifier, a millisecond timestamp, and a raw message. The output reports each metadata field, the number of entries, and then one line per entry carrying its identifier, timestamp, and message; multiple subscription filters are reported as a comma-separated list.

**Test Cases:** `rcb_tests/public_test_cases/feature3_cloudwatch_logs.json`

```json
{
    "description": "Decode a managed-log delivery payload. The event carries a single opaque field holding the log batch as text that has been gzip-compressed and then base64-encoded. Decoding base64-decodes the field, decompresses it, and parses the embedded JSON document to recover the batch metadata (the account owner, the log group and stream names, the configured subscription filters, and the message type) together with the ordered list of log entries, each with its identifier, millisecond timestamp, and raw message text. The output reports the metadata fields, the number of entries, and one line per entry.",
    "cases": [
        {"input": {"action": "cloudwatch_logs_parse", "awslogs": {"data": "H4sIAAAAAAAAAHWPwQqCQBCGX0Xm7EFtK+smZBEUgXoLCdMhFtKV3akI8d0bLYmibvPPN3wz00CJxmQnTO41whwWQRIctmEcB6sQbFC3CjW3XW8kxpOpP+OC22d1Wml1qZkQGtoMsScxaczKN3plG8zlaHIta5KqWsozoTYw3/djzwhpLwivWFGHGpAFe7DL68JlBUk+l7KSN7tCOEJ4M3/qOI49vMHj+zCKdlFqLaU2ZHV2a4Ct/an0/ivdX8oYc1UVX860fQDQiMdxRQEAAA=="}}, "expected_output": "[AWS metadata fields structure]\n[AWS metadata fields structure]\n[AWS metadata fields structure]\n[AWS metadata fields structure]\n[AWS metadata fields structure]\nevents=2\n[0] id=eventId1 timestamp=1440442987000 message=[ERROR] First test message\n[1] id=eventId2 timestamp=1440442987001 message=[ERROR] Second test message\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result (or a normalized error) to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `dynamodb_decode` decodes one attribute envelope (`value`); `dynamodb_number` converts a number attribute (`value`) to the numeric form named by `as` (`integer` or `float`); `dynamodb_access` requests an accessor (`as`) on a value (`value`) and reports a normalized error on type mismatch; `epoch_seconds_decode`/`epoch_millis_decode` decode an epoch number (`value`) into calendar components; `epoch_seconds_encode`/`epoch_millis_encode` encode an ISO-8601 UTC timestamp (`iso`) into an epoch number; `cloudwatch_logs_parse` expands the compressed log batch carried under `awslogs.data`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follows the same formatting pattern as C011 and C013 for arrays
- refer to the comma-delimited format for multiple filters
