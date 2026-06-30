## Product Requirement Document

# Sequential State-Update Queue — Ordered, Resilient Single-Value State Management

## Project Goal

Build a small state-management primitive that holds a single current value and updates it by running asynchronous "update" actions strictly one at a time. Developers schedule actions that compute and publish new state; the primitive guarantees that each scheduled action runs to completion before the next one starts, so callers never have to reason about overlapping or interleaved updates. The result is a predictable, ordered stream of state transitions that UI or other observers can follow.

---

## Background & Problem

Applications frequently need to coordinate a sequence of asynchronous state changes against a single piece of state — for example, advancing through a series of computed values where each step may depend on the value produced by the previous one. Doing this by hand is error-prone: actions launched concurrently can race, partially completed updates can clobber each other, and a single failing step can silently leave the whole pipeline stuck or inconsistent.

This component solves that by serializing updates through an internal queue. Each scheduled action is an asynchronous producer that may publish one new value for the state. Actions are dequeued and executed in submission order, each fully draining before the next begins. The current value is republished only when an action actually produces a value different from the present one, yielding a clean ordered transition stream. Failures are contained: if one action throws, the failure is reported through a neutral error channel and the queue keeps going with the remaining actions, leaving the last successfully produced value in place.

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

### Feature 1: Sequential Action Queue With Ordered State Emission

**As a developer**, I want to schedule multiple state-update actions and have them run one at a time in the order I submitted them, so I can rely on a predictable, ordered stream of state transitions without worrying about races or overlap.

**Expected Behavior / Usage:**

The state holds a single integer value, starting from a given initial value. A request supplies that `initial` value and an ordered list of `actions`. Each action describes a single asynchronous step that computes the next value from the current one: a `set` action publishes a fixed `value`; a `divide` action publishes the current value truncated-divided by a given divisor `by`. Actions are processed strictly in submission order, each running to completion before the next starts. Each time an action produces a value that differs from the current state, that new value is published as a `[the specific sequence of literal prefixes used for output lines]<value>` line; if an action produces a value equal to the current state, no line is published for it. After all actions have drained, a final `[the specific sequence of literal prefixes used for output lines]<value>` line reports the settled state. Lines are emitted in execution order, each terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_sequential_updates.json`

```json
{
    "description": "Schedule a series of state-producing actions on a single-value queue, then observe the settled state stream. Each action runs to completion before the next begins, in submission order; whenever an action produces a value different from the current state, that new value is published. The observed output is the ordered list of published states followed by the final settled state. This exercises that actions are processed sequentially and that state transitions are emitted in the order the actions were submitted.",
    "cases": [
        {
            "input": {
                "initial": 0,
                "actions": [
                    {"op": "set", "value": 100},
                    {"op": "divide", "by": 2},
                    {"op": "divide", "by": 5}
                ]
            },
            "expected_output": "[the specific sequence of literal prefixes used for output lines]100\n[the specific sequence of literal prefixes used for output lines]50\n[the specific sequence of literal prefixes used for output lines]10\n[the specific sequence of literal prefixes used for output lines]10\n"
        }
    ]
}
```

---

### Feature 2: Resilient Processing — Recovery After A Failing Action

**As a developer**, I want a single failing action to be contained rather than break the whole pipeline, so that the queue reports the failure neutrally and still runs every remaining action with the last good state preserved.

**Expected Behavior / Usage:**

When one of the scheduled actions raises a runtime error during execution (for example, a truncating division by zero, which is an undefined arithmetic operation), the queue does not crash, abort, or stop processing. The failure is reported exactly once as a neutral category line of the form `[the specific sequence of literal prefixes used for output lines]<category>` — for an undefined division the category is `division_by_zero` — and the error carries no host-language or runtime-specific identity. The failed action publishes no new state, so the current value is left unchanged by it. Every action scheduled after the failing one still runs normally. The output interleaves `[the specific sequence of literal prefixes used for output lines]<value>` lines and the `[the specific sequence of literal prefixes used for output lines]<category>` line in the exact order events occur, and ends with a `[the specific sequence of literal prefixes used for output lines]<value>` line that reflects the value produced by the last action that succeeded. Each line is terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_error_recovery.json`

```json
{
    "description": "Schedule a series of actions where one of them fails at runtime (an arithmetic operation that is undefined, such as a truncating division by zero). The failing action does not tear down the queue or halt processing: the failure is reported once as a neutral error category, the current state is left unchanged by the failed action, and every subsequent action still runs. The observed output interleaves published states and the normalized error in execution order, ending with the final settled state which reflects the last successful action. This exercises resilient sequential processing and recovery after a failing action.",
    "cases": [
        {
            "input": {
                "initial": 0,
                "actions": [
                    {"op": "set", "value": 100},
                    {"op": "divide", "by": 0},
                    {"op": "divide", "by": 2}
                ]
            },
            "expected_output": "[the specific sequence of literal prefixes used for output lines]100\n[the specific error category string — query the error handler module for valid categories]\n[the specific sequence of literal prefixes used for output lines]50\n[the specific sequence of literal prefixes used for output lines]50\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the single-value sequential update queue described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic (the queue, its ordering guarantees, its emission-on-change behavior, and its error-containment hook) must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It receives a single JSON request describing an `initial` value and an ordered list of `actions` (`set` with a `value`, or `divide` with a divisor `by`), drives the core queue accordingly, observes the published state transitions and any contained failure, and prints the resulting `[the specific sequence of literal prefixes used for output lines]<value>` / `[the specific sequence of literal prefixes used for output lines]<category>` / `[the specific sequence of literal prefixes used for output lines]<value>` lines to stdout, matching the per-feature contracts above. All translation of native runtime errors into neutral `[the specific sequence of literal prefixes used for output lines]<category>` lines happens in this adapter layer; the core remains free to raise idiomatic errors.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- store the raw stdout output following the existing test result directory convention
- pad the filename suffix to ensure exactly 3 digits using the library's standard numeric padding function
