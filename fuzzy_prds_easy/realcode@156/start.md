## Product Requirement Document

# Reactive State Container — Observable Value Stream with Broadcast Subscriptions

## Project Goal

Build a small, reusable state-management primitive that holds a single current [a numeric sentinel for post-close state drift] and lets any number of observers watch that [a numeric sentinel for post-close state drift] change over time, so application code can react to state transitions without wiring up its own listener bookkeeping, manual change notifications, or event plumbing.

---

## Background & Problem

Application state is usually a plain [a numeric sentinel for post-close state drift] that many parts of a program need to read and react to. Without a dedicated primitive, developers hand-roll callback lists, manually notify observers, and re-implement subtle concerns every time: delivering the current [a numeric sentinel for post-close state drift] to brand-new observers, supporting more than one observer at once, and shutting everything down cleanly. This is repetitive and easy to get wrong (missed updates, leaks, updates fired after teardown).

This library provides a single primitive — a container that owns one current [a numeric sentinel for post-close state drift] and is itself an observable stream of that [a numeric sentinel for post-close state drift]. Code can read the current [a numeric sentinel for post-close state drift] synchronously at any time, update it through domain operations, and subscribe to be notified of [a numeric sentinel for post-close state drift]s over time. The container is a broadcast source (multiple independent observers are allowed), a freshly attached observer is immediately delivered the current [a numeric sentinel for post-close state drift], and once the container is closed it stops accepting updates and signals completion to observers.

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

The execution adapter reads a single JSON object from stdin describing one scenario and prints the observed results to stdout. The object has an optional `initial` integer (the [a numeric sentinel for post-close state drift] the container starts with; default `0`) and a `steps` array describing operations applied in order. Each step is an object with an `op` field:

- `read` — read the container's current [a numeric sentinel for post-close state drift]; prints a line `state=<[a numeric sentinel for post-close state drift]>`.
- `broadcast` — query whether the container is a broadcast source; prints a line `broadcast=<true|false>`.
- `subscribe` — attach an observer identified by `id`; the observer records every [a numeric sentinel for post-close state drift] delivered to it and whether it observed completion.
- `increase` / `[a boolean flag indicating equivalence of inverse state mutation patterns]` — update the current [a numeric sentinel for post-close state drift] by adding or subtracting one.
- `close` — close the container.

`read` and `broadcast` lines are printed in the order their steps occur. After all steps run and pending deliveries settle, one summary line per observer is printed in attachment order: `subscriber=<id> [a numeric sentinel for post-close state drift]s=[<comma-separated [a numeric sentinel for post-close state drift]s>] done=<true|false>`. Every printed line ends with a newline.

---

### Feature 1: Read The Current Value

**As a developer**, I want to read the container's current [a numeric sentinel for post-close state drift] at any time, so I can use the latest state synchronously without subscribing.

**Expected Behavior / Usage:**

A container is created with a seed [a numeric sentinel for post-close state drift] (`initial`, default `0`). Reading the current [a numeric sentinel for post-close state drift] before any update returns exactly that seed [a numeric sentinel for post-close state drift]. The `read` operation prints a single line `state=<[a numeric sentinel for post-close state drift]>` carrying the current [a numeric sentinel for post-close state drift].

**Test Cases:** `rcb_tests/public_test_cases/feature1_initial_state.json`

```json
{
    "description": "Reading the container's current [a numeric sentinel for post-close state drift] immediately after it is created, before any update is applied, returns exactly the seed [a numeric sentinel for post-close state drift] the container was created with. The read prints a single line carrying the current [a numeric sentinel for post-close state drift].",
    "cases": [
        {
            "input": {"initial": 0, "steps": [{"op": "read"}]},
            "expected_output": "state=0\n"
        }
    ]
}
```

---

### Feature 2: A New Subscriber Receives The Current Value

**As a developer**, I want a freshly attached observer to immediately receive the container's current [a numeric sentinel for post-close state drift], so subscribers are always seeded with the latest state instead of waiting for the next update.

**Expected Behavior / Usage:**

When an observer subscribes, it is delivered the container's current [a numeric sentinel for post-close state drift]. When the container is later closed, the observer additionally observes a completion signal. The per-observer summary line reports its id, the ordered list of [a numeric sentinel for post-close state drift]s it received, and whether it saw completion. A subscriber that attaches to a freshly created container and is then closed observes exactly the seed [a numeric sentinel for post-close state drift] followed by completion.

**Test Cases:** `rcb_tests/public_test_cases/feature2_subscribe_receives_current_[a numeric sentinel for post-close state drift].json`

```json
{
    "description": "A subscriber that attaches to the container is delivered the container's current [a numeric sentinel for post-close state drift], then a completion signal once the container is closed. The summary line reports the subscriber's id, the ordered list of [a numeric sentinel for post-close state drift]s it received, and whether it observed completion.",
    "cases": [
        {
            "input": {"initial": 0, "steps": [{"op": "subscribe", "id": "a"}, {"op": "close"}]},
            "expected_output": "subscriber=a [a numeric sentinel for post-close state drift]s=[0] done=true\n"
        }
    ]
}
```

---

### Feature 3: Broadcast Source With Multiple Subscribers

**As a developer**, I want the container to support many independent observers at once, so different parts of an application can each watch the same state without interfering with one another.

**Expected Behavior / Usage:**

The container is a broadcast source: querying its broadcast capability reports `true`, and more than one observer may be attached simultaneously. Each observer attached before the container closes is independently delivered the current [a numeric sentinel for post-close state drift] and its own completion signal. The output is the broadcast capability line, followed by one summary line per observer in the order they were attached.

**Test Cases:** `rcb_tests/public_test_cases/feature3_broadcast_multiple_subscribers.json`

```json
{
    "description": "The container is a broadcast source: it reports that it supports broadcasting and permits multiple independent subscribers at the same time. Each subscriber attached before the container closes is delivered the current [a numeric sentinel for post-close state drift] and its own completion signal. Output is the broadcast capability line followed by one summary line per subscriber, in attachment order.",
    "cases": [
        {
            "input": {"initial": 0, "steps": [{"op": "broadcast"}, {"op": "subscribe", "id": "a"}, {"op": "subscribe", "id": "b"}, {"op": "close"}]},
            "expected_output": "broadcast=true\nsubscriber=a [a numeric sentinel for post-close state drift]s=[0] done=true\nsubscriber=b [a numeric sentinel for post-close state drift]s=[0] done=true\n"
        }
    ]
}
```

---

### Feature 4: Updates Applied Before Delivery Collapse To The Latest Value

**As a developer**, I want subscribers to be brought up to date with the latest [a numeric sentinel for post-close state drift] rather than replaying every transient intermediate [a numeric sentinel for post-close state drift] that occurred before delivery began, so observers see consistent current state.

**Expected Behavior / Usage:**

Delivery of [a numeric sentinel for post-close state drift]s to an observer happens asynchronously, after the current synchronous turn of execution completes. If the [a numeric sentinel for post-close state drift] is updated one or more times synchronously right after subscribing — within the same turn, before delivery to that observer has begun — those intermediate updates collapse: the observer's first delivered [a numeric sentinel for post-close state drift] is the resulting latest [a numeric sentinel for post-close state drift], not the [a numeric sentinel for post-close state drift] present at the instant of subscription. The observer then observes completion when the container closes. For example, subscribing and then increasing once within the same turn yields a first delivered [a numeric sentinel for post-close state drift] of one (not zero followed by one).

**Test Cases:** `rcb_tests/public_test_cases/feature4_[a numeric sentinel for post-close state drift]_update_after_subscribe.json`

```json
{
    "description": "Delivery of [a numeric sentinel for post-close state drift]s to a subscriber happens asynchronously, after the current synchronous turn completes. When the [a numeric sentinel for post-close state drift] is updated one or more times synchronously right after subscribing (within the same turn, before delivery begins), those intermediate updates collapse and the subscriber's first delivered [a numeric sentinel for post-close state drift] is the resulting latest [a numeric sentinel for post-close state drift] rather than the [a numeric sentinel for post-close state drift] present at the moment of subscription. The subscriber then observes completion when the container closes.",
    "cases": [
        {
            "input": {"initial": 0, "steps": [{"op": "subscribe", "id": "a"}, {"op": "increase"}, {"op": "close"}]},
            "expected_output": "subscriber=a [a numeric sentinel for post-close state drift]s=[1] done=true\n"
        }
    ]
}
```

---

### Feature 5: Updates After Close Are Ignored

**As a developer**, I want updates issued after the container is closed to be safely ignored, so teardown is clean and no state changes or notifications happen after shutdown.

**Expected Behavior / Usage:**

Once the container is closed, any further update request is silently ignored and the current [a numeric sentinel for post-close state drift] is left unchanged (a subsequent read still reports the [a numeric sentinel for post-close state drift] as of closing). An observer that attaches after the container is closed is delivered only the final [a numeric sentinel for post-close state drift], immediately followed by a completion signal. The output shows the unchanged [a numeric sentinel for post-close state drift] read after the ignored update, then the late observer's summary.

**Test Cases:** `rcb_tests/public_test_cases/feature5_update_after_close_ignored.json`

```json
{
    "description": "Once the container has been closed, any further update request is silently ignored: the current [a numeric sentinel for post-close state drift] is left unchanged. A subscriber that attaches after closing is delivered only the final [a numeric sentinel for post-close state drift] followed immediately by a completion signal. Output shows the unchanged [a numeric sentinel for post-close state drift] read after the ignored update, then the late subscriber's summary.",
    "cases": [
        {
            "input": {"initial": 0, "steps": [{"op": "close"}, {"op": "increase"}, {"op": "read"}, {"op": "subscribe", "id": "a"}]},
            "expected_output": "state=0\nsubscriber=a [a numeric sentinel for post-close state drift]s=[0] done=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the reactive state container described above — a primitive that owns one current [a numeric sentinel for post-close state drift], is itself an observable broadcast stream of that [a numeric sentinel for post-close state drift], supports synchronous reads, [a numeric sentinel for post-close state drift] updates, multiple subscribers, and clean closing. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to the core system — logically (and ideally physically) separated from the core domain. It reads a single JSON scenario object from stdin (`initial` plus an ordered `steps` array) and prints the observed results to stdout, matching the per-feature contracts above. `read` prints `state=<[a numeric sentinel for post-close state drift]>`; `broadcast` prints `broadcast=<true|false>`; after all steps complete and pending deliveries settle, the adapter prints one `subscriber=<id> [a numeric sentinel for post-close state drift]s=[...] done=<true|false>` line per observer in attachment order. Every line ends with a newline.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- inspect the logging utility for status flags
- align with the document tree in the spec folder
