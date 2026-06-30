## Product Requirement Document

# Expression Graph Evaluation Engine - Standardized Expression Evaluation Contracts

## Project Goal

Build an expression evaluation library that allows developers to query, transform, and update structured object graphs using compact string expressions without hand-writing repetitive traversal, conversion, and invocation code.

---

## Background & Problem

Without this library/tool, developers are forced to manually walk nested objects, maps, arrays, and collections; coerce values between scalar and container types; call helper behavior explicitly; and duplicate conditional or filtering logic across application code. This leads to repetitive boilerplate, inconsistent conversion behavior, fragile null and index handling, and maintenance issues whenever the shape of the object graph changes.

With this library/tool, developers can provide an expression and a root fixture or variable context, then receive a deterministic value or normalized error report from a single evaluation interface.

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

### Feature 1: Literal Values

**As a developer**, I want to parse literal expressions into typed scalar or list values, so I can write constants directly in expressions and receive their value without manual parsing.

**Expected Behavior / Usage:**

An input command supplies an expression and a fixture name. For literal-only expressions, the fixture may be `none`. The adapter prints two lines: `kind=<value category>` and `result=<normalized value>`. Numbers, booleans, strings, nulls, and list literals must be preserved with deterministic rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature1_literals.json`

```json
{
    "description": "Literal parsing returns typed scalar and list values.",
    "cases": [
        {
            "input": {
                "expression": "12345",
                "fixture": "none"
            },
            "expected_output": "kind=number\nresult=12345\n"
        },
        {
            "input": {
                "expression": "0x100",
                "fixture": "none"
            },
            "expected_output": "kind=number\nresult=256\n"
        },
        {
            "input": {
                "expression": "\"hello world\"",
                "fixture": "none"
            },
            "expected_output": "kind=string\nresult=\"hello world\"\n"
        },
        {
            "input": {
                "expression": "null",
                "fixture": "none"
            },
            "expected_output": "kind=null\nresult=null\n"
        },
        {
            "input": {
                "expression": "{ false, true, null, 0, 1. }",
                "fixture": "none"
            },
            "expected_output": "kind=list\n[the precursor to the serialization format — ask the PM for the exact string]\n"
        }
    ]
}
```

---

### Feature 2: Arithmetic and Logical Evaluation

**As a developer**, I want to evaluate arithmetic, comparison, membership, and conditional expressions, so I can combine simple values in expressions without writing separate imperative code.

**Expected Behavior / Usage:**

An input command supplies an expression and optional fixture. Arithmetic must respect precedence and parentheses. Comparisons and membership tests return booleans. Conditional expressions must only evaluate the chosen branch, so unreachable invalid arithmetic does not fail when the condition selects the safe branch. The adapter prints the value category and normalized result.

**Test Cases:** `rcb_tests/public_test_cases/feature2_arithmetic_logic.json`

```json
{
    "description": "Arithmetic, comparison, membership, and conditional expressions produce evaluated values.",
    "cases": [
        {
            "input": {
                "expression": "5+2*3",
                "fixture": "none"
            },
            "expected_output": "kind=number\nresult=11\n"
        },
        {
            "input": {
                "expression": "(5+2)*3",
                "fixture": "none"
            },
            "expected_output": "kind=number\nresult=21\n"
        },
        {
            "input": {
                "expression": "5/2.",
                "fixture": "none"
            },
            "expected_output": "kind=number\nresult=2.5\n"
        },
        {
            "input": {
                "expression": "5<2",
                "fixture": "none"
            },
            "expected_output": "kind=boolean\nresult=false\n"
        },
        {
            "input": {
                "expression": "null in {true,false,null}",
                "fixture": "none"
            },
            "expected_output": "kind=boolean\nresult=true\n"
        },
        {
            "input": {
                "expression": "true ? 1 : 1/0",
                "fixture": "none"
            },
            "expected_output": "kind=number\nresult=1\n"
        }
    ]
}
```

---

### Feature 3: Scoped Variables

**As a developer**, I want to use scoped variables inside a single evaluation, so I can store intermediate values and supply external context data.

**Expected Behavior / Usage:**

An input command may include a `variables` object whose keys become expression variables. Expressions may also assign intermediate variables and reuse them later in the same evaluation. The adapter prints the evaluated value category and result after all expression steps complete.

**Test Cases:** `rcb_tests/public_test_cases/feature3_context_variables.json`

```json
{
    "description": "Context variables can be read, assigned, and reused inside one expression.",
    "cases": [
        {
            "input": {
                "expression": "#name in {\"Greenland\", \"Austin\", \"Africa\", \"Rome\"}",
                "fixture": "none",
                "variables": {
                    "name": "Austin"
                }
            },
            "expected_output": "kind=boolean\nresult=true\n"
        },
        {
            "input": {
                "expression": "#f=5, #s=6, #f + #s",
                "fixture": "simple"
            },
            "expected_output": "kind=number\nresult=11\n"
        },
        {
            "input": {
                "expression": "#six=(#five=5, 6), #five + #six",
                "fixture": "simple"
            },
            "expected_output": "kind=number\nresult=11\n"
        }
    ]
}
```

---

### Feature 4: Object and Container Navigation

**As a developer**, I want to navigate object graphs and container roots from expressions, so I can read and update structured data consistently.

**Expected Behavior / Usage:**

*4.1 Object Graph Navigation — Navigate nested object, map, and indexed data in a provided sample graph.*

An input command uses the `sample` fixture to evaluate an expression against a representative object graph. Property names, map keys, nested indexes, first/last element selectors, and conditional expressions must resolve through the graph. The output is the normalized category and value that a caller observes from evaluating the expression.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_property_navigation.json`

```json
{
    "description": "Nested properties, map entries, index aliases, and conditional property expressions resolve against a sample object graph.",
    "cases": [
        {
            "input": {
                "expression": "map[\"size\"]",
                "fixture": "sample"
            },
            "expected_output": "kind=number\nresult=5000\n"
        },
        {
            "input": {
                "expression": "map.array[0]",
                "fixture": "sample"
            },
            "expected_output": "kind=number\nresult=1\n"
        },
        {
            "input": {
                "expression": "map.list[2]",
                "fixture": "sample"
            },
            "expected_output": "kind=array\nresult=[1,2,3,4]\n"
        },
        {
            "input": {
                "expression": "map[^]",
                "fixture": "sample"
            },
            "expected_output": "kind=number\nresult=99\n"
        },
        {
            "input": {
                "expression": "map[$].(#this == null ? 'empty' : #this)",
                "fixture": "sample"
            },
            "expected_output": "kind=string\nresult=\"empty\"\n"
        },
        {
            "input": {
                "expression": "disabled ? 'disabled' : 'othernot'",
                "fixture": "sample"
            },
            "expected_output": "kind=string\nresult=\"disabled\"\n"
        }
    ]
}
```

---

*4.2 Collection and Array Access — Access and update indexed or iterable container roots.*

An input command selects an array or collection fixture. Expressions can read length, access an indexed element, traverse an iterator, and assign to an indexed element when `set_to` is present. Assignment output includes the value before and after setting, each with its category, so conversion behavior is externally visible.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_collection_array_access.json`

```json
{
    "description": "Array and collection roots expose length, iterator, indexed access, and assignment with conversion.",
    "cases": [
        {
            "input": {
                "expression": "length",
                "fixture": "string_array"
            },
            "expected_output": "kind=number\nresult=2\n"
        },
        {
            "input": {
                "expression": "[1]",
                "fixture": "string_array"
            },
            "expected_output": "kind=string\nresult=\"world\"\n"
        },
        {
            "input": {
                "expression": "[1]",
                "fixture": "int_array"
            },
            "expected_output": "kind=number\nresult=20\n"
        },
        {
            "input": {
                "expression": "[1]",
                "fixture": "int_array",
                "set_to": "50"
            },
            "expected_output": "before_kind=number\nbefore=20\nafter_kind=number\nafter=50\n"
        },
        {
            "input": {
                "expression": "size",
                "fixture": "list"
            },
            "expected_output": "kind=number\nresult=2\n"
        },
        {
            "input": {
                "expression": "#it = iterator, #it.next, #it.next, #it.hasNext",
                "fixture": "list"
            },
            "expected_output": "kind=boolean\nresult=false\n"
        }
    ]
}
```

---

### Feature 5: Projection and Selection

**As a developer**, I want to project and filter collection-like values, so I can derive lists from an object graph using expression predicates.

**Expected Behavior / Usage:**

An input command evaluates an expression that projects or selects over a collection-like value in the sample fixture. Full selection returns all matching values, first-match selection returns a one-item list containing the first match, and last-match selection returns a one-item list containing the last match. The result must be rendered as a deterministic normalized list or boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature5_projection_selection.json`

```json
{
    "description": "Projection and selection operators transform arrays and lists into selected result lists.",
    "cases": [
        {
            "input": {
                "expression": "map.array.{? #this > 2 }",
                "fixture": "sample"
            },
            "expected_output": "kind=list\nresult=[3,4]\n"
        },
        {
            "input": {
                "expression": "map.array.{^ #this > 2 }",
                "fixture": "sample"
            },
            "expected_output": "kind=list\nresult=[3]\n"
        },
        {
            "input": {
                "expression": "map.array.{$ #this > 2 }",
                "fixture": "sample"
            },
            "expected_output": "kind=list\nresult=[4]\n"
        },
        {
            "input": {
                "expression": "map.array[*].{?true} instanceof java.util.Collection",
                "fixture": "sample"
            },
            "expected_output": "kind=boolean\nresult=true\n"
        }
    ]
}
```

---

### Feature 6: Composite Value Construction

**As a developer**, I want to construct lists, maps, and arrays from expressions, so I can create structured values inline and pass them through the evaluator.

**Expected Behavior / Usage:**

An input command evaluates an expression that constructs a composite value. List construction preserves order, map construction preserves key/value associations with deterministic output ordering, and array construction converts literal elements to the requested element type. The adapter prints `kind` as `list`, `map`, or `array` and renders the structure recursively.

**Test Cases:** `rcb_tests/public_test_cases/feature6_composite_construction.json`

```json
{
    "description": "List, map, and array construction expressions create structured values with converted element values.",
    "cases": [
        {
            "input": {
                "expression": "{'1','2','3'}",
                "fixture": "none"
            },
            "expected_output": "kind=list\nresult=[\"1\",\"2\",\"3\"]\n"
        },
        {
            "input": {
                "expression": "#{ \"foo\" : \"bar\" }",
                "fixture": "sample"
            },
            "expected_output": "kind=map\nresult={\"foo\":\"bar\"}\n"
        },
        {
            "input": {
                "expression": "#{ \"foo\", \"bar\" : \"baz\"  }",
                "fixture": "sample"
            },
            "expected_output": "kind=map\nresult={\"bar\":\"baz\",\"foo\":null}\n"
        },
        {
            "input": {
                "expression": "new String[] { \"one\", \"two\" }",
                "fixture": "sample"
            },
            "expected_output": "kind=array\n[the map array literal string used for test cases]\n"
        },
        {
            "input": {
                "expression": "new Integer[] { \"1\", 2, \"3\" }",
                "fixture": "sample"
            },
            "expected_output": "kind=array\nresult=[1,2,3]\n"
        }
    ]
}
```

---

### Feature 7: Method, Static, and Constructor Calls

**As a developer**, I want to invoke accessible behavior and constructors from expressions, so I can compose navigation with callable operations when reading object graph data.

**Expected Behavior / Usage:**

An input command may call accessible zero-argument or argument-taking operations on the fixture, invoke allowed static-style helpers, or construct an object and then call behavior on it. The result is printed using the same normalized category and value format as other evaluations.

**Test Cases:** `rcb_tests/public_test_cases/feature7_methods_static_constructors.json`

```json
{
    "description": "Expressions may invoke accessible instance behavior, static behavior, and constructors as part of evaluation.",
    "cases": [
        {
            "input": {
                "expression": "isDisabled()",
                "fixture": "simple"
            },
            "expected_output": "kind=boolean\nresult=true\n"
        },
        {
            "input": {
                "expression": "isThisVarArgsWorking()",
                "fixture": "simple"
            },
            "expected_output": "kind=boolean\nresult=true\n"
        },
        {
            "input": {
                "expression": "getValueIsTrue(!false) ? \"\" : \"here\"",
                "fixture": "simple"
            },
            "expected_output": "kind=string\nresult=\"\"\n"
        },
        {
            "input": {
                "expression": "@@max(3,4)",
                "fixture": "sample"
            },
            "expected_output": "kind=number\nresult=4\n"
        },
        {
            "input": {
                "expression": "new java.lang.StringBuffer().append(55).toString()",
                "fixture": "sample"
            },
            "expected_output": "kind=string\nresult=\"55\"\n"
        }
    ]
}
```

---

### Feature 8: Normalized Error Reporting

**As a developer**, I want to receive stable error categories for invalid input, so I can handle failures without depending on host runtime exception names.

**Expected Behavior / Usage:**

When parsing or evaluation fails for malformed syntax or an invalid construction form, the adapter must not print host-language exception class names, stack traces, or runtime-generated messages. It prints only a language-neutral category line such as `error=syntax` so black-box tests can compare failures deterministically.

**Test Cases:** `rcb_tests/public_test_cases/feature8_errors.json`

```json
{
    "description": "Malformed or invalid expressions are reported with normalized language-neutral error categories.",
    "cases": [
        {
            "input": {
                "expression": "\"hello world",
                "fixture": "none"
            },
            "expected_output": "error=syntax\n"
        },
        {
            "input": {
                "expression": "\"hello\\x world\"",
                "fixture": "none"
            },
            "expected_output": "error=syntax\n"
        },
        {
            "input": {
                "expression": "new Object[4] { #root, #this }",
                "fixture": "sample"
            },
            "expected_output": "error=syntax\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_literals.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_literals@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- follow the same ordering convention as the headers module
- apply the null-safe projection pattern defined in C017 with predicate inversion
