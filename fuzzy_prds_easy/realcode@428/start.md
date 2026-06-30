## Product Requirement Document

# Portable Numeric Components - Exact Integer, Rational, and Fixed-Point Behavior

## Project Goal

Build a numeric utility library that allows developers to express fixed-width bit operations, rational arithmetic, binary fixed-point values, and explicit overflow behavior without writing repetitive low-level arithmetic and boundary handling code.

---

## Background & Problem

Without this library/tool, developers are forced to hand-code bit counting, bit rotation, rational normalization, fixed-point scaling, and overflow boundary logic for each numeric type and width. This leads to duplicated formulas, inconsistent edge-case behavior, hard-to-review arithmetic, and bugs around rounding, sign placement, and integer limits.

With this library/tool, developers can use clear numeric abstractions and policy-driven operations while still receiving deterministic, externally observable results for bit patterns, rational values, fixed-point updates, and overflow-sensitive arithmetic.

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

### Feature 1: Fixed-Width Bit Rotation

**As a developer**, I want to rotate unsigned integer bit patterns by signed distances, so I can move bits cyclically without losing information outside the selected width.

**Expected Behavior / Usage:**

An input selects a bit width, an unsigned integer value, a direction, and a signed shift distance. The output reports the operation, width, original decimal value, shift, resulting decimal value, and resulting hexadecimal value. Shift distances are interpreted modulo the bit width; negative distances rotate in the opposite direction.

**Test Cases:** `rcb_tests/public_test_cases/feature1_bit_rotation.json`

```json
{
    "description": "Rotate an unsigned fixed-width integer by a signed bit distance while preserving the selected storage width.",
    "cases": [
        {
            "input": "command=bit_rotation\ndirection=left\nwidth=8\nvalue=128\nshift=4090\n",
            "expected_output": "operation=rotate_left\nwidth=8\ninput_decimal=128\nshift=4090\nresult_decimal=2\nresult_hex=0x2\n"
        },
        {
            "input": "command=bit_rotation\ndirection=left\nwidth=8\nvalue=20\nshift=-5\n",
            "expected_output": "operation=rotate_left\nwidth=8\ninput_decimal=20\nshift=-5\nresult_decimal=160\nresult_hex=0xa0\n"
        }
    ]
}
```

---
### Feature 2: Bit Pattern Counting

**As a developer**, I want to inspect unsigned integer bit patterns, so I can derive portable bit metrics without handwritten width-specific code.

**Expected Behavior / Usage:**

An input selects a bit width and unsigned integer value. The output reports the width and value, followed by the number of leading zero bits, leading one bits, trailing zero bits, trailing one bits, and total one bits in the selected fixed-width representation.

**Test Cases:** `rcb_tests/public_test_cases/feature2_bit_pattern_counts.json`

```json
{
    "description": "Inspect an unsigned fixed-width integer and report leading, trailing, and total one-bit/zero-bit counts.",
    "cases": [
        {
            "input": "command=bit_inspection\nwidth=8\nvalue=0\n",
            "expected_output": "width=8\nvalue=0\nleading_zero_bits=8\nleading_one_bits=0\ntrailing_zero_bits=8\ntrailing_one_bits=0\npopulation_count=0\n"
        },
        {
            "input": "command=bit_inspection\nwidth=8\nvalue=126\n",
            "expected_output": "width=8\nvalue=126\nleading_zero_bits=1\nleading_one_bits=0\ntrailing_zero_bits=1\ntrailing_one_bits=0\npopulation_count=6\n"
        }
    ]
}
```

---
### Feature 3: Power-of-Two Classification and Rounding

**As a developer**, I want to identify and round unsigned values around powers of two, so I can choose alignment and capacity boundaries consistently.

**Expected Behavior / Usage:**

An input selects a bit width and unsigned integer value. The output reports whether the value is an exact power of two, the greatest power of two not exceeding the value, and the least power of two not less than the value. Zero is reported as not a power of two and rounds to zero for both floor and ceiling.

**Test Cases:** `rcb_tests/public_test_cases/feature3_power_of_two_rounding.json`

```json
{
    "description": "Classify an unsigned fixed-width integer as a power of two and return the nearest power-of-two floor and ceiling values within the same width.",
    "cases": [
        {
            "input": "command=power_rounding\nwidth=8\nvalue=0\n",
            "expected_output": "width=8\nvalue=0\nis_power_of_two=false\nbit_floor=0\nbit_ceil=0\n"
        },
        {
            "input": "command=power_rounding\nwidth=8\nvalue=3\n",
            "expected_output": "width=8\nvalue=3\nis_power_of_two=false\nbit_floor=2\nbit_ceil=4\n"
        }
    ]
}
```

---
### Feature 4: Rational Arithmetic

**As a developer**, I want to combine rational values exactly, so I can preserve numerator/denominator results without premature floating-point conversion.

**Expected Behavior / Usage:**

An input provides two rational values as numerator/denominator pairs and selects an arithmetic operation. The output reports the selected operation and the resulting numerator and denominator. Results are the exact arithmetic result shape exercised by the contract and are not implicitly canonicalized unless the selected operation naturally produces that representation.

**Test Cases:** `rcb_tests/public_test_cases/feature4_fraction_arithmetic.json`

```json
{
    "description": "Combine two rational values with the requested arithmetic operation and return the raw numerator and denominator produced by exact rational arithmetic.",
    "cases": [
        {
            "input": "command=fraction_binary\noperation=add\nleft_numerator=1\nleft_denominator=3\nright_numerator=2\nright_denominator=3\n",
            "expected_output": "operation=add\nnumerator=9\ndenominator=9\n"
        },
        {
            "input": "command=fraction_binary\noperation=add\nleft_numerator=1\nleft_denominator=4\nright_numerator=1\nright_denominator=3\n",
            "expected_output": "operation=add\nnumerator=7\ndenominator=12\n"
        }
    ]
}
```

---
### Feature 5: Rational Normalization

**As a developer**, I want to normalize a rational value on request, so I can control whether common factors and sign placement are changed.

**Expected Behavior / Usage:**

An input provides one rational value as a numerator/denominator pair and selects a transformation. Reduction divides numerator and denominator by their common factor while preserving sign placement. Canonicalization reduces and places the sign in a stable canonical position. Absolute magnitude returns a non-negative magnitude while preserving the denominator shape used by that operation.

**Test Cases:** `rcb_tests/public_test_cases/feature5_fraction_normalization.json`

```json
{
    "description": "Transform one rational value by reducing common factors, canonicalizing sign placement, or taking absolute magnitude, then return numerator and denominator.",
    "cases": [
        {
            "input": "command=fraction_normalize\noperation=reduce\nnumerator=1024\ndenominator=360\n",
            "expected_output": "operation=reduce\nnumerator=128\ndenominator=45\n"
        },
        {
            "input": "command=fraction_normalize\noperation=reduce\nnumerator=-6\ndenominator=-3\n",
            "expected_output": "operation=reduce\nnumerator=-2\ndenominator=-1\n"
        }
    ]
}
```

---
### Feature 6: Rational Comparison

**As a developer**, I want to compare rational values by numeric value, so I can make ordering decisions without converting to approximate decimals.

**Expected Behavior / Usage:**

An input provides two rational values as numerator/denominator pairs. The output reports all five relations: less, greater, less-or-equal, greater-or-equal, and equal. Numerically equivalent ratios compare equal even when their numerator and denominator pairs differ.

**Test Cases:** `rcb_tests/public_test_cases/feature6_fraction_comparison.json`

```json
{
    "description": "Compare two rational values by numeric value and report the full set of ordering and equality relations.",
    "cases": [
        {
            "input": "command=fraction_compare\nleft_numerator=2\nleft_denominator=9\nright_numerator=4\nright_denominator=18\n",
            "expected_output": "less=false\ngreater=false\nless_or_equal=true\ngreater_or_equal=true\nequal=true\n"
        },
        {
            "input": "command=fraction_compare\nleft_numerator=2\nleft_denominator=9\nright_numerator=2\nright_denominator=8\n",
            "expected_output": "less=true\ngreater=false\nless_or_equal=true\ngreater_or_equal=false\nequal=false\n"
        }
    ]
}
```

---
### Feature 7: Binary Fixed-Point Numeric Operations

**As a developer**, I want to store and update binary fixed-point values, so I can obtain deterministic fractional results with fixed binary resolution.

**Expected Behavior / Usage:**

An input selects a fixed-point scenario. Assignment scenarios report the stored numeric value after assigning from floating-point or rational input. Compound and increment/decrement scenarios report each externally visible numeric result in sequence, including the distinction between returned and stored values for pre/post operations.

**Test Cases:** `rcb_tests/public_test_cases/feature7_fixed_point_operations.json`

```json
{
    "description": "Store values in binary fixed-point form and report the externally visible numeric value after assignment, compound arithmetic, or increment/decrement operations.",
    "cases": [
        {
            "input": "command=fixed_point\nscenario=assign_from_floating\nvalue=234.567\n",
            "expected_output": "scenario=assign_from_floating\nvalue=234.56698608398438\n"
        },
        {
            "input": "command=fixed_point\nscenario=assign_from_fraction\nnumerator=1\ndenominator=3\n",
            "expected_output": "scenario=assign_from_fraction\nvalue=0.33331298828125\n"
        }
    ]
}
```

---
### Feature 8: Overflow Policy Arithmetic

**As a developer**, I want to apply selected overflow behavior to numeric conversion and arithmetic, so I can make boundary handling explicit for conversions and arithmetic operations.

**Expected Behavior / Usage:**

An input selects an overflow mode, operation, and numeric operands. The output echoes the selected mode and operation and reports the resulting value. Native conversion follows fixed-width wraparound behavior for the tested conversions; saturated behavior clamps overflowing results to the destination or result type boundary; throwing mode is included for a non-overflowing arithmetic sample and returns the ordinary result.

**Test Cases:** `rcb_tests/public_test_cases/feature8_overflow_policies.json`

```json
{
    "description": "Apply an arithmetic overflow policy to conversion or arithmetic and report the resulting numeric value together with the selected policy and operation.",
    "cases": [
        {
            "input": "command=overflow\n[the mode parameter value for the overflow test]\noperation=convert_uint8\nvalue=259\n",
            "expected_output": "[the mode parameter value for the overflow test]\noperation=convert_uint8\nresult=3\n"
        },
        {
            "input": "command=overflow\n[the mode parameter value for the overflow test]\noperation=convert_uint16\nvalue=-123\n",
            "expected_output": "[the mode parameter value for the overflow test]\noperation=convert_uint16\nresult=65413\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_bit_rotation.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_bit_rotation@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- matches the behavior documented in the `conversions` test spec for float precision loss
- aligns with the logic in `rational_calculator.rs` for the `add` operation without reduction
