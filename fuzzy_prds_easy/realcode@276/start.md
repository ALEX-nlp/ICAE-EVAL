## Product Requirement Document

# Asynchronous Result Toolkit — Promise Combinators, Cancellation & Streaming Primitives

## Project Goal

Build a small toolkit of primitives for working with the results of operations that complete in the future, so developers can combine many concurrent operations, react to their collective outcome, cancel work cooperatively, and consume ordered streams of values — without hand-writing bespoke coordination logic for every call site.

---

## Background & Problem

A program frequently launches several operations whose results arrive later (each modeled as a *placeholder* for a future value that will eventually be either fulfilled with a value or rejected with a failure reason). Coordinating them by hand is repetitive and error-prone: deciding whether to wait for all of them, for a threshold of them, or only for the first success; collecting partial results when some fail; cleanly aborting in-flight work; and turning a collection of items into an asynchronous stream.

This toolkit provides well-defined contracts for these recurring needs: combinators that aggregate a list of placeholders under different success policies, a single-settlement placeholder with a completion callback, a cooperative cancellation mechanism, a typo-guarded value object, and an adapter that turns any iterable into an ordered asynchronous stream. Each primitive has a precise, observable input/output contract so the same expectations hold regardless of how the internals are built.

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

Every feature is exercised through one JSON request object on stdin and one textual result on stdout. A request carries an `op` field selecting the operation. Results are emitted as newline-terminated `key=value` lines. Collections are rendered as compact JSON: a positional collection with contiguous positions starting at zero renders as a JSON array (e.g. `[1,2,3]`); a collection with non-contiguous positions renders as a JSON object keyed by position (e.g. `{"0":1,"2":3}`). Error outcomes are reported with neutral category names, never with host-language runtime details.

A list of operations is supplied under `promises` as an array of operand specs. An operand spec is one of: `{"resolve": <value>}` for an operation that succeeds with the given value, `{"fail": <message>}` for an operation that fails with the given reason message, or `{"value": <x>}` for a raw non-operation value used to probe input validation.

### Feature 1: Aggregate — Require Every Operation To Succeed

**As a developer**, I want to wait for a whole batch of operations and get all their values only if every one succeeds, so I can treat the batch as a single all-or-nothing unit.

**Expected Behavior / Usage:**

The `all` operation aggregates the `promises` list. It fulfills with `values`, an ordered collection of each operation's success value at the same position as its operand. An empty list fulfills with an empty collection. If any operand is a raw non-operation value, the operation does not proceed and instead reports `status=error` with `error=invalid_operand`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_all.json`

```json
{
    "description": "Aggregate a list of asynchronous operations and require every one of them to succeed. The result is fulfilled with an ordered collection of the success values, one per input operation, in the same positions as the inputs. An empty input yields an empty collection. If any element of the input is not an asynchronous operation handle, the aggregation reports an invalid-operand error rather than proceeding.",
    "cases": [
        {
            "input": {"op": "all", "promises": [{"resolve": 1}, {"resolve": 2}, {"resolve": 3}]},
            "expected_output": "status=fulfilled\nvalues=[1,2,3]\n"
        },
        {
            "input": {"op": "all", "promises": [{"value": 1}]},
            "expected_output": "status=error\nerror=invalid_operand\n"
        }
    ]
}
```

---

### Feature 2: Threshold Aggregate — Succeed If Enough Operations Succeed

**As a developer**, I want a batch to succeed as long as at least a chosen number of operations succeed, collecting both the successes and the failures, so I can tolerate partial failure.

**Expected Behavior / Usage:**

The `some` operation aggregates `promises` and accepts an optional `required` count (default `1`). It fulfills with two position-preserving collections: `errors` (failed positions mapped to their failure messages) and `values` (succeeded positions mapped to their values). If fewer than `required` operations succeed, it instead rejects with `reason=multiple_failures` and a `reasons` list of every failure message in order. A negative `required` reports `error=negative_required`; a `required` larger than the number of operations reports `error=too_few_promises`; a raw non-operation operand reports `error=invalid_operand`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_some.json`

```json
{
    "description": "Aggregate a list of asynchronous operations into a partitioned result, succeeding as long as at least a required number of operations succeed. The fulfilled result carries two collections that preserve the original positions: the failures (mapped to their failure messages) and the successes (mapped to their values). The required count defaults to one. If fewer than the required number succeed, the result is rejected with a combined multiple-failures outcome listing every failure reason in order. Supplying a negative required count, requiring more successes than there are operations, or passing a non-operation operand are each reported as a distinct invalid-input error.",
    "cases": [
        {
            "input": {"op": "some", "promises": [{"fail": "boom"}, {"fail": "boom"}, {"resolve": 3}]},
            "expected_output": "status=fulfilled\nerrors=[\"boom\",\"boom\"]\nvalues={\"2\":3}\n"
        },
        {
            "input": {"op": "some", "promises": [{"fail": "a"}, {"fail": "b"}, {"fail": "c"}]},
            "expected_output": "status=rejected\nreason=multiple_failures\nreasons=[\"a\",\"b\",\"c\"]\n"
        },
        {
            "input": {"op": "some", "promises": [], "required": -1},
            "expected_output": "status=error\nerror=negative_required\n"
        }
    ]
}
```

---

### Feature 3: Partition Aggregate — Never Reject

**As a developer**, I want to collect the outcome of every operation and always get a result, even if all of them fail, so I can inspect partial results without handling a batch-level failure.

**Expected Behavior / Usage:**

The `any` operation aggregates `promises` and always fulfills with the same two position-preserving collections used by the threshold aggregate: `errors` (failed positions mapped to failure messages) and `values` (succeeded positions mapped to values). When all succeed, `errors` is empty; when all fail, `values` is empty; a mix yields both, each keyed by original position. A raw non-operation operand reports `error=invalid_operand`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_any.json`

```json
{
    "description": "Aggregate a list of asynchronous operations into a partitioned result that never rejects, regardless of how many operations fail. The fulfilled result always carries two collections preserving the original positions: the failures (mapped to their failure messages) and the successes (mapped to their values). When all operations succeed the failure collection is empty; when all fail the success collection is empty; a mix yields both, each keyed by original position. Passing a non-operation operand is reported as an invalid-operand error.",
    "cases": [
        {
            "input": {"op": "any", "promises": [{"resolve": 1}, {"fail": "b"}, {"resolve": 3}]},
            "expected_output": "status=fulfilled\nerrors={\"1\":\"b\"}\nvalues={\"0\":1,\"2\":3}\n"
        },
        {
            "input": {"op": "any", "promises": [{"fail": "a"}, {"fail": "b"}, {"fail": "c"}]},
            "expected_output": "status=fulfilled\nerrors=[\"a\",\"b\",\"c\"]\nvalues=[]\n"
        }
    ]
}
```

---

### Feature 4: Race — Fulfill With The First Success

**As a developer**, I want the value of whichever operation succeeds first and to fail only if none succeed, so I can pick the fastest available result.

**Expected Behavior / Usage:**

The `first` operation races `promises` and fulfills with `value`, the value of the first operation to succeed, disregarding later results and any earlier failures. If every operation fails, it rejects with `reason=multiple_failures` and a `reasons` list of all failure messages in order. An empty list reports `error=no_promises`; a raw non-operation operand reports `error=invalid_operand`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_first.json`

```json
{
    "description": "Race a list of asynchronous operations and fulfill with the value of the first one to succeed, ignoring later results and any failures that occurred before the first success. If every operation fails, the result is rejected with a combined multiple-failures outcome listing every failure reason in order. An empty input is reported as a no-operations error, and a non-operation operand is reported as an invalid-operand error.",
    "cases": [
        {
            "input": {"op": "first", "promises": [{"resolve": 1}, {"resolve": 2}, {"resolve": 3}]},
            "expected_output": "status=fulfilled\nvalue=1\n"
        },
        {
            "input": {"op": "first", "promises": [{"fail": "a"}, {"fail": "b"}, {"fail": "c"}]},
            "expected_output": "status=rejected\nreason=multiple_failures\nreasons=[\"a\",\"b\",\"c\"]\n"
        },
        {
            "input": {"op": "first", "promises": []},
            "expected_output": "status=error\nerror=no_promises\n"
        }
    ]
}
```

---

### Feature 5: Single-Settlement Placeholder

**As a developer**, I want a placeholder for a future result that settles exactly once and notifies a completion callback, so I can hand a value-to-come around before it is known.

**Expected Behavior / Usage:**

The `settle` operation drives a single placeholder. With `mode` of `resolve`, the placeholder is fulfilled with the provided `value` (a scalar or a structured object/array) and the result reports `status=fulfilled` with `value` rendered as compact JSON. With `mode` of `fail`, the placeholder is rejected with the provided `reason` and the result reports `status=rejected` with that reason message. The reported value/reason is the placeholder's own settlement, independent of how the placeholder was produced.

**Test Cases:** `rcb_tests/public_test_cases/feature5_settle.json`

```json
{
    "description": "Observe the single settlement of a placeholder for a future result. A placeholder is settled exactly once, either fulfilled with a value or rejected with a failure reason, and a registered completion callback is notified of that outcome. A fulfillment exposes the carried value (which may be a scalar or a structured object/array); a rejection exposes the failure reason message. The reported value is the placeholder's own value, independent of how the placeholder was produced.",
    "cases": [
        {
            "input": {"op": "settle", "mode": "resolve", "value": "Resolution value"},
            "expected_output": "status=fulfilled\nvalue=\"Resolution value\"\n"
        },
        {
            "input": {"op": "settle", "mode": "fail", "reason": "failure reason"},
            "expected_output": "status=rejected\nreason=failure reason\n"
        }
    ]
}
```

---

### Feature 6: Cooperative Cancellation

**As a developer**, I want to request cancellation through a token that notifies registered handlers, so in-flight work can abort cleanly and idempotently.

**Expected Behavior / Usage:**

The `cancellation` operation drives a cancellation source and its token. `subscribe` lists labels of handlers registered before cancellation; `unsubscribe` lists labels removed before cancellation; `[a specific positive integer threshold for cancellation timing]` requests cancellation that many times; `subscribe_after` lists handlers registered after the first cancellation request. Each notified handler receives a neutral cancellation signal. The token reports `requested_before=false` and `requested_after=true`. Requesting cancellation more than once notifies each handler at most once. An unsubscribed handler is never notified. A handler subscribing after cancellation is notified immediately. The result reports `fired` as the ordered list of notified handler labels and `reason=cancelled` when any handler was notified (else `reason=none`).

**Test Cases:** `rcb_tests/public_test_cases/feature6_cancellation.json`

```json
{
    "description": "Coordinate cooperative cancellation through a cancellation source and its token. Handlers subscribe to the token to be notified when cancellation is requested; each notified handler receives a neutral cancellation signal. Before any request the token reports not-requested; after a request it reports requested. Requesting cancellation more than once notifies each handler at most once. A handler that unsubscribes before the request is never notified. A handler that subscribes after cancellation has already been requested is notified immediately. The result lists, in subscription order, the labels of the handlers that were notified.",
    "cases": [
        {
            "input": {"op": "cancellation", "subscribe": ["s1", "s2"], "unsubscribe": ["s1"], "[a specific positive integer threshold for cancellation timing]": 1},
            "expected_output": "requested_before=false\nrequested_after=true\nfired=[\"s2\"]\nreason=cancelled\n"
        },
        {
            "input": {"op": "cancellation", "subscribe": [], "[a specific positive integer threshold for cancellation timing]": 1, "subscribe_after": ["late"]},
            "expected_output": "requested_before=false\nrequested_after=true\nfired=[\"late\"]\nreason=cancelled\n"
        }
    ]
}
```

---

### Feature 7: Typo-Guarded Value Object

**As a developer**, I want a value object that rejects access to misspelled properties and suggests the intended name, so configuration typos fail fast and helpfully.

**Expected Behavior / Usage:**

The `struct` operation accesses a value object that has two public properties named `callback` and `_foofoofoofoofoofoofoofoobar`. With `action` of `set` or `get` on a `property` that does not exist, access fails with `error=[the exact string payload sent for unknown properties]` and echoes the offending `property`. If the offending name is sufficiently similar to an existing public property, that property name is offered as `suggestion`; otherwise `suggestion` is empty. Property names beginning with an underscore are never offered as suggestions. Reads and writes behave identically.

**Test Cases:** `rcb_tests/public_test_cases/feature7_struct.json`

```json
{
    "description": "Guard a value object against typos by rejecting reads or writes of properties that do not exist. Reading or writing an undefined property fails with an unknown-property error that names the offending property. When the offending name is sufficiently similar to an existing public property, a suggestion of that property name is offered; otherwise no suggestion is offered. Property names beginning with an underscore are never offered as suggestions. Both read and write access behave identically.",
    "cases": [
        {
            "input": {"op": "struct", "action": "set", "property": "callbac"},
            "expected_output": "error=[the exact string payload sent for unknown properties]\nproperty=callbac\nsuggestion=callback\n"
        },
        {
            "input": {"op": "struct", "action": "set", "property": "callZZZZZZZZZZZ"},
            "expected_output": "error=[the exact string payload sent for unknown properties]\nproperty=callZZZZZZZZZZZ\nsuggestion=\n"
        }
    ]
}
```

---

### Feature 8: Iterable-To-Stream Adapter

**As a developer**, I want to turn an in-memory iterable into an ordered asynchronous stream, so I can consume its elements one at a time even when some are themselves operations.

**Expected Behavior / Usage:**

The `iterator` operation builds a stream from `elements`, an array of operand specs. Each element that is an operation is awaited and its resolved value is emitted; each plain `{"value": x}` element is emitted directly. The stream emits in order and then completes (`status=completed`). If an element fails, the stream stops there: it reports the values emitted before the failure and then `status=failed` with that element's `reason`; elements after the failure are never emitted. The result reports `emitted` as the ordered list of emitted values. Supplying a non-iterable source under `invalid` reports `status=error` with `error=[the precise technical error name for non-iterable inputs]`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_iterator.json`

```json
{
    "description": "Turn an in-memory iterable into an asynchronous stream that emits each element in order. Elements that are themselves asynchronous operations are awaited and their resolved values are emitted; plain values are emitted directly. The stream completes after the last element. If an element fails, the stream stops at that point, emitting any values produced before it and then failing with that element's failure reason; elements after the failure are never emitted. The result reports the ordered list of emitted values plus whether the stream completed or failed (and, on failure, the reason). Providing a source that is not iterable is reported as an invalid-iterable error.",
    "cases": [
        {
            "input": {"op": "iterator", "elements": [{"resolve": 1}, {"resolve": 2}, {"fail": "boom"}, {"resolve": 4}]},
            "expected_output": "emitted=[1,2]\nstatus=failed\nreason=boom\n"
        },
        {
            "input": {"op": "iterator", "invalid": "string"},
            "expected_output": "status=error\nerror=[the precise technical error name for non-iterable inputs]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the primitives described above (the aggregating combinators, the single-settlement placeholder, the cancellation source/token, the typo-guarded value object, and the iterable-to-stream adapter). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, dispatches on the `op` field, invokes the appropriate core logic, and prints the result (or neutral error) to stdout, matching the per-feature contracts above. Outcomes are rendered as newline-terminated `key=value` lines; collections are compact JSON (array for contiguous zero-based positions, object keyed by position otherwise); all failures are reported with neutral category names rather than host-language runtime details.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- maintain the same priority ordering as the initializer module
