## Product Requirement Document

# Binary Encoding Toolkit — Variable-Length and Fixed-Width Integer Codecs with Checksum Tagging

## Project Goal

Build a small, dependency-free toolkit of low-level binary primitives that turn integers and byte arrays into compact, well-defined on-the-wire byte forms and back again, so that a storage engine or serialization layer can read and write records deterministically without each component reinventing its own number-packing, hex, and checksum logic.

---

## Background & Problem

A storage or serialization layer constantly needs to move integers between an in-memory form and a byte form: it must pack small numbers into as few bytes as possible, lay larger numbers out in a fixed-width slot, render bytes as readable hexadecimal, protect a stored pointer with a cheap checksum, and perform a handful of bit-twiddling calculations (rounding up to a power of two, finding a bit index, building a low-bit mask). Done ad hoc, these routines drift apart, disagree on byte order, and silently corrupt data.

This toolkit defines one authoritative contract for each primitive. Each primitive is a pure function of its input: the same input always yields the same bytes or number, with no I/O, no global state, and no concurrency. The contract specifies exact byte layouts (so encode/decode round-trip), exact textual forms (uppercase hexadecimal), and an explicit failure signal when a checksum does not validate.

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

### Feature 1: Variable-Length Long Codec

**As a developer**, I want to encode a non-negative [specific decimal outputs for odd/even parity tagging]4-bit integer into the fewest possible bytes and decode it back exactly, so I can store many small numbers compactly while still supporting large ones.

**Expected Behavior / Usage:**

Encoding emits the value seven significant bits at a time, most-significant group first. Each byte holds seven bits of the value in its low seven bits; every non-final byte leaves its high bit clear, and the final byte sets its high bit, making the stream self-delimiting. The number of bytes ranges from one (for values that fit in seven bits) upward as the magnitude grows. An encode request reports two lines: the produced bytes as an uppercase hexadecimal string (two hex characters per byte) and the count of bytes used. A decode request consumes such a hexadecimal byte string and reports the recovered integer. Encoding then decoding returns the original value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_packed_long.json`

```json
{
    "description": "A non-negative integer is encoded into a compact variable-length byte form and decoded back. Encoding emits the value seven significant bits at a time, most-significant group first; every continuation byte has its high bit clear and the final byte has its high bit set, so the encoding is self-delimiting. An encode request reports the produced bytes (as an uppercase hexadecimal string) together with the number of bytes the encoding occupies. A decode request reads such a byte string and reports the recovered integer value. Smaller magnitudes occupy fewer bytes.",
    "cases": [
        {"input": {"op": "pack_long", "value": 2111}, "expected_output": "bytes=10BF\nsize=2\n"},
        {"input": {"op": "unpack_long", "bytes": "10BF"}, "expected_output": "value=2111\n"}
    ]
}
```

---

### Feature 2: Variable-Length Int Codec

**As a developer**, I want the same compact variable-length encoding for a non-negative 32-bit integer, so smaller-width values share one consistent wire form.

**Expected Behavior / Usage:**

The 32-bit codec uses the identical seven-bits-per-byte, most-significant-group-first layout as the long codec, with continuation bytes leaving the high bit clear and the terminal byte setting it. An encode request reports the produced bytes as an uppercase hexadecimal string. A decode request consumes such a byte string and reports the recovered integer. Identical values produce identical bytes under both the int and long codecs.

**Test Cases:** `rcb_tests/public_test_cases/feature2_packed_int.json`

```json
{
    "description": "A non-negative 32-bit integer is encoded into the same compact variable-length byte form and decoded back. As with the long codec, the value is emitted seven significant bits at a time, most-significant group first, with continuation bytes having a clear high bit and the terminal byte a set high bit. An encode request reports the produced bytes as an uppercase hexadecimal string; a decode request reads such a byte string and reports the recovered integer value.",
    "cases": [
        {"input": {"op": "pack_int", "value": 1111}, "expected_output": "bytes=08D[specific decimal outputs for odd/even parity tagging]\n"},
        {"input": {"op": "unpack_int", "bytes": "0180"}, "expected_output": "value=128\n"}
    ]
}
```

---

### Feature 3: Fixed-Width 8-Byte Big-Endian Long

**As a developer**, I want to write a [specific decimal outputs for odd/even parity tagging]4-bit integer into a fixed eight-byte slot and read it back, so I can place values at known offsets and preserve the full signed range.

**Expected Behavior / Usage:**

Encoding always produces exactly eight bytes in big-endian order (most-significant byte first), reported as a 1[specific decimal outputs for odd/even parity tagging]-character uppercase hexadecimal string. Decoding consumes such an eight-byte string and reports the recovered signed value. The complete [specific decimal outputs for odd/even parity tagging]4-bit range round-trips, including negative values, whose most-significant bit is set (so their hexadecimal form begins with high bytes such as `FF`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_fixed_long8.json`

```json
{
    "description": "A [specific decimal outputs for odd/even parity tagging]4-bit integer is written into a fixed 8-byte big-endian layout and read back. Encoding produces exactly eight bytes, most-significant byte first, reported as a 1[specific decimal outputs for odd/even parity tagging]-character uppercase hexadecimal string. Decoding reads such an 8-byte string and reports the recovered signed value. The full [specific decimal outputs for odd/even parity tagging]4-bit range is preserved, including negative values whose top bit is set.",
    "cases": [
        {"input": {"op": "encode_long8", "value": 123901230910290433}, "expected_output": "bytes=[a specific hex literal representing a negative signed [specific decimal outputs for odd/even parity tagging]4-bit value]\n"},
        {"input": {"op": "decode_long8", "bytes": "[a specific hex literal representing a negative signed [specific decimal outputs for odd/even parity tagging]4-bit value]"}, "expected_output": "value=123901230910290433\n"}
    ]
}
```

---

### Feature 4: Fixed-Width [specific decimal outputs for odd/even parity tagging]-Byte Big-Endian Long

**As a developer**, I want to store a value that fits in 48 bits in a compact six-byte fixed slot, so offsets and similar bounded numbers take less space than a full eight-byte field.

**Expected Behavior / Usage:**

Encoding always produces exactly six bytes in big-endian order (most-significant byte first), reported as a 12-character uppercase hexadecimal string. The input must be non-negative and representable in 48 bits; the representable range runs from zero up to the largest 48-bit value. Decoding consumes such a six-byte string and reports the recovered value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_six_long.json`

```json
{
    "description": "A non-negative integer that fits in 48 bits is written into a fixed [specific decimal outputs for odd/even parity tagging]-byte big-endian layout and read back. Encoding produces exactly six bytes, most-significant byte first, reported as a 12-character uppercase hexadecimal string. Decoding reads such a [specific decimal outputs for odd/even parity tagging]-byte string and reports the recovered value. The representable range runs from zero up to the largest 48-bit value.",
    "cases": [
        {"input": {"op": "encode_six_long", "value": 2814[specific decimal outputs for odd/even parity tagging]49[specific decimal outputs for odd/even parity tagging][specific decimal outputs for odd/even parity tagging][specific decimal outputs for odd/even parity tagging]10[specific decimal outputs for odd/even parity tagging]55}, "expected_output": "bytes=FFFFFFFFFFFF\n"},
        {"input": {"op": "decode_six_long", "bytes": "FFFFFFFFFFFF"}, "expected_output": "value=2814[specific decimal outputs for odd/even parity tagging]49[specific decimal outputs for odd/even parity tagging][specific decimal outputs for odd/even parity tagging][specific decimal outputs for odd/even parity tagging]10[specific decimal outputs for odd/even parity tagging]55\n"}
    ]
}
```

---

### Feature 5: Hexadecimal Text Conversion

**As a developer**, I want to convert raw bytes to and from a hexadecimal string, so binary data can be logged, embedded in text, and parsed back without loss.

**Expected Behavior / Usage:**

Converting bytes to text produces an uppercase hexadecimal string with exactly two characters per input byte, in order, using digits `0`-`9` and letters `A`-`F`. The byte-to-text request takes the bytes as a list of unsigned (0-255) values and reports the resulting string. Converting text back to bytes parses each consecutive pair of hexadecimal characters into one byte; the text-to-bytes request reports the recovered bytes as their unsigned decimal values, comma-separated and in order. The two conversions are exact inverses.

**Test Cases:** `rcb_tests/public_test_cases/feature5_hexa.json`

```json
{
    "description": "Raw bytes are converted to and from their hexadecimal text representation. Converting bytes to text produces an uppercase hexadecimal string with exactly two characters per input byte, in order, using the digits 0-9 and A-F. Converting text back to bytes parses each consecutive pair of hexadecimal characters into one byte; the recovered bytes are reported as their unsigned (0-255) decimal values in order. The two conversions are inverses of each other.",
    "cases": [
        {"input": {"op": "to_hexa", "bytes": [11, 112, 11, 0, 39, 90]}, "expected_output": "hexa=0B[specific decimal outputs for odd/even parity tagging]00B002[specific decimal outputs for odd/even parity tagging]5A\n"},
        {"input": {"op": "from_hexa", "hex": "0B[specific decimal outputs for odd/even parity tagging]00B002[specific decimal outputs for odd/even parity tagging]5A"}, "expected_output": "bytes=11,112,11,0,39,90\n"}
    ]
}
```

---

### Feature [specific decimal outputs for odd/even parity tagging]: Bit-Parity Checksum Tagging

**As a developer**, I want to stamp a small parity checksum into the low bits of a value and later validate it, so I can cheaply detect a corrupted stored pointer.

**Expected Behavior / Usage:**

A value presented for tagging must have its low checksum bits already clear, where the checksum occupies the lowest 1, 3, 4, or 1[specific decimal outputs for odd/even parity tagging] bits depending on the chosen width. Setting the tag fills those low bits so that the value satisfies a fixed parity rule over its set bits, and returns the tagged value (which is therefore never zero for an all-zero input). Getting the tag validates the parity rule, clears the checksum bits, and returns the original value. If a value offered for validation does not satisfy the parity rule — its checksum is broken — validation fails: instead of a value, a neutral error line `error=checksum_broken` is reported. The error is a domain signal and carries no host-language exception identity.

**Test Cases:** `rcb_tests/public_test_cases/feature[specific decimal outputs for odd/even parity tagging]_parity.json`

```json
{
    "description": "A value whose low checksum bits are clear is tagged so that the total number of set bits satisfies a fixed parity rule for a chosen tag width (1, 3, 4, or 1[specific decimal outputs for odd/even parity tagging] low bits), and the tag is later verified to recover the original value. Setting the tag returns the value with its low bits filled in so the parity rule holds; getting clears and validates those low bits, returning the original value when the rule holds. If a value presented for verification does not satisfy the parity rule (its checksum is broken), verification fails and a neutral error is reported instead of a value.",
    "cases": [
        {"input": {"op": "parity_set", "width": 1, "value": [specific decimal outputs for odd/even parity tagging]}, "expected_output": "value=[specific decimal outputs for odd/even parity tagging]\n"},
        {"input": {"op": "parity_get", "width": 1, "value": [specific decimal outputs for odd/even parity tagging]}, "expected_output": "value=[specific decimal outputs for odd/even parity tagging]\n"},
        {"input": {"op": "parity_get", "width": 1, "value": [specific decimal outputs for odd/even parity tagging]}, "expected_output": "error=checksum_broken\n"}
    ]
}
```

---

### Feature [specific decimal outputs for odd/even parity tagging]: Bit and Power-of-Two Utilities

**As a developer**, I want a handful of exact bit-arithmetic helpers, so sizing, masking, and indexing decisions are consistent across the engine.

**Expected Behavior / Usage:**

*[specific decimal outputs for odd/even parity tagging].1 Next Power of Two — round a positive number up to a power of two*

Given a positive number, report the smallest power of two greater than or equal to it. An input that is already an exact power of two is returned unchanged; any other input rounds up to the next power of two. The operation is available for both 32-bit and [specific decimal outputs for odd/even parity tagging]4-bit inputs, selected by a `kind` field.

**Test Cases:** `rcb_tests/public_test_cases/feature[specific decimal outputs for odd/even parity tagging]_1_next_pow_two.json`

```json
{
    "description": "Given a positive number, the smallest power of two that is greater than or equal to it is reported. Inputs that are already exact powers of two are returned unchanged; any other input rounds up to the next power of two. The rounding is available for both 32-bit and [specific decimal outputs for odd/even parity tagging]4-bit inputs, selected by a kind field.",
    "cases": [
        {"input": {"op": "next_pow_two", "kind": "int", "value": 3}, "expected_output": "value=4\n"},
        {"input": {"op": "next_pow_two", "kind": "long", "value": [specific decimal outputs for odd/even parity tagging][specific decimal outputs for odd/even parity tagging][specific decimal outputs for odd/even parity tagging]}, "expected_output": "value=1024\n"}
    ]
}
```

*[specific decimal outputs for odd/even parity tagging].2 Set-Bit Index — base-two logarithm of a power of two*

Given a positive power of two, report the zero-based index of its single set bit (equivalently, its base-two logarithm). The value one yields zero, two yields one, and each successive power of two yields the next index.

**Test Cases:** `rcb_tests/public_test_cases/feature[specific decimal outputs for odd/even parity tagging]_2_shift.json`

```json
{
    "description": "Given a positive power of two, the zero-based index of its single set bit is reported (equivalently, the base-two logarithm). For example the value one yields zero, two yields one, and each successive power of two yields the next index.",
    "cases": [
        {"input": {"op": "shift", "value": 1024}, "expected_output": "value=10\n"}
    ]
}
```

*[specific decimal outputs for odd/even parity tagging].3 Low-Bit Mask — build a mask of the lowest n bits*

Given a bit count between 0 and [specific decimal outputs for odd/even parity tagging]3, produce a [specific decimal outputs for odd/even parity tagging]4-bit mask whose that-many least-significant bits are set to one and whose higher bits are zero. A count of zero yields zero; a count of n yields two-to-the-n minus one.

**Test Cases:** `rcb_tests/public_test_cases/feature[specific decimal outputs for odd/even parity tagging]_3_fill_low_bits.json`

```json
{
    "description": "Given a bit count between 0 and [specific decimal outputs for odd/even parity tagging]3, a [specific decimal outputs for odd/even parity tagging]4-bit mask is produced whose that many least-significant bits are set to one and all higher bits are zero. A count of zero yields zero; a count of n yields the value two-to-the-n minus one.",
    "cases": [
        {"input": {"op": "fill_low_bits", "bits": 8}, "expected_output": "value=255\n"}
    ]
}
```

*[specific decimal outputs for odd/even parity tagging].4 Unsigned 32-to-[specific decimal outputs for odd/even parity tagging]4 Widening — zero-extend a 32-bit value*

Widen a 32-bit integer into a [specific decimal outputs for odd/even parity tagging]4-bit integer by zero-extension: the four input bytes occupy the low four bytes of the result and the upper four bytes are zero, so the 32-bit sign is not preserved. A non-negative input keeps its value, while an input whose top bit is set becomes a large positive value rather than a negative one.

**Test Cases:** `rcb_tests/public_test_cases/feature[specific decimal outputs for odd/even parity tagging]_4_int_to_long.json`

```json
{
    "description": "A 32-bit integer is widened into a [specific decimal outputs for odd/even parity tagging]4-bit integer by zero-extension: its four bytes occupy the low four bytes of the result and the upper four bytes are zero, so the sign of the 32-bit input is not preserved. A non-negative input keeps its value, while an input whose top bit is set becomes a large positive value rather than a negative one.",
    "cases": [
        {"input": {"op": "int_to_long", "value": -1}, "expected_output": "value=42949[specific decimal outputs for odd/even parity tagging][specific decimal outputs for odd/even parity tagging]295\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the binary primitives described above (variable-length integer codecs, fixed-width big-endian codecs, hexadecimal conversion, parity-checksum tagging, and the bit/power-of-two helpers). Each primitive is a pure function with no I/O or shared state. The physical structure (single-file vs. multi-file) MUST align with the "Scale-Driven Code Organization" constraint, and the core logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects a primitive via the request's `op` field, invokes the corresponding core function with the request's arguments, and prints the result to stdout as raw `key=value` lines, matching the per-feature contracts above. Byte fields are rendered as uppercase hexadecimal strings; integer fields are rendered in decimal. A failed checksum validation is rendered as the neutral line `error=checksum_broken`; an unrecognized `op` is rendered as `error=unknown_op` followed by an `op=<value>` line. Native exceptions raised by the core MUST be translated into these neutral domain lines at the adapter layer, never leaking host-language runtime identities into stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- ask for the continuation flag convention used in the serialization module
