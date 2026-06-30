## Product Requirement Document

# Asynchronous Result Coordination Library - Deferred Workflows and Aggregation

## Project Goal

Build a lightweight asynchronous result coordination library that allows developers to represent pending, fulfilled, and rejected work; compose dependent workflows; aggregate multiple results; and drain scheduled callbacks without hand-writing brittle state machines.

---

## Background & Problem

Without this library, developers are forced to manually track whether each unit of deferred work has completed, store success values or failure reasons, decide when callbacks should run, and coordinate groups of related results. This leads to repetitive control-flow code, subtle ordering bugs, recursion risks, and inconsistent error handling.

With this library, developers can model asynchronous outcomes as composable result objects, attach callbacks that run predictably through a queue, wait for completion when needed, combine many results into higher-level results, and expose normalized failure information to callers.

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

### Feature 1: Single Result Lifecycle

**As a developer**, I want to create and control individual deferred results, so I can safely model one unit of asynchronous work from creation through completion, failure, or cancellation.

**Expected Behavior / Usage:**

*1.1 Pre-Settled Results — Completed and failed results expose stable state and wait behavior.*

A result created already fulfilled reports `fulfilled`, ignores cancellation, and waiting returns the stored value. A result created already rejected reports `rejected`; waiting on it emits a normalized `result_rejected` error with the original reason and leaves the state rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_pre_settled_promises.json`

```json
{
    "description": "Pre-settled success and failure objects expose their state, waiting behavior, and cancellation stability.",
    "cases": [
        {
            "input": {
                "operation": "fulfilled_wait_cancel",
                "value": "foo"
            },
            "expected_output": "state_before=fulfilled\nstate_after_cancel=fulfilled\nwait_value=foo\n"
        },
        {
            "input": {
                "operation": "rejected_wait",
                "reason": "foo"
            },
            "expected_output": "state_before=rejected\nerror=result_rejected\nreason=foo\nstate_after=rejected\n"
        }
    ]
}
```

*1.2 Single Settlement — A pending result can be completed once and cannot later change outcome.*

The adapter input describes a first settlement action and a second attempted settlement action. Repeating the same action with the same value is accepted and keeps the original state. Attempting to change a fulfilled result into a rejection, or a rejected result into fulfillment, is rejected with `state_change_forbidden`; the final state and stored fulfillment value remain unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_single_settlement.json`

```json
{
    "description": "A pending asynchronous result may settle once; identical repeat settlement is ignored, but changing an already settled outcome is rejected.",
    "cases": [
        {
            "input": {
                "operation": "settle_once",
                "first_action": "resolve",
                "first_value": "foo",
                "second_action": "resolve",
                "second_value": "foo"
            },
            "expected_output": "state_after_first=fulfilled\nsecond_action=accepted\nfinal_state=fulfilled\nwait_value=foo\n"
        }
    ]
}
```

*1.3 Waiting and Unwrapping — Waiting drives producer execution and controls whether failures are surfaced.*

The adapter input describes a producer mode. A resolving producer fulfills the result and waiting prints the value. A rejecting producer sets the state to rejected; when unwrapping is enabled, stdout contains `error=result_rejected` and the original reason, while disabling unwrapping only drives the state transition. If the producer itself fails, stdout reports `error=callback_error` with the callback message.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_waiting_and_unwrapping.json`

```json
{
    "description": "Waiting triggers the producer callback, reports fulfilled values, and normalizes rejection or callback failure as data.",
    "cases": [
        {
            "input": {
                "operation": "wait_callback",
                "mode": "resolve",
                "value": "10"
            },
            "expected_output": "state=fulfilled\nwait_value=10\n"
        }
    ]
}
```

*1.4 Chaining and Recovery — Dependent callbacks transform values and can recover from rejection.*

A chain of fulfillment callbacks receives the previous value and returns the next value in order, producing a final fulfilled result. Rejection handlers can observe a reason, return a replacement value, and allow downstream fulfillment handlers to continue with that replacement. Callback effects are emitted as ordered event lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_chaining_and_recovery.json`

```json
{
    "description": "Callbacks attached to asynchronous results run through the queue, transform fulfillment values, and allow rejection recovery through later fulfillment.",
    "cases": [
        {
            "input": {
                "operation": "chain_transform",
                "start": "a",
                "append": [
                    "-1-",
                    "2"
                ]
            },
            "expected_output": "wait_value=a-1-2\nstate=fulfilled\n"
        }
    ]
}
```

*1.5 Cancellation — Pending work can be cancelled and cancellation propagates through dependent chains.*

Cancelling a pending result rejects it and invokes its cancellation hook exactly once. Cancelling an intermediate node in a dependency chain rejects the upstream pending nodes and the cancelled node, while later children remain pending until waited on; waiting on such a child reports `result_cancelled` and then leaves it rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_cancellation.json`

```json
{
    "description": "Cancellation rejects pending work, invokes cancellation hooks, and propagates cancellation to ancestor chain nodes while later children settle when waited on.",
    "cases": [
        {
            "input": {
                "operation": "cancel_pending"
            },
            "expected_output": "state=rejected\ncancel_callback_called=true\n"
        }
    ]
}
```

---

### Feature 2: Batch Aggregation and Inspection

**As a developer**, I want to combine multiple asynchronous results, so I can coordinate groups of work and obtain deterministic aggregate outcomes.

**Expected Behavior / Usage:**

*2.1 All-Required Batches and Value Unwrapping — Every input must fulfill for a successful value list.*

For an all-required batch, each input is resolved or rejected in the requested resolution order, but the successful aggregate value preserves the original input order. If any input rejects, the aggregate rejects with that reason. Unwrapping a keyed set of fulfilled results returns the keyed value object; unwrapping a rejected item emits `result_rejected` and the original reason.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_all_and_unwrap.json`

```json
{
    "description": "Batch waiting preserves input keys and order for all fulfilled items, while the first rejected item rejects the aggregate or unwrap operation.",
    "cases": [
        {
            "input": {
                "operation": "batch_all_required",
                "values": [
                    {
                        "state": "fulfilled",
                        "value": "a"
                    },
                    {
                        "state": "fulfilled",
                        "value": "b"
                    },
                    {
                        "state": "fulfilled",
                        "value": "c"
                    }
                ],
                "resolution_order": [
                    1,
                    0,
                    2
                ]
            },
            "expected_output": "result_state=fulfilled\nresult_value=[\"a\",\"b\",\"c\"]\n"
        }
    ]
}
```

*2.2 Competitive Fulfillment — A batch can complete after a requested number of successes or after the first success.*

A count-based competitive batch fulfills when the requested number of inputs have fulfilled and returns the winning values in completion order. If too few inputs can fulfill, it rejects with `not_enough_fulfilled` and a list of rejection reasons. A first-success batch fulfills with the first fulfilled value rather than a single-item list.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_some_and_any.json`

```json
{
    "description": "Competitive aggregation fulfills when enough inputs have fulfilled in resolution order, or rejects with normalized aggregate failure when the requested count is impossible.",
    "cases": [
        {
            "input": {
                "operation": "batch_some_required",
                "count": 2,
                "values": [
                    {
                        "state": "fulfilled",
                        "value": "a"
                    },
                    {
                        "state": "fulfilled",
                        "value": "b"
                    },
                    {
                        "state": "fulfilled",
                        "value": "c"
                    }
                ],
                "resolution_order": [
                    1,
                    2,
                    0
                ]
            },
            "expected_output": "result_state=fulfilled\nresult_value=[\"b\",\"c\"]\n"
        }
    ]
}
```

*2.3 Settlement Reports — Batch inspection reports every item outcome without throwing.*

Settling a batch always fulfills with an array of per-item records. Each record contains `state=fulfilled` and `value` for success, or `state=rejected` and `reason` for failure, in original input order. Inspecting several already settled results returns the same per-item record shape without raising errors.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_settle_and_inspect.json`

```json
{
    "description": "Inspection reports fulfilled values and rejected reasons without throwing, and settling a batch always fulfills with per-item inspection records.",
    "cases": [
        {
            "input": {
                "operation": "batch_settle_report",
                "values": [
                    {
                        "state": "rejected",
                        "reason": "a"
                    },
                    {
                        "state": "fulfilled",
                        "value": "b"
                    },
                    {
                        "state": "fulfilled",
                        "value": "c"
                    }
                ],
                "resolution_order": [
                    1,
                    2,
                    0
                ]
            },
            "expected_output": "result_state=fulfilled\nresult_value=[{\"state\":\"rejected\",\"reason\":\"a\"},{\"state\":\"fulfilled\",\"value\":\"b\"},{\"state\":\"fulfilled\",\"value\":\"c\"}]\n"
        }
    ]
}
```

---

### Feature 3: Iterable Processing

**As a developer**, I want to process an iterable of values or asynchronous results, so I can run side effects as each item settles while receiving a final aggregate completion signal.

**Expected Behavior / Usage:**

*3.1 Unbounded Iteration — Every item is consumed and reports a fulfillment or rejection event.*

The adapter input supplies a list of settled items. Iteration invokes a success event for fulfilled values and a failure event for rejected reasons, preserving each item index in the event text. The aggregate fulfills after the iterable has been consumed, even when per-item rejections are handled by the rejection callback.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_each_iteration.json`

```json
{
    "description": "Iterator-style processing invokes success and failure callbacks for each item and fulfills the aggregate once the iterable is consumed.",
    "cases": [
        {
            "input": {
                "operation": "iterate_all",
                "items": [
                    {
                        "state": "fulfilled",
                        "value": "a"
                    },
                    {
                        "state": "fulfilled",
                        "value": "c"
                    },
                    {
                        "state": "fulfilled",
                        "value": "b"
                    }
                ]
            },
            "expected_output": "aggregate_state=fulfilled\nevents=[\"fulfilled:0:a\",\"fulfilled:1:c\",\"fulfilled:2:b\"]\n"
        }
    ]
}
```

*3.2 Limited Iteration — Processing can cap outstanding pending work and optionally fail fast on rejection.*

Limited iteration accepts a concurrency value and only advances through pending work as earlier items settle. Fulfillment events preserve indexes and values. The fail-fast variant fulfills events for earlier successes but rejects the aggregate with the first rejection reason when any item fails.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_limited_iteration.json`

```json
{
    "description": "Limited iterator processing caps concurrent pending work while preserving callback indexes and completion events.",
    "cases": [
        {
            "input": {
                "operation": "iterate_limited",
                "concurrency": 2,
                "values": [
                    {
                        "state": "fulfilled",
                        "value": "a"
                    },
                    {
                        "state": "fulfilled",
                        "value": "b"
                    },
                    {
                        "state": "fulfilled",
                        "value": "c"
                    },
                    {
                        "state": "fulfilled",
                        "value": "d"
                    }
                ],
                "resolution_order": [
                    0,
                    1,
                    2,
                    3
                ]
            },
            "expected_output": "aggregate_state=fulfilled\nevents=[\"fulfilled:0:a\",\"fulfilled:1:b\",\"fulfilled:2:c\",\"fulfilled:3:d\"]\n"
        }
    ]
}
```

---

### Feature 4: Deferred Task Queue

**As a developer**, I want queued callbacks and scheduled thunks, so I can defer callback execution and drain work in deterministic FIFO order.

**Expected Behavior / Usage:**

*4.1 FIFO Queue — Queued callbacks run in insertion order and update empty-state signals.*

A queue starts empty, becomes non-empty after tasks are added, runs scheduled callbacks in the same order they were added, and becomes empty after draining. Stdout reports the empty-state transitions and the ordered event list.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_task_queue.json`

```json
{
    "description": "A FIFO task queue reports emptiness, executes scheduled tasks in insertion order, and is empty after draining.",
    "cases": [
        {
            "input": {
                "operation": "fifo_queue",
                "tasks": [
                    "a",
                    "b",
                    "c"
                ]
            },
            "expected_output": "empty_before=true\nempty_after_add=false\nevents=[\"a\",\"b\",\"c\"]\nempty_after_run=true\n"
        }
    ]
}
```

*4.2 Scheduled Thunks — A queued unit of work resolves or rejects a pending result when drained.*

Scheduling a thunk returns a pending result before the queue runs. When drained, a returning thunk fulfills with its return value, while a failing thunk rejects with a normalized `callback_error` record containing the message.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_scheduled_tasks.json`

```json
{
    "description": "A scheduled thunk starts pending, then fulfills with the return value or rejects with a normalized callback error when the queue runs.",
    "cases": [
        {
            "input": {
                "operation": "schedule_task",
                "mode": "return",
                "value": "Hi!"
            },
            "expected_output": "state_before_run=pending\nresult_state=fulfilled\nresult_value=Hi!\n"
        }
    ]
}
```

---

### Feature 5: Generator-Driven Workflows

**As a developer**, I want to express asynchronous workflows as generators that yield intermediate results, so I can write sequential-looking control flow while preserving deferred result semantics.

**Expected Behavior / Usage:**

*5.1 Sequential Generator Results — Yielded results feed values back into the workflow and the final yield becomes the outcome.*

A generator workflow receives the fulfilled value of each yielded result before continuing. If several results are yielded, the final yielded value becomes the workflow result. An optional suffix can be appended to the final received value before the workflow fulfills.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_generator_sequences.json`

```json
{
    "description": "Generator-style generators consume yielded asynchronous results in sequence and fulfill with the final yielded value.",
    "cases": [
        {
            "input": {
                "operation": "generator_sequence",
                "yields": [
                    {
                        "state": "fulfilled",
                        "value": "a"
                    }
                ],
                "append": "b"
            },
            "expected_output": "result_state=fulfilled\nresult_value=ab\n"
        }
    ]
}
```

*5.2 Generator Rejection Handling — A workflow can catch a yielded rejection and continue with a replacement value.*

When a yielded result rejects, the workflow may catch the rejection, read the original reason, yield a fulfilled replacement based on that reason, and then fulfill with the replacement-derived value. Stdout reports the final fulfilled state and value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_generator_rejection_handling.json`

```json
{
    "description": "Generator-style generators can catch a rejected yielded result, inspect the rejection reason, and continue by yielding a fulfilled replacement.",
    "cases": [
        {
            "input": {
                "operation": "generator_catch",
                "reason": "a",
                "append": "b"
            },
            "expected_output": "result_state=fulfilled\nresult_value=ab\n"
        }
    ]
}
```

---

### Feature 6: State Predicate Reporting

**As a developer**, I want simple state predicates for asynchronous results, so I can branch on fulfillment, rejection, or general settlement without inspecting internal representation.

**Expected Behavior / Usage:**

The adapter input names several results and assigns each one a state of fulfilled, rejected, or pending. For each named result, stdout reports whether it is fulfilled, whether it is rejected, and whether it is settled. Fulfilled and rejected results are settled; pending results are neither fulfilled nor rejected and are not settled.

**Test Cases:** `rcb_tests/public_test_cases/feature6_state_predicates.json`

```json
{
    "description": "State predicate helpers report whether asynchronous results are fulfilled, rejected, or generally settled.",
    "cases": [
        {
            "input": {
                "operation": "state_flags",
                "states": {
                    "ready": "fulfilled",
                    "failed": "rejected",
                    "later": "pending"
                }
            },
            "expected_output": "ready_is_fulfilled=true\nready_is_rejected=false\nready_is_settled=true\nfailed_is_fulfilled=false\nfailed_is_rejected=true\nfailed_is_settled=true\nlater_is_fulfilled=false\nlater_is_rejected=false\nlater_is_settled=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_pre_settled_promises.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_pre_settled_promises@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- preserve original input index order ignoring resolution_order
- follow the exact string format pattern for iterations
