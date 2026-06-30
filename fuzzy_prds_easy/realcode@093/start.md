## Product Requirement Document

# Dependency Injection Container — Type-Driven Provide & Resolve

## Project Goal

Build a dependency-injection container that lets developers register providers for the values their program needs and then resolve those values automatically by type, so collaborators are wired together on demand without hand-written construction and bookkeeping code.

---

## Background & Problem

Without a container, developers wire objects together by hand: every component must know how to build each of its collaborators, in the right order, threading shared instances through long constructor chains. This produces repetitive, fragile boilerplate, makes it hard to swap implementations, and forces manual ordering of construction whenever the dependency graph changes.

With this container, developers instead register *providers*. A provider declares which type(s) of value it produces and which type(s) it needs as inputs. When a consumer asks the container for a value, the container locates the provider for that type, recursively resolves the provider's own inputs, constructs the value, caches it, and hands it back. The container guarantees each value is built at most once, supports distinguishing several values of the same type by name, lets a request opt into tolerating a missing value, and refuses to wire a graph that contains a cycle. Construction failures and misuse are reported as neutral, well-defined error categories rather than vague faults.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., graph storage, resolution, validation, error reporting), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core container.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core resolution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

The container is exercised through a *scenario*: an object with a `steps` array. Each step is one operation against a single shared container and produces exactly one output line (newline-terminated), in order. There are two operations:

- A `provide` step registers a provider. It declares `out` (the list of produced keys, each `{type, name?, value?}`) and optionally `in` (its dependency requests, each `{type, name?, optional?}`), an optional default `value`, and an optional `fails` flag. Types are identified by short string ids (`"A"`, `"B"`, …). On success the step emits `provide ok keys=<comma-separated keys>`, where a key is the bare `type`, or `type:name` when named. On rejection it emits `provide error=<category>`.
- An `invoke` step runs a consumer that requests values. It declares `in` (its requests). On success it emits `invoke ok ` followed by, for each request in order, `<key>=<payload>` (space-separated), where `<payload>` is the integer carried by the received instance, or `nil` for an absent optional value. On failure it emits `invoke error=<category>` (with an extra `key=<key>` field for a missing dependency).

Each produced instance carries an integer payload so consumers can observe exactly which instance they received. A produced key takes its payload from its own `value`, else the provider's default `value`, else (when neither is given) the number of times that provider has constructed so far.

### Feature 1: Register Providers And Resolve Values By Type

**As a developer**, I want to register providers and then resolve values by their type, so collaborators (including multi-level dependency chains) are constructed and wired automatically.

**Expected Behavior / Usage:**

A `provide` step makes the declared `out` type(s) resolvable; if it lists `in` requests, those are this provider's dependencies. An `invoke` step requests one or more types; the container constructs each on demand, first resolving that provider's own dependencies (transitively), and the consumer reports the payload of every received instance in request order. A chain where C depends on B and B depends on A resolves fully when any of them is requested.

**Test Cases:** `rcb_tests/public_test_cases/feature1_provide_and_invoke.json`

```json
{
    "description": "Register one or more providers with the container, then run a consumer that requests values by their declared types. A provider declares the type(s) it produces and the type(s) it depends on; the container constructs each requested value on demand, resolving a provider's dependencies first (transitively). Each produced instance carries an integer payload, and the consumer reports, for each requested type in request order, the payload of the instance it received. This shows direct resolution and multi-level dependency chains where a requested value's provider depends on values produced by other providers.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A", "value": 5}]},
                {"op": "invoke", "in": [{"type": "A"}]}
            ]},
            "expected_output": "provide ok keys=A\ninvoke ok A=5\n"
        },
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A", "value": 1}]},
                {"op": "provide", "out": [{"type": "B", "value": 2}], "in": [{"type": "A"}]},
                {"op": "provide", "out": [{"type": "C", "value": 3}], "in": [{"type": "B"}]},
                {"op": "invoke", "in": [{"type": "A"}, {"type": "B"}, {"type": "C"}]}
            ]},
            "expected_output": "provide ok keys=A\nprovide ok keys=B\nprovide ok keys=C\ninvoke ok A=1 B=2 C=3\n"
        }
    ]
}
```

---

### Feature 2: One Provider Producing Multiple Types

**As a developer**, I want a single provider to contribute several distinct types at once, so one registration can populate the graph with a group of related values.

**Expected Behavior / Usage:**

A `provide` step whose `out` lists several keys registers all of them; the success line lists every produced key. Afterwards a consumer may request any subset of those keys, in any order, and receives each instance's payload.

**Test Cases:** `rcb_tests/public_test_cases/feature2_multiple_outputs.json`

```json
{
    "description": "A single provider may declare several distinct produced types at once; registering it makes every one of those types resolvable from the container. The provide step lists all produced keys, and a later consumer can request any subset of them in any order, receiving each instance's payload. This shows that one registration can populate the graph with multiple independent types.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A", "value": 10}, {"type": "B", "value": 20}]},
                {"op": "invoke", "in": [{"type": "A"}, {"type": "B"}]}
            ]},
            "expected_output": "provide ok keys=A,B\ninvoke ok A=10 B=20\n"
        }
    ]
}
```

---

### Feature 3: Singleton Caching

**As a developer**, I want each resolved value to be constructed at most once and reused thereafter, so the container behaves like a singleton registry and avoids redundant construction.

**Expected Behavior / Usage:**

The first time a type is needed its provider runs and the result is cached; every later request returns the cached instance without re-running the provider. To make this observable, a provider that omits an explicit `value` stamps each constructed instance with the running count of its own constructions (1, 2, 3, …). Because the value is cached, the provider runs once, so repeated consumers all observe payload `1`; an implementation that re-ran the provider per request would instead yield increasing payloads.

**Test Cases:** `rcb_tests/public_test_cases/feature3_singleton_cache.json`

```json
{
    "description": "Resolved values are cached and effectively behave as singletons: a provider runs at most once, and every later request for the same type returns the already-constructed instance. To make the construction count observable, this provider omits an explicit payload; in that case the produced instance carries the number of times the provider has constructed so far (1 on the first construction, 2 on the second, and so on). Because the value is cached after the first construction, repeated consumers all observe the payload 1 — a provider that re-ran on every request would instead yield increasing payloads.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A"}]},
                {"op": "invoke", "in": [{"type": "A"}]},
                {"op": "invoke", "in": [{"type": "A"}]}
            ]},
            "expected_output": "provide ok keys=A\ninvoke ok A=1\ninvoke ok A=1\n"
        }
    ]
}
```

---

### Feature 4: Optional Dependencies

**As a developer**, I want a request to opt into tolerating a missing value, so a consumer can run with reduced functionality instead of failing when an optional collaborator is absent.

**Expected Behavior / Usage:**

A request may set `optional: true`. If no provider exists for that type, resolution does not fail; the consumer receives an absent value, reported as `nil`, and still runs. If the type is provided, the consumer receives its payload exactly as a required request would.

**Test Cases:** `rcb_tests/public_test_cases/feature4_optional_dependency.json`

```json
{
    "description": "A dependency request may be marked optional. When an optional type has no provider in the container, resolution does not fail; the consumer receives an absent value (reported as nil) and still runs. When the optional type IS provided, the consumer receives its payload as normal. This lets a consumer tolerate missing collaborators instead of failing outright.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "invoke", "in": [{"type": "A", "optional": true}]}
            ]},
            "expected_output": "invoke ok A=nil\n"
        },
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A", "value": 7}]},
                {"op": "invoke", "in": [{"type": "A", "optional": true}]}
            ]},
            "expected_output": "provide ok keys=A\ninvoke ok A=7\n"
        }
    ]
}
```

---

### Feature 5: Named Values Of The Same Type

**As a developer**, I want to register and request several values of the same type under distinct names, so I can keep multiple instances of one type side by side and select the right one.

**Expected Behavior / Usage:**

A produced key may carry a `name`, forming the key `type:name`. Several names of the same type coexist, and a named key is independent of the unnamed key of that type (both may exist at once). A request selects by both type and name. Name matching is exact and case-sensitive: requesting a name that differs only in case matches nothing and fails with a missing-dependency error naming the requested `type:name`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_named_values.json`

```json
{
    "description": "Several instances of the same type can coexist in the container when each is given a distinct name; a request then selects an instance by both its type and name. A named key (type:name) and an unnamed key of the same type are independent and may both be present at once. Name matching is exact and case-sensitive, so requesting a name that differs only in letter case finds no matching instance and resolution fails with a missing-dependency error naming the requested type:name.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A", "name": "first", "value": 1}, {"type": "A", "name": "second", "value": 2}, {"type": "A", "name": "third", "value": 3}]},
                {"op": "invoke", "in": [{"type": "A", "name": "first"}, {"type": "A", "name": "third"}]}
            ]},
            "expected_output": "provide ok keys=A:first,A:second,A:third\ninvoke ok A:first=1 A:third=3\n"
        },
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A", "name": "CamelCase", "value": 1}]},
                {"op": "invoke", "in": [{"type": "A", "name": "camelcase"}]}
            ]},
            "expected_output": "provide ok keys=A:CamelCase\ninvoke error=missing_dependency key=A:camelcase\n"
        }
    ]
}
```

---

### Feature 6: Cycle Detection

**As a developer**, I want the container to reject a dependency graph that contains a cycle, so I learn about unsatisfiable wiring at registration time rather than through infinite resolution.

**Expected Behavior / Usage:**

The graph must stay acyclic. Providers register normally until one would close a loop (directly, or through a chain of other providers); that provide step is rejected and reports a cycle error. Earlier, still-acyclic registrations succeed.

**Test Cases:** `rcb_tests/public_test_cases/feature6_cycle_detection.json`

```json
{
    "description": "The dependency graph must remain acyclic. Registration of a provider whose dependencies would close a cycle (directly or through a chain of other providers) is rejected, and the offending provide step reports a cycle error. Earlier providers that did not yet complete a loop register normally; only the provide that introduces the cycle fails.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A"}], "in": [{"type": "C"}]},
                {"op": "provide", "out": [{"type": "B"}], "in": [{"type": "A"}]},
                {"op": "provide", "out": [{"type": "C"}], "in": [{"type": "B"}]}
            ]},
            "expected_output": "provide ok keys=A\nprovide ok keys=B\nprovide error=cycle\n"
        }
    ]
}
```

---

### Feature 7: Error Reporting

**As a developer**, I want misuse and resolution failures reported as neutral, well-defined categories, so failures are explicit and easy to handle.

**Expected Behavior / Usage:**

*7.1 Missing required dependency — a required request with no provider fails*

When a consumer requests a required (non-optional) type that has no provider, resolution fails with `invoke error=missing_dependency key=<key>`, where `<key>` is the bare type, or `type:name` when named. If several required dependencies are missing, one of them is named.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_missing_dependency.json`

```json
{
    "description": "When a consumer requests a required (non-optional) type for which no provider exists, resolution fails with a missing-dependency error that names the unsatisfied key. The key is the bare type when unnamed, or type:name when a name was requested. If several required dependencies are missing, the error names one of them.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "invoke", "in": [{"type": "B"}]}
            ]},
            "expected_output": "invoke error=missing_dependency key=B\n"
        }
    ]
}
```

*7.2 Duplicate type — a type may have only one provider*

Each key may be produced by only one provider. Registering a second provider for a key already in the container is rejected with `provide error=duplicate_type`; the first registration stays in effect.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_duplicate_type.json`

```json
{
    "description": "Each type key may be produced by only one provider. Registering a second provider for a type that is already in the container is rejected; the duplicate provide step reports a duplicate-type error while the first registration remains in effect.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A", "value": 1}]},
                {"op": "provide", "out": [{"type": "A", "value": 2}]}
            ]},
            "expected_output": "provide ok keys=A\nprovide error=duplicate_type\n"
        }
    ]
}
```

*7.3 Constructor failure — a provider that fails during construction*

A provider may report a failure at construction time (`fails: true`). Registration still succeeds, because providers run lazily. When a consumer needs (directly or transitively) a value whose provider fails during construction, resolution aborts with `invoke error=constructor_failed` and the consumer body does not run.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_constructor_error.json`

```json
{
    "description": "A provider may fail at construction time by reporting an error. Registration itself still succeeds, because the provider is only run when its value is actually needed. When a consumer (directly or transitively) requires a value whose provider fails during construction, resolution is aborted and the consumer reports a constructor-failed error; the consumer body is not run.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "provide", "out": [{"type": "A"}], "fails": true},
                {"op": "invoke", "in": [{"type": "A"}]}
            ]},
            "expected_output": "provide ok keys=A\ninvoke error=constructor_failed\n"
        }
    ]
}
```

*7.4 Invalid provide target — a provider must be a constructor*

A provider must be a callable that produces values. Registering a null provider fails with `provide error=nil_constructor`; registering a non-callable value fails with `provide error=not_a_constructor`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_4_invalid_provide_target.json`

```json
{
    "description": "A provider must be supplied as a constructor (a callable that produces values). Registering an absent/null provider, or a plain value that is not callable, is rejected up front. A null provider reports a nil-constructor error; any non-callable value reports a not-a-constructor error.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "provide", "target": "nil"}
            ]},
            "expected_output": "provide error=nil_constructor\n"
        },
        {
            "input": {"steps": [
                {"op": "provide", "target": "object"}
            ]},
            "expected_output": "provide error=not_a_constructor\n"
        }
    ]
}
```

*7.5 Invalid invoke target — a consumer must be a callable*

The consumer passed to an invocation must itself be callable. A null target fails with `invoke error=nil_function`; a non-callable target fails with `invoke error=not_a_function`. Neither performs any resolution.

**Test Cases:** `rcb_tests/public_test_cases/feature7_5_invalid_invoke_target.json`

```json
{
    "description": "The consumer passed to an invocation must itself be a callable. Invoking with an absent/null target reports a nil-function error, and invoking with a value that is not callable reports a not-a-function error. Neither attempts any dependency resolution.",
    "cases": [
        {
            "input": {"steps": [
                {"op": "invoke", "target": "nil"}
            ]},
            "expected_output": "invoke error=nil_function\n"
        },
        {
            "input": {"steps": [
                {"op": "invoke", "target": "non_function"}
            ]},
            "expected_output": "invoke error=not_a_function\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the container described above (graph storage, type/named keys, lazy construction with caching, optional resolution, cycle detection, and error modeling). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON scenario object from stdin, executes each step in order against one shared container, and prints exactly one line per step to stdout, matching the per-feature contracts above. The adapter is responsible for translating the abstract type ids and step declarations into idiomatic container calls and for normalizing any native construction/validation failures into the neutral `provide error=<category>` / `invoke error=<category>` lines defined here.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same naming convention as the registry keys
