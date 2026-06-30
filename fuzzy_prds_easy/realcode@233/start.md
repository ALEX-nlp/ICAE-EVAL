## Product Requirement Document

# Binary Parsing Contract Adapter - Declarative Binary Input Reader

## Project Goal

Build a binary parsing library and execution adapter that allows developers to describe structured reads from byte streams and receive parsed values, selected variants, decoded strings, pointer-resolved data, and normalized parse errors without writing repetitive stream-position and conversion boilerplate.

---

## Background & Problem

Without this library/tool, developers are forced to manually read bytes, track cursor positions, validate signatures, branch over variant layouts, resolve offsets, decode null-terminated strings, and convert raw values. This leads to repetitive code, fragile error handling, missed rewinds, and maintenance issues when binary formats evolve.

With this library/tool, developers express the intended binary contract declaratively and use a small execution adapter to translate JSON test commands into idiomatic parsing calls whose stdout is a stable black-box contract.

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

### Feature 1: Declarative Value Assertions

**As a developer**, I want to validate binary data against declared conditions, so I can reject malformed input with useful domain-level parse errors.

**Expected Behavior / Usage:**

A record may declare conditions that must hold after reading fields. The adapter receives a JSON object with a `feature` selector and hexadecimal byte input, parses the corresponding binary record, and prints either `[a specific status code and response variable — ask the PM for the exact pair]` with parsed field values or a normalized `error=assertion_failed` / `error=custom_failure` block with byte position and domain message. Custom assertion payloads are exposed as separate fields rather than host-language exception text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_assertions.json`

```json
{
    "description": "Parses a one-byte record that must satisfy a declared value condition, reporting success values or normalized assertion/custom failure details.",
    "cases": [
        {
            "input": {
                "feature": "assertion_check",
                "bytes": "01"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\n[a specific status code and response variable — ask the PM for the exact pair]\n"
        },
        {
            "input": {
                "feature": "assertion_check",
                "bytes": "00"
            },
            "expected_output": "error=assertion_failed\npos=0\nmessage=a == 1\n"
        }
    ]
}
```

---

### Feature 2: Literal Markers and Field Padding

**As a developer**, I want to require marker bytes and skip structural padding, so I can recognize binary formats with fixed signatures and reserved bytes.

**Expected Behavior / Usage:**

A record may require literal marker bytes at the start or between fields. Matching markers produce parsed field output; mismatches produce `error=bad_magic` with the failing byte position. Fields may also declare padding before or after values, and skipped padding bytes must not appear as parsed values.

**Test Cases:** `rcb_tests/public_test_cases/feature2_magic_and_padding.json`

```json
{
    "description": "Validates literal marker bytes around binary records and applies declared byte padding before and after fields while exposing parsed field values or marker errors.",
    "cases": [
        {
            "input": {
                "feature": "magic_constant",
                "bytes": "61"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\n"
        },
        {
            "input": {
                "feature": "magic_constant",
                "bytes": "78"
            },
            "expected_output": "error=bad_magic\npos=0\n"
        }
    ]
}
```

---

### Feature 3: Derived Field Controls

**As a developer**, I want to derive output fields from length prefixes, conditions, defaults, and byte order, so I can express compact binary layouts without manual bookkeeping.

**Expected Behavior / Usage:**

A parser may use earlier bytes or caller-supplied parameters to control later reads. Length prefixes can determine vector sizes without becoming output fields, conditional fields may either read from the stream or use a supplied fallback value, defaulted or ignored fields use their default values without consuming extra data, and individual fields may override byte order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_derived_field_controls.json`

```json
{
    "description": "Reads records whose output fields are controlled by length prefixes, temporary values, caller-supplied booleans, defaults, and per-field byte order.",
    "cases": [
        {
            "input": {
                "feature": "temporary_length",
                "bytes": "000000054142434445"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\nvalues=65,66,67,68,69\n"
        },
        {
            "input": {
                "feature": "conditional_default",
                "bytes": "01",
                "try_read": true
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\n[a specific status code and response variable — ask the PM for the exact pair]\n"
        }
    ]
}
```

---

### Feature 4: Optional Reads and Pointer Resolution

**As a developer**, I want to recover from failed optional reads and resolve pointer-based values, so I can parse sparse or offset-based binary records safely.

**Expected Behavior / Usage:**

A fallible field read may return no value instead of failing the entire record, while successful reads return the parsed values. Pointer fields read an offset, later resolve the value at that offset, and restore the surrounding stream so following fields are parsed correctly. Pointer resolution must also occur when the pointer field is wrapped in a fallible optional read.

**Test Cases:** `rcb_tests/public_test_cases/feature4_optional_and_pointer_reads.json`

```json
{
    "description": "Parses fallible optional binary fields and pointer-based fields, preserving stream recovery semantics and resolving pointed-to values after parsing.",
    "cases": [
        {
            "input": {
                "feature": "fallible_optional_read",
                "bytes": "00000000"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\nvalue=none\n"
        },
        {
            "input": {
                "feature": "fallible_optional_read",
                "bytes": "ffffffff00000000"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\nvalue=-1,0\n"
        }
    ]
}
```

---

### Feature 5: Mapping and Fallible Conversion

**As a developer**, I want to transform raw binary values during parsing, so I can return application-ready values and normalized conversion failures.

**Expected Behavior / Usage:**

Raw bytes may be mapped into different output values through caller-aware closures, reusable mapping expressions, or whole-record constructors. Fallible mappings return parsed values on success and `error=custom_failure` with byte position and neutral conversion message on failure.

**Test Cases:** `rcb_tests/public_test_cases/feature5_mapping_transforms.json`

```json
{
    "description": "Transforms raw binary values through mapping and fallible conversion steps, returning transformed values or normalized conversion failures.",
    "cases": [
        {
            "input": {
                "feature": "map_transform",
                "bytes": "01",
                "mode": "closure",
                "extra": 5
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\na=6\n"
        },
        {
            "input": {
                "feature": "map_transform",
                "bytes": "01",
                "mode": "expr"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\na=2\n"
        }
    ]
}
```

---

### Feature 6: Binary Variant Selection

**As a developer**, I want to select variants from markers, numeric representations, byte order, and preconditions, so I can model tagged binary choices precisely.

**Expected Behavior / Usage:**

Variant parsing chooses the first record shape whose markers and preconditions match the input. Variants may carry parsed payload fields, use variant-specific byte order, match literal byte markers, match numeric discriminants, or skip variants when preconditions fail. If no variant matches, output is a normalized no-match or per-variant error report.

**Test Cases:** `rcb_tests/public_test_cases/feature6_enum_selection.json`

```json
{
    "description": "Selects binary enum variants using markers, numeric representations, endianness overrides, and preconditions, returning variant data or normalized no-match errors.",
    "cases": [
        {
            "input": {
                "feature": "enum_mixed",
                "bytes": "00"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\nvariant=Zero\n"
        },
        {
            "input": {
                "feature": "enum_mixed",
                "bytes": "0200030004"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\nvariant=Two\na=3\nb=4\n"
        }
    ]
}
```

---

### Feature 7: Variant Error Reporting Modes

**As a developer**, I want to control how variant-selection failures are surfaced, so I can choose between diagnostic detail and compact no-match errors.

**Expected Behavior / Usage:**

When all variants fail, one mode returns every variant failure with variant names and normalized nested errors; another mode collapses unexpected variant failures into `error=no_variant_match`. The mode affects only error rendering, not successful variant parsing.

**Test Cases:** `rcb_tests/public_test_cases/feature7_enum_error_modes.json`

```json
{
    "description": "Controls how variant-selection failures are surfaced, either preserving per-variant failure details or collapsing unexpected failures into a single no-match category.",
    "cases": [
        {
            "input": {
                "feature": "enum_error_mode",
                "bytes": "0001",
                "mode": "all"
            },
            "expected_output": "error=variant_errors\npos=0\nvariant_error_count=2\nvariant=One\nerror=bad_magic\npos=0\nvariant=Two\nerror=unexpected_eof\n"
        },
        {
            "input": {
                "feature": "enum_error_mode",
                "bytes": "0001",
                "mode": "unexpected"
            },
            "expected_output": "error=no_variant_match\npos=0\n"
        }
    ]
}
```

---

### Feature 8: Null-Terminated String Parsing

**As a developer**, I want to decode null-terminated byte and wide strings, so I can read text from binary streams without manual terminator scanning.

**Expected Behavior / Usage:**

A byte string parser reads bytes until a null terminator and can be called repeatedly on the same stream. A wide-string parser reads two-byte code units until a null code unit and applies the requested byte order before returning decoded text.

**Test Cases:** `rcb_tests/public_test_cases/feature8_string_parsing.json`

```json
{
    "description": "Reads null-terminated byte strings and null-terminated wide strings, using the requested byte order for wide characters and returning decoded text values.",
    "cases": [
        {
            "input": {
                "feature": "null_strings",
                "bytes": "6e756c6c207465726d696e6174656420737472696e67733f20696e206d792073797374656d2773206c616e67756167653f006e6f207468616e6b7300"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\nfirst=null terminated strings? in my system's language?\nsecond=no thanks\n"
        },
        {
            "input": {
                "feature": "null_strings",
                "bytes": "7700690064006500200073007400720069006e00670073000000",
                "endian": "wide_little"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\nvalue=wide strings\n"
        }
    ]
}
```

---

### Feature 9: Punctuated Counted Sequences

**As a developer**, I want to read counted lists separated by marker records, so I can parse delimiter-based binary lists while retaining list shape.

**Expected Behavior / Usage:**

A counted sequence reads the requested number of items and consumes separator records between items. In trailing mode, a separator is also required after the final item. Output includes the declared count, parsed item count, debug-form item values, and separator count.

**Test Cases:** `rcb_tests/public_test_cases/feature9_punctuated_sequences.json`

```json
{
    "description": "Reads counted sequences whose elements are separated by marker records, optionally requiring a trailing separator, and exposes item and separator counts.",
    "cases": [
        {
            "input": {
                "feature": "punctuated",
                "bytes": "030102010201",
                "mode": "separated"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\ncount=3\nlen=3\nvalues=[One, One, One]\nseparators=2\n"
        },
        {
            "input": {
                "feature": "punctuated",
                "bytes": "03010201020102",
                "mode": "trailing"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\ncount=3\nlen=3\nvalues=[One, One, One]\nseparators=3\n"
        }
    ]
}
```

---

### Feature 10: Position Tracking and Cursor Reads

**As a developer**, I want to track byte positions and expose cursor-compatible reads, so I can reason about where values came from in a binary stream.

**Expected Behavior / Usage:**

A parsed value can carry the byte position at which it was read while still behaving like the underlying value for mutation and cloning. The cursor interface supports seeking, setting positions, and reading into fixed-size buffers, returning the number of bytes read, buffer contents, and resulting positions.

**Test Cases:** `rcb_tests/public_test_cases/feature10_position_and_cursor.json`

```json
{
    "description": "Exposes reader position tracking for parsed values and cursor-style seeking, position setting, and buffered reads over byte input.",
    "cases": [
        {
            "input": {
                "feature": "pos_value",
                "bytes": "fffefd"
            },
            "expected_output": "[a specific status code and response variable — ask the PM for the exact pair]\na=65534\ntracked_pos=2\ninitial_value=253\nmutated_value=1\nclone_value=1\nclone_pos=2\n"
        },
        {
            "input": {
                "feature": "cursor",
                "bytes": "0102030405",
                "start_position": 0,
                "set_position": 0,
                "read_lengths": [
                    4,
                    4
                ]
            },
            "expected_output": "initial_pos=0\nstart_seek=0\nafter_set=0\nread0_len=4\nread0_bytes=1,2,3,4\nread0_pos=4\nread1_len=1\nread1_bytes=5,0,0,0\nread1_pos=5\n"
        }
    ]
}
```

---

### Feature 11: Byte-Order Names and Zero-Field Gates

**As a developer**, I want to render canonical byte-order names and evaluate payload-free preconditions, so I can support metadata and gated record recognition.

**Expected Behavior / Usage:**

Byte-order values render to canonical names. A zero-field record may be accepted or rejected solely from a caller-supplied precondition; success prints `[a specific status code and response variable — ask the PM for the exact pair]`, while rejection prints a normalized assertion failure at position zero.

**Test Cases:** `rcb_tests/public_test_cases/feature11_names_and_gates.json`

```json
{
    "description": "Returns canonical byte-order names and evaluates zero-field record preconditions without reading payload bytes.",
    "cases": [
        {
            "input": {
                "feature": "endian_name",
                "endian": "big"
            },
            "expected_output": "name=Big\n"
        },
        {
            "input": {
                "feature": "endian_name",
                "endian": "little"
            },
            "expected_output": "name=Little\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_assertions.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_assertions@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
