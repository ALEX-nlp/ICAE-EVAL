## Product Requirement Document

# Callable Expression Reconstruction - Convert Compiled Logic into Queryable Forms

## Project Goal

Build a callable expression reconstruction library that allows developers to convert compiled routines, computed record members, and routine bodies into inspectable query expressions without manually rewriting the same logic in expression form.

---

## Background & Problem

Without this library, developers are forced to maintain duplicate versions of business logic: one callable version for normal execution and one symbolic version for query providers or expression-based tooling. This leads to repetitive code, stale translations, and query predicates that drift away from the actual business rules.

With this library, developers can write ordinary callable logic once, then reconstruct an equivalent symbolic representation for filtering, ordering, projection, and inspection while preserving the externally visible result of the original callable logic.

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

### Feature 1: Scalar Expression Reconstruction

**As a developer**, I want to reconstruct compiled scalar transformations as symbolic expressions, so I can inspect or pass those transformations to expression-based consumers while retaining the callable result.

**Expected Behavior / Usage:**

The adapter accepts a request for scalar callable reconstruction. The input identifies the scalar transformation category and supplies any sample values needed to execute the callable. The output MUST include the reconstructed symbolic expression, a stable debug hash for the expression shape, and the callable result for the supplied values. Supported scalar samples include identity, integer arithmetic, integer remainder, integer shift with masked shift count, boolean negation, and mixed object-to-text concatenation.

**Test Cases:** `rcb_tests/public_test_cases/feature1_scalar_expression_reconstruction.json`

```json
{
    "description": "Compiled scalar transformations are reconstructed as symbolic expressions and still evaluate to the same scalar result for the supplied values.",
    "cases": [
        {
            "input": {
                "scenario": "decompile_function",
                "expression": "identity",
                "value": "alpha"
            },
            "expected_output": "expression=o\ndebug_hash=62bc3bd4\nresult=alpha\n"
        }
    ]
}
```

---

### Feature 2: Null and Conditional Expression Reconstruction

**As a developer**, I want null-aware and branch-based compiled logic to reconstruct into symbolic expressions, so I can preserve fallback and branch semantics in expression consumers.

**Expected Behavior / Usage:**

The adapter accepts a request for null-aware or conditional callable reconstruction. The input identifies the expression category and provides nullable values, branch values, or text values as appropriate. The output MUST include the reconstructed symbolic expression, a stable debug hash, and the result for the supplied input. Null fallback, nullable equality, conditional choice, short-circuit checks, and nullable yes/no mapping must preserve the same externally visible result as the compiled callable.

**Test Cases:** `rcb_tests/public_test_cases/feature2_null_and_conditional_reconstruction.json`

```json
{
    "description": "Compiled null-aware and conditional transformations are reconstructed without changing their branch and fallback behavior for the supplied values.",
    "cases": [
        {
            "input": {
                "scenario": "decompile_function",
                "expression": "nullable fallback",
                "value": null
            },
            "expected_output": "expression=(x ?? 100)\n[an arbitrary but consistent debug hash]\nresult=100\n"
        }
    ]
}
```

---

### Feature 3: Collection Expression Reconstruction

**As a developer**, I want collection construction and lookup callables to reconstruct as symbolic expressions, so I can verify collection-shaped logic without executing hidden implementation details.

**Expected Behavior / Usage:**

The adapter accepts a collection reconstruction request. The input identifies whether the sample covers array creation, list initialization, or keyed lookup, and supplies any value needed by the callable. The output MUST include the reconstructed symbolic expression, a stable debug hash, and the resulting collection or looked-up value. Collection output uses bracketed comma-separated values for arrays and lists, and plain text for lookup results.

**Test Cases:** `rcb_tests/public_test_cases/feature3_collection_expression_reconstruction.json`

```json
{
    "description": "Compiled collection construction and indexed lookup operations are reconstructed as symbolic expressions and preserve the resulting collection or lookup value.",
    "cases": [
        {
            "input": {
                "scenario": "decompile_collection",
                "expression": "array with parameter",
                "value": 8
            },
            "expected_output": "expression=new [] {x, 2, 3, 4}\ndebug_hash=0651bbc0\nresult=[8,2,3,4]\n"
        }
    ]
}
```

---

### Feature 4: Query Computed Member Inlining

**As a developer**, I want query predicates and orderings that refer to computed record members to be expanded into their underlying field operations, so query providers can see translatable expressions instead of opaque computed members.

**Expected Behavior / Usage:**

The adapter accepts an inline-query request containing records, a target match value, and a computed expression category. The output MUST include the rewritten query expression and the matched records after executing that query. Rewritten query output must show framework-observable query operators such as `Where` and `OrderBy`, and must show that computed full-text, affixed full-text, numeric-text, boolean, and ordering expressions have been expanded to field-level operations rather than bypassing the query pipeline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_query_computed_member_inlining.json`

```json
{
    "description": "Query predicates and ordering expressions that refer to computed record fields are expanded into the underlying field operations before the query executes.",
    "cases": [
        {
            "input": {
                "scenario": "inline_query",
                "expression": "computed full text property",
                "match": "Ada Lovelace",
                "records": [
                    {
                        "first": "Ada",
                        "last": "Lovelace"
                    },
                    {
                        "first": "Grace",
                        "last": "Hopper"
                    }
                ]
            },
            "expected_output": "query_expression=records.Where(p => (((p.First + \" \") + p.Last) == target))\nmatched=Ada Lovelace\n"
        }
    ]
}
```

---

### Feature 5: Method Body Reconstruction

**As a developer**, I want standalone routine bodies to reconstruct into symbolic callable functions, so I can inspect control flow, output-slot parsing, and assignments from routine bodies.

**Expected Behavior / Usage:**

The adapter accepts a method-body reconstruction request. The input identifies the body shape and supplies sample text values when the reconstructed function is executable. The output MUST include the reconstructed expression and, when applicable, a stable debug hash plus execution results for each supplied value. Output-slot parsing must produce parsed numbers or a fallback; assignment bodies must expose the reconstructed assignment expression and ordered assignment steps for multi-assignment bodies.

**Test Cases:** `rcb_tests/public_test_cases/feature5_method_body_reconstruction.json`

```json
{
    "description": "Standalone routine bodies are reconstructed into callable symbolic functions, including output-slot parsing and assignment statements.",
    "cases": [
        {
            "input": {
                "scenario": "decompile_method_body",
                "expression": "parse with output slot",
                "values": [
                    "123",
                    "bad",
                    "999"
                ]
            },
            "expected_output": "expression=s => {var Param_0; ... }\ndebug_hash=8cbf20fc\nresult[123]=123\n[internal mapping format for bad inputs]\nresult[999]=999\n"
        }
    ]
}
```

---

### Feature 6: Configuration Lifecycle

**As a developer**, I want the reconstruction engine configuration to have a predictable lifecycle, so application startup can rely on default behavior or install one explicit configuration safely.

**Expected Behavior / Usage:**

The adapter accepts a configuration lifecycle request. The default-instance case MUST report that no configuration existed before first access and that first access supplies the default kind. The custom-instance case MUST report that the installed configuration object is the same object later used by the engine. Attempting to configure after configuration already exists MUST render a language-neutral error category and must not expose host-language exception type names or runtime-generated message suffixes.

**Test Cases:** `rcb_tests/public_test_cases/feature6_configuration_lifecycle.json`

```json
{
    "description": "The global configuration lifecycle supplies a default configuration when unset, accepts a first explicit configuration, and rejects later replacement.",
    "cases": [
        {
            "input": {
                "scenario": "configuration_lifecycle",
                "expression": "default instance"
            },
            "expected_output": "initial_configured=no\ninstance_kind=default\n"
        },
        {
            "input": {
                "scenario": "configuration_lifecycle",
                "expression": "configure twice"
            },
            "expected_output": "error=already_configured\n"
        }
    ]
}
```

---

### Feature 7: Large Predicate Optimization

**As a developer**, I want large predicate expressions to optimize within a bounded time, so expression reconstruction remains usable for long disjunction chains.

**Expected Behavior / Usage:**

The adapter accepts a predicate optimization request with a count of equality alternatives. The output MUST include the optimized symbolic predicate, the number of alternatives used to construct the input predicate, and a bounded-time signal. For the provided sample, the optimizer must complete under the stated millisecond bound and preserve all equality alternatives in the rendered predicate.

**Test Cases:** `rcb_tests/public_test_cases/feature7_large_predicate_optimization.json`

```json
{
    "description": "A large disjunction predicate is optimized quickly and returns a symbolic predicate with the same set of equality alternatives.",
    "cases": [
        {
            "input": {
                "scenario": "optimize_predicate",
                "count": 27
            },
            "expected_output": "optimized_expression=(((((((((((((((((((((((((((p.Id == 1) OrElse (p.Id == 2)) OrElse (p.Id == 3)) OrElse (p.Id == 4)) OrElse (p.Id == 5)) OrElse (p.Id == 6)) OrElse (p.Id == 7)) OrElse (p.Id == 8)) OrElse (p.Id == 9)) OrElse (p.Id == 10)) OrElse (p.Id == 11)) OrElse (p.Id == 12)) OrElse (p.Id == 13)) OrElse (p.Id == 14)) OrElse (p.Id == 15)) OrElse (p.Id == 16)) OrElse (p.Id == 17)) OrElse (p.Id == 18)) OrElse (p.Id == 19)) OrElse (p.Id == 20)) OrElse (p.Id == 21)) OrElse (p.Id == 22)) OrElse (p.Id == 23)) OrElse (p.Id == 24)) OrElse (p.Id == 25)) OrElse (p.Id == 26)) OrElse (p.Id == 27))\ninput_disjuncts=27\ncompleted_under_ms=1000\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same recursion depth as the parser module uses for lambda nodes
- apply the same variable naming convention as the type inference engine
