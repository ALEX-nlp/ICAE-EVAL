## Product Requirement Document

# Assertion & Expectation Engine — A Library for Expressing, Evaluating, and Reporting Test Expectations

## Project Goal

Build a lightweight assertion-and-expectation engine that lets developers write checks as ordinary comparison expressions, evaluate them to a pass/fail outcome, render them back as readable text, and group them under named tests — so a test author can state *what* should be true and immediately see both the outcome and a faithful rendering of the expression that was checked, without hand-writing message strings or bespoke reporting code.

---

## Background & Problem

Without such an engine, developers writing checks must manually pair every comparison with a hand-crafted description ("expected 42 to equal 42") and manually track how many checks passed or failed. This is repetitive, drifts out of sync with the actual condition being tested, and produces inconsistent output across a codebase.

With this engine, a comparison such as "the left value equals the right value" is both *evaluated* (yielding a boolean outcome) and *rendered* (yielding a canonical textual form of the same comparison) by the same mechanism, so the reported expression can never disagree with what was actually checked. The engine supports relational comparisons between values, logical composition of comparisons, approximate (tolerance-based) numeric equality, compile-time type-identity comparisons, exception-behavior matchers, and the grouping of expectations under named tests with aggregate pass/fail accounting.

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

### Feature 1: Relational Expectation Between Two Values

**As a developer**, I want to assert a comparison between two values and get back both the outcome and a readable rendering of the comparison, so my reports always reflect exactly what was checked.

**Expected Behavior / Usage:**

The request supplies two integer operands (`lhs`, `rhs`) and a comparison operator named by a short token in `op`: `eq` (equal), `ne` (not equal), `lt` (less than), `le` (less than or equal), `gt` (greater than), `ge` (greater than or equal). The engine evaluates the comparison and emits exactly two lines. The first line, `expression=...`, is the canonical rendering of the comparison: the left operand, a single space, the operator's mathematical symbol (`==`, `!=`, `<`, `<=`, `>`, `[a specific comparison operator (explained in docs)]`), a single space, then the right operand. The second line, `outcome=...`, is `pass` when the comparison holds and `fail` when it does not. Both lines end with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_relational_expectation.json`

```json
{
    "description": "A single relational expectation is evaluated between two integer operands using one of the comparison operators (equal, not-equal, less-than, less-or-equal, greater-than, greater-or-equal). The engine reports two things: the rendered form of the comparison expression (the left operand, an operator symbol, and the right operand) and the boolean outcome of evaluating it. The operator is named in the request as a short token and is rendered using its mathematical symbol.",
    "cases": [
        {"input": {"action": "compare", "op": "eq", "lhs": 42, "rhs": 42}, "expected_output": "expression=42 == 42\noutcome=pass\n"},
        {"input": {"action": "compare", "op": "gt", "lhs": 1, "rhs": 2}, "expected_output": "expression=1 > 2\noutcome=fail\n"}
    ]
}
```

---

### Feature 2: Logical Composition of Comparisons

**As a developer**, I want to combine comparisons with logical connectives or negate one, so I can express compound conditions and still see a faithful rendering of the whole condition.

**Expected Behavior / Usage:**

The request's `op` selects the connective. For `and` and `or`, the request supplies two sub-comparisons under `left` and `right`, each a `{op, lhs, rhs}` object using the same relational tokens and integer operands as Feature 1. The engine renders a binary composition as an opening parenthesis, the rendered left comparison, a space, the connective word (`and` or `or`), a space, the rendered right comparison, and a closing parenthesis — e.g. `(1 == 2 or 3 > 7)`. Its outcome is the boolean conjunction/disjunction of the two sub-outcomes (both sides are always evaluated). For `not`, the request supplies a single sub-comparison under `operand`; the engine renders the word `not`, a space, then the inner comparison with **no** surrounding parentheses — e.g. `not 1 == 2` — and its outcome is the boolean negation of the inner comparison. Output is the same two lines (`expression=...`, `outcome=...`) as Feature 1, each newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature2_logical_composition.json`

```json
{
    "description": "Two relational comparisons are combined with a logical connective, or a single relational comparison is negated. For a conjunction or disjunction the engine renders the combined expression as a parenthesized pair joined by the connective word, and evaluates it with the usual short-circuit-free boolean semantics. For a negation the engine renders the word for negation followed by the inner comparison (no extra parentheses) and inverts its boolean result. In every case the engine reports the rendered expression and the boolean outcome.",
    "cases": [
        {"input": {"action": "logic", "op": "or", "left": {"op": "eq", "lhs": 1, "rhs": 2}, "right": {"op": "gt", "lhs": 3, "rhs": 7}}, "expected_output": "expression=(1 == 2 or 3 > 7)\noutcome=fail\n"},
        {"input": {"action": "logic", "op": "not", "operand": {"op": "eq", "lhs": 1, "rhs": 2}}, "expected_output": "expression=not 1 == 2\noutcome=pass\n"}
    ]
}
```

---

### Feature 3: Approximate (Tolerance-Based) Numeric Equality

**As a developer**, I want to assert that two numbers are close enough within a tolerance, so I can check floating-point or fuzzy values without demanding exact equality.

**Expected Behavior / Usage:**

The request supplies a left operand (`lhs`), a right operand (`rhs`), and a tolerance (`epsilon`), plus a `kind` of `int` or `double` selecting integer or floating-point operands. The outcome is `pass` when the absolute difference between `lhs` and `rhs` is **strictly less than** `epsilon`, and `fail` otherwise. The engine renders the expression as the left operand, a space, a tilde (`~`), a space, then an opening parenthesis, the right operand, a space, `+/-`, a space, the epsilon, and a closing parenthesis — e.g. `42 ~ (43 +/- 2)`. Numbers are rendered using the engine's default numeric formatting (for example, `0.2` renders as `0.2`). Output is the standard two lines (`expression=...`, `outcome=...`), each newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature3_approx_equality.json`

```json
{
    "description": "An approximate-equality expectation checks whether two numeric operands are within a tolerance (epsilon) of one another. The outcome is a pass when the absolute difference between the two operands is strictly less than epsilon, and a fail otherwise. The engine renders the expression as the left operand, a tilde, then the right operand and the epsilon shown as a plus-or-minus tolerance inside parentheses. Operands may be integers or floating-point numbers; numbers are rendered using the engine's default numeric formatting.",
    "cases": [
        {"input": {"action": "approx", "kind": "int", "lhs": 42, "rhs": 43, "epsilon": 2}, "expected_output": "expression=42 ~ (43 +/- 2)\noutcome=pass\n"},
        {"input": {"action": "approx", "kind": "int", "lhs": 1, "rhs": 5, "epsilon": 2}, "expected_output": "expression=1 ~ (5 +/- 2)\noutcome=fail\n"}
    ]
}
```

---

### Feature 4: Compile-Time Type-Identity Comparison

**As a developer**, I want to assert that two types are the same (or different), so I can check type-level expectations and see them rendered by type name.

**Expected Behavior / Usage:**

The request supplies two type operands as plain type-name tokens (`lhs`, `rhs`) drawn from a supported set of primitive type names (`int`, `float`, `double`, `void`, `char`, `bool`) and an `op` of `eq` or `ne`. The engine renders the expression as the left type name, a space, the operator symbol (`==` for `eq`, `!=` for `ne`), a space, then the right type name — e.g. `int == float`. For `eq`, the outcome is `pass` exactly when the two names denote the same type; for `ne`, the outcome is `pass` exactly when they denote different types. Output is the standard two lines (`expression=...`, `outcome=...`), each newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature4_type_identity.json`

```json
{
    "description": "A type-identity expectation compares two compile-time types for sameness using an equality or inequality operator. The engine renders the expression as the left type's name, an operator symbol, and the right type's name, and reports a boolean outcome: equality is a pass exactly when both names denote the same type, and inequality is a pass exactly when they denote different types. Type operands are given by their plain type-name tokens.",
    "cases": [
        {"input": {"action": "type_compare", "op": "eq", "lhs": "int", "rhs": "float"}, "expected_output": "expression=int == float\noutcome=fail\n"},
        {"input": {"action": "type_compare", "op": "ne", "lhs": "void", "rhs": "double"}, "expected_output": "expression=void != double\noutcome=pass\n"}
    ]
}
```

---

### Feature 5: Exception-Behavior Matchers

**As a developer**, I want to assert whether a piece of code raises an exception or completes normally, so I can verify error-handling behavior without writing my own try/catch scaffolding.

**Expected Behavior / Usage:**

The request supplies a `matcher` of `throws` or `nothrow` and a `behavior` of `throw` or `noop` that selects what the wrapped code does (raise an exception, or do nothing). The `throws` matcher yields `pass` when the wrapped code raises an exception and `fail` when it completes normally. The `nothrow` matcher yields `pass` when the wrapped code completes normally and `fail` when it raises an exception. The engine catches any raised exception internally as part of evaluating the matcher; no host-language exception type or message ever appears in the output. The rendered expression is simply the matcher's name (`throws` or `nothrow`). Output is the standard two lines (`expression=...`, `outcome=...`), each newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature5_exception_matchers.json`

```json
{
    "description": "An exception-matcher expectation wraps a piece of code and checks its throwing behavior. The throws matcher passes when the wrapped code raises an exception and fails when it completes normally. The nothrow matcher passes when the wrapped code completes normally and fails when it raises an exception. The wrapped code's behavior is selected by the request (it either raises an exception or does nothing). The engine catches any raised exception internally; the reported expression is the matcher's name and the outcome is the boolean result. No host-language exception identity appears in the output.",
    "cases": [
        {"input": {"action": "matcher", "matcher": "throws", "behavior": "throw"}, "expected_output": "expression=throws\noutcome=pass\n"},
        {"input": {"action": "matcher", "matcher": "nothrow", "behavior": "throw"}, "expected_output": "expression=nothrow\noutcome=fail\n"}
    ]
}
```

---

### Feature 6: Named Test Execution & Reporting

**As a developer**, I want to group expectations under a named test and get aggregate pass/fail counts, or skip a test entirely, so I can organize and report my checks at the test level.

**Expected Behavior / Usage:**

The request supplies a test `name` and, when the test is to run, a `body` array of zero or more relational expectations (each a `{op, lhs, rhs}` object as in Feature 1). When executed, the engine evaluates every expectation in the body in order and emits five lines: `test=<name>`, `status=executed`, `asserts=<total>` (the number of expectations evaluated), `passed=<n>` (how many held), and `failed=<n>` (how many did not). An empty body yields zero counts. Alternatively, when the request sets `skip` to true, the test is not executed: the engine emits exactly two lines, `test=<name>` and `status=skipped`, and the body (if any) is never evaluated. Every emitted line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature6_named_test_reporting.json`

```json
{
    "description": "A named test is registered and executed by the engine. A test carries a human-readable name and a body consisting of zero or more relational expectations. When the test runs, the engine reports the test name, an executed status, and the aggregate assertion counts: the total number of expectations evaluated, how many passed, and how many failed. A test may instead be marked to be skipped; a skipped test reports its name and a skipped status and its body is never evaluated.",
    "cases": [
        {"input": {"action": "run_test", "name": "assertions", "body": [{"op": "eq", "lhs": 42, "rhs": 42}]}, "expected_output": "test=assertions\nstatus=executed\nasserts=1\npassed=1\nfailed=0\n"},
        {"input": {"action": "run_test", "name": "skipped test", "skip": true}, "expected_output": "test=skipped test\nstatus=skipped\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core engine — value/expression modeling, comparison and logical operators, approximate equality, type-identity comparison, exception matchers, and named-test accounting — must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting outcome lines to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `compare` (Feature 1), `logic` (Feature 2), `approx` (Feature 3), `type_compare` (Feature 4), `matcher` (Feature 5), and `run_test` (Feature 6). For the expectation features the program prints an `expression=` line (the canonical rendering) followed by an `outcome=` line (`pass`/`fail`). For `run_test` it prints `test=`/`status=` lines plus, when executed, `asserts=`/`passed=`/`failed=` counts. The supported type-name tokens are `int`, `float`, `double`, `void`, `char`, `bool`; the supported relational tokens are `eq`, `ne`, `lt`, `le`, `gt`, `ge`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same spacing and capitalization as other logical operators
- follow the approximate equality formula format
