## Product Requirement Document

# Native Function Binding Layer — Exposing Compiled Functions to a Dynamic Runtime

## Project Goal

Build a binding layer that exposes statically-typed native (compiled) functions to a dynamic scripting runtime, so developers can call high-performance native code as if it were ordinary dynamic-language functions — with familiar calling conventions (defaults, keyword arguments, overloading), correct value marshalling across the boundary, and faithful error propagation — without hand-writing brittle glue code for every function.

---

## Background & Problem

Native code is fast and strongly typed, but a dynamic runtime cannot call it directly: every argument must be converted from a dynamic object into a concrete native type, the right implementation must be chosen when several share a name, and any failure must surface as a clean runtime error rather than a crash.

Without a binding layer, developers write that conversion and dispatch glue by hand for each function — repetitive, error-prone boilerplate that silently mishandles edge cases (out-of-range integers, the wrong overload, keyword-only parameters passed positionally) and leaks low-level failure details.

With this binding layer, a native function is exposed once and then behaves like an idiomatic dynamic-language callable: arguments bind by position or by name with defaults, overloaded names dispatch by argument type, fixed-width integers are range-checked, strings and raw byte buffers round-trip correctly, keyword-only parameters are enforced, variadic arguments are captured, and native exceptions propagate as runtime errors. This PRD specifies the externally-observable contract of that calling surface.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., argument binding, type conversion, overload dispatch, error translation), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core binding logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, argument binding, type conversion, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Positional Defaults & Keyword Arguments

**As a developer**, I want a bound function to accept its arguments positionally or by name and to fall back to declared defaults, so calling native code feels like calling an ordinary dynamic-language function.

**Expected Behavior / Usage:**

A bound binary function over two integer parameters returns the first minus the second. The first parameter has a default of 8 and the second a default of 1. A call supplies an optional `args` array (positional values) and an optional `kwargs` object (named values); anything omitted uses its default. Positional values fill the parameters left to right; named values bind to the matching parameter regardless of order; the two styles may be combined (positional first, then keywords). The output is the single resulting integer followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_default_keyword_args.json`

```json
{
    "description": "A bound binary function over two integer parameters returns the first minus the second. The first parameter defaults to 8 and the second to 1 when omitted. Arguments may be supplied positionally, by name, in either name order, or as a mix; omitted trailing parameters fall back to their defaults. The output is the resulting integer.",
    "cases": [
        {"input": {"op": "subtract"}, "expected_output": "7\n"},
        {"input": {"op": "subtract", "args": [3], "kwargs": {"k": 5}}, "expected_output": "-2\n"}
    ]
}
```

---

### Feature 2: Type-Dispatched Overloading

**As a developer**, I want one callable name to host several implementations selected by argument type, so the runtime automatically routes each call to the matching native function.

**Expected Behavior / Usage:**

A single callable name carries two overloads distinguished only by the runtime type of its one argument: one overload accepts an integer, the other accepts a real (floating-point) number. The binding layer inspects the argument's type and routes the call accordingly, returning a small integer tag that identifies which overload ran — `1` for the integer overload and `2` for the real-number overload. The distinction is by genuine value type: an integer-valued argument selects the integer overload, while a value written with a fractional part selects the real-number overload. If the argument matches no overload (for example, a text value), argument resolution fails and the adapter reports the neutral line `error=type_mismatch`. Each output ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_type_overloading.json`

```json
{
    "description": "A single callable name carries two overloads distinguished only by the runtime type of its one argument: one overload accepts an integer and one accepts a real (floating-point) number. The binding layer selects the overload by argument type and returns a small integer tag identifying which overload ran (1 for the integer overload, 2 for the real-number overload). When the argument matches no overload (for example, a text value), argument resolution fails and a neutral type-mismatch error is reported.",
    "cases": [
        {"input": {"op": "classify", "value": 0}, "expected_output": "1\n"},
        {"input": {"op": "classify", "value": 0.0}, "expected_output": "2\n"},
        {"input": {"op": "classify", "value": "x"}, "expected_output": "error=type_mismatch\n"}
    ]
}
```

---

### Feature 3: Variadic Positional & Keyword Capture

**As a developer**, I want a bound function to accept an arbitrary number of trailing positional and keyword arguments beyond its declared parameters, so it can forward or inspect open-ended argument lists.

**Expected Behavior / Usage:**

A bound function declares two leading positional parameters and then captures everything else: positional arguments beyond the first two are gathered into a variadic positional pack, and any keyword arguments are gathered into a variadic keyword pack. The function reports two counts — how many extra positional arguments were captured and how many keyword arguments were captured. The first two supplied positional values fill the declared parameters and are NOT counted as extras. The output is two lines: `positional=<n>` then `keyword=<n>`, each terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_variadic_capture.json`

```json
{
    "description": "A bound function declares two leading positional parameters and then captures any further arguments: extra positional arguments are gathered into a variadic positional pack, and any keyword arguments beyond the declared parameters are gathered into a variadic keyword pack. The function reports how many extra positional arguments and how many keyword arguments it received. Output lists the positional count and the keyword count, each on its own line.",
    "cases": [
        {"input": {"op": "count_extras", "args": [1, 2]}, "expected_output": "positional=0\nkeyword=0\n"},
        {"input": {"op": "count_extras", "args": [1, 2, 3, 4], "kwargs": {"c": 5, "d": 6}}, "expected_output": "positional=2\nkeyword=2\n"}
    ]
}
```

---

### Feature 4: Fixed-Width Integer Range Enforcement

**As a developer**, I want integer arguments converted into a specific fixed-width native integer type with range checking, so out-of-range values are rejected instead of silently truncated or wrapped.

**Expected Behavior / Usage:**

A family of identity functions is exposed, one per fixed-width integer type, parameterised by signedness (`signed` true/false) and bit width (`bits` of 8, 16, 32, or 64). Given a value, the matching function returns it unchanged when it fits the target type's representable range, and otherwise fails conversion. A signed N-bit type represents the inclusive range from `-2^(N-1)` to `2^(N-1)-1`; an unsigned N-bit type represents `0` to `2^N-1`. A value within range is echoed back as an integer followed by a newline; a value outside the range (too large, too small, or negative for an unsigned type) yields the neutral line `error=type_mismatch`. The full 64-bit unsigned range up to `2^64-1` must round-trip exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature4_integer_width_range.json`

```json
{
    "description": "A family of identity functions each bound to a fixed-width integer type, parameterised by signedness (signed or unsigned) and bit width (8, 16, 32, or 64). When the supplied integer fits within the representable range of the chosen type it is returned unchanged; when it falls outside that range, argument conversion fails and a neutral type-mismatch error is reported. Signed N-bit types span -2^(N-1) .. 2^(N-1)-1; unsigned N-bit types span 0 .. 2^N-1.",
    "cases": [
        {"input": {"op": "identity", "signed": true, "bits": 8, "value": 127}, "expected_output": "127\n"},
        {"input": {"op": "identity", "signed": true, "bits": 8, "value": 128}, "expected_output": "error=type_mismatch\n"},
        {"input": {"op": "identity", "signed": false, "bits": 64, "value": [a very large unsigned 64-bit integer literal — ask the PM for the exact hex value]}, "expected_output": "[a very large unsigned 64-bit integer literal — ask the PM for the exact hex value]\n"}
    ]
}
```

---

### Feature 5: String & Byte-Buffer Marshalling

**As a developer**, I want text strings and raw byte buffers to convert correctly in both directions across the binding boundary, so binary-safe data and ordinary text both survive the round trip.

**Expected Behavior / Usage:**

*5.1 String Round-Trip — a text value crosses the boundary and returns unchanged*

A bound function accepts a text string and returns the same text. The output is the string verbatim (including spaces, punctuation, or emptiness) followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_string_roundtrip.json`

```json
{
    "description": "A bound function accepts a text string and returns the same text, demonstrating round-trip marshalling of string values across the binding boundary. The output is the string unchanged, including any embedded punctuation or spaces.",
    "cases": [
        {"input": {"op": "echo_string", "value": "[a default sample greeting — ask the PM for the exact string literal]"}, "expected_output": "[a default sample greeting — ask the PM for the exact string literal]\n"}
    ]
}
```

*5.2 Byte-Buffer Length — counting raw bytes including embedded zeros*

A bound function receives a raw byte buffer (supplied as an array of byte values 0–255) and returns its length in bytes. The count includes every byte, so embedded zero bytes are counted like any other; a buffer of four zero bytes has length 4. The output is the integer length followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_byte_length.json`

```json
{
    "description": "A bound function receives a raw byte buffer and returns its length in bytes. The buffer is supplied as an array of byte values (0-255). The length counts every byte, including embedded zero bytes, so a buffer of four zero bytes has length 4. Output is the integer length.",
    "cases": [
        {"input": {"op": "byte_length", "bytes": [0, 0, 0, 0]}, "expected_output": "4\n"}
    ]
}
```

*5.3 Truncating Byte-Buffer Construction — keep the first N bytes of a source*

A bound function builds a byte buffer from a text source but keeps only the first `size` bytes. The result is the leading `size`-byte prefix of the source; a size equal to or exceeding the source length yields the whole source, and a size of 0 yields an empty result. The output is the prefix rendered as text followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_byte_prefix.json`

```json
{
    "description": "A bound function builds a byte buffer from a text source but keeps only the first N bytes, where N is supplied explicitly. The result is the leading N-byte prefix of the source text. Output is that prefix rendered as text.",
    "cases": [
        {"input": {"op": "byte_prefix", "text": "[a default sample greeting — ask the PM for the exact string literal] world", "size": 5}, "expected_output": "[a default sample greeting — ask the PM for the exact string literal]\n"}
    ]
}
```

---

### Feature 6: Keyword-Only Parameters

**As a developer**, I want to mark certain parameters as keyword-only, so callers must name them explicitly and cannot accidentally bind them by position.

**Expected Behavior / Usage:**

*6.1 Fully Keyword-Only — every parameter must be named*

A bound function declares two integer parameters that are BOTH keyword-only. Each must be supplied by name (`kwargs`), in any order, and never positionally. A valid call returns the received pair. Supplying any value positionally, or omitting a required keyword, fails argument resolution. Valid output is two lines `i=<value>` and `j=<value>`, each terminated by a newline; an invalid call yields the neutral line `error=type_mismatch`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_all_keyword_only.json`

```json
{
    "description": "A bound function declares two integer parameters that are BOTH keyword-only: each must be supplied by name, in any order, and never positionally. Supplying them by name succeeds and the function returns the pair. Passing either value positionally, or omitting a required keyword, fails argument resolution and reports a neutral type-mismatch error. Output lists the two received values, each on its own line.",
    "cases": [
        {"input": {"op": "kw_only_all", "kwargs": {"i": 1, "j": 2}}, "expected_output": "i=1\nj=2\n"},
        {"input": {"op": "kw_only_all", "args": [1, 2]}, "expected_output": "error=type_mismatch\n"}
    ]
}
```

*6.2 Mixed Positional-Then-Keyword-Only — a positional lead followed by a keyword-only tail*

A bound function declares a leading parameter that may be passed positionally or by name, followed by a second parameter that is keyword-only. The leading value may arrive either way; the second must always be a keyword. A valid call returns the received pair. Passing the keyword-only value positionally, or omitting it, fails argument resolution. Valid output is two lines `i=<value>` and `j=<value>`, each terminated by a newline; an invalid call yields the neutral line `error=type_mismatch`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_mixed_keyword_only.json`

```json
{
    "description": "A bound function declares a leading parameter that may be passed positionally or by name, followed by a second parameter that is keyword-only. The first value may arrive either way; the second must always be a keyword. Mixing them validly returns the pair. Passing the keyword-only value positionally, or omitting it, fails argument resolution and reports a neutral type-mismatch error. Output lists the two received values, each on its own line.",
    "cases": [
        {"input": {"op": "kw_only_mixed", "args": [1], "kwargs": {"j": 2}}, "expected_output": "i=1\nj=2\n"},
        {"input": {"op": "kw_only_mixed", "args": [1, 2]}, "expected_output": "error=type_mismatch\n"}
    ]
}
```

---

### Feature 7: Native Exception Propagation

**As a developer**, I want exceptions thrown inside native code to surface as clean runtime errors in the dynamic runtime, so failures are reported rather than crashing the process.

**Expected Behavior / Usage:**

A bound function whose underlying native implementation unconditionally fails by throwing an exception with a fixed diagnostic message. The binding layer catches the native exception at the boundary and propagates it as a runtime error carrying that message. The adapter renders this as two lines: the neutral category line `error=runtime_error`, then `message=<text>` where the text is the preserved diagnostic (here, `oops!`). Each line ends with a newline. The host-language identity of the exception is never exposed — only the neutral category and the domain message.

**Test Cases:** `rcb_tests/public_test_cases/feature7_exception_propagation.json`

```json
{
    "description": "A bound function whose underlying native implementation unconditionally raises an exception. The binding layer propagates the failure across the boundary as a runtime error carrying the original diagnostic message. The adapter renders it as a neutral runtime-error category line followed by the preserved message.",
    "cases": [
        {"input": {"op": "raise_runtime"}, "expected_output": "error=runtime_error\nmessage=oops!\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the binding behaviors described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core binding logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin and prints the result (or a neutral error) to stdout, matching the per-feature contracts above. The request's `op` field selects the behavior; `args` (array) and `kwargs` (object) supply positional and named arguments where applicable; feature-specific fields (`value`, `signed`, `bits`, `bytes`, `text`, `size`) carry the remaining inputs. Native failures are translated in this adapter layer into neutral lines: `error=type_mismatch` for argument/overload/range resolution failures and `error=runtime_error` followed by `message=<text>` for propagated runtime exceptions. The host-language identity of any native exception MUST NOT appear in the output.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- near guessed timeout
