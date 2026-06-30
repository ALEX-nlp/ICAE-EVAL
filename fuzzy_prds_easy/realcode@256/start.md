## Product Requirement Document

# Type-Erased Polymorphic Container — Run-Time Dispatch Without Inheritance

## Project Goal

Build a reusable polymorphic container that can hold any object satisfying a declared set of behaviors and dispatch operations to it at run time, so developers can write polymorphic code without forcing every concrete type to inherit from a common base class.

---

## Background & Problem

The classic way to treat different concrete types uniformly is inheritance: every participating type must derive from an abstract base and override its virtual methods. This is intrusive — types you do not own (standard containers, third-party classes, closures, primitive values) cannot be retrofitted with a base class — and it couples the abstraction tightly to the implementation hierarchy.

This library inverts that. A *facade* declares the behaviors an abstraction needs (a named operation, possibly with several overloads, possibly optional). A *container* parameterized by a facade can then hold **any** object that provides those behaviors, regardless of its type or origin, and forwards calls to the held object at run time. The held object may be supplied by value, through an allocator, or as a borrowed pointer; the container's observable behavior is the same. The library additionally supports declaring an operation as optional (with a well-defined fallback when the held object lacks it) and recovering the stored object back out by its run-time type.

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

### Feature 1: Polymorphic Dispatch Over Heterogeneous Held Types

**As a developer**, I want one container type that can hold any object exposing the operations my abstraction needs and dispatch to it at run time, so I can treat unrelated concrete types uniformly without a shared base class.

**Expected Behavior / Usage:**

The abstraction declares two operations: a *render* operation that writes a textual form of the held object to an output sink, and a *measure* operation that returns a numeric value and is declared non-throwing. Several unrelated concrete kinds implement these operations independently, with no common base type. The input is a request whose `action` is `render_shape` and whose `command` is a single space-separated string naming a kind followed by its numeric parameters. The adapter parses the command, places a freshly built object of the named kind into the container, then invokes the render operation followed by the measure operation and emits one line of the form `shape = <rendered text>, area = <measure>`. All numeric output (both inside the rendered text and the measure) is formatted in fixed-point notation with exactly five fractional digits. Recognized kinds and their parameter counts: a rectangle taking a width and a height (rendered as `{Rectangle: width = W, height = H}`, measured as the product), a circle taking a radius (rendered as `{Circle: radius = R}`, measured as pi times the radius squared), and a point taking no parameters (rendered as `{Point}`, measured as zero). A command naming an unrecognized kind, or a recognized kind with the wrong number of parameters, is rejected: the adapter emits `error=invalid_command` followed by a line `command=<the raw command>`. The held object may be provided by value, via an allocator, or as a borrowed pointer — this choice has no effect on the observable output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_polymorphic_dispatch.json`

```json
{
    "description": "Build a single polymorphic container that can hold any object exposing a textual-render operation and a numeric-measure operation, then drive both operations through the container. A command string names which concrete kind of object to place inside (and supplies its parameters); unrelated kinds with no shared base type are all accepted by the same container. After the container is populated, its render operation writes a textual form of the held object and its measure operation returns a numeric value; the two are combined into one line. Numeric values are emitted in fixed-point notation with five fractional digits. A command that names an unknown kind, or supplies the wrong number of parameters, is rejected as an invalid command.",
    "cases": [
        {
            "input": {"action": "render_shape", "command": "Rectangle 2 3"},
            "expected_output": "shape = {Rectangle: width = 2.00000, height = 3.00000}, area = 6.00000\n"
        },
        {
            "input": {"action": "render_shape", "command": "Triangle 2 3"},
            "expected_output": "error=invalid_command\ncommand=Triangle 2 3\n"
        }
    ]
}
```

---

### Feature 2: Overloaded Operation Routed By Argument Arity

**As a developer**, I want a single named operation on the abstraction to carry multiple overloads, so callers can invoke the same operation with different argument shapes and have the right implementation selected.

**Expected Behavior / Usage:**

The abstraction declares one named logging operation with two overloads: one taking just a message, and one taking a message plus an error description. The input is a request whose `action` is `log` and whose `entries` is an ordered array of log entries; each entry has a `message`, and may additionally carry an `error`. The container is populated with an implementation that appends rendered lines to an internal buffer. For each entry, an entry with only a message is routed to the one-argument overload and rendered as `[INFO] <message>`; an entry that also carries an `error` is routed to the two-argument overload and rendered as `[ERROR] <message> (exception info: <error>)`. Lines are produced in the order the entries are supplied, each terminated by a newline, and the full accumulated buffer is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature2_overloaded_operation.json`

```json
{
    "description": "A single named operation on the container carries two overloads distinguished by how many arguments are supplied. A sequence of log entries is fed through the container; each entry with only a message is routed to the one-argument overload and rendered as an informational line, while an entry that also carries an error description is routed to the two-argument overload and rendered as an error line that embeds the error description. The held implementation accumulates every rendered line in order, and the full accumulated text is emitted.",
    "cases": [
        {
            "input": {"action": "log", "entries": [{"message": "hello"}]},
            "expected_output": "[INFO] hello\n"
        },
        {
            "input": {"action": "log", "entries": [{"message": "hello"}, {"message": "world", "error": "runtime error!"}]},
            "expected_output": "[INFO] hello\n[ERROR] world (exception info: runtime error!)\n"
        }
    ]
}
```

---

### Feature 3: Optional Operation With Capability Fallback

**As a developer**, I want to declare an operation on the abstraction as optional, so the container can hold backing objects that do not all provide it and degrade gracefully instead of failing to compile or crashing.

**Expected Behavior / Usage:**

The abstraction declares a positional keyed-lookup operation as *optional*: the container can be populated with backing collections regardless of whether they natively provide that operation. The input is a request whose `action` is `lookup`, with a `backing` selecting which kind of collection to hold and an `index` to look up. An `indexed` backing is a collection that natively supports positional keyed access; looking up a present index returns the stored element and the adapter emits `value=<element>`. A `sequential` backing is a collection that does NOT provide positional keyed access; attempting the lookup must not crash or return a wrong result — instead the framework raises a neutral not-supported signal, which the adapter renders as `error=not_supported` followed by a line `operation=lookup`. The two backings are seeded so that index `0` resolves to `hello` and index `1` to `world` on the indexed backing.

**Test Cases:** `rcb_tests/public_test_cases/feature3_optional_operation.json`

```json
{
    "description": "The container declares a keyed-lookup operation as optional rather than mandatory, so it can hold backing collections that do not all provide that operation. When the held collection natively supports positional keyed lookup, looking up a key returns the stored element. When the held collection does not provide that operation, the lookup does not crash or silently misbehave; instead the framework reports a neutral not-supported signal naming the attempted operation. The chosen backing collection determines which path is taken.",
    "cases": [
        {
            "input": {"action": "lookup", "backing": "indexed", "index": 0},
            "expected_output": "value=hello\n"
        },
        {
            "input": {"action": "lookup", "backing": "sequential", "index": 0},
            "expected_output": "error=not_supported\noperation=lookup\n"
        }
    ]
}
```

---

### Feature 4: Run-Time Type Recovery

**As a developer**, I want to query and recover the concrete value a container is holding, so I can get the original object back out when I know its type and detect when I do not.

**Expected Behavior / Usage:**

*4.1 Stored-Type Inspection — report a tag for the kind of value currently held*

When type-recovery support is enabled, the container can report a tag describing what it currently holds, independent of the actual value. The input is a request whose `action` is `inspect_type` with a `stored` field that is either a whole number to place into the container or `null` for an empty container. A container holding a whole-number value reports `type=integer`; an empty container reports `type=empty`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_stored_type.json`

```json
{
    "description": "The container can report a tag describing the kind of value it currently holds. When the container is populated with a whole-number value, it reports an integer tag. When the container holds nothing at all, it reports an empty tag. The tag reflects only whether and what kind of value is stored, independent of the concrete value.",
    "cases": [
        {
            "input": {"action": "inspect_type", "stored": null},
            "expected_output": "type=empty\n"
        },
        {
            "input": {"action": "inspect_type", "stored": 123},
            "expected_output": "type=integer\n"
        }
    ]
}
```

*4.2 Value Recovery By Expected Type — return the stored value, or reject a mismatch*

Recovering the stored value requires naming the type it was stored as. The input is a request whose `action` is `recover_value`, with a `stored` field (a whole number or `null`) and an `expect` field naming the expected type (`integer` for a whole number, `real` for a fractional number). When the expected type matches the stored value's type, recovery succeeds and the adapter emits `value=<recovered value>`. When the expected type does not match the stored value's type, recovery is rejected: the adapter emits `error=type_mismatch` followed by a line `expected=<the expected type name>`. Attempting to recover from an empty container is likewise rejected as a type mismatch.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_recover_value.json`

```json
{
    "description": "A stored value can be recovered out of the container only by naming the type it was stored as. When the expected type matches the stored value's type, recovery succeeds and yields the original value. When the expected type does not match the stored value's type, recovery is rejected with a neutral type-mismatch error that echoes the expected type. Attempting to recover from an empty container is likewise rejected as a type mismatch.",
    "cases": [
        {
            "input": {"action": "recover_value", "stored": 123, "expect": "integer"},
            "expected_output": "value=123\n"
        },
        {
            "input": {"action": "recover_value", "stored": 123, "expect": "real"},
            "expected_output": "error=type_mismatch\nexpected=real\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the polymorphic container and the facade/abstraction machinery described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting output to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `render_shape` builds a container from a command string and renders the held object; `log` feeds a sequence of entries through an overloaded operation; `lookup` exercises an optional operation over different backing collections; `inspect_type` and `recover_value` query and recover the stored value by its run-time type. Native failures raised by the core (the optional-operation fallback and the type-recovery mismatch) MUST be translated by the adapter into the neutral `error=<category>` lines specified above; the core domain itself must remain free of stdout/JSON concerns.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- validate against the same whitelist logic used for primitive types
