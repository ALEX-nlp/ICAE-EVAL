## Product Requirement Document

# A Dynamic Scripting Language Interpreter — Execute Programs of a Small Dynamically-Typed Language and Capture Their Output

## Project Goal

Build an interpreter for a small, dynamically-typed scripting language so developers can run a program written as source text and observe exactly what it prints, without needing a separate compiler, build step, or external runtime. The interpreter parses the source, evaluates it top to bottom, and emits everything the program writes to standard output.

---

## Background & Problem

Embedding scripting behavior into a tool usually means either pulling in a heavyweight third-party runtime or hand-writing an ad-hoc evaluator that only understands a handful of expressions. Both paths are painful: the former is large and opaque, the latter is incomplete and inconsistent.

This project defines one cohesive interpreter for a compact dynamic language with the features programmers expect: integer, floating-point, boolean, string, array, and object values; the usual arithmetic, bitwise, comparison, and logical operators; variables and assignment; conditionals and loops with early-exit control; first-class functions with recursion; objects with fields and methods; and structured exception handling. A single built-in printing primitive is the program's window to the outside world, and a small set of normalized error reports describe the ways a run can fail. Given the same program, the interpreter always produces the same output, making it a dependable execution contract.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This language has a lexer, a parser, an evaluator, a value model, and a built-in environment — these are distinct responsibilities and should be separated accordingly.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core interpreter.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate lexing, parsing, evaluation, the value model, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The evaluator must be open for extension (new operators, new built-ins) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors (malformed source, failed assertions, exceptions that escape every handler) must be modeled properly rather than relying on generic faults, and must be reported through the normalized error contract described below.

---

## Core Features

### Feature 1: Expression Evaluation

**As a developer**, I want to evaluate arithmetic, bitwise, comparison, logical, floating-point, and type-query expressions, so I can compute values the way every general-purpose language does.

**Expected Behavior / Usage:**

A program is a sequence of statements terminated by semicolons and executed top to bottom. The built-in `print(x)` writes the textual rendering of its argument followed by a single newline. Value renderings are: an integer renders as its decimal digits (with a leading `-` when negative); a boolean renders as the lowercase word `true` or `false`; a string renders as its raw characters; a floating-point number renders with its fractional digits, or as a plain integer-looking form when it has no fractional part; the type-query operator yields a short type-name string.

*1.1 Integer arithmetic & operator precedence*

Supports `+`, `-`, `*`, the remainder operator `%`, and unary minus over 32-bit signed integers. Multiplication and remainder bind tighter than addition and subtraction; binary `+`/`-` are left-associative. Each `print` of an integer is followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_arithmetic.json`

```json
{
    "description": "Evaluate integer arithmetic expressions honoring operator precedence and unary minus, printing each computed value. Multiplication and the remainder operator bind tighter than addition and subtraction; subtraction is left-associative. Each printed integer is followed by a newline.",
    "cases": [
        {"input": {"program": "print(1 + 2 * 3);"}, "expected_output": "7\n"},
        {"input": {"program": "print(1 * 2 + 3);"}, "expected_output": "5\n"}
    ]
}
```

*1.2 Bitwise & shift operators*

Supports bitwise AND `&`, OR `|`, XOR `^`, complement `~`, left shift `<<`, and right shift `>>` over 32-bit signed integers, using two's-complement semantics.

**Test Cases:** `rcb_tests/public_test_cases/feature2_bitwise.json`

```json
{
    "description": "Evaluate bitwise and bit-shift operators on 32-bit signed integers: bitwise AND, OR, XOR, left shift, arithmetic right shift, and bitwise complement. Each result is printed on its own line.",
    "cases": [
        {"input": {"program": "print(7 & 3);"}, "expected_output": "3\n"},
        {"input": {"program": "print(5 | 2);"}, "expected_output": "7\n"}
    ]
}
```

*1.3 Comparison & logical operators*

Supports ordering comparisons (`<`, `<=`, `>`, `>=`) and equality, short-circuit conjunction `&&` and disjunction `||`, and logical negation `!`. These expressions produce a boolean, which renders as its lowercase word.

**Test Cases:** `rcb_tests/public_test_cases/feature3_logic.json`

```json
{
    "description": "Evaluate comparison and boolean-logic operators and print the resulting boolean. Supports ordering comparisons, short-circuit conjunction and disjunction, and logical negation. A boolean value renders as its lowercase word.",
    "cases": [
        {"input": {"program": "print(1 < 2);"}, "expected_output": "true\n"},
        {"input": {"program": "print(2 <= 2);"}, "expected_output": "true\n"}
    ]
}
```

*1.4 Floating-point arithmetic*

A floating-point literal is written as digits with a decimal point and a trailing `f` marker (for example `3.5f`). Floating-point values support `+`, `-`, `*`, and `/`. A floating-point result with no fractional part renders without a decimal point; otherwise its fractional digits are shown.

**Test Cases:** `rcb_tests/public_test_cases/feature4_floats.json`

```json
{
    "description": "Evaluate floating-point arithmetic and print the result. Floating-point literals are written with a trailing marker. A floating-point value that has no fractional part renders without a decimal point; otherwise the fractional digits are shown.",
    "cases": [
        {"input": {"program": "print(3.5f);"}, "expected_output": "3.5\n"},
        {"input": {"program": "print(10.0f / 4.0f);"}, "expected_output": "2.5\n"}
    ]
}
```

*1.5 Runtime type inspection*

The prefix `typeof` operator returns the type name of its operand as a string. The distinct names are `int32` for 32-bit integers, `string` for text, `bool` for booleans, and `float32` for floating-point numbers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_typeof.json`

```json
{
    "description": "Inspect the runtime type of a value with the type-query operator and print the type name. Distinct names are produced for 32-bit integers, text strings, booleans, and floating-point numbers.",
    "cases": [
        {"input": {"program": "print(typeof 1);"}, "expected_output": "int32\n"},
        {"input": {"program": "print(typeof \"s\");"}, "expected_output": "string\n"}
    ]
}
```

---

### Feature 2: String Values

**As a developer**, I want immutable text strings with length, indexing, and concatenation, so I can manipulate textual data.

**Expected Behavior / Usage:**

A string literal is written between double quotes `"..."` or single quotes `'...'`. The `.length` property reports the number of characters. Indexing with `s[i]` (zero-based) returns the single character at position `i` as a one-character string. The `+` operator concatenates two strings left to right.

**Test Cases:** `rcb_tests/public_test_cases/feature6_strings.json`

```json
{
    "description": "Operate on immutable text strings: query the character count, index a single character by zero-based position, and concatenate two strings. Indexing yields a one-character string; concatenation joins operands left to right.",
    "cases": [
        {"input": {"program": "print(\"foo\".length);"}, "expected_output": "3\n"},
        {"input": {"program": "print(\"foo\"[0]);"}, "expected_output": "f\n"}
    ]
}
```

---

### Feature 3: Array Values

**As a developer**, I want ordered, mutable, zero-indexed arrays with length, element read/write, and iteration, so I can store and process sequences.

**Expected Behavior / Usage:**

An array literal is written as `[e0, e1, ...]`. Elements are read with `a[i]` and written with `a[i] = v` (zero-based). The `.length` property reports the element count. A counting `for` loop can iterate over indices to read or accumulate values. Each printed element appears on its own line in iteration order.

**Test Cases:** `rcb_tests/public_test_cases/feature7_arrays.json`

```json
{
    "description": "Work with ordered, mutable, zero-indexed arrays: read an element by index, query the element count, assign to an element, and iterate with a counting loop while accumulating a running total. Reading or printing elements reflects the current contents.",
    "cases": [
        {"input": {"program": "var arr = [2,5,7];\n\nvar sum = 0;\n\nfor (var i = 0; i < arr.length; i = i + 1)\n{\n    print(arr[i]);\n\n    sum = sum + arr[i];\n}\n\nprint(sum);\n\nassert (sum == 14);\n"}, "expected_output": "2\n5\n7\n14\n"},
        {"input": {"program": "var a = [5, 7, 2];\nprint(a[1]);\nprint(a.length);"}, "expected_output": "7\n3\n"}
    ]
}
```

---

### Feature 4: Control Flow With Early-Exit And Skip

**As a developer**, I want conditionals and a counting loop with both an immediate-stop and a skip-to-next construct, so I can express iteration logic precisely.

**Expected Behavior / Usage:**

A `for (init; condition; update) { ... }` loop runs its body while the condition holds. Inside the body, the immediate-stop construct (`break`) terminates the loop at once, and the skip construct (`continue`) abandons the current iteration and proceeds to the next. An `if (cond) { ... } else { ... }` statement selects which branch runs. Variables declared with `var` hold mutable state; `=` reassigns. Values printed during the loop appear in execution order, and statements after the loop run once it ends.

**Test Cases:** `rcb_tests/public_test_cases/feature8_control_flow.json`

```json
{
    "description": "Drive a counting loop with early-exit and skip control: one construct stops the loop immediately, the other abandons the current iteration and proceeds to the next. Branch selection chooses which path runs each iteration; values are printed as the loop progresses and a final total is printed afterwards.",
    "cases": [
        {"input": {"program": "var sum = 0;\n\nvar odd = true;\n\nfor (var i = 1; i < 10; i = i + 1)\n{\n    if (i == 5)\n    {\n        print(\"break\");\n        break;\n    }\n\n    print(i);\n    sum = sum + i;\n}\n\nprint(sum);\nassert (sum == 10);\n"}, "expected_output": "1\n2\n3\n4\nbreak\n10\n"},
        {"input": {"program": "var sum = 0;\n\nvar odd = true;\n\nfor (var i = 1; i < 10; i = i + 1)\n{\n    if (odd)\n    {\n        odd = false;\n        continue;\n    }\n    else\n    {\n        odd = true;\n    }\n\n    print(i);\n\n    sum = sum + i;\n}\n\nprint(sum);\nassert (sum == 20);\n"}, "expected_output": "2\n4\n6\n8\n20\n"}
    ]
}
```

---

### Feature 5: First-Class Functions And Recursion

**As a developer**, I want to define functions, call them with arguments, and recurse, so I can factor and reuse logic.

**Expected Behavior / Usage:**

A function is created with `function (params) { ... }` and may be stored in a variable. Calling it with `name(args)` binds the arguments to the parameters and runs the body; `return expr` ends the call and hands `expr` back to the caller. A function may call itself, enabling recursion. The printed result is the value produced by invoking the function.

**Test Cases:** `rcb_tests/public_test_cases/feature9_functions.json`

```json
{
    "description": "Define first-class functions, call them with arguments, and use recursion. A function may call itself; control returns the computed value to the caller. The printed result is the value produced by invoking the function.",
    "cases": [
        {"input": {"program": "var fib = function (n)\n{\n    if (n < 2)\n        return n;\n\n    return fib(n-1) + fib(n-2);\n};\n\nvar r = fib(7);\n\nprint(r);\n\nassert (r == 13);\n"}, "expected_output": "13\n"},
        {"input": {"program": "var add = function (a, b) { return a + b; };\nprint(add(3, 4));"}, "expected_output": "7\n"}
    ]
}
```

---

### Feature 6: Objects With Fields And Methods

**As a developer**, I want objects with named fields and methods that receive the object as their receiver, so I can model stateful entities.

**Expected Behavior / Usage:**

An object literal is written as `{ field0: value0, field1: value1, ... }`. A field is read with `obj.field` and written with `obj.field = value`. Storing a function in a field makes it a method; invoking it with the method-call form `obj:method(args)` passes the receiver object as the implicit first parameter, so the method can read and mutate the object's own fields. Mutations performed through a method are observable on subsequent field reads. The compound assignment `+=` updates a field in place.

**Test Cases:** `rcb_tests/public_test_cases/feature10_objects.json`

```json
{
    "description": "Create objects with named fields, read and update fields, attach a function to a field, and invoke it as a method so the receiver object is passed as the implicit first argument. Mutations performed through the method are observable on subsequent field reads.",
    "cases": [
        {"input": {"program": "var counter = { count: 0 };\n\ncounter.incr = function (self)\n{\n    self.count += 1;\n};\n\ncounter:incr();\nprint(counter.count);\n\ncounter:incr();\nprint(counter.count);\n\nassert (counter.count == 2);\n"}, "expected_output": "1\n2\n"},
        {"input": {"program": "var o = { x:1, y:2 };\nprint(o.x);\nprint(o.y);\no.x = o.x + 10;\nprint(o.x);"}, "expected_output": "1\n2\n11\n"}
    ]
}
```

---

### Feature 7: Structured Exception Handling

**As a developer**, I want to raise an exception and recover from it, so I can separate error handling from normal control flow.

**Expected Behavior / Usage:**

`throw expr` raises an exception carrying the value of `expr`. A `try { ... } catch (e) { ... }` statement runs the protected block; if any statement in it (or in a function it calls, at any depth) throws, the call stack unwinds to the nearest enclosing `catch`, which binds the thrown value to its parameter and runs the handler block. After the handler completes, execution continues with the statements following the `try`/`catch`. A thrown value may be any value (for example a string or an integer expression result).

**Test Cases:** `rcb_tests/public_test_cases/feature11_exceptions.json`

```json
{
    "description": "Raise an exception and recover from it with a protected block and a handler that binds the thrown value. The thrown value propagates outward across nested function calls, unwinding the call stack until a handler catches it; execution then continues after the protected block.",
    "cases": [
        {"input": {"program": "// Test one level of stack unwinding along with a unit-level exception\n// handler. The catch variable is implemented differently for\n// unit-level functions.\n\nvar foo = function()\n{\n    throw \"foo\";\n};\n\ntry\n{\n    foo();\n}\ncatch (e)\n{\n    print('caught exception');\n    assert (e == \"foo\");\n}\n\nprint('done');\n"}, "expected_output": "caught exception\ndone\n"},
        {"input": {"program": "var leThrow = function (x)\n{\n    throw x + 1;\n};\n\nvar foo = function(x, y)\n{\n    leThrow(x);\n};\n\nvar catchFun = function()\n{\n    try\n    {\n        foo(7, 9);\n    }\n    catch (e)\n    {\n        print('caught exception');\n        assert (e == 8);\n    }\n};\n\ncatchFun();\nprint('done');\n"}, "expected_output": "caught exception\ndone\n"}
    ]
}
```

---

### Feature 8: Uncaught Exception Reporting

**As a developer**, I want an exception that escapes every handler to terminate the run with a clear, language-neutral report, so failures are unambiguous and free of host-runtime noise.

**Expected Behavior / Usage:**

When a thrown value propagates past the top level with no enclosing handler, the run ends in failure and the interpreter emits a normalized two-line report: the first line is exactly `error=uncaught_exception`, and the second line is `value=` followed by the rendering of the thrown value (the same rendering `print` would produce). No host-language type names, stack traces, or file paths appear in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature12_uncaught.json`

```json
{
    "description": "When an exception escapes every handler and reaches the top level, the run terminates with a normalized error report carrying the rendered thrown value, rather than leaking any host runtime detail.",
    "cases": [
        {"input": {"program": "// This is a regression test to verify that uncaught exceptions that\n// aren't objects are handled properly\n\nthrow \"foobar\";\n"}, "expected_output": "error=uncaught_exception\nvalue=foobar\n"},
        {"input": {"program": "throw 42;"}, "expected_output": "error=uncaught_exception\nvalue=42\n"}
    ]
}
```

---

### Feature 9: Parse-Error And Assertion Reporting

**As a developer**, I want syntactically invalid source to be rejected with a clear, normalized report before any execution, and a built-in assertion that fails loudly, so malformed or wrong programs fail fast and predictably.

**Expected Behavior / Usage:**

Before running, the interpreter reads and parses the whole source. If the source is not a syntactically valid program (for example a statement that cannot be parsed), the run ends in failure and the interpreter emits exactly the single line `error=parse_error`. No part of the program runs in this case, and no host-runtime detail (file paths, internal positions, host exception names) appears in the output. The companion check `assert(cond)` runs silently when `cond` holds and, when it does not, fails the run with the normalized line `error=assertion_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature13_parse_error.json`

```json
{
    "description": "When the supplied source text is not a syntactically valid program, the run terminates with a normalized parse-error report instead of executing anything.",
    "cases": [
        {"input": {"program": "var foo = 3;\n\nThis test will fail to parse. This is intentional.\n\nvar bif = 4;\n"}, "expected_output": "error=parse_error\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured interpreter (lexer, parser, evaluator, value model, and built-in environment) implementing the language described above. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to the core interpreter — logically (and ideally physically) separated from it. It reads a single JSON request object from stdin of the shape `{"program": "<source text>"}`, executes the program through the core interpreter, and prints to stdout exactly what the program writes via `print`, matching the per-feature contracts above. When a run fails, the adapter emits the corresponding normalized error contract instead: `error=parse_error` for malformed source; `error=assertion_failed` for a failed assertion; and the two lines `error=uncaught_exception` / `value=<rendered thrown value>` for an exception that escapes every handler. The adapter is the only place that translates failures into these neutral reports; the core may raise idiomatic errors internally but must never leak host-runtime identity into stdout.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- handle errors using the same pattern as the parser initialization
