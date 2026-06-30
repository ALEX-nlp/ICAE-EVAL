## Product Requirement Document

# Reactive Key-Value Preference — Observable Persisted Values Backed by a Key-Value Store

## Project Goal

Build a reusable abstraction that represents a single persisted value identified by a key and exposes it as an observable stream, so developers can both read/write the value and react to its changes over time without manually wiring up polling, change notifications, or default-value handling.

---

## Background & Problem

Application settings and similar small pieces of state are usually persisted in a simple key-value store. Reading such a value gives only a one-time snapshot; to keep a UI or other consumer in sync, developers end up re-reading the store on every suspected change, hand-rolling change notifications, and repeatedly substituting a fallback whenever the value is absent. This is repetitive and error-prone.

With this abstraction, a value is wrapped together with its key, its fallback (default) value, and a backing key-value store. Writing the value persists it and notifies observers; removing it deletes it from the store and reverts observers to the default; and observing the value yields the current contents immediately and then every distinct subsequent change. The wrapper deduplicates consecutive identical values and fans out every change to all active observers.

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

The execution adapter reads a single JSON request describing one scenario and replays a short sequence of operations against one persisted value, emitting a plain-text event log. The request fields are: `key` (the identifier the value is stored under; may be `null` to model a value with no key), `default` (the fallback value emitted whenever the stored value is absent), and `ops` (an ordered list of operations to perform). Each operation is an object with an `op` field; the supported operations are `observe` (attach a new observer to the value), `put` (set/persist a new value, supplied in `value`), `remove` (delete the stored value), and `preset` (a side-channel write that seeds the backing store directly **without** notifying existing observers).

The event log uses these line forms, written in execution order: `[a specific value suffix pattern — ask the PM for the exact format]` when observer number `<i>` (numbered from 0 in attachment order) receives a value; `store write key=<k> value=<v>` and `store remove key=<k>` when an operation delegates to the backing store; `put ok=<bool>` / `remove ok=<bool>` reporting whether the operation's persistence call reported success; and `error=<category> op=<op> reason=<reason>` for a rejected operation. When an observer is attached it immediately receives the value currently held in the store, or the default value when none is stored.

### Feature 1: Persist A Value And Notify Observers

**As a developer**, I want setting the value to write it to the backing store and push the new value to anyone observing it, so persisted state and live consumers stay in sync.

**Expected Behavior / Usage:**

A `put` operation persists the supplied `value` under the value's `key`. It delegates exactly one write to the backing store (observable as a `store write key=<k> value=<v>` line carrying the key and value, in operation order) and reports the persistence result as `put ok=true`. After the write, every active observer is notified and re-reads the now-current value, emitting it. An observer attached before any write first receives the default value (because the store is initially empty). Performing several `put` operations in sequence yields one store-write line and one emission per operation, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_set_value_and_notify.json`

```json
{
    "description": "Persisting a sequence of values through the value-setting operation. The store starts empty and one observer is attached, so it first receives the configured default value. Each set operation delegates the write to the backing key-value store (recording the key and the value written, in call order) and reports whether the write succeeded, and then notifies the active observer which re-reads the freshly stored value. The observer therefore sees each newly persisted value in turn.",
    "cases": [
        {
            "input": {"key": "key", "default": "default value", "ops": [
                {"op": "observe"},
                {"op": "put", "value": "value1"},
                {"op": "put", "value": "value2"},
                {"op": "put", "value": "value3"}
            ]},
            "expected_output": "emit[0] default value\nstore write key=key value=value1\nput ok=true\nemit[0] value1\nstore write key=key value=value2\nput ok=true\nemit[0] value2\nstore write key=key value=value3\nput ok=true\nemit[0] value3\n"
        }
    ]
}
```

---

### Feature 2: Remove A Value And Revert To Default

**As a developer**, I want removing the value to delete it from the backing store and have observers fall back to the default, so clearing a setting behaves predictably.

**Expected Behavior / Usage:**

A `remove` operation deletes the value's `key` from the backing store. It delegates exactly one removal (observable as a `store remove key=<k>` line) and reports the result as `remove ok=true`. Because the stored value is now absent, every active observer is notified and re-reads, emitting the default value. In a scenario where the store is preset with a value and an observer is attached, the observer first emits the preset value and then, after the removal, emits the default value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_clear_value.json`

```json
{
    "description": "Removing the stored value. The store is preset with an existing value and an observer is attached, so the observer first sees the preset value. The removal operation delegates a deletion of the key to the backing store (recorded as a remove call) and reports whether it succeeded; because the value associated with the key is now absent, the observer is notified and re-reads, seeing the configured default value.",
    "cases": [
        {
            "input": {"key": "key", "default": "default value", "ops": [
                {"op": "preset", "value": "stored value"},
                {"op": "observe"},
                {"op": "remove"}
            ]},
            "expected_output": "emit[0] stored value\nstore remove key=key\nremove ok=true\nemit[0] default value\n"
        }
    ]
}
```

---

### Feature 3: Reject Mutations On A Value With No Key

**As a developer**, I want set and remove to fail cleanly when the value has no key, so a value that cannot be persisted does not silently corrupt the store.

**Expected Behavior / Usage:**

When the value is constructed with a `null` key, both `put` and `remove` are unsupported. Each such operation fails without touching the backing store (no store line is produced) and instead emits a normalized error line `[a specific error format string — ask the PM for the exact text]`, where `<op>` is `put` or `remove`. The error is language-neutral: it names the operation category and reason rather than exposing any host runtime exception.

**Test Cases:** `rcb_tests/public_test_cases/feature3_null_key_guard.json`

```json
{
    "description": "Guarding mutating operations on a value that has no key. When the value is constructed without a key, both the set operation and the removal operation are unsupported and must fail instead of touching the store. Each attempt produces a normalized error line naming the attempted operation and the reason, and no store mutation is recorded.",
    "cases": [
        {
            "input": {"key": null, "default": "", "ops": [
                {"op": "put", "value": ""},
                {"op": "remove"}
            ]},
            "expected_output": "error=unsupported_operation op=put reason=null_key\nerror=unsupported_operation op=remove reason=null_key\n"
        }
    ]
}
```

---

### Feature 4: A New Observer Starts With The Latest Value

**As a developer**, I want each observer to immediately receive the value that is current at the moment it starts observing, so consumers never begin from a stale or empty state.

**Expected Behavior / Usage:**

Attaching an observer (`observe`) causes that observer to immediately emit the value currently held in the backing store (or the default when none is stored). A `preset` operation writes directly to the store as a side channel and does **not** notify any already-attached observer. Therefore, when the store is preset to one value then an observer is attached, then preset to a second value and another observer attached, and so on, each newly attached observer emits exactly the value present when it began observing — and earlier observers are not disturbed by later presets.

**Test Cases:** `rcb_tests/public_test_cases/feature4_starts_with_latest.json`

```json
{
    "description": "A freshly attached observer immediately receives the value currently held in the backing store. Between attachments the store is updated through a side channel that does NOT notify existing observers, so each newly attached observer (and only it) emits the value present at the moment it begins observing.",
    "cases": [
        {
            "input": {"key": "key", "default": "default value", "ops": [
                {"op": "preset", "value": "1"},
                {"op": "observe"},
                {"op": "preset", "value": "2"},
                {"op": "observe"},
                {"op": "preset", "value": "3"},
                {"op": "observe"}
            ]},
            "expected_output": "emit[0] 1\nemit[1] 2\nemit[2] 3\n"
        }
    ]
}
```

---

### Feature 5: Suppress Consecutive Duplicate Values Per Observer

**As a developer**, I want an observer to be notified only when the value actually changes, so consumers are not woken up by writes that leave the value unchanged.

**Expected Behavior / Usage:**

For a single observer, after its initial emission, a `put` triggers an emission only when the freshly re-read value differs from the last value that observer emitted. Every `put` still delegates its write to the store (each producing a `store write` line and a `put ok=true` line), but writing the same value as the current one produces no new emission. Distinct new values are each emitted once. Thus repeating the same write after the value already equals it yields one emission for the first transition and none for the following identical ones; subsequent genuinely different values are emitted one by one.

**Test Cases:** `rcb_tests/public_test_cases/feature5_no_duplicate_consecutive.json`

```json
{
    "description": "A single observer never receives the same value twice in a row. After the initial default emission, repeated set operations that write the same value still delegate every write to the store, but the observer only emits when the re-read value actually differs from the last value it emitted; consecutive identical writes produce no new emission, while each genuinely changed value is emitted once.",
    "cases": [
        {
            "input": {"key": "key", "default": "default value", "ops": [
                {"op": "observe"},
                {"op": "put", "value": "new value"},
                {"op": "put", "value": "new value"},
                {"op": "put", "value": "new value"},
                {"op": "put", "value": "another value 1"},
                {"op": "put", "value": "another value 2"},
                {"op": "put", "value": "another value 3"}
            ]},
            "expected_output": "emit[0] default value\nstore write key=key value=new value\nput ok=true\nemit[0] new value\nstore write key=key value=new value\nput ok=true\nstore write key=key value=new value\nput ok=true\nstore write key=key value=another value 1\nput ok=true\nemit[0] another value 1\nstore write key=key value=another value 2\nput ok=true\nemit[0] another value 2\nstore write key=key value=another value 3\nput ok=true\nemit[0] another value 3\n"
        }
    ]
}
```

---

### Feature 6: Broadcast Every Change To All Observers

**As a developer**, I want every active observer to receive each value change, so multiple consumers of the same value stay consistent.

**Expected Behavior / Usage:**

Multiple observers may observe the same value concurrently. Each one independently emits the current value when it attaches (here, the default value). A single `put` delegates exactly one store write and then notifies all active observers, so each emits the same new value; the emissions appear in observer-attachment order (observer 0, then 1, then 2). Successive changes are likewise delivered to every observer.

**Test Cases:** `rcb_tests/public_test_cases/feature6_broadcasts_to_all_listeners.json`

```json
{
    "description": "Every value change is delivered to all active observers. Three observers are attached and each first receives the default value. Each subsequent set operation delegates the write to the store once and notifies all three observers, so every observer sees the same new value, in observer-attachment order.",
    "cases": [
        {
            "input": {"key": "key", "default": "default value", "ops": [
                {"op": "observe"},
                {"op": "observe"},
                {"op": "observe"},
                {"op": "put", "value": "first change"},
                {"op": "put", "value": "second change"}
            ]},
            "expected_output": "emit[0] default value\nemit[1] default value\nemit[2] default value\nstore write key=key value=first change\nput ok=true\nemit[0] first change\nemit[1] first change\nemit[2] first change\nstore write key=key value=second change\nput ok=true\nemit[0] second change\nemit[1] second change\nemit[2] second change\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing a persisted, observable key-value preference: a value bound to a key, a default fallback, and a backing key-value store, exposed as a stream of value changes. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing, and from any specific persistence implementation (it depends on an abstract key-value store).

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request (`key`, `default`, `ops`) from its input, replays the operations against one preference instance, and prints the plain-text event log described above. The `observe` operation attaches an observer (numbered from 0 in attachment order) that prints `[a specific value suffix pattern — ask the PM for the exact format]` for each value it receives; `put` and `remove` delegate to the backing store (printing `store write key=… value=…` / `store remove key=…`) and print `put ok=<bool>` / `remove ok=<bool>`; `preset` seeds the store without notifying; and an unsupported mutation prints `error=<category> op=<op> reason=<reason>`. Native exceptions thrown by the core must be translated by the adapter into these neutral error lines rather than surfaced directly.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the state update logic defined in the observer history module
- align with the standard success signal protocol for key-value mutations
