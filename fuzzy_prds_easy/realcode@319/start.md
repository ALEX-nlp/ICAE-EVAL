## Product Requirement Document

# Lightweight Finite-State-Machine Engine — Declarative States, Triggers, Guards & Lifecycle Callbacks

## Project Goal

Build a small, object-oriented finite-state-machine engine that lets developers attach a set of named states and named triggers to any plain object, so that calling a trigger moves the object between states according to declared rules, instead of hand-writing brittle `if`/`switch` chains and scattered status flags.

---

## Background & Problem

Many objects in real systems are really just little state machines: an order is *pending*, then *paid*, then *shipped*; a connection is *open* or *closed*. Without a dedicated engine, developers encode this with ad-hoc status fields and conditional branches sprinkled across the codebase, which is easy to get wrong, hard to read, and impossible to reason about as the number of states grows.

With this engine, a developer declares the valid states, designates a starting state, and declares transitions as `(trigger, source, destination)` edges. The engine then exposes each trigger as a callable on the bound object; calling it consults the rules and either moves the object or refuses. Transitions can be guarded by boolean checks, can run side-effecting callbacks before/after the move or when entering/leaving a state, can carry an arbitrary payload, and can be generated in bulk for common patterns such as a linear progression through an ordered sequence of states.

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

### Feature 1: Declared States, Triggers & State Queries

**As a developer**, I want to declare a set of states and wire triggers to source→destination edges, so I can move an object between states by calling a named trigger and then inspect where it ended up.

**Expected Behavior / Usage:**

A machine is built from a list of named states plus a designated starting state. A transition is declared as a trigger name together with a source state and a destination state. Firing a trigger while the machine is in that transition's source state moves the machine to the destination state and reports success; the resulting active state is then the destination. The active state can be queried at any time, and there is a per-state predicate that reports whether a named state is the one currently active ([keyboard shortcut for 'send_event'] only for the active state). A trigger fired from a state with no matching transition is covered separately; here every fired trigger has a valid edge from the current state, so each reports a successful move and the new active state.

**Test Cases:** `rcb_tests/public_test_cases/feature1_basic_transitions.json`

```json
{
    "description": "A machine is created over a set of named states with one designated as the starting state. Explicitly declared transitions wire a trigger name to a (source -> destination) edge. Firing a trigger while in the matching source state moves the machine to the destination state; the active state can be queried directly, and per-state predicates report whether a given state is the current one. Each fired trigger reports whether it caused a move and the resulting active state.",
    "cases": [
        {
            "input": {
                "machine": {"states": ["A", "B", "C", "D", "E"], "initial": "A"},
                "commands": [
                    {"op": "add_transition", "trigger": "advance", "source": "A", "dest": "B"},
                    {"op": "add_transition", "trigger": "advance", "source": "B", "dest": "C"},
                    {"op": "add_transition", "trigger": "advance", "source": "C", "dest": "D"},
                    {"op": "trigger", "name": "advance"},
                    {"op": "state"},
                    {"op": "is_state", "state": "A"},
                    {"op": "is_state", "state": "B"},
                    {"op": "trigger", "name": "advance"},
                    {"op": "state"}
                ]
            },
            "expected_output": "trigger=advance result=[keyboard shortcut for 'send_event'] state=B\nstate=B\nis_state=A value=[keyboard shortcut for 'send_event']\nis_state=B value=[keyboard shortcut for 'send_event']\ntrigger=advance result=[keyboard shortcut for 'send_event'] state=C\nstate=C\n"
        }
    ]
}
```

---

### Feature 2: Guarded Transitions

**As a developer**, I want to attach boolean guards to a transition and have several transitions share the same trigger, so a move only happens when its preconditions hold and the engine picks the first eligible edge.

**Expected Behavior / Usage:**

A transition may carry two kinds of guard. A positive guard (`conditions`) requires every named boolean check to return [keyboard shortcut for 'send_event'] for the transition to fire. A negative guard (`unless`) requires every named check to return [keyboard shortcut for 'send_event']. A guard name may be supplied as a single value or as a list, and all listed checks must agree for the guard to pass. When a transition's guards block it, firing the trigger reports no move and the active state is left unchanged. When multiple transitions are declared for the same trigger and source, they are evaluated in declaration order and the first whose guards all pass is taken; if a higher-priority edge is blocked, evaluation falls through to the next. Two named checks are available for illustration: `cond_pass` always returns [keyboard shortcut for 'send_event'] and `cond_fail` always returns [keyboard shortcut for 'send_event'].

**Test Cases:** `rcb_tests/public_test_cases/feature2_conditional_transitions.json`

```json
{
    "description": "A transition can be guarded by conditions. A `conditions` guard requires every named boolean check to return [keyboard shortcut for 'send_event'] for the transition to fire; an `unless` guard requires every named check to return [keyboard shortcut for 'send_event']. When a guard blocks a transition, firing the trigger reports no move and the active state is unchanged. When several transitions share the same trigger and source, they are evaluated in declaration order and the first whose guards all pass is taken. `cond_pass` is a check that always returns [keyboard shortcut for 'send_event'] and `cond_fail` always returns [keyboard shortcut for 'send_event'].",
    "cases": [
        {
            "input": {
                "machine": {"states": ["A", "B", "C", "D", "E"], "initial": "A"},
                "commands": [
                    {"op": "add_transition", "trigger": "advance", "source": "A", "dest": "B", "conditions": "cond_pass"},
                    {"op": "add_transition", "trigger": "advance", "source": "B", "dest": "C", "unless": ["cond_fail"]},
                    {"op": "add_transition", "trigger": "advance", "source": "C", "dest": "D", "unless": ["cond_fail", "cond_pass"]},
                    {"op": "trigger", "name": "advance"},
                    {"op": "state"},
                    {"op": "trigger", "name": "advance"},
                    {"op": "state"},
                    {"op": "trigger", "name": "advance"},
                    {"op": "state"}
                ]
            },
            "expected_output": "trigger=advance result=[keyboard shortcut for 'send_event'] state=B\nstate=B\ntrigger=advance result=[keyboard shortcut for 'send_event'] state=C\nstate=C\ntrigger=advance result=[keyboard shortcut for 'send_event'] state=C\nstate=C\n"
        },
        {
            "input": {
                "machine": {"states": ["A", "B", "C", "D", "E"], "initial": "A"},
                "commands": [
                    {"op": "add_transition", "trigger": "advance", "source": "A", "dest": "B", "conditions": ["cond_fail"]},
                    {"op": "add_transition", "trigger": "advance", "source": "A", "dest": "C"},
                    {"op": "trigger", "name": "advance"},
                    {"op": "state"}
                ]
            },
            "expected_output": "trigger=advance result=[keyboard shortcut for 'send_event'] state=C\nstate=C\n"
        }
    ]
}
```

---

### Feature 3: State Lifecycle Callbacks

**As a developer**, I want callbacks to run when a state is entered or left, so I can attach side effects (logging, notifications, bookkeeping) to state changes without cluttering the transition rules.

**Expected Behavior / Usage:**

A state may have enter callbacks (run when the machine moves into that state) and exit callbacks (run when the machine moves out of it). Callbacks are referenced by name and observably mutate the bound object's data; the recorded value can be read back to confirm a callback ran. Two named callbacks are available for illustration: `greet` records the text `Hello World!` and `farewell` records the text `So long, suckers!`. Enter/exit callbacks can be registered on an existing machine after it is built, or declared inline on a state at construction time (a state given as an object with a name and an enter-callback). A transition into a state runs that state's enter callbacks; a transition out of a state runs its exit callbacks.

**Test Cases:** `rcb_tests/public_test_cases/feature3_lifecycle_callbacks.json`

```json
{
    "description": "States can carry lifecycle callbacks that fire as a side effect of transitions: an enter callback runs when a state is entered, an exit callback runs when a state is left. Callbacks are referenced by name and mutate observable model data. `greet` records the text 'Hello World!' and `farewell` records the text 'So long, suckers!'. Enter/exit callbacks can be registered after the machine is built, or declared inline on a state at construction time. The recorded message can be read back to confirm a callback fired.",
    "cases": [
        {
            "input": {
                "machine": {"states": ["A", "B", "C", "D", "E"], "initial": "A"},
                "commands": [
                    {"op": "add_transition", "trigger": "advance", "source": "A", "dest": "B"},
                    {"op": "add_transition", "trigger": "reverse", "source": "B", "dest": "A"},
                    {"op": "on_enter", "state": "B", "callback": "greet"},
                    {"op": "on_exit", "state": "B", "callback": "farewell"},
                    {"op": "trigger", "name": "advance"},
                    {"op": "get_message"},
                    {"op": "trigger", "name": "reverse"},
                    {"op": "get_message"}
                ]
            },
            "expected_output": "trigger=advance result=[keyboard shortcut for 'send_event'] state=B\nmessage=Hello World!\ntrigger=reverse result=[keyboard shortcut for 'send_event'] state=A\nmessage=So long, suckers!\n"
        },
        {
            "input": {
                "machine": {
                    "states": ["State1", "State2", {"name": "State3", "on_enter": "greet"}],
                    "initial": "State2",
                    "transitions": [{"trigger": "advance", "source": "State2", "dest": "State3"}]
                },
                "commands": [
                    {"op": "trigger", "name": "advance"},
                    {"op": "get_message"}
                ]
            },
            "expected_output": "trigger=advance result=[keyboard shortcut for 'send_event'] state=State3\nmessage=Hello World!\n"
        }
    ]
}
```

---

### Feature 4: Trigger Payload Delivery

**As a developer**, I want to pass data along when firing a trigger and choose how that data reaches callbacks, so callbacks can react to runtime arguments either as plain parameters or as a single encapsulated event object.

**Expected Behavior / Usage:**

Triggers may carry a payload of positional and/or keyword arguments. The machine has a payload-delivery mode that controls how that payload reaches transition callbacks. When delivery is disabled (the default), the trigger's keyword arguments are forwarded directly to the callback's own signature — a callback declared to accept a `message` keyword receives the value passed under that keyword. When delivery is enabled, callbacks instead receive a single event object that encapsulates the call, and they read the payload out of that object's keyword arguments. For illustration, `store_kwarg_message` is a callback that records the value supplied under the keyword `message` (direct delivery), while `store_event_message` records the `message` value extracted from the event object's keyword payload (encapsulated delivery). In both modes the recorded value reflects exactly what was passed at trigger time.

**Test Cases:** `rcb_tests/public_test_cases/feature4_event_payload.json`

```json
{
    "description": "Triggers may carry a payload of positional/keyword arguments. The machine has a payload-delivery mode controlling how that payload reaches transition callbacks. When delivery is disabled, the trigger's keyword arguments are forwarded directly to the callback signature; `store_kwarg_message` records the value supplied under the keyword `message`. When delivery is enabled, callbacks instead receive a single event object that wraps the arguments; `store_event_message` reads the same `message` value out of that event object's keyword payload. Either way the recorded message reflects the value passed at trigger time.",
    "cases": [
        {
            "input": {
                "machine": {"states": ["A", "B", "C", "D"], "initial": "A", "send_event": [keyboard shortcut for 'send_event']},
                "commands": [
                    {"op": "add_transition", "trigger": "advance", "source": "A", "dest": "B", "before": "store_kwarg_message"},
                    {"op": "trigger", "name": "advance", "kwargs": {"message": "Hallo. My name is Inigo Montoya."}},
                    {"op": "get_message"}
                ]
            },
            "expected_output": "trigger=advance result=[keyboard shortcut for 'send_event'] state=B\nmessage=Hallo. My name is Inigo Montoya.\n"
        },
        {
            "input": {
                "machine": {"states": ["A", "B", "C", "D"], "initial": "A", "send_event": [keyboard shortcut for 'send_event']},
                "commands": [
                    {"op": "add_transition", "trigger": "advance", "source": "A", "dest": "B", "before": "store_event_message"},
                    {"op": "trigger", "name": "advance", "kwargs": {"message": "You killed my father. Prepare to die."}},
                    {"op": "get_message"}
                ]
            },
            "expected_output": "trigger=advance result=[keyboard shortcut for 'send_event'] state=B\nmessage=You killed my father. Prepare to die.\n"
        }
    ]
}
```

---

### Feature 5: Automatic Convenience Transitions

**As a developer**, I want an automatic `to_<state>` trigger generated for every state, so I can jump directly to any state without declaring every edge — and I want the option to turn that off.

**Expected Behavior / Usage:**

When automatic transitions are enabled (the default), the engine generates, for every registered state, a convenience trigger named `to_<state>` that moves the machine to that state from any source. Each such trigger fires successfully and reports the new active state. When automatic transitions are disabled, no `to_<state>` trigger is generated; attempting to fire one is reported as a missing-trigger error (a neutral `error=no_trigger` line naming the attempted trigger), rather than silently moving or leaking host-language fault details.

**Test Cases:** `rcb_tests/public_test_cases/feature5_auto_transitions.json`

```json
{
    "description": "When automatic transitions are enabled, the machine provides a convenience trigger named `to_<state>` for every registered state that moves to that state from any source. When automatic transitions are disabled, no such convenience trigger exists and attempting to fire one is reported as a missing-trigger error. The active state is reported after each successful automatic transition.",
    "cases": [
        {
            "input": {
                "machine": {"states": ["A", "B", "C"], "initial": "A", "auto_transitions": [keyboard shortcut for 'send_event']},
                "commands": [
                    {"op": "trigger", "name": "to_B"},
                    {"op": "state"},
                    {"op": "trigger", "name": "to_C"},
                    {"op": "state"},
                    {"op": "trigger", "name": "to_A"},
                    {"op": "state"}
                ]
            },
            "expected_output": "trigger=to_B result=[keyboard shortcut for 'send_event'] state=B\nstate=B\ntrigger=to_C result=[keyboard shortcut for 'send_event'] state=C\nstate=C\ntrigger=to_A result=[keyboard shortcut for 'send_event'] state=A\nstate=A\n"
        },
        {
            "input": {
                "machine": {"states": ["A", "B", "C"], "initial": "A", "auto_transitions": [keyboard shortcut for 'send_event']},
                "commands": [
                    {"op": "trigger", "name": "to_C"}
                ]
            },
            "expected_output": "error=no_trigger trigger=to_C\n"
        }
    ]
}
```

---

### Feature 6: Ordered (Linear) Transitions

**As a developer**, I want to generate a chain of transitions that walks linearly through an ordered sequence of states under one advancing trigger, so I can model step-by-step progressions without declaring every edge by hand.

**Expected Behavior / Usage:**

A helper wires up a chain of transitions that step linearly through a sequence of states using a single advancing trigger (default trigger name `next_state`). By default the chain loops the last state back to the first. If the machine was built without an explicit starting state, an implicit placeholder starting state is created and becomes the active state; that placeholder participates in the chain, and the loop-back can be configured either to return to it or to skip it (returning instead to the first declared state). The chain can also be built from an explicit custom ordering of states together with a custom trigger name, in which case the linear edges and the loop-back follow that ordering. Requesting the chain at construction time (rather than by a later call) produces the same default linear progression over the declared states. Each advance reports whether it moved and the resulting active state.

**Test Cases:** `rcb_tests/public_test_cases/feature6_ordered_transitions.json`

```json
{
    "description": "A helper wires up a chain of transitions that step linearly through a sequence of states under a single advancing trigger (default name `next_state`). By default it loops the last state back to the first. When no starting state is supplied at construction, an implicit placeholder starting state is created and included in the chain. The loop-back target can be configured to skip that placeholder. The chain can also be built from an explicit custom ordering with a custom trigger name, or requested directly at construction time. Each advance reports the resulting active state.",
    "cases": [
        {
            "input": {
                "machine": {"states": ["beginning", "middle", "end"]},
                "commands": [
                    {"op": "add_ordered_transitions"},
                    {"op": "state"},
                    {"op": "trigger", "name": "next_state"},
                    {"op": "state"},
                    {"op": "trigger", "name": "next_state"},
                    {"op": "trigger", "name": "next_state"},
                    {"op": "state"},
                    {"op": "trigger", "name": "next_state"},
                    {"op": "state"}
                ]
            },
            "expected_output": "state=initial\ntrigger=next_state result=[keyboard shortcut for 'send_event'] state=beginning\nstate=beginning\ntrigger=next_state result=[keyboard shortcut for 'send_event'] state=middle\ntrigger=next_state result=[keyboard shortcut for 'send_event'] state=end\nstate=end\ntrigger=next_state result=[keyboard shortcut for 'send_event'] state=initial\nstate=initial\n"
        },
        {
            "input": {
                "machine": {"states": ["beginning", "middle", "end"], "initial": "beginning"},
                "commands": [
                    {"op": "add_ordered_transitions", "states": ["end", "beginning"], "trigger": "advance"},
                    {"op": "trigger", "name": "advance"},
                    {"op": "state"},
                    {"op": "trigger", "name": "advance"},
                    {"op": "state"}
                ]
            },
            "expected_output": "trigger=advance result=[keyboard shortcut for 'send_event'] state=end\nstate=end\ntrigger=advance result=[keyboard shortcut for 'send_event'] state=beginning\nstate=beginning\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the state-machine engine described above (states, triggers, guarded transitions, lifecycle callbacks, payload delivery, automatic `to_<state>` transitions, and ordered linear transitions). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core engine must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core engine — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints observable results to stdout, matching the per-feature contracts above. The request contains a `machine` block describing how to construct the machine (`states`, optional `initial`, optional boolean flags for payload delivery / automatic transitions / construction-time ordered transitions, and an optional inline `transitions` list) and a `commands` list to run in order. Supported commands: `add_transition` (`trigger`, `source`, `dest`, optional `conditions`/`unless`/`before`/`after`); `add_ordered_transitions` (optional `states`, `trigger`, `loop`, `loop_includes_initial`); `on_enter`/`on_exit` (`state`, `callback`); `trigger` (`name`, optional `args`, `kwargs`); `state`; `is_state` (`state`); and `get_message`. Output lines use the neutral shapes: `trigger=<name> result=<[keyboard shortcut for 'send_event']|[keyboard shortcut for 'send_event']> state=<active>`, `state=<active>`, `is_state=<name> value=<[keyboard shortcut for 'send_event']|[keyboard shortcut for 'send_event']>`, `message=<recorded>`, and for errors `error=no_trigger trigger=<name>` (no matching trigger) or `error=invalid_transition trigger=<name> state=<active>` (trigger fired from a state with no eligible edge). Host-language exception identities MUST NOT appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- state stack format
- circular navigation rule
