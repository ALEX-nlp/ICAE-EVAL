## Product Requirement Document

# Architecture Rule Engine — Express, Evaluate and Report Structural Constraints over a Compiled Code Model

## Project Goal

Build a rule engine that lets developers express structural constraints about a body of code ("which parts are allowed to depend on or call which other parts") and automatically evaluate those constraints against a model of that code, producing a precise, human-readable violation report. This lets teams encode and enforce architecture decisions as executable checks instead of relying on manual code review.

---

## Background & Problem

Software projects accumulate structural rules that are easy to state but hard to enforce: a domain layer must not reach into infrastructure, a reporting component must not call into a low-level data-access component, and so on. Without tooling, these rules live only in documentation and erode over time, because nothing fails when someone introduces a forbidden dependency or method call.

This engine turns such rules into checks over a **code model**: a set of types (classes), the members declared in them, and the structural relations between them (one type *depends on* another when it references it as a field type, parameter type, base type, or inside a method body; one method *calls* another when its body invokes it). A caller selects a group of elements (a set of classes, or all methods declared in a set of classes), states a constraint they must satisfy, and asks the engine to evaluate it. The engine returns a report that either confirms every selected element satisfied the rule, or lists exactly which elements violated it and why.

The request, the constraint, and the resulting report form a stable black-box contract (described below), independent of how the model is built or stored.

---

## The Analysed Code Model (fixed sample corpus)

All rules in this document are evaluated against one fixed sample corpus. A conforming implementation must analyse a code model containing exactly the following types and relations, and must identify each type by its fully-qualified name (`Namespace.TypeName`). Method members are identified by a fully-qualified signature of the form `ReturnType DeclaringType::MethodName(ParamType1,ParamType2,...)`, where every type is written by its fully-qualified name and `ReturnType` is the runtime void type for methods that return nothing.

- `[the fully qualified paths of classes in the sample corpus that define the dependency graph]` — has a method that takes an integer and returns a string. Depends on nothing else in the corpus.
- `[the fully qualified paths of classes in the sample corpus that define the dependency graph]` — has a method `Load` that takes an integer and returns a string (`System.String [the fully qualified paths of classes in the sample corpus that define the dependency graph]::Load(System.Int32)`). Depends on nothing else in the corpus.
- `SampleApp.Domain.Customer` — a plain domain type with a name and a greeting method. Depends on nothing else in the corpus.
- `[the fully qualified paths of classes in the sample corpus that define the dependency graph]` — holds and is constructed with a `[the fully qualified paths of classes in the sample corpus that define the dependency graph]`, and one of its methods invokes that database. As a result `[the fully qualified paths of classes in the sample corpus that define the dependency graph]` **depends on** `[the fully qualified paths of classes in the sample corpus that define the dependency graph]`.
- `[a specific fully-qualified class name in the sample corpus]` — its method `Generate` takes a `[the fully qualified paths of classes in the sample corpus that define the dependency graph]` and invokes that repository's `Load` method. As a result the method `System.Void [a specific fully-qualified class name in the sample corpus]::Generate([the fully qualified paths of classes in the sample corpus that define the dependency graph])` **calls** `System.String [the fully qualified paths of classes in the sample corpus that define the dependency graph]::Load(System.Int32)`.
- `SampleApp.Services.AuditService` — its method does not call any method declared in the corpus types above.

---

## Request & Report Contract

The execution adapter reads a single JSON request from stdin. A request has two parts:

- `scope` — which elements to constrain. `scope.kind` is either `"types"` (constrain a set of classes) or `"methods"` (constrain every method member declared in a set of classes). `scope.members` is a non-empty array of fully-qualified class names.
- `constraint` — the rule the scoped elements must satisfy. `constraint.kind` selects the constraint family (see features). `constraint.targets` is a non-empty array of fully-qualified class names whose meaning depends on the constraint family.

The adapter evaluates the rule against the sample corpus and writes a **report** to stdout:

- If every selected element satisfies the constraint, the report is exactly the text `All Evaluations passed` (no trailing newline).
- If at least one selected element violates the constraint, the report begins with the rule's own sentence wrapped in double quotes and followed by ` failed:` and a newline. Then, for each violating element, a line consisting of a single tab character followed by that element's violation description and a newline. The block ends with one additional empty line (a final newline). The violation descriptions and the exact wording of the rule sentence are shown in the per-feature examples below and are part of the contract.

If the request is malformed, names an element kind or constraint the engine does not support, or references a class name that is not present in the corpus, the adapter emits a neutral error line instead of a report: `error=<category>` followed by a newline, and for an unknown class name an additional `type=<name>` line. Categories include `invalid_request`, `unknown_scope`, `unknown_constraint`, and `unknown_type`.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension (new constraint families) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Dependency Constraints

**As a developer**, I want to forbid a chosen set of classes from depending on certain other classes, so I can keep layers and components decoupled.

**Expected Behavior / Usage:**

The `scope.kind` is `"types"` and `scope.members` lists the classes whose dependencies are being constrained. A class is considered to *depend on* another whenever it references that other class in any structural position (field type, constructor or method parameter type, base type, or a reference inside a method body). The constraint forbids the scoped classes from depending on a forbidden set of classes; the forbidden set can be specified in two equivalent ways, described in the sub-features. When a scoped class does depend on a forbidden class, its violation description is `<offending class full name> does depend on <forbidden class full name>`. When no scoped class depends on any forbidden class, the report is `All Evaluations passed`.

*1.1 Forbid dependency on explicitly named classes — the forbidden classes are listed directly.*

`constraint.kind` is `"no_dependency_on_types"` and `constraint.targets` lists the forbidden classes directly. The rule sentence reads `Classes that are "<scoped>" should not depend on "<forbidden>"`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_forbidden_type_dependency.json`

```json
{
    "description": "A rule selects one or more named classes from the analysed code model and forbids them from depending, in any way (field types, parameter types, base types, method-body references, etc.), on one or more explicitly named target classes. The engine evaluates the rule against the fixed sample corpus and renders a report. When a selected class does have a forbidden dependency, the report contains the quoted rule sentence followed by a tab-indented violation line of the form '<full name of offending class> does depend on <full name of forbidden class>'. When no selected class has the forbidden dependency, the report is the single line stating all evaluations passed.",
    "cases": [
        {
            "input": {
                "scope": {"kind": "types", "members": ["[the fully qualified paths of classes in the sample corpus that define the dependency graph]"]},
                "constraint": {"kind": "no_dependency_on_types", "targets": ["[the fully qualified paths of classes in the sample corpus that define the dependency graph]"]}
            },
            "expected_output": "\"Classes that are \"[the fully qualified paths of classes in the sample corpus that define the dependency graph]\" should not depend on \"[the fully qualified paths of classes in the sample corpus that define the dependency graph]\"\" failed:\n\t[the fully qualified paths of classes in the sample corpus that define the dependency graph] does depend on [the fully qualified paths of classes in the sample corpus that define the dependency graph]\n\n"
        },
        {
            "input": {
                "scope": {"kind": "types", "members": ["SampleApp.Domain.Customer"]},
                "constraint": {"kind": "no_dependency_on_types", "targets": ["[the fully qualified paths of classes in the sample corpus that define the dependency graph]"]}
            },
            "expected_output": "All Evaluations passed"
        }
    ]
}
```

*1.2 Forbid dependency on classes matching an identity predicate — the forbidden set is described as "types that are <named classes>".*

`constraint.kind` is `"no_dependency_on_types_matching"` and `constraint.targets` lists the classes that make up the forbidden set, but the rule is phrased in terms of a predicate over the model. This constrains exactly the same dependency relation as 1.1, but the rule sentence reads `Classes that are "<scoped>" should not depend on any types that are "<forbidden>"`. The violation description is identical to 1.1.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_forbidden_dependency_by_identity.json`

```json
{
    "description": "A rule selects one or more named classes and forbids them from depending on any class that satisfies an identity predicate (the forbidden set is described by 'types that are <named classes>' rather than by passing the classes directly). Behaviourally this constrains the same dependency relation as the direct-target form, but the rule sentence is phrased in terms of the predicate. The engine evaluates against the fixed sample corpus: a selected class with a forbidden dependency yields the quoted rule sentence and a tab-indented '<offending class> does depend on <forbidden class>' line; otherwise the report states all evaluations passed.",
    "cases": [
        {
            "input": {
                "scope": {"kind": "types", "members": ["[the fully qualified paths of classes in the sample corpus that define the dependency graph]"]},
                "constraint": {"kind": "no_dependency_on_types_matching", "targets": ["[the fully qualified paths of classes in the sample corpus that define the dependency graph]"]}
            },
            "expected_output": "\"Classes that are \"[the fully qualified paths of classes in the sample corpus that define the dependency graph]\" should not depend on any types that are \"[the fully qualified paths of classes in the sample corpus that define the dependency graph]\"\" failed:\n\t[the fully qualified paths of classes in the sample corpus that define the dependency graph] does depend on [the fully qualified paths of classes in the sample corpus that define the dependency graph]\n\n"
        },
        {
            "input": {
                "scope": {"kind": "types", "members": ["SampleApp.Domain.Customer"]},
                "constraint": {"kind": "no_dependency_on_types_matching", "targets": ["[the fully qualified paths of classes in the sample corpus that define the dependency graph]"]}
            },
            "expected_output": "All Evaluations passed"
        }
    ]
}
```

---

### Feature 2: Method-Call Constraints

**As a developer**, I want to forbid the methods declared in a chosen set of classes from calling the methods declared in certain other classes, so I can prevent components from reaching into one another at the call level.

**Expected Behavior / Usage:**

The `scope.kind` is `"methods"` and `scope.members` lists the classes whose declared methods are being constrained; the scope is every method member declared in those classes. `constraint.kind` is `"no_call_to_methods_in"` and `constraint.targets` lists the classes whose declared methods may not be called. A method *calls* another when its body invokes it. The rule sentence reads `Method members that are declared in "<scoped>" should not call Method members that are declared in "<forbidden>"`. When a scoped method invokes a forbidden method, its violation description names both methods by their fully-qualified signatures: `<caller signature> does call <callee signature>`, where a signature is `ReturnType DeclaringType::Name(ParamTypes)`. When no scoped method calls any forbidden method, the report is `All Evaluations passed`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_forbidden_method_call.json`

```json
{
    "description": "A rule selects all method members declared in one or more named classes and forbids them from calling any method member declared in one or more named target classes. The engine evaluates against the fixed sample corpus and renders a report. When a selected method calls a forbidden method, the report contains the quoted rule sentence followed by a tab-indented violation line naming both methods by their full IL-style signatures, of the form '<return-type> <caller-signature> does call <return-type> <callee-signature>'. When no selected method calls any forbidden method, the report is the single line stating all evaluations passed.",
    "cases": [
        {
            "input": {
                "scope": {"kind": "methods", "members": ["[a specific fully-qualified class name in the sample corpus]"]},
                "constraint": {"kind": "no_call_to_methods_in", "targets": ["[the fully qualified paths of classes in the sample corpus that define the dependency graph]"]}
            },
            "expected_output": "\"Method members that are declared in \"[a specific fully-qualified class name in the sample corpus]\" should not call Method members that are declared in \"[the fully qualified paths of classes in the sample corpus that define the dependency graph]\"\" failed:\n\tSystem.Void [a specific fully-qualified class name in the sample corpus]::Generate([the fully qualified paths of classes in the sample corpus that define the dependency graph]) does call System.String [the fully qualified paths of classes in the sample corpus that define the dependency graph]::Load(System.Int32)\n\n"
        },
        {
            "input": {
                "scope": {"kind": "methods", "members": ["SampleApp.Services.AuditService"]},
                "constraint": {"kind": "no_call_to_methods_in", "targets": ["[the fully qualified paths of classes in the sample corpus that define the dependency graph]"]}
            },
            "expected_output": "All Evaluations passed"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the rule engine described above — a code model of types and their members, the dependency and call relations between them, a way to select a scope of elements, constraint families that can be evaluated against the model, and a report renderer. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, builds the corresponding scope and constraint, evaluates it against the fixed sample corpus, and prints the resulting report (or a neutral error line) to stdout, matching the per-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same non-printable character separator as the 'pagination' utility component
