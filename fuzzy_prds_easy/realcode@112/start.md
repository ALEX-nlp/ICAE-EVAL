## Product Requirement Document

# Format-String Rendering Engine - A C-style `printf` String Formatter

## Project Goal

Build a small, self-contained string-formatting engine that turns a C-style format string plus a typed argument list into a rendered output string, so developers can produce precisely formatted text (numbers, strings, characters, addresses, floating-point values) without depending on a platform's standard-library `printf` family. The engine implements the classic conversion grammar — flags, field width, precision, length modifiers and conversion specifiers — with deterministic, portable output.

---

## Background & Problem

Without a dedicated engine, developers targeting constrained or freestanding environments are forced either to pull in a heavyweight standard-library formatter or to hand-roll ad-hoc number-to-text conversions for every call site. This leads to inconsistent padding/sign/precision behavior, subtle base-conversion bugs, and non-portable output that differs from one toolchain to the next.

With this engine, a single routine accepts a format string and a sequence of typed arguments and renders the exact result string, honoring the full classic conversion grammar uniformly across platforms.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. The core is a focused formatting engine (format-spec parsing, integer/float-to-text conversion, padding/justification, and an output sink). Keep the conversion logic cleanly separated from the request-decoding/output adapter; do not collapse unrelated responsibilities into a single god file, and do not over-engineer what is fundamentally one cohesive formatter.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box testing contract** for the execution adapter, NOT the internal data model of the engine. The core formatting logic MUST remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for decoding a JSON request, marshaling the typed arguments, invoking the engine, and rendering the stdout contract.

3. **Adherence to SOLID Design Principles:** Separate format-spec parsing, value conversion, justification/padding, and the output sink into distinct logical units. The engine must be open for extension (new conversions/sinks) but closed for modification, with small cohesive interfaces and high-level logic depending on an output-sink abstraction rather than concrete I/O.

4. **Robustness & Interface Design:** The public entry point must be idiomatic for the target language and hide internal complexity. Edge cases (zero values with explicit precision, narrowing length modifiers, negative dynamic width/precision, non-finite floats, empty output) must be handled deterministically.

---

## Execution Contract (request → stdout)

The execution adapter reads ONE JSON request object from stdin:

```json
{ "format": "<format string>", "args": [ { "t": "<type tag>", "v": <number|string> }, ... ] }
```

`format` is a classic format string. `args` lists the values it consumes, in left-to-right order. Each argument carries a **type tag** `t` that fixes the width/category of the value, and (except for write-back destinations) a value `v`:

- `i32` / `u32` — signed / unsigned 32-bit integer.
- `i64` / `u64` — signed / unsigned 64-bit integer (used for `l`, `ll`, `j`, `z`, `t` length modifiers).
- `f64` — double-precision float; `v` may be a number or one of the strings `"inf"`, `"-inf"`, `"nan"`.
- `f80` — extended-precision float (used with the `L` length modifier); `v` as for `f64`.
- `str` — a text string.
- `ptr` — an opaque address, given as a decimal or `0x`-prefixed hex string.
- `wb_int`, `wb_short`, `wb_long`, `wb_char`, `wb_llong`, `wb_intmax`, `wb_size`, `wb_ptrdiff` — a write-back destination of the named width (no `v`).

The adapter prints a language-neutral contract to stdout:

```
[the result line format and escape sequence specifics]<rendered string>
length=<integer return value: the number of characters the conversion produces>
```

In `[the result line format and escape sequence specifics]`, every printable ASCII byte is emitted verbatim; any non-printable byte (and the backslash itself) is shown as a `\xHH` escape so the rendered bytes are always representable. When the format contains one or more write-back conversions, one additional line `[a specific output prefix requiring doc review]<integer>` is printed per destination, in order.

The conversion grammar supported by every feature below is: an optional set of flags (`-` left-justify, `+` force sign, space reserve-sign-blank, `#` alternate form, `0` zero-pad), an optional minimum field width, an optional `.precision`, an optional length modifier (`hh`, `h`, `l`, `ll`, `j`, `z`, `t`, `L`), and a conversion specifier. Width and precision may be given literally or dynamically (see the dynamic-argument feature).

---

## Core Features

### Feature 1: Literal Percent Sign

**As a developer**, I want to emit a literal percent sign by escaping it, so I can include the character that otherwise introduces a conversion.

**Expected Behavior / Usage:**

A doubled percent sign renders as exactly one percent sign and consumes no argument. A single flag character placed between the two percent signs is tolerated and does not change the output. The reported length is the number of characters produced.

**Test Cases:** `rcb_tests/public_test_cases/feature1_percent_literal.json`

```json
{
    "description": "Render a format string in which a percent sign is escaped by doubling it, optionally with a flag character placed between the two percent signs. The engine emits a single literal percent sign and reports the number of characters produced.",
    "cases": [
        {"input": {"format": "%%", "args": []}, "expected_output": "[the result line format and escape sequence specifics]%\nlength=1\n"},
        {"input": {"format": "%-%", "args": []}, "expected_output": "[the result line format and escape sequence specifics]%\nlength=1\n"}
    ]
}
```

---

### Feature 2: Character Conversion

**As a developer**, I want to render a single character from its integer code, so I can place individual bytes into formatted output.

**Expected Behavior / Usage:**

The low byte of the integer argument is emitted verbatim; a code of zero produces no visible character (but still counts as one produced character). A field width pads the single character with leading spaces, or with trailing spaces when the left-justify flag is present. Sign-related flags have no effect on the emitted character. Non-printable bytes appear in `[the result line format and escape sequence specifics]` as `\xHH` escapes.

**Test Cases:** `rcb_tests/public_test_cases/feature2_char.json`

```json
{
    "description": "Render a single character from its integer character code using the char conversion. The low byte of the code is emitted verbatim (a code of zero yields no visible character). Field width pads the single character with spaces on the left, or on the right when the left-justify flag is present; sign-related flags have no effect on the emitted character. The contract reports the rendered byte (non-printable bytes shown as a \\xHH escape) and the produced character count.",
    "cases": [
        {"input": {"format": "%c", "args": [{"t": "i32", "v": 65}]}, "expected_output": "[the result line format and escape sequence specifics]A\nlength=1\n"},
        {"input": {"format": "%+c", "args": [{"t": "i32", "v": 65}]}, "expected_output": "[the result line format and escape sequence specifics]A\nlength=1\n"}
    ]
}
```

---

### Feature 3: String Conversion

**As a developer**, I want to render text strings with optional width and precision, so I can align and truncate text fields.

**Expected Behavior / Usage:**

Each string conversion copies its argument; multiple conversions concatenate in order. A field width right-justifies the string within a minimum number of columns by padding with leading spaces. A precision caps the maximum number of characters copied from the source: a precision larger than the string copies it whole, and a precision of zero emits nothing. Width and precision may combine.

**Test Cases:** `rcb_tests/public_test_cases/feature3_string.json`

```json
{
    "description": "Render text strings using the string conversion. Multiple strings in one format are concatenated in order. A field width right-justifies the string within a minimum number of columns by padding with leading spaces. A precision caps the maximum number of characters copied from the source string; a precision larger than the string copies it whole and a precision of zero emits nothing. Width and precision may combine.",
    "cases": [
        {"input": {"format": "%s", "args": [{"t": "str", "v": "one"}]}, "expected_output": "[the result line format and escape sequence specifics]one\nlength=3\n"},
        {"input": {"format": "%s%s%s", "args": [{"t": "str", "v": "one"}, {"t": "str", "v": "two"}, {"t": "str", "v": "three"}]}, "expected_output": "[the result line format and escape sequence specifics]onetwothree\nlength=11\n"}
    ]
}
```

---

### Feature 4: Unsigned Decimal Integer

**As a developer**, I want to render unsigned integers in base ten with width, precision and length modifiers, so I can format counts and sizes precisely.

**Expected Behavior / Usage:**

The value is rendered in base ten with no sign. Length modifiers select the supplied value's width (default, short, char, long, long-long, and the maximum/size/pointer-difference widths); the short and char modifiers narrow the value before printing. A field width right-justifies with leading spaces, or with leading zeros under the zero flag. A precision sets a minimum digit count; a precision of zero renders the value zero as an empty string. Sign-related flags are ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature4_unsigned_int.json`

```json
{
    "description": "Render an unsigned integer in base ten. Length modifiers select the width of the supplied value (default, short, char, long, long-long, and the maximum/size/pointer-difference widths), with the short and char modifiers narrowing the value before printing. Field width right-justifies with spaces and the zero flag pads with leading zeros; precision sets a minimum digit count, where a precision of zero renders the value zero as an empty string. Sign-related flags are ignored for unsigned values.",
    "cases": [
        {"input": {"format": "%u", "args": [{"t": "u32", "v": 0}]}, "expected_output": "[the result line format and escape sequence specifics]0\nlength=1\n"},
        {"input": {"format": "%u", "args": [{"t": "u32", "v": 4294967295}]}, "expected_output": "[the result line format and escape sequence specifics]4294967295\nlength=10\n"}
    ]
}
```

---

### Feature 5: Signed Decimal Integer

**As a developer**, I want to render signed integers with sign control, width, precision and length modifiers, so I can format positive and negative numbers consistently.

**Expected Behavior / Usage:**

The value is rendered in base ten with a leading minus for negatives. The plus flag forces a sign on non-negative values; the space flag reserves a leading blank for them. Length modifiers select the value width (default, char, long, long-long, and the maximum/size/pointer-difference widths); the char modifier narrows the value first. A field width right-justifies with leading spaces, or with leading zeros (placed after any sign) under the zero flag. A precision sets a minimum digit count; a precision of zero renders the value zero as an empty digit field, though a forced sign still appears. Width and precision combine.

**Test Cases:** `rcb_tests/public_test_cases/feature5_signed_int.json`

```json
{
    "description": "Render a signed integer in base ten. Length modifiers select the value width (default, char, long, long-long, and the maximum/size/pointer-difference widths), with the char modifier narrowing the value first. The plus flag forces a leading sign on non-negative values and the space flag reserves a leading blank for them. Field width right-justifies with spaces or, with the zero flag, with leading zeros placed after any sign. Precision sets a minimum digit count; a precision of zero renders the value zero as an empty digit field (a forced sign still appears). Width and precision combine.",
    "cases": [
        {"input": {"format": "%i", "args": [{"t": "i32", "v": -2147483648}]}, "expected_output": "[the result line format and escape sequence specifics]-2147483648\nlength=11\n"},
        {"input": {"format": "%+i", "args": [{"t": "i32", "v": 1}]}, "expected_output": "[the result line format and escape sequence specifics]+1\nlength=2\n"}
    ]
}
```

---

### Feature 6: Octal Integer

**As a developer**, I want to render unsigned integers in base eight, so I can display values in octal notation.

**Expected Behavior / Usage:**

The value is rendered in base eight. The alternate-form flag forces a leading zero prefix, except that the value zero already renders as a single zero. Length modifiers select and narrow the value width as for unsigned decimal. A field width right-justifies with leading spaces or zeros; a precision sets a minimum digit count, where precision zero renders zero as empty unless the alternate-form flag keeps a single zero. Sign-related flags are ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature6_octal.json`

```json
{
    "description": "Render an unsigned integer in base eight. The alternate-form flag forces a leading zero prefix, except that the value zero already renders as a single zero. Length modifiers select and narrow the value width as for unsigned decimal. Field width right-justifies with spaces or, with the zero flag, leading zeros; precision sets a minimum digit count, where precision zero renders zero as empty unless the alternate-form flag keeps a single zero. Sign-related flags are ignored.",
    "cases": [
        {"input": {"format": "%o", "args": [{"t": "u32", "v": 0}]}, "expected_output": "[the result line format and escape sequence specifics]0\nlength=1\n"},
        {"input": {"format": "%#o", "args": [{"t": "u32", "v": 0}]}, "expected_output": "[the result line format and escape sequence specifics]0\nlength=1\n"}
    ]
}
```

---

### Feature 7: Hexadecimal Integer

**As a developer**, I want to render unsigned integers in base sixteen in either letter case with an optional prefix, so I can display addresses, masks and raw values.

**Expected Behavior / Usage:**

The value is rendered in base sixteen, using lowercase digits for the lowercase conversion and uppercase digits for the uppercase conversion. The alternate-form flag prepends a `0x` (or `0X`) prefix to non-zero values. Length modifiers select and narrow the value width as for unsigned decimal. A field width right-justifies with leading spaces or zeros; a precision sets a minimum digit count, where precision zero renders zero as empty. Sign flags are ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature7_hex.json`

```json
{
    "description": "Render an unsigned integer in base sixteen, using lowercase digits for the lowercase conversion and uppercase digits for the uppercase conversion. The alternate-form flag prepends a 0x (or 0X) prefix to non-zero values. Length modifiers select and narrow the value width as for unsigned decimal. Field width right-justifies with spaces or leading zeros; precision sets a minimum digit count where precision zero renders zero as empty. Sign flags are ignored.",
    "cases": [
        {"input": {"format": "%x", "args": [{"t": "u32", "v": 0}]}, "expected_output": "[the result line format and escape sequence specifics]0\nlength=1\n"},
        {"input": {"format": "%x", "args": [{"t": "u32", "v": 305419896}]}, "expected_output": "[the result line format and escape sequence specifics]12345678\nlength=8\n"}
    ]
}
```

---

### Feature 8: Pointer/Address Conversion

**As a developer**, I want to render an opaque address value, so I can display memory locations in a canonical notation.

**Expected Behavior / Usage:**

The pointer conversion renders the address in the engine's canonical pointer notation (a `0x`-prefixed hexadecimal form). A field width right-justifies the rendered address within a minimum number of columns by padding with leading spaces.

**Test Cases:** `rcb_tests/public_test_cases/feature8_pointer.json`

```json
{
    "description": "Render an opaque address value using the pointer conversion. The address is formatted in the engine's canonical pointer notation. A field width right-justifies the rendered address within a minimum number of columns by padding with leading spaces.",
    "cases": [
        {"input": {"format": "%p", "args": [{"t": "ptr", "v": "0x12345678"}]}, "expected_output": "[the result line format and escape sequence specifics]0x12345678\nlength=10\n"}
    ]
}
```

---

### Feature 9: Dynamic Width and Precision

**As a developer**, I want to supply field width and/or precision as runtime arguments, so I can compute alignment dynamically.

**Expected Behavior / Usage:**

When the width and/or precision are given as `*` in the format, their values are taken from integer arguments that precede the value being formatted, consumed in left-to-right order. A negative dynamic width means left-justify within the absolute width; a negative dynamic precision is ignored (treated as absent).

**Test Cases:** `rcb_tests/public_test_cases/feature9_star_args.json`

```json
{
    "description": "Supply field width and/or precision dynamically as integer arguments rather than as literal digits in the format string, consumed in order before the value being formatted. A negative dynamic width means left-justify within the absolute width; a negative dynamic precision is ignored. Each dynamic value argument is read in left-to-right order.",
    "cases": [
        {"input": {"format": "%*c", "args": [{"t": "i32", "v": 10}, {"t": "i32", "v": 90}]}, "expected_output": "[the result line format and escape sequence specifics]         Z\nlength=10\n"},
        {"input": {"format": "%*u", "args": [{"t": "i32", "v": -6}, {"t": "u32", "v": 5}]}, "expected_output": "[the result line format and escape sequence specifics]5     \nlength=6\n"}
    ]
}
```

---

### Feature 10: Fixed-Decimal Floating Point

**As a developer**, I want to render floating-point values in fixed-decimal notation with precision, sign and padding control, so I can format measurements and ratios.

**Expected Behavior / Usage:**

The value is rendered in fixed-decimal notation. The default precision is six fractional digits; an explicit precision sets the number of fractional digits, and a precision of zero drops the fractional part (the alternate-form flag then keeps a trailing decimal point). Positive and negative infinity render as the word "infinity" abbreviated (lowercase for the lowercase conversion, uppercase for the uppercase conversion). The plus and space flags control the leading sign of non-negative values; a field width right-justifies with leading spaces or, under the zero flag, leading zeros placed after the sign. An extended-precision length modifier is accepted on the value.

**Test Cases:** `rcb_tests/public_test_cases/feature10_float.json`

```json
{
    "description": "Render a floating-point value in fixed-decimal notation. The default precision is six fractional digits; an explicit precision sets the number of fractional digits, and a precision of zero drops the fractional part (the alternate-form flag then keeps a trailing decimal point). Positive and negative infinity render as the word infinity (lowercase for the lowercase conversion, uppercase for the uppercase conversion). The plus and space flags control the leading sign of non-negative values; field width right-justifies with spaces or, with the zero flag, leading zeros placed after the sign. An extended-precision length modifier is accepted.",
    "cases": [
        {"input": {"format": "%f", "args": [{"t": "f64", "v": "inf"}]}, "expected_output": "[the result line format and escape sequence specifics]inf\nlength=3\n"},
        {"input": {"format": "%f", "args": [{"t": "f64", "v": 0.0}]}, "expected_output": "[the result line format and escape sequence specifics]0.000000\nlength=8\n"}
    ]
}
```

---

### Feature 11: Not-a-Number Floating Point

**As a developer**, I want not-a-number values to render as a recognizable word, so I can display the result of undefined floating-point operations.

**Expected Behavior / Usage:**

A not-a-number value renders as the not-a-number word: lowercase for the lowercase float conversion and uppercase for the uppercase conversion. An implementation-chosen sign character may precede the word.

**Test Cases:** `rcb_tests/public_test_cases/feature11_float_nan.json`

```json
{
    "description": "Render a not-a-number floating-point value. The lowercase conversion emits the lowercase not-a-number word and the uppercase conversion emits the uppercase form; an implementation-chosen sign character may precede it.",
    "cases": [
        {"input": {"format": "%f", "args": [{"t": "f64", "v": "nan"}]}, "expected_output": "[the result line format and escape sequence specifics]nan\nlength=3\n"}
    ]
}
```

---

### Feature 12: Character-Count Write-Back

**As a developer**, I want a conversion that reports how many characters have been produced so far, so I can measure output length in place.

**Expected Behavior / Usage:**

The write-back conversion emits no characters; instead it stores the number of characters produced so far into a caller-supplied destination. The destination's width is selected by the length modifier (default, short, char, long, long-long, and the maximum/size/pointer-difference widths). The stored count is reported on a `[a specific output prefix requiring doc review]` line, alongside the rendered text and its length.

**Test Cases:** `rcb_tests/public_test_cases/feature12_writeback.json`

```json
{
    "description": "Process a write-back conversion that emits no characters but stores, into a caller-supplied destination, the number of characters produced so far. The destination width is chosen by the length modifier (default, short, char, long, long-long, and the maximum/size/pointer-difference widths). The contract reports the rendered text, its length, and the stored count.",
    "cases": [
        {"input": {"format": "%n", "args": [{"t": "wb_int"}]}, "expected_output": "[the result line format and escape sequence specifics]\nlength=0\n[a specific output prefix requiring doc review]0\n"},
        {"input": {"format": "%s%n", "args": [{"t": "str", "v": "abcd"}, {"t": "wb_int"}]}, "expected_output": "[the result line format and escape sequence specifics]abcd\nlength=4\n[a specific output prefix requiring doc review]4\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured formatting engine implementing the conversion grammar and all conversions described above, with format-spec parsing, value-to-text conversion, justification/padding, and an output sink kept as distinct, decoupled units.

2. **The Execution/Test Adapter:** A runnable program that reads ONE JSON request from stdin, marshals the typed argument list, invokes the engine, and prints the `[the result line format and escape sequence specifics]` / `length=` / `[a specific output prefix requiring doc review]` contract to stdout, strictly matching the per-feature contracts above. This adapter must be logically and physically separated from the core engine.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`) to choose the directory. For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{case_index:03d}.txt` containing **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- default hex case behavior
