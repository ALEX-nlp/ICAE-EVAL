## Product Requirement Document

# Local Actor Runtime - Message-Driven Concurrency Core

## Project Goal

Build a local actor runtime library that allows developers to structure concurrent application logic as isolated, named actors that exchange messages, keep private per-actor state, and recover from faults, without hand-writing mailbox queues, lifecycle timers, child-tracking registries, and supervision plumbing.

---

## Background & Problem

Without this library, developers are forced to coordinate asynchronous work with ad hoc queues, timers, callback registries, and shared mutable state. This leads to repetitive concurrency code, fragile message-ordering assumptions, unclear ownership of child tasks, and failure handling that is hard to reason about and easy to get wrong.

With this library, developers start independent actor systems, address actors through a stable hierarchical naming scheme, send fire-and-forget messages, perform bounded request-response interactions, stop whole actor subtrees, and select explicit fault-recovery policies, all expressed as small message-handling functions over private state.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain (addressing, mailbox scheduling, lifecycle, supervision) is non-trivial and warrants clear module separation.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate addressing/validation, mailbox scheduling, lifecycle, supervision, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension (new supervision policies, new message handlers) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity (mailbox, timers, reference resolution).
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) and surfaced as stable, language-neutral categories rather than leaking runtime fault details.

---

## Core Features

### Feature 1: Actor Address Segment Validation

**As a developer**, I want to validate actor address segment names before building an address, so I can reject names that would make hierarchical routing ambiguous.

**Expected Behavior / Usage:**

The adapter accepts a list of candidate names and prints two lines per candidate: the name rendered as a JSON literal (`name=<json>`) and whether it is acceptable (`valid=yes` or `valid=no`). A name is valid only when it is a non-empty text value composed solely of letters, digits, and the URI-safe "extra" characters `-`, `_`, `.`, `$`, `+`, `!`, `*`, `'`, `(`, `)`, and `,`. Empty strings, non-text values, whitespace (leading, trailing, or interior), path separators, reserved query/fragment characters, and escape characters are all invalid. The output preserves input order, one candidate after another.

**Test Cases:** `rcb_tests/public_test_cases/feature1_path_name_validation.json`

```json
{
    "description": "Validate actor address segment names against the accepted character set and reject empty, non-text, whitespace, reserved, escape, and fragment/query characters.",
    "cases": [
        {
            "input": {
                "action": "validate-name-list",
                "names": [
                    "frog",
                    "123-abc",
                    "frog.path",
                    "frog(path)"
                ]
            },
            "expected_output": "name=\"frog\"\nvalid=yes\nname=\"123-abc\"\nvalid=yes\nname=\"frog.path\"\nvalid=yes\nname=\"frog(path)\"\nvalid=yes\n"
        }
    ]
}
```

---

### Feature 2: Child Address Path Creation

**As a developer**, I want to derive child addresses by appending valid child segments to a system root, so I can route messages through a stable hierarchy.

**Expected Behavior / Usage:**

The adapter accepts a root system name and an ordered list of child segment names, then builds a hierarchical address by appending each segment in turn. When every segment is valid, stdout reports the owning system identity (`system=<name>`) and the slash-separated path parts (`[a root node identifier defined in the configuration]`). If any segment is invalid (per the same character rules as Feature 1), construction stops and stdout instead contains a normalized error category (`error=invalid_actor_name`) followed by the rejected segment on its own line (`child_name=<json>`). The error must never expose a runtime exception type or stack trace.

**Test Cases:** `rcb_tests/public_test_cases/feature2_child_path_creation.json`

```json
{
    "description": "Build a child address path by appending valid child segments to a root system path, and report invalid child segments as normalized contract errors.",
    "cases": [
        {
            "input": {
                "action": "create-child-path",
                "system": "root",
                "child_names": [
                    "a",
                    "b",
                    "c1234-d4"
                ]
            },
            "expected_output": "[a root node identifier defined in the configuration]\n[a root node identifier defined in the configuration]1234-d4\n"
        }
    ]
}
```

---

### Feature 3: Actor System Identity and Isolation

**As a developer**, I want each actor system to own its identity and namespace, so I can run multiple systems side by side without name collisions.

**Expected Behavior / Usage:**

Starting a system with a requested name yields a root handle whose system identity equals that name (`system1=<name>`). Multiple systems are fully isolated: each may contain an actor with the same local name, and a request-response interaction addressed within one system resolves against that system only, never crossing into another system's namespace. When two isolated systems each host an actor that transforms an input value differently, querying each actor returns that system's own result independently.

**Test Cases:** `rcb_tests/public_test_cases/feature3_system_identity_and_isolation.json`

```json
{
    "description": "Start named actor systems and keep actors with identical local names isolated by their owning system.",
    "cases": [
        {
            "input": {
                "action": "start-systems",
                "systems": [
                    {
                        "name": "henry"
                    }
                ]
            },
            "expected_output": "system1=henry\n"
        }
    ]
}
```

---

### Feature 4: Stateful Message Processing

**As a developer**, I want an actor to retain and update private state across messages, so I can model long-lived workflows without shared mutable data.

**Expected Behavior / Usage:**

The adapter drives a stateful text accumulator. Append messages are applied strictly in arrival order, each extending the actor's private state; a query message returns the current accumulated state (`state=<value>`). When an explicit initial state is supplied, accumulation begins from that value; otherwise it begins from the actor's default empty state. State is never shared between messages except through the actor's own returned next-state.

**Test Cases:** `rcb_tests/public_test_cases/feature4_stateful_message_processing.json`

```json
{
    "description": "Process append messages through a stateful actor and return the accumulated state, including when the actor starts from an explicit initial state.",
    "cases": [
        {
            "input": {
                "action": "stateful-append",
                "system": "stateful-a",
                "actor_name": "writer",
                "appends": [
                    "Hello ",
                    "World. ",
                    "The time has come!!"
                ]
            },
            "expected_output": "[a predefined state string based on the test scenario]\n"
        }
    ]
}
```

---

### Feature 5: Context-Based Initial State

**As a developer**, I want an actor's initial state to be computed from its startup context, so initialization can depend on the actor's own identity.

**Expected Behavior / Usage:**

The adapter creates a stateful actor whose initial state is produced from a template string containing the placeholder `{name}`. At startup the placeholder is replaced with the actor's configured name, yielding the seed state. Subsequent append messages extend that computed seed, and a query returns the combined result (`state=<value>`). This demonstrates that initialization has read access to the actor's own context before any message is processed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_context_based_initial_state.json`

```json
{
    "description": "Create the initial state from the actor context so that the actor name can be reflected in subsequent stateful message handling.",
    "cases": [
        {
            "input": {
                "action": "initial-state-from-name",
                "system": "ctx-init",
                "actor_name": "NamedActor",
                "template": "Hello {name}! Is today not a joyous occasion?",
                "appends": [
                    " It is indeed"
                ]
            },
            "expected_output": "state=Hello NamedActor! Is today not a joyous occasion? It is indeed\n"
        }
    ]
}
```

---

### Feature 6: Sequential Async Mailbox Processing

**As a developer**, I want asynchronous actor handlers to preserve mailbox order, so a slower earlier message can never be overtaken by a later one.

**Expected Behavior / Usage:**

The adapter sends numbered messages to a worker actor whose handler may asynchronously delay specific messages before forwarding them to a listener actor; the listener appends each received number to its state. Even when a middle message is artificially delayed, the listener's final recorded sequence must equal the original send order (`received=1,2,3`). One message is fully processed before the next begins, regardless of per-message asynchronous work.

**Test Cases:** `rcb_tests/public_test_cases/feature6_async_sequential_processing.json`

```json
{
    "description": "Preserve mailbox order for asynchronous stateful message handlers even when an earlier message takes longer to complete.",
    "cases": [
        {
            "input": {
                "action": "promise-order",
                "system": "ordering",
                "worker_name": "worker",
                "listener_name": "listener",
                "messages": [
                    {
                        "number": 1
                    },
                    {
                        "number": 2,
                        "delay_ms": 30
                    },
                    {
                        "number": 3
                    }
                ]
            },
            "expected_output": "received=1,2,3\n"
        }
    ]
}
```

---

### Feature 7: Request-Response Query

**As a developer**, I want to send a request carrying a temporary reply address and await the response, so I can perform bounded request-response interactions on top of fire-and-forget message passing.

**Expected Behavior / Usage:**

The adapter creates a responder actor and issues a query with a timeout. The query may either embed the temporary reply address inside a message object (the responder reads the sender field and replies to it) or pass the temporary reply address itself as the whole message (the responder replies directly to it). In both shapes, if the actor replies before the timeout elapses, the interaction resolves and stdout reports `response=<value>`. The temporary reply address is single-use and is reclaimed once the response is delivered.

**Test Cases:** `rcb_tests/public_test_cases/feature7_query_request_response.json`

```json
{
    "description": "Send a request that includes a temporary reply address and resolve with the response when the actor replies before the timeout.",
    "cases": [
        {
            "input": {
                "action": "query",
                "system": "query-ok",
                "actor_name": "responder",
                "response": "done",
                "response_delay_ms": 10,
                "timeout_ms": 80,
                "message_shape": "object_with_sender"
            },
            "expected_output": "response=done\n"
        }
    ]
}
```

---

### Feature 8: Query Error Contracts

**As a developer**, I want query failures to be reported as stable domain categories, so callers can distinguish a configuration mistake from a timeout or a stopped-target failure.

**Expected Behavior / Usage:**

Query failures are normalized to language-neutral categories. Attempting a query without supplying a timeout prints `error=missing_timeout`. When no response arrives before the supplied timeout, stdout prints `error=query_timeout` followed by the timeout value on its own line (`timeout_ms=<value>`). Querying a stopped or never-existing target prints `error=stopped_reference`. None of these outputs may contain runtime exception class names, message suffixes, or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature8_query_error_contracts.json`

```json
{
    "description": "Normalize request-response failures when no timeout is supplied, the target is stopped, or no response arrives before the timeout window.",
    "cases": [
        {
            "input": {
                "action": "missing-query-timeout",
                "system": "query-missing",
                "actor_name": "silent"
            },
            "expected_output": "error=missing_timeout\n"
        }
    ]
}
```

---

### Feature 9: Child Registration and Duplicate Names

**As a developer**, I want parents to track their direct children and reject duplicate child names, so actor hierarchies stay inspectable and unambiguous.

**Expected Behavior / Usage:**

A freshly spawned parent reports no children. After child actors are spawned beneath it, both the parent's own context and the system registry expose those direct child names (sorted), without surfacing deeper descendants. An actor may also spawn children while handling a message, and those children become visible immediately afterward. Spawning a second child with a name already used by a sibling under the same parent is rejected with `error=duplicate_child_name` followed by `child_name=<name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_child_registration_and_duplicates.json`

```json
{
    "description": "Register children under their parent, expose child names through the parent context, allow children to be created from within message handling, and reject duplicate sibling names.",
    "cases": [
        {
            "input": {
                "action": "child-registration",
                "system": "children",
                "parent_name": "parent",
                "child_names": [
                    "testGrandchildActor",
                    "testGrandchildActor2"
                ]
            },
            "expected_output": "before=\nafter=testGrandchildActor,testGrandchildActor2\nsystem_children=parent\nparent_children=testGrandchildActor,testGrandchildActor2\n"
        }
    ]
}
```

---

### Feature 10: Stop and Idle Lifecycle

**As a developer**, I want explicit and timer-based stopping for actors and systems, so resources are released predictably.

**Expected Behavior / Usage:**

Stopping an actor marks that actor stopped and cascades the stop to every descendant, while sibling actors stay alive; stopping the root system stops every remaining actor in the tree. After a reference is stopped, spawning a child below it is rejected with `error=stopped_reference`, and any later message dispatched to it is silently ignored. An actor configured with an idle shutdown period stops automatically once that period elapses with no message activity, and receiving a message before the deadline renews the idle timer (keeping the actor alive). Liveness is reported per actor as `<name>=true` (stopped) or `<name>=false` (alive).

**Test Cases:** `rcb_tests/public_test_cases/feature10_stop_and_idle_lifecycle.json`

```json
{
    "description": "Stop actors and systems safely, cascade stops to descendants, reject spawning below stopped references, ignore later dispatches, and stop idle actors after a configured inactivity period while allowing message activity to renew the timer.",
    "cases": [
        {
            "input": {
                "action": "stop-cascade",
                "system": "cascade",
                "parent_name": "parent",
                "child_names": [
                    "child1",
                    "child2"
                ],
                "grandchild_names": [
                    "grandchild1",
                    "grandchild2"
                ]
            },
            "expected_output": "after_child_stop=child1=true,grandchild1=true,grandchild2=true,child2=false\nparent=true\nchild2=true\n"
        }
    ]
}
```

---

### Feature 11: Default Fault Handling

**As a developer**, I want sensible default behavior when an actor handler fails, so faults do not silently corrupt actor state.

**Expected Behavior / Usage:**

By default, a stateful actor whose handler throws while processing a message is terminated (`actor_stopped=true`), because its private state can no longer be trusted. A stateless actor whose handler throws keeps running by default (`actor_stopped=false`), since it carries no state to corrupt. If an actor's startup state computation fails, its crash handler is invoked; when that handler elects to stop, the actor becomes stopped and the handler invocation is observable. The adapter suppresses implementation-level fault logging and prints only liveness and handler-observation signals.

**Test Cases:** `rcb_tests/public_test_cases/feature11_default_fault_handling.json`

```json
{
    "description": "Apply the default fault behavior: stateful actors stop after handler failure, stateless actors resume after handler failure, and initialization failures can be observed by a crash handler that stops the actor.",
    "cases": [
        {
            "input": {
                "action": "default-fault-behavior",
                "system": "fault-a",
                "actor_name": "stateful",
                "actor_kind": "stateful",
                "check_after_ms": 80
            },
            "expected_output": "actor_stopped=true\n"
        }
    ]
}
```

---

### Feature 12: Self Supervision Actions

**As a developer**, I want a faulted actor's own crash policy to choose resume, reset, stop, or escalate, so actor-local recovery can match the workflow's consistency needs.

**Expected Behavior / Usage:**

The adapter builds a parent and a stateful child that fails when it reaches a configured message count unless a designated recovery message is used. The child's crash policy determines the outcome. `resume` keeps the actor alive and preserves its pre-fault state, so a follow-up query reflects progress already made. `reset` keeps the actor alive but restores its initial state, so a follow-up query reflects a fresh start. `stop` terminates the child while the parent stays alive. `escalate` forwards the fault to the parent; with no parent override in place, the default reaction terminates both the child and the parent. Output reports `child_stopped`, `parent_stopped`, and, when the child survives, `query_result`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_self_supervision_actions.json`

```json
{
    "description": "Let an actor-specific crash policy resume, reset, stop, or escalate a faulted actor and expose the resulting actor state and liveness.",
    "cases": [
        {
            "input": {
                "action": "supervision-self",
                "system": "sup-resume",
                "parent_name": "parent",
                "child_name": "child",
                "policy": "resume",
                "fail_on_count": 3,
                "pre_messages": [
                    "msg0",
                    "msg1",
                    "msg2"
                ],
                "recovery_message": "msg3",
                "query_after": "msg3"
            },
            "expected_output": "child_stopped=false\nparent_stopped=false\nquery_result=3\n"
        }
    ]
}
```

---

### Feature 13: Parent Supervision Actions

**As a developer**, I want a parent actor to decide how to handle an escalated child fault, so a failure can affect only the necessary part of an actor tree.

**Expected Behavior / Usage:**

When a child escalates a fault, the parent's crash policy chooses the response. Stopping all children leaves the parent alive but terminates both the faulted child and its peer. Resetting all children leaves every child alive and restores each child's state to its initial value, so follow-up queries reflect fresh starts for both. Resetting only the faulted child restores that child's state while leaving the peer alive with its accumulated state intact, so the peer's follow-up query reflects the messages it had already processed. Output reports parent and per-child liveness, plus the surviving children's follow-up query results.

**Test Cases:** `rcb_tests/public_test_cases/feature13_parent_supervision_actions.json`

```json
{
    "description": "Let a parent crash policy respond to an escalated child failure by stopping all children, resetting all children, or resetting only the faulted child while leaving unaffected actors according to the selected action.",
    "cases": [
        {
            "input": {
                "action": "supervision-parent-policy",
                "system": "par-stop-children",
                "parent_name": "parent",
                "parent_policy": "stop_all_children",
                "faulting_child_name": "faulty",
                "other_child_name": "peer",
                "fail_on_count": 3,
                "pre_messages": [
                    "msg0",
                    "msg1",
                    "msg2"
                ],
                "recovery_message": "msg3"
            },
            "expected_output": "parent_stopped=false\nfaulty_stopped=true\npeer_stopped=true\n"
        }
    ]
}
```

---

### Feature 14: Peer and Descendant Stop Supervision

**As a developer**, I want a fault policy that stops the faulted actor together with its peers and descendants while keeping the parent alive, so a related group can be torn down as one unit.

**Expected Behavior / Usage:**

The adapter builds a parent with two children, each owning one grandchild. When the faulting child reaches its configured failure count and its crash policy selects the stop-self-peers-and-descendants action, the parent stays alive while the faulting child, the peer child, and both grandchildren are all stopped. Output reports the parent's liveness and each affected actor's liveness.

**Test Cases:** `rcb_tests/public_test_cases/feature14_peer_and_descendant_supervision.json`

```json
{
    "description": "Apply a self crash policy that stops the faulted actor, its peers, and descendants while keeping the parent alive.",
    "cases": [
        {
            "input": {
                "action": "supervision-stop-all",
                "system": "sup-stop-all",
                "parent_name": "parent",
                "faulting_child_name": "faulty",
                "peer_child_name": "peer",
                "grandchild_names": [
                    "faulty-child",
                    "peer-child"
                ],
                "fail_on_count": 3,
                "pre_messages": [
                    "msg0",
                    "msg1",
                    "msg2"
                ]
            },
            "expected_output": "parent_stopped=false\nfaulty_stopped=true\npeer_stopped=true\nfaulty-child_stopped=true\npeer-child_stopped=true\n"
        }
    ]
}
```

---

### Feature 15: After-Stop Context Callback

**As a developer**, I want an after-stop callback to inspect the stop-time context, so cleanup logic can observe the parent reference and the messages still queued behind in-flight work.

**Expected Behavior / Usage:**

The adapter starts an actor with a slow message handler and an after-stop callback. Two messages are dispatched; while the first is still being processed, the actor is stopped. The after-stop callback then receives a context exposing the parent reference and the mailbox contents that were queued but never processed. Output reports the number of still-queued messages (`queued_messages`), the first queued message value (`first_queued`), and the parent system identity (`parent_system`).

**Test Cases:** `rcb_tests/public_test_cases/feature15_after_stop_context.json`

```json
{
    "description": "Run an after-stop callback with access to the parent reference and any messages still queued behind an in-flight message.",
    "cases": [
        {
            "input": {
                "action": "after-stop",
                "system": "after-stop",
                "actor_name": "worker",
                "processing_delay_ms": 80,
                "messages": [
                    1,
                    2
                ]
            },
            "expected_output": "queued_messages=1\nfirst_queued=2\nparent_system=after-stop\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_path_name_validation@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- preserve send order as dictated by the standard event queue
- arrivals match the sequence defined in the sender queue
