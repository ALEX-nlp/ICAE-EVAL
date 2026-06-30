## Product Requirement Document

# QR Matrix Encoder - Bitstream and Matrix Rendering Contracts

## Project Goal

Build a QR matrix generation library that allows developers to encode text, byte arrays, and digit-only numeric payloads into deterministic QR-compatible bit streams and module matrices without manually implementing packing, mode encoding, masking, sizing, and error-correction matrix layout rules.

---

## Background & Problem

Without this library, developers are forced to hand-pack bits, split numeric strings into QR-sized digit groups, convert raw bytes into binary streams, choose matrix sizes, apply masks, and verify the final black/white module grid themselves. This leads to fragile encoding code, off-by-one errors, inconsistent mask handling, and outputs that are hard to compare across implementations.

With this library, developers provide simple payload data and explicit encoding options, and the system returns observable bit streams or QR module matrices in a stable textual form that can be used by rendering layers, file exporters, or automated tests.

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

### Feature 1: Bit Stream Packing

**As a developer**, I want to append fixed-width integer values into a binary stream, so I can build QR payload segments with exact bit ordering.

**Expected Behavior / Usage:**

The input is an object with `action` set to `pack_bits` and `values` as an ordered array of objects containing `number` and `width`. Each number is written most-significant bit first using exactly the requested width. Only the low bits visible through that width are emitted, so values wider than the requested width are truncated by the fixed-width write. The output reports the total bit length, the full bit string, and the resulting packed byte values in order. If the final byte is partial, its remaining low-order positions are zero.

**Test Cases:** `rcb_tests/public_test_cases/feature1_bit_stream_packing.json`

```json
{
    "description": "Pack integers into a most-significant-bit-first bit stream and expose both the bit sequence and completed byte values.",
    "cases": [
        {
            "input": {
                "action": "pack_bits",
                "values": [
                    {
                        "number": 1,
                        "width": 8
                    }
                ]
            },
            "expected_output": "length=8\nbits=00000001\nbytes=1\n"
        },
        {
            "input": {
                "action": "pack_bits",
                "values": [
                    {
                        "number": 256,
                        "width": 9
                    }
                ]
            },
            "expected_output": "length=9\nbits=100000000\nbytes=128,0\n"
        }
    ]
}
```

---

### Feature 2: Byte Mode Encoding

**As a developer**, I want to encode raw bytes without changing their order or values, so I can place arbitrary binary data into a QR payload.

**Expected Behavior / Usage:**

The input is an object with `action` set to `encode_bytes` and `bytes` as an array of integer byte values. The encoder reports byte mode, the number of bytes supplied, the emitted bit string with each byte written most-significant bit first, and the reconstructed byte values from the produced bit stream. The byte list in the output must exactly match the input sequence.

**Test Cases:** `rcb_tests/public_test_cases/feature2_byte_mode_encoding.json`

```json
{
    "description": "Encode a byte array in byte mode, preserving byte length and each input byte in order in the produced bit stream.",
    "cases": [
        {
            "input": {
                "action": "encode_bytes",
                "bytes": [
                    0,
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    10,
                    11,
                    12,
                    13,
                    14,
                    15,
                    16,
                    17,
                    18,
                    19,
                    20,
                    21,
                    22,
                    23,
                    24,
                    25,
                    26,
                    27,
                    28,
                    29,
                    30,
                    31,
                    32,
                    33,
                    34,
                    35,
                    36,
                    37,
                    38,
                    39,
                    40,
                    41,
                    42,
                    43,
                    44,
                    45,
                    46,
                    47,
                    48,
                    49,
                    50,
                    51,
                    52,
                    53,
                    54,
                    55,
                    56,
                    57,
                    58,
                    59,
                    60,
                    61,
                    62,
                    63,
                    64,
                    65,
                    66,
                    67,
                    68,
                    69,
                    70,
                    71,
                    72,
                    73,
                    74,
                    75,
                    76,
                    77,
                    78,
                    79,
                    80,
                    81,
                    82,
                    83,
                    84,
                    85,
                    86,
                    87,
                    88,
                    89,
                    90,
                    91,
                    92,
                    93,
                    94,
                    95,
                    96,
                    97,
                    98,
                    99,
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                    115,
                    116,
                    117,
                    118,
                    119,
                    120,
                    121,
                    122,
                    123,
                    124,
                    125,
                    126,
                    127,
                    128,
                    129,
                    130,
                    131,
                    132,
                    133,
                    134,
                    135,
                    136,
                    137,
                    138,
                    139,
                    140,
                    141,
                    142,
                    143,
                    144,
                    145,
                    146,
                    147,
                    148,
                    149,
                    150,
                    151,
                    152,
                    153,
                    154,
                    155,
                    156,
                    157,
                    158,
                    159,
                    160,
                    161,
                    162,
                    163,
                    164,
                    165,
                    166,
                    167,
                    168,
                    169,
                    170,
                    171,
                    172,
                    173,
                    174,
                    175,
                    176,
                    177,
                    178,
                    179,
                    180,
                    181,
                    182,
                    183,
                    184,
                    185,
                    186,
                    187,
                    188,
                    189,
                    190,
                    191,
                    192,
                    193,
                    194,
                    195,
                    196,
                    197,
                    198,
                    199,
                    200,
                    201,
                    202,
                    203,
                    204,
                    205,
                    206,
                    207,
                    208,
                    209,
                    210,
                    211,
                    212,
                    213,
                    214,
                    215,
                    216,
                    217,
                    218,
                    219,
                    220,
                    221,
                    222,
                    223,
                    224,
                    225,
                    226,
                    227,
                    228,
                    229,
                    230,
                    231,
                    232,
                    233,
                    234,
                    235,
                    236,
                    237,
                    238,
                    239,
                    240,
                    241,
                    242,
                    243,
                    244,
                    245,
                    246,
                    247,
                    248,
                    249,
                    250,
                    251,
                    252,
                    253,
                    254,
                    255
                ]
            },
            "expected_output": "mode=byte\nlength=256\nbits=00000000000000010000001000000011000001000000010100000110000001110000100000001001000010100000101100001100000011010000111000001111000100000001000100010010000100110001010000010101000101100001011100011000000110010001101000011011000111000001110100011110000111110010000000100001001000100010001100100100001001010010011000100111001010000010100100101010001010110010110000101101001011100010111100110000001100010011001000110011001101000011010100110110001101110011100000111001001110100011101100111100001111010011111000111111010000000100000101000010010000110100010001000101010001100100011101001000010010010100101001001011010011000100110101001110010011110101000001010001010100100101001101010100010101010101011001010111010110000101100101011010010110110101110001011101010111100101111101100000011000010110001001100011011001000110010101100110011001110110100001101001011010100110101101101100011011010110111001101111011100000111000101110010011100110111010001110101011101100111011101111000011110010111101001111011011111000111110101111110011111111000000010000001100000101000001110000100100001011000011010000111100010001000100110001010100010111000110010001101100011101000111110010000100100011001001010010011100101001001010110010110100101111001100010011001100110101001101110011100100111011001111010011111101000001010000110100010101000111010010010100101101001101010011110101000101010011010101010101011101011001010110110101110101011111011000010110001101100101011001110110100101101011011011010110111101110001011100110111010101110111011110010111101101111101011111111000000110000011100001011000011110001001100010111000110110001111100100011001001110010101100101111001100110011011100111011001111110100001101000111010010110100111101010011010101110101101101011111011000110110011101101011011011110111001101110111011110110111111110000011100001111000101110001111100100111001011110011011100111111010001110100111101010111010111110110011101101111011101110111111110000111100011111001011110011111101001111010111110110111101111111100011111001111110101111101111111100111111011111111011111111\nbytes=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,198,199,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228,229,230,231,232,233,234,235,236,237,238,239,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255\n"
        }
    ]
}
```

---

### Feature 3: Numeric Mode Encoding

**As a developer**, I want to encode digit-only text compactly and reject non-digit text, so I can use QR numeric mode safely.

**Expected Behavior / Usage:**

*3.1 Numeric Group Encoding — Encode digit strings into compact numeric groups.*

The input is an object with `action` set to `encode_numeric` and `digits` as a string containing only characters `0` through `9`. The output reports numeric mode, the original digit count, the total encoded bit length, the exact emitted bit string, and the decoded numeric segment values. Digits are processed left to right in groups of three digits using 10 bits per full group; a trailing two-digit group uses 7 bits; a trailing one-digit group uses 4 bits.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_numeric_mode_encoding.json`

```json
{
    "description": "Encode digit-only text in numeric mode using QR numeric grouping rules and report the emitted bit stream and decoded segment values.",
    "cases": [
        {
            "input": {
                "action": "encode_numeric",
                "digits": "1234567890"
            },
            "expected_output": "mode=numeric\nlength=10\nencoded_bit_length=34\nbits=0001111011011100100011000101010000\nsegments=123,456,789,0\n"
        },
        {
            "input": {
                "action": "encode_numeric",
                "digits": "5"
            },
            "expected_output": "mode=numeric\nlength=1\nencoded_bit_length=4\nbits=0101\nsegments=5\n"
        }
    ]
}
```

*3.2 Numeric Input Validation — Reject non-digit numeric-mode input.*

The input is an object with `action` set to `encode_numeric` and `digits` containing at least one character outside `0` through `9`. The output must be the normalized domain error `[a specific error category requiring validation against invalid characters]` and must not expose any host-language exception type or runtime-specific message.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_numeric_mode_validation.json`

```json
{
    "description": "Reject text that contains non-digit characters when numeric-mode encoding is requested.",
    "cases": [
        {
            "input": {
                "action": "encode_numeric",
                "digits": "hello"
            },
            "expected_output": "[a specific error category requiring validation against invalid characters]\n"
        }
    ]
}
```

---

### Feature 4: QR Matrix Rendering

**As a developer**, I want to render complete QR module matrices from text or bytes with controlled sizing, error correction, and masking, so I can produce deterministic black/white grids for downstream renderers.

**Expected Behavior / Usage:**

*4.1 Fixed-Version Text Matrix Rendering — Render text with an explicit version and error-correction level.*

The input is an object with `action` set to `render_text_matrix`, `text` as the payload, `version` as the requested QR version, and `error_correction` as one of `low`, `medium`, `quality`, or `high`. The output reports the version used, the square matrix size, and a `matrix=` section containing one line per row. Each row is a string of `1` and `0`, where `1` represents a dark module and `0` represents a light module.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_fixed_version_text_matrix.json`

```json
{
    "description": "Render QR matrices for a supplied text payload, explicit version, and explicit error-correction level.",
    "cases": [
        {
            "input": {
                "action": "render_text_matrix",
                "text": "shanna!",
                "version": 1,
                "error_correction": "low"
            },
            "expected_output": "version=1\nsize=21\nmatrix=\n111111100101101111111\n100000100111001000001\n101110101101101011101\n101110100101001011101\n101110100010101011101\n100000100000101000001\n111111101010101111111\n000000001101100000000\n111011111111011000100\n001110001010001101111\n101101110000100010111\n100110000110001000001\n101100111110101010001\n000000001011010111001\n111111101111011011111\n100000101101110000001\n101110101001011010011\n101110100010001110110\n101110101100100110001\n100000101100001110010\n111111101000101100011\n"
        }
    ]
}
```

*4.2 Automatic-Version Text Matrix Rendering — Choose the smallest fitting version for text.*

The input is an object with `action` set to `render_text_matrix`, `text` as the payload, and `error_correction` as one of the supported levels, with no explicit `version`. The encoder chooses the smallest version that can contain the payload at the requested error-correction level, then emits the same version, size, and row-by-row matrix format used for fixed-version rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_auto_version_text_matrix.json`

```json
{
    "description": "Choose the smallest fitting QR version for a text payload and render its matrix at the requested error-correction level.",
    "cases": [
        {
            "input": {
                "action": "render_text_matrix",
                "text": "shanna!",
                "error_correction": "low"
            },
            "expected_output": "version=1\nsize=21\nmatrix=\n111111100101101111111\n100000100111001000001\n101110101101101011101\n101110100101001011101\n101110100010101011101\n100000100000101000001\n111111101010101111111\n000000001101100000000\n111011111111011000100\n001110001010001101111\n101101110000100010111\n100110000110001000001\n101100111110101010001\n000000001011010111001\n111111101111011011111\n100000101101110000001\n101110101001011010011\n101110100010001110110\n101110101100100110001\n100000101100001110010\n111111101000101100011\n"
        }
    ]
}
```

*4.3 Automatic-Version Byte Matrix Rendering — Choose the smallest fitting version for raw bytes.*

The input is an object with `action` set to `render_byte_matrix`, `bytes` as an ordered array of byte values, and `error_correction` as one of the supported levels. The encoder chooses the smallest version that can contain those bytes and emits the version, size, and row-by-row matrix. A byte payload that represents the same UTF-8 bytes as a text payload must render to the same matrix when the other options are the same.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_auto_version_byte_matrix.json`

```json
{
    "description": "Choose the smallest fitting QR version for raw bytes and render the same matrix that the equivalent byte payload would produce.",
    "cases": [
        {
            "input": {
                "action": "render_byte_matrix",
                "bytes": [
                    115,
                    104,
                    97,
                    110,
                    110,
                    97,
                    33
                ],
                "error_correction": "low"
            },
            "expected_output": "version=1\nsize=21\nmatrix=\n111111100101101111111\n100000100111001000001\n101110101101101011101\n101110100101001011101\n101110100010101011101\n100000100000101000001\n111111101010101111111\n000000001101100000000\n111011111111011000100\n001110001010001101111\n101101110000100010111\n100110000110001000001\n101100111110101010001\n000000001011010111001\n111111101111011011111\n100000101101110000001\n101110101001011010011\n101110100010001110110\n101110101100100110001\n100000101100001110010\n111111101000101100011\n"
        }
    ]
}
```

*4.4 Masked Matrix Rendering — Render a matrix with a caller-selected mask pattern.*

The input is an object with `action` set to `render_text_matrix`, `text`, explicit `version`, `error_correction`, and `mask`. Valid mask values are integers from 0 through 7 inclusive. The selected mask must affect the final module matrix, and the output uses the same version, size, and row-by-row matrix format as other matrix rendering features.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_masked_matrix_rendering.json`

```json
{
    "description": "Render a version-1 low-error-correction QR matrix with a caller-selected mask pattern.",
    "cases": [
        {
            "input": {
                "action": "render_text_matrix",
                "text": "shanna!",
                "version": 1,
                "error_correction": "low",
                "mask": 0
            },
            "expected_output": "version=1\nsize=21\nmatrix=\n111111100101101111111\n100000100111001000001\n101110101101101011101\n101110100101001011101\n101110100010101011101\n100000100000101000001\n111111101010101111111\n000000001101100000000\n111011111111011000100\n001110001010001101111\n101101110000100010111\n100110000110001000001\n101100111110101010001\n000000001011010111001\n111111101111011011111\n100000101101110000001\n101110101001011010011\n101110100010001110110\n101110101100100110001\n100000101100001110010\n111111101000101100011\n"
        },
        {
            "input": {
                "action": "render_text_matrix",
                "text": "shanna!",
                "version": 1,
                "error_correction": "low",
                "mask": 7
            },
            "expected_output": "version=1\nsize=21\nmatrix=\n111111100101101111111\n100000101101001000001\n101110101100101011101\n101110100101001011101\n101110101000101011101\n100000101001101000001\n111111101010101111111\n000000001111100000000\n110100110110001110110\n001110001010001101111\n111111100010110000101\n101111001111000001000\n101100111110101010001\n000000001001000101011\n111111101110010010110\n100000100101110000001\n101110100011001000001\n101110101011000111111\n101110100100100110001\n100000101110011100000\n111111101001100101010\n"
        }
    ]
}
```

*4.5 Mask Pattern Validation — Reject mask values outside the supported range.*

The input is an object with `action` set to `render_text_matrix` and a `mask` value lower than 0 or higher than 7. The output must be the normalized domain error `error=invalid_mask_pattern` and must not expose any host-language assertion type, exception class, stack trace, or runtime-specific message.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_mask_validation.json`

```json
{
    "description": "Reject caller-selected mask patterns outside the inclusive range 0 through 7.",
    "cases": [
        {
            "input": {
                "action": "render_text_matrix",
                "text": "shanna!",
                "version": 1,
                "error_correction": "low",
                "mask": -1
            },
            "expected_output": "error=invalid_mask_pattern\n"
        },
        {
            "input": {
                "action": "render_text_matrix",
                "text": "shanna!",
                "version": 1,
                "error_correction": "low",
                "mask": 8
            },
            "expected_output": "error=invalid_mask_pattern\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_bit_stream_packing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_bit_stream_packing@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same ordering convention as the BitStreamConst enum
- utilize the legacy QR verification utility as fallback
