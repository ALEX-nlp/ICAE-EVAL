## Product Requirement Document

# Binary-Scaled Fixed-Point Numerics Library - Approximating Real Numbers with Integer Arithmetic

## Project Goal

Build a numerics library that lets developers approximate real numbers using binary fixed-point arithmetic — an integer stored value combined with a compile-time binary scaling exponent — so they can do fractional math with the speed and determinism of integer operations and without depending on hardware floating-point. The library must expose construction from real numbers, decimal rendering, operator and widening ("named") arithmetic, elementary math functions, selectable overflow policies, optional arbitrary-precision backing storage, and bit-width introspection.

---

## Background & Problem

Without such a library, developers who need fractional arithmetic on platforms that lack (or cannot afford) floating-point hardware must hand-roll scaled-integer code: every value carries an implicit "this int is really value × 2^N" convention that lives only in the programmer's head. This leads to error-prone boilerplate — manual shifts on every multiply and divide, ad-hoc rounding, silent overflow when intermediate products exceed the word size, and no consistent way to render the scaled integer back to a human-readable decimal. Changing the precision of a value means revisiting every arithmetic site by hand.

With this library, a value's scaling exponent is part of its type, so the compiler tracks precision automatically. Constructing from a real number rounds toward zero into the chosen bit budget; arithmetic operators behave like fixed-width machine integers (and wrap predictably) while widening "named" operations preserve full precision; math functions (sine, cosine, square root) operate directly on fixed-point operands; overflow is handled by an explicit, selectable policy (wrap, saturate, or signal an error); the stored integer can optionally be an arbitrary-precision big integer so results never lose precision; and the real number a value represents can be rendered as decimal text for display.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility numerics library (representation/rendering, operator arithmetic, widening arithmetic, math functions, overflow policy, arbitrary-precision storage, bit introspection). It MUST NOT be a single "god file": separate the core numeric type and its policies from the math/algorithm layer, and keep the execution/test adapter physically separate from the core domain. Do not over-engineer, but avoid monolithic files.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, NOT the internal data model of the core system. The core numeric types must be usable directly from idiomatic application code and must not depend on stdin/stdout or JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls on the core types and rendering results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, routing, value construction, arithmetic, math functions, overflow handling, and output formatting in distinct logical units.
   - **Open/Closed Principle (OCP):** New overflow policies, storage backends, or math functions should be addable without modifying the core numeric engine.
   - **Liskov Substitution Principle (LSP):** A value backed by a wider or arbitrary-precision integer must be usable wherever a narrower-backed value is, with consistent observable semantics.
   - **Interface Segregation Principle (ISP):** Keep the construction, arithmetic, and policy interfaces small and cohesive.
   - **Dependency Inversion Principle (DIP):** Math functions and adapters depend on the abstract numeric type, not on a specific integer width or storage backend.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic for the target language; the scaling exponent and storage type should be expressible declaratively, hiding shift/round bookkeeping.
   - **Resilience:** Edge cases (overflow under a throwing policy, square root of a negative operand, an unrecognized policy/format) must be modeled as explicit error conditions surfaced through a normalized, language-neutral error contract — never as silent corruption.

---

## Core Features

### Feature 1: Binary-Scaled Representation & Decimal Rendering

**As a developer**, I want to store a real number as an integer scaled by a binary exponent and read both the raw stored integer and the rendered decimal, so I can do fractional math using integer storage while still displaying human-readable values.

**Expected Behavior / Usage:**

A value is defined by a real number `real` and a fractional-bit count `frac_bits`. It is stored as `data = truncate(real * 2^frac_bits)` (truncation is toward zero) and represents `data * 2^-frac_bits`. The output reports two labelled lines: `data=<stored integer>` and `value=<decimal rendering>`. Increasing `frac_bits` increases precision; a value that is not exactly representable in the given budget renders as the nearest representable approximation (e.g. an angle constant stored with 28 fractional bits round-trips to a slightly truncated decimal). `data` is the exact stored integer; `value` is the real number that integer denotes.

**Test Cases:** `rcb_tests/public_test_cases/feature1_representation.json`

```json
{
    "description": "Approximate a real number as an integer scaled by a binary exponent. The value is stored as data = truncate(real * 2^frac_bits) and rendered back as data * 2^-frac_bits. Reports both the stored integer and the rendered real number.",
    "cases": [
        {"input": {"op": "represent", "real": 3.5, "frac_bits": 1}, "expected_output": "data=7\nvalue=3.5\n"},
        {"input": {"op": "represent", "real": 3.1415926535, "frac_bits": 28}, "expected_output": "data=843314856\nvalue=3.141592652\n"}
    ]
}
```

---

### Feature 2: Construction Rounding & Exact Stored Value

**As a developer**, I want construction from a real number to round into the available bit budget deterministically and let me inspect the exact stored value at full precision, so I can reason precisely about quantization error and signed vs. unsigned storage.

**Expected Behavior / Usage:**

Given `real`, a fractional-bit count `frac_bits`, and an optional `signed` flag (default signed), the value is constructed by truncating toward zero into the representation. The output reports `data=<stored integer>` and `value=<exact stored value rendered at full precision>`. A real number that fits exactly is preserved (e.g. `15.9375` with 4 fractional bits stores `255` and renders `15.9375`); one that needs more precision is stored as the closest representable value below it in magnitude (e.g. `0.1` with 8 fractional bits stores `25`, which is exactly `0.09765625`). Negative reals are supported for signed representations. The full-precision rendering exposes the true stored approximation rather than a rounded display form.

**Test Cases:** `rcb_tests/public_test_cases/feature2_construction.json`

```json
{
    "description": "Constructing a fixed-point value from a real number rounds toward zero to the nearest value representable with the given integer/fractional bit budget. A value that fits exactly is preserved; one that needs more precision is stored as the closest approximation. Reports the stored integer and the exact stored value rendered at full precision, optionally for a signed or unsigned representation.",
    "cases": [
        {"input": {"op": "store_exact", "real": 15.9375, "frac_bits": 4, "signed": false}, "expected_output": "data=255\nvalue=15.9375\n"},
        {"input": {"op": "store_exact", "real": 0.1, "frac_bits": 8, "signed": true}, "expected_output": "data=25\nvalue=0.09765625\n"}
    ]
}
```

---

### Feature 3: Operator Arithmetic — Fixed-Width Promotion & Wraparound

**As a developer**, I want the built-in arithmetic operators to behave like fixed-width machine integers — staying in the operand's representation and wrapping predictably on overflow — so I get the speed and determinism of integer math with no hidden widening.

**Expected Behavior / Usage:**

Operator arithmetic keeps the result in the operand's representation. Scaling or halving by an integer preserves the format and may discard low-order precision. Squaring a value that already uses the full capacity of a same-width store overflows and wraps modulo the representable range (a full-scale value near 16 squared reports `14`, not ~254). Adding two values whose sum exceeds the available integer range likewise wraps (two values summing past the 2-integer-bit range wrap to `0`). A chain of in-place compound assignments (`+=`, `-=`, `/=`, `*=`) emits one `result=<value>` line after each step, showing the running value through truncating division and sign changes. Each operation's output line is `result=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_operator_arithmetic.json`

```json
{
    "description": "Built-in operator arithmetic follows fixed-width machine rules: results stay in the operand's representation. Scaling or halving by an integer keeps the format and may lose low-order precision. Squaring a value that uses the full capacity of a same-width store, or adding two values whose sum exceeds the available integer range, wraps around modulo the range rather than widening. A chain of compound assignments shows the running value after each step.",
    "cases": [
        {"input": {"op": "square_wrap", "real": 15.9375}, "expected_output": "result=14\n"},
        {"input": {"op": "sum_wrap", "a": 3, "b": 1}, "expected_output": "result=0\n"},
        {"input": {"op": "compound", "real": 22.75}, "expected_output": "result=35.25\nresult=-0.25\nresult=-0.0625\nresult=9.9375\nresult=-29.8125\nresult=-30\n"}
    ]
}
```

---

### Feature 4: Widening Named Arithmetic

**As a developer**, I want named arithmetic operations that widen their result type just enough to preserve full precision, so I can avoid the silent overflow of fixed-width operators when I actually need the exact answer.

**Expected Behavior / Usage:**

Named arithmetic widens the result representation to hold the mathematically exact outcome. A widening multiply / named multiply of a full-capacity value squared yields the exact product (`254.00390625`) where the fixed-width operator would have wrapped. Division comes in two flavors: a widening divide keeps the fractional quotient (`15 / 2 = 7.5`), while a representation-preserving named divide truncates the fractional part toward zero (`1 / 2 = 0`, `3 / 2 = 1`). A named add widens enough to hold operands of vastly different magnitudes without loss. Each result is emitted as `result=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_named_arithmetic.json`

```json
{
    "description": "Widening named arithmetic preserves precision that fixed-width operators would lose. The widening multiply produces the exact product of a full-capacity value squared, matching the named multiply. Division can either widen to keep the fractional quotient or stay in the operand representation and truncate the fractional part toward zero. The named add widens enough to hold operands of vastly different magnitudes without loss.",
    "cases": [
        {"input": {"op": "named_multiply", "real": 15.9375}, "expected_output": "result=254.00390625\n"},
        {"input": {"op": "divide_widen", "a": 15, "b": 2}, "expected_output": "result=7.5\n"},
        {"input": {"op": "divide_truncate", "a": 1, "b": 2}, "expected_output": "result=0\n"}
    ]
}
```

---

### Feature 5: Elementary Math Functions

**As a developer**, I want sine, cosine, and square-root functions that operate directly on fixed-point operands, so I can do trigonometry and geometry without converting to floating-point, while understanding that the operand's bit format bounds the achievable precision.

**Expected Behavior / Usage:**

*5.1 Trigonometric functions — sine and cosine of a fixed-point angle*

`sin` and `cos` take an angle in radians (`value`) held in a representation described by `signed`, total `bits`, and `frac_bits`. The result is a fixed-point value whose precision is bounded by that format; near-exact angles yield the expected landmark values (`cos(π)` in a 16-bit signed format with 13 fractional bits reports `-1`; the quarter-turn and half-turn landmarks yield `0`, `±1`). The output is `result=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_trig.json`

```json
{
    "description": "Sine and cosine of an angle in radians held in a fixed-point representation described by signedness, total bit width and fractional-bit count. The achievable precision is bounded by the operand's bit format; near-exact angles yield the expected landmark values such as -1, 0, +1 or a quarter-turn magnitude.",
    "cases": [
        {"input": {"op": "trig", "func": "cos", "signed": true, "bits": 16, "frac_bits": 13, "value": 3.1415926}, "expected_output": "[the trigonometric cosine approximation for pi]\n"},
        {"input": {"op": "trig", "func": "sin", "signed": false, "bits": 16, "frac_bits": 14, "value": 1.5707963}, "expected_output": "result=1\n"}
    ]
}
```

*5.2 Square root and Euclidean magnitude — including the negative-operand error*

`sqrt` returns the (truncated) square root of a non-negative operand (`sqrt(4) = 2`). A `magnitude` operation composes squaring, addition, and square root to compute `sqrt(x^2 + y^2 + z^2)` over fixed-point operands. A negative square-root operand is an out-of-domain condition and is reported as the normalized error line `error=domain`. Successful results are emitted as `result=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_sqrt.json`

```json
{
    "description": "Square root of a non-negative fixed-point operand returns its truncated root, and a Euclidean magnitude composes squaring, addition and square root over three operands. A negative square-root operand is an out-of-domain condition reported as a normalized domain error rather than a value.",
    "cases": [
        {"input": {"op": "magnitude", "x": 1, "y": 4, "z": 9}, "expected_output": "result=9.8994948864\n"},
        {"input": {"op": "sqrt", "value": -1}, "expected_output": "error=domain\n"}
    ]
}
```

---

### Feature 6: Configurable Overflow Policies

**As a developer**, I want to choose how out-of-range results are resolved — wrap, saturate, or signal an error — so I can pick the right trade-off between speed, safety, and correctness per use site.

**Expected Behavior / Usage:**

When a value does not fit a target representation, a selectable `policy` decides the outcome:
- **wrap** reduces the value modulo the target range (`259` into an unsigned 8-bit target → `3`).
- **saturate** clamps to the nearest representable bound (`259` into an unsigned 8-bit target → `255`).
- **throw** refuses to produce a value and signals overflow (`259` into an unsigned 8-bit target → `error=overflow`); an in-range value under the throw policy stores normally (`200` → `result=200`).

Policies apply both to converting a value into a narrower target (`convert`) and to addition (`add_policy`). Assigning an out-of-range real into a throw-on-overflow representation reports `error=overflow`, while an in-range real stores and renders normally. Successful numeric results are emitted as `result=<value>`; the throwing policy's failure is the normalized line `error=overflow`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_overflow_policies.json`

```json
{
    "description": "A value that does not fit in a target representation is resolved according to a selectable overflow policy. The wrap policy reduces the value modulo the target range; the saturate policy clamps it to the nearest representable bound; the throw policy reports an overflow error instead of producing a value. Policies apply both to converting a value into a narrower target and to addition. Assigning an out-of-range value into a throw-on-overflow representation reports an overflow error, while an in-range value is stored normally.",
    "cases": [
        {"input": {"op": "convert", "policy": "wrap", "signed": false, "bits": 8, "value": 259}, "expected_output": "result=3\n"},
        {"input": {"op": "convert", "policy": "saturate", "signed": false, "bits": 8, "value": 259}, "expected_output": "result=255\n"},
        {"input": {"op": "convert", "policy": "throw", "signed": false, "bits": 8, "value": 259}, "expected_output": "error=overflow\n"}
    ]
}
```

---

### Feature 7: Arbitrary-Precision Big-Number Arithmetic

**As a developer**, I want the stored integer to optionally be an arbitrary-precision big integer, so arithmetic on numbers far beyond machine word size stays exact and I can represent extreme magnitudes.

**Expected Behavior / Usage:**

When backed by an arbitrary-precision integer, the storage grows as wide as needed and arithmetic loses no precision. Large integers supplied as decimal text support exact add, subtract, multiply, and divide (`123456789012345678 × 123456789012345678 = 15241578753238836527968299765279684`). Building ten-to-the-hundredth by repeated multiplication in a very wide store renders as `1e+100`, and taking its reciprocal renders as `1e-100`. The `bignum` operation selects the arithmetic via `func` (`add`/`subtract`/`multiply`/`divide`) over text operands `a` and `b`; the `googol` operation needs no operands. Each result is emitted as `result=<value>` (the googol case emits two result lines).

**Test Cases:** `rcb_tests/public_test_cases/feature7_arbitrary_precision.json`

```json
{
    "description": "Arbitrary-precision integers grow as wide as needed, so arithmetic on numbers far beyond machine word size is exact. Addition, subtraction, multiplication and division of large integers (supplied as decimal text) return exact results. Building ten-to-the-hundredth by repeated multiplication and then taking its reciprocal in a 400-bit store renders the expected very large and very small magnitudes.",
    "cases": [
        {"input": {"op": "bignum", "func": "multiply", "a": "123456789012345678", "b": "123456789012345678"}, "expected_output": "result=15241578753238836527968299765279684\n"},
        {"input": {"op": "googol"}, "expected_output": "result=1e+100\nresult=1e-100\n"}
    ]
}
```

---

### Feature 8: Bit-Width Introspection

**As a developer**, I want to count the redundant leading bits of a signed integer, so I can know how much headroom a value has before it needs more storage and drive precision-management decisions.

**Expected Behavior / Usage:**

Given a 32-bit signed integer `value`, the `leading_bits` operation reports the number of redundant leading bits above the most significant bit that carries magnitude information. For a non-negative value it is the count of leading zero bits beyond the sign bit (`0 → 31`, `127 → 24`); for a negative value it is the count of leading one bits beyond the sign bit (`-129 → 23`). Zero has the maximum redundancy. The output is `result=<count>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_bit_introspection.json`

```json
{
    "description": "Counts the number of redundant leading bits of a 32-bit signed integer: the bits above the most significant bit that carries information about the magnitude. For a non-negative value it is the count of leading zero bits beyond the sign bit; for a negative value it is the count of leading one bits beyond the sign bit. Zero has the maximum redundancy.",
    "cases": [
        {"input": {"op": "leading_bits", "value": 0}, "expected_output": "result=31\n"},
        {"input": {"op": "leading_bits", "value": 127}, "expected_output": "result=24\n"},
        {"input": {"op": "leading_bits", "value": -129}, "expected_output": "result=23\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured numerics library implementing binary-scaled fixed-point representation, construction/rendering, operator and widening arithmetic, elementary math functions, configurable overflow policies, optional arbitrary-precision backing storage, and bit-width introspection. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint (multi-file, with the core numeric type and policies separated from the math/algorithm layer), ensuring maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core system. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. All error conditions are normalized to language-neutral category lines (`error=domain`, `error=overflow`, `error=range`) — no host-language exception class names or runtime message fragments may appear in stdout. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_representation.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_representation@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same list pattern as the dispatch keywords
- apply the negative rendering rule to floating point results
