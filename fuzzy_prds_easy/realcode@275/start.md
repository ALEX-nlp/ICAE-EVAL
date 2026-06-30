## Product Requirement Document

# Saga Workflow Verification Toolkit - Standardized I/O Contract

## Project Goal

Build a testing toolkit for generator-based asynchronous workflows (sagas) that lets developers verify a workflow's externally-observable behavior — the coordination instructions it yields (wait for an action, emit an action, invoke a function, read state, start background work), the values it returns, and the store state it produces — without coupling the test to the workflow's exact internal implementation. The toolkit offers two complementary styles: a step-by-step walker for precise unit assertions, and a run-to-completion runner for order-independent integration assertions.

---

## Background & Problem

A saga is a long-running generator that coordinates side effects by *yielding* descriptive instructions ("wait for action X", "call function F with these args", "emit action Y", "read state via selector S") to an external runtime that actually performs them. Testing such a workflow is awkward. If you assert on raw yielded values you couple the test to the precise ordering and shape of every yield, so an innocuous reorder breaks the test even though behavior is unchanged. If instead you run the real runtime, you must bootstrap stores, reducers, timers, and real network/IO just to observe one effect.

This toolkit removes that friction. The **step-by-step walker** drives the workflow one resume at a time, lets you inject the value each resume produces, lets you rewind, bookmark/restore positions, restart with new arguments, finish early, or throw an error into the workflow, and after each step asserts the yielded instruction against an expected one — reporting a per-assertion `met`/`unmet` verdict. The **run-to-completion runner** executes the whole workflow against an optional state snapshot or reducer, lets you mock the result (or thrown error) of intercepted effects, dispatch actions the workflow is waiting for, and then make order-independent assertions ("it emitted this action at some point", "it invoked this function", "it read state via this selector", "its final return value / store state was this") — each reported as a per-expectation `met`/`unmet` verdict. A small pattern-serialization utility renders action-matching patterns to stable strings.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility library (a step walker, a whole-run engine, effect matching, value/state comparison, mocking interception, output formatting). It MUST NOT be a single "god file"; output a clear multi-file tree (core domain modules, an execution adapter, and tests) that reflects a production-grade repository. Do not over-engineer, but keep the walker, the runner, the matchers, and the adapter in distinct units.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, not the internal data model of the core toolkit. The core logic must remain decoupled from stdin/stdout and JSON parsing. The adapter alone translates JSON commands into idiomatic calls on the core API and renders results to the line-based stdout contract.

3. **Adherence to SOLID Design Principles:** Separate parsing/routing, effect construction, matching/comparison, execution, and output formatting (SRP). The matching engine must be open to new effect kinds without modification (OCP). Effect kinds must be substitutable wherever a generic effect is expected (LSP). Keep the walker API and the runner API as small, cohesive interfaces (ISP). High-level assertion logic must depend on an abstract notion of "effect" / "comparison", not on concrete IO primitives (DIP).

4. **Robustness & Interface Design:** The public API must be elegant and idiomatic to the target language, hiding internal complexity. Edge cases (rewinding past the start, restoring an unknown bookmark, asserting completion/return before the workflow finishes, a workflow that blocks forever waiting on an action that is never dispatched) must be handled gracefully and modeled explicitly. Errors must be modeled as proper categories rather than generic faults, and a blocked run must be bounded by an internal timeout so it always terminates.

---

## Core Features

### Feature 1: Step-by-Step Workflow Walker

**As a developer**, I want to drive a workflow one resume at a time and assert exactly what instruction each step yields, so I can pinpoint precisely where behavior diverges.

**Expected Behavior / Usage:**

A command has `mode: "unit"`, a `saga` (with optional `args`, a `body` of statements, and an optional `catch` recovery body), and an ordered list of `steps`. A `body`/`catch` statement is one of: `{"yield": <effect>, "as": <name>?}` (yield a coordination instruction and optionally bind the resumed value to a name reusable later via `{"$var": name}`), `{"put": <action>}` (shorthand for yielding an emit-action instruction), or `{"return": <value>}`. Effect descriptors are `{"take": <pattern>}`, `{"put": <action>}`, `{"call": {"fn": <name>, "args": [...]}}`, `{"fork": {...}}`, `{"spawn": {...}}`, `{"select": {"selector": <name>}}`, or `{"all": [<effect>, ...]}`. Function and selector names are neutral labels resolved to stable references so identity-based matching is meaningful; positional workflow arguments are exposed as `arg0`, `arg1`, …; `{"$op": "add"|"sub"|"mul", "args": [...]}` computes a numeric value.

Each step is `{"next": true}` (advance), `{"nextWith": <value>}` (advance injecting a value the workflow receives from its last yield), or `{"assert": <assertion>}`. Each `assert` prints one line `assertion <n> met` or `assertion <n> unmet`, where `<n>` counts asserts in order. The toolkit must short-circuit a step run only on a navigation error (Feature 2.6); ordinary assertion mismatches do NOT stop the walk.

*1.1 Sequential effect assertions — assert each yielded coordination instruction in order*

After each advance, assert the current instruction equals an expected one (wait-for-action by pattern, emit-action by full action, invoke-function by function + args, background-invoke by function + args). A final completion assert confirms the workflow is exhausted. Resuming with an injected value lets later steps read that value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_sequential_effects.json`

```json
{
    "description": "Walk a generator-based workflow one step at a time and assert that each step yields the expected coordination instruction (wait-for-action, emit-action, invoke-function, background-invoke) in order, then assert the sequence is exhausted. Stepping advances the generator; an optional injected value can be passed to a resume so later steps observe it.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"args": [40, 2, 20], "body": [{"yield": {"take": "HELLO"}}, {"yield": {"put": {"type": "ADD", "payload": {"$op": "add", "args": [{"$var": "arg0"}, {"$var": "arg1"}]}}}}, {"yield": {"call": {"fn": "identity", "args": [7]}}}, {"yield": {"fork": {"fn": "otherSaga", "args": [{"$var": "arg2"}]}}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 42}}}, {"next": true}, {"assert": {"call": {"fn": "identity", "args": [7]}}}, {"next": true}, {"assert": {"fork": {"fn": "otherSaga", "args": [20]}}}, {"next": true}, {"assert": {"isDone": true}}]}, "expected_output": "assertion 1 met\nassertion 2 met\nassertion 3 met\nassertion 4 met\nassertion 5 met\n"},
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "REQUEST"}, "as": "action"}, {"yield": {"select": {"selector": "getName"}}}]}, "steps": [{"next": true}, {"assert": {"take": "REQUEST"}}, {"nextWith": {"type": "REQUEST"}}, {"assert": {"select": {"selector": "getName"}}}]}, "expected_output": "assertion 1 met\nassertion 2 met\n"}
    ]
}
```


*1.2 Effect mismatch reporting — a wrong expected instruction is reported unmet*

When the asserted instruction differs from what was yielded (wrong action pattern, wrong emitted action type or payload, wrong invoked function, or wrong arguments), that assertion is `unmet` while preceding asserts keep their verdicts.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_effect_mismatch.json`

```json
{
    "description": "When a step-by-step assertion expects a particular coordination instruction but the generator yielded a different one (wrong action pattern, wrong emitted action type or payload, wrong invoked function or arguments), the assertion is reported as unmet. The walker keeps emitting verdicts per assertion.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}]}, "steps": [{"next": true}, {"assert": {"take": "WORLD"}}]}, "expected_output": "assertion 1 unmet\n"},
        {"input": {"mode": "unit", "saga": {"args": [40, 2], "body": [{"yield": {"take": "HELLO"}}, {"yield": {"put": {"type": "ADD", "payload": 42}}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 43}}}]}, "expected_output": "assertion 1 met\nassertion 2 unmet\n"}
    ]
}
```


*1.3 Completion assertion — confirm the workflow has finished*

A completion assertion is `met` only when the generator is exhausted; asserting completion while steps remain is `unmet`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_completion.json`

```json
{
    "description": "Assert that the workflow has finished. A completion assertion is met only when the generator is exhausted; asserting completion while steps remain reports unmet.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}]}, "steps": [{"next": true}, {"next": true}, {"assert": {"isDone": true}}]}, "expected_output": "assertion 1 met\n"},
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}]}, "steps": [{"next": true}, {"assert": {"isDone": true}}]}, "expected_output": "assertion 1 unmet\n"}
    ]
}
```


*1.4 Raw yielded value assertion — compare the raw yielded value by deep equality*

Assert the raw value yielded at the current step deep-equals an expected value (primitives and nested objects), independent of any instruction shape. A non-matching value is `unmet`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_raw_value.json`

```json
{
    "description": "Assert the raw value yielded at the current step equals an expected value (deep equality over primitives and nested objects), independent of any coordination-instruction shape. A non-matching value reports unmet.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"put": {"type": "IGNORED"}}}, {"return": 42}]}, "steps": [{"next": true}, {"next": true}, {"assert": {"is": 42}}]}, "expected_output": "assertion 1 met\n"},
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"put": {"type": "IGNORED"}}}, {"return": {"hello": "world", "foo": {"bar": "baz"}}}]}, "steps": [{"next": true}, {"next": true}, {"assert": {"is": {"hello": "world", "foo": {"bar": "baz"}}}}]}, "expected_output": "assertion 1 met\n"}
    ]
}
```


*1.5 Return value assertion — assert the workflow's completed return value*

A return assertion is `met` only when the workflow has finished AND its returned value deep-equals the expected value. Asserting a return value before completion, or with a mismatching value, is `unmet`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_return_value.json`

```json
{
    "description": "Assert the workflow's final return value once it has completed. The return assertion is met only when the generator has finished AND the returned value deep-equals the expected value; asserting a return value before completion, or with a mismatching value, reports unmet.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"args": [1], "body": [{"put": {"type": "OTHER", "payload": "hi"}}, {"return": {"$var": "arg0"}}]}, "steps": [{"next": true}, {"assert": {"put": {"type": "OTHER", "payload": "hi"}}}, {"next": true}, {"assert": {"returns": 1}}]}, "expected_output": "assertion 1 met\nassertion 2 met\n"},
        {"input": {"mode": "unit", "saga": {"args": [1], "body": [{"put": {"type": "OTHER", "payload": "hi"}}, {"return": {"$var": "arg0"}}]}, "steps": [{"next": true}, {"next": true}, {"assert": {"returns": "foobar"}}]}, "expected_output": "assertion 1 unmet\n"}
    ]
}
```


*1.6 Parallel effect group assertion — assert a step yields a group of effects to run together*

Assert that a single step yields a group of effects to run in parallel, expressed either as an explicit parallel group or as a plain array of effects, both matched against an expected list. A wrong member effect is `unmet`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_parallel_effects.json`

```json
{
    "description": "Assert that a single step yields a group of effects to run in parallel. The group may be expressed by the workflow either as an explicit parallel-group instruction or as a plain array of effects; both are matched against an expected list of effects. A wrong member effect in the group reports unmet.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"all": [{"call": {"fn": "identity"}}, {"put": {"type": "[specific pattern instance format for arrays]"}}]}}]}, "steps": [{"next": true}, {"assert": {"all": [{"call": {"fn": "identity"}}, {"put": {"type": "[specific pattern instance format for arrays]"}}]}}]}, "expected_output": "assertion 1 met\n"},
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"all": [{"call": {"fn": "identity"}}, {"put": {"type": "[specific pattern instance format for arrays]"}}]}}]}, "steps": [{"next": true}, {"assert": {"all": [{"call": {"fn": "identity"}}, {"put": {"type": "[specific pattern instance format for arrays]"}}]}}]}, "expected_output": "assertion 1 unmet\n"}
    ]
}
```


---

### Feature 2: Walk Navigation & Control

**As a developer**, I want to rewind, bookmark, restart, finish, and inject errors while walking, so I can explore branches and recovery paths without rebuilding the workflow each time.

**Expected Behavior / Usage:**

Additional step kinds operate on the walk position: `{"back": <n>}` rewinds `n` positions, `{"save": <name>}` bookmarks the current position, `{"restore": <name>}` returns to a bookmark (replaying up to it), `{"restart": [<args>...]}` restarts from the beginning (optionally with new arguments), `{"finish": true}` / `{"finishWith": <value>}` ends the workflow early (optionally as if it returned a value), and `{"throw": {"message": <text>}}` injects an error into the workflow at the current step.

*2.1 Step back — rewind one or more positions and re-examine the upcoming step*

After rewinding, advancing again re-yields the instruction from that earlier position, so the same step can be asserted again.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_step_back.json`

```json
{
    "description": "Rewind the step-by-step walk. Stepping back one or several positions returns the walk to an earlier point so the same upcoming step can be re-examined. After rewinding, advancing again re-yields the effect from that position.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}, {"yield": {"put": {"type": "ADD", "payload": 42}}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"back": 1}, {"next": true}, {"assert": {"take": "HELLO"}}]}, "expected_output": "assertion 1 met\nassertion 2 met\n"},
        {"input": {"mode": "unit", "saga": {"args": [40, 2], "body": [{"yield": {"take": "HELLO"}}, {"yield": {"put": {"type": "ADD", "payload": 42}}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 42}}}, {"back": 2}, {"next": true}, {"assert": {"take": "HELLO"}}]}, "expected_output": "assertion 1 met\nassertion 2 met\nassertion 3 met\n"}
    ]
}
```


*2.2 Bookmark and restore — jump back to a named position*

Bookmark the current position under a name, then later return to that exact bookmark; the walk replays up to it and subsequent steps continue from there.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_save_restore.json`

```json
{
    "description": "Bookmark the current position under a name and later jump back to that exact bookmark, replaying the workflow up to that point so subsequent steps continue from there.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}, {"yield": {"put": {"type": "ADD", "payload": 42}}}, {"yield": {"call": {"fn": "identity", "args": [1]}}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"save": "afterTake"}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 42}}}, {"restore": "afterTake"}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 42}}}]}, "expected_output": "assertion 1 met\nassertion 2 met\nassertion 3 met\n"}
    ]
}
```


*2.3 Restart — re-run from the beginning, optionally with new arguments*

Restarting re-runs the workflow from its first step. Supplying new arguments changes any values derived from them on the second run.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_restart.json`

```json
{
    "description": "Restart the walk from the very beginning, optionally with new starting arguments. After restart the workflow re-runs from its first step; new arguments change values derived from them on the second run.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"args": [40, 2], "body": [{"yield": {"take": "HELLO"}}, {"yield": {"put": {"type": "ADD", "payload": {"$op": "add", "args": [{"$var": "arg0"}, {"$var": "arg1"}]}}}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 42}}}, {"restart": []}, {"next": true}, {"assert": {"take": "HELLO"}}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 42}}}]}, "expected_output": "assertion 1 met\nassertion 2 met\nassertion 3 met\nassertion 4 met\n"},
        {"input": {"mode": "unit", "saga": {"args": [40, 2], "body": [{"yield": {"take": "HELLO"}}, {"yield": {"put": {"type": "ADD", "payload": {"$op": "add", "args": [{"$var": "arg0"}, {"$var": "arg1"}]}}}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 42}}}, {"restart": [20, 1]}, {"next": true}, {"assert": {"take": "HELLO"}}, {"next": true}, {"assert": {"put": {"type": "ADD", "payload": 21}}}]}, "expected_output": "assertion 1 met\nassertion 2 met\nassertion 3 met\nassertion 4 met\n"}
    ]
}
```


*2.4 Finish early — end the workflow before it would naturally complete*

Finishing drives the workflow to completion so a later completion assertion is `met`; a supplied finish value is observable by a return assertion.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_finish_early.json`

```json
{
    "description": "Terminate the walk early before the workflow would naturally finish, optionally supplying a value as if the workflow had returned it. Finishing drives the workflow to completion so a subsequent completion assertion is met, and a supplied finish value is observable by a return assertion.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}, {"yield": {"call": {"fn": "identity", "args": [1]}}}, {"yield": {"take": "HELLO"}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"next": true}, {"assert": {"call": {"fn": "identity", "args": [1]}}}, {"finish": true}, {"next": true}, {"assert": {"isDone": true}}]}, "expected_output": "assertion 1 met\nassertion 2 met\nassertion 3 met\n"},
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}, {"yield": {"call": {"fn": "identity", "args": [1]}}}]}, "steps": [{"next": true}, {"assert": {"take": "HELLO"}}, {"finishWith": 42}, {"assert": {"returns": 42}}]}, "expected_output": "assertion 1 met\nassertion 2 met\n"}
    ]
}
```


*2.5 Throw into the workflow — divert into the recovery branch*

Injecting an error into a workflow that wraps its body in error-handling diverts execution into the recovery branch, where the thrown error becomes available and recovery effects (e.g. emitting an error action that carries the error) can be asserted.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_throw_into_workflow.json`

```json
{
    "description": "Inject an error into the workflow at the current step. A workflow that wraps its body in error-handling diverts into the recovery branch, where the thrown error becomes available and the recovery effects (e.g. emitting an error action carrying the error) can be asserted.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}], "catch": [{"put": {"type": "ERROR", "payload": {"$var": "error"}}}]}, "steps": [{"next": true}, {"throw": {"message": "My Error"}}, {"assert": {"put": {"type": "ERROR", "payload": {"$error": "My Error"}}}}, {"next": true}, {"assert": {"isDone": true}}]}, "expected_output": "assertion 1 met\nassertion 2 met\n"}
    ]
}
```


*2.6 Navigation errors — language-neutral error categories*

Navigation faults are reported as a neutral `error=<category>` line (and, where relevant, a separate data field) rather than leaking any runtime exception detail. Rewinding further back than the number of steps taken yields `error=cannot_step_back`. Restoring a bookmark that was never created yields `error=unknown_save_point` plus a `detail=<name>` line carrying the requested name.

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_navigation_errors.json`

```json
{
    "description": "Navigation errors are reported as language-neutral error categories on a separate line. Rewinding further back than the number of steps taken yields a step-back-limit error; jumping to a bookmark that was never created yields an unknown-bookmark error with the requested name in its own field.",
    "cases": [
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}]}, "steps": [{"back": 1}]}, "expected_output": "error=cannot_step_back\n"},
        {"input": {"mode": "unit", "saga": {"body": [{"yield": {"take": "HELLO"}}]}, "steps": [{"next": true}, {"back": 2}]}, "expected_output": "error=cannot_step_back\n"}
    ]
}
```


---

### Feature 3: Run-to-Completion Integration Assertions

**As a developer**, I want to run the whole workflow and assert what it did without caring about ordering, so my tests survive refactors that only change effect ordering.

**Expected Behavior / Usage:**

A command has `mode: "integration"`, a `saga` (same shape as Feature 1), optional `state` (a state snapshot), optional `dispatch` (a list of actions fed to the workflow's wait-for-action points), an `expect` list of order-independent expectations, and an optional `report` list. Each expectation prints `expectation <n> met` / `expectation <n> unmet` in order; then each `report` field prints zero or more data lines. Report fields: `put` (each emitted action as `put=<wire-format action>`), `call`/`select` (each invocation as `name(arg, ...)`), `take` (each awaited pattern), `returnValue`, and `storeState`. Wire-format objects render with keys sorted, e.g. `{"payload": 42, "type": "READY"}`. A workflow that blocks waiting for an action that is never dispatched is bounded by an internal timeout so expectations still resolve. Every expectation has a negated form prefixed with `not.`.

*3.1 Emitted-action expectation — assert an action was (or was not) emitted*

Assert the workflow emitted a given action at some point: match the full action (`put`), match only the action type (`putType`), or negate either (`not.put`, `not.putType`). The `put` report exposes each emitted action's wire format.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_emitted_action.json`

```json
{
    "description": "Run the whole workflow to completion and assert that it emitted a given action at some point, regardless of ordering. Assertions can match the full action (type + payload), match only the action type, or be negated to assert an action was NOT emitted. A report of emitted actions exposes the wire-format of each emitted action.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"put": {"type": "READY", "payload": 42}}]}, "expect": [{"put": {"type": "READY", "payload": 42}}, {"putType": "READY"}, {"not.put": {"type": "[specific pattern instance format for arrays]", "payload": 42}}, {"not.put": {"type": "READY", "payload": 43}}, {"not.putType": "[specific pattern instance format for arrays]"}], "report": ["put"]}, "expected_output": "expectation 1 met\nexpectation 2 met\nexpectation 3 met\nexpectation 4 met\nexpectation 5 met\nput={\"payload\": 42, \"type\": \"READY\"}\n"},
        {"input": {"mode": "integration", "saga": {"body": [{"put": {"type": "READY", "payload": 42}}]}, "expect": [{"put": {"type": "[specific pattern instance format for arrays]", "payload": 42}}, {"put": {"type": "READY", "payload": 43}}, {"not.put": {"type": "READY", "payload": 42}}, {"putType": "[specific pattern instance format for arrays]"}, {"not.putType": "READY"}]}, "expected_output": "expectation 1 unmet\nexpectation 2 unmet\nexpectation 3 unmet\nexpectation 4 unmet\nexpectation 5 unmet\n"}
    ]
}
```


*3.2 Function-invocation expectation — assert a function was invoked*

Assert a function was invoked: exact function-and-arguments (`call`), function only (`callFn`), partial function-and-arguments shape (`callMatch`), or any negated form. The `call` report exposes each invocation as `name(args)`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_function_invocation.json`

```json
{
    "description": "Run the whole workflow and assert that a given function was invoked. Matching can require exact function-and-arguments, match the function only, match a partial function-and-arguments shape, or be negated. A report of invocations exposes each invoked function name with its arguments.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"args": [42], "body": [{"yield": {"call": {"fn": "identity", "args": [{"$var": "arg0"}]}}}]}, "expect": [{"call": {"fn": "identity", "args": [42]}}, {"callFn": "identity"}, {"callMatch": {"fn": "identity", "args": [42]}}, {"not.call": {"fn": "identity", "args": [43]}}, {"not.callFn": "double"}, {"not.callMatch": {"fn": "identity", "args": [43]}}], "report": ["call"]}, "expected_output": "expectation 1 met\nexpectation 2 met\nexpectation 3 met\nexpectation 4 met\nexpectation 5 met\nexpectation 6 met\ncall=identity(42)\n"},
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"call": {"fn": "identity"}}}]}, "expect": [{"call": {"fn": "double"}}, {"callFn": "double"}, {"not.call": {"fn": "identity"}}, {"not.callFn": "identity"}]}, "expected_output": "expectation 1 unmet\nexpectation 2 unmet\nexpectation 3 unmet\nexpectation 4 unmet\n"}
    ]
}
```


*3.3 State-selection expectation — assert state was read through a selector*

Run against a `state` snapshot and assert the workflow read state through a given selector: exact selector (`select`), selector-only partial match (`selectFn`), or negated forms. The `select` report exposes selector invocations.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_state_selection.json`

```json
{
    "description": "Run the whole workflow against a provided state snapshot and assert that it read state through a given selector. Matching can require the exact selector, match the selector partially, or be negated. A report exposes the selector invocations.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"select": {"selector": "getName"}}, "as": "n"}, {"put": {"type": "DATA", "payload": {"$var": "n"}}}]}, "state": {"name": "Tucker", "age": 11}, "expect": [{"select": {"selector": "getName"}}, {"selectFn": {"selector": "getName"}}, {"not.select": {"selector": "getAge"}}, {"not.selectFn": {"selector": "getAge"}}, {"put": {"type": "DATA", "payload": "Tucker"}}], "report": ["select", "put"]}, "expected_output": "expectation 1 met\nexpectation 2 met\nexpectation 3 met\nexpectation 4 met\nexpectation 5 met\nselect=getName()\nput={\"payload\": \"Tucker\", \"type\": \"DATA\"}\n"},
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"select": {"selector": "getName"}}, "as": "n"}, {"put": {"type": "DATA", "payload": {"$var": "n"}}}]}, "state": {"name": "Tucker", "age": 11}, "expect": [{"select": {"selector": "getAge"}}, {"selectFn": {"selector": "getAge"}}, {"not.select": {"selector": "getName"}}]}, "expected_output": "expectation 1 unmet\nexpectation 2 unmet\nexpectation 3 unmet\n"}
    ]
}
```


*3.4 Awaited-action expectation — assert the workflow waited for a pattern*

Assert the workflow waited for a given action pattern (`take`) or negate it (`not.take`). With no matching action dispatched, the run is bounded by the internal timeout so the verdict still resolves.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_awaited_action.json`

```json
{
    "description": "Run the whole workflow and assert that it waited for a given action pattern. The assertion can match the awaited pattern or be negated. With no matching action ever dispatched, the run is bounded by an internal timeout so the assertion still resolves.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"take": "READY"}}]}, "expect": [{"take": "READY"}, {"not.take": "[specific pattern instance format for arrays]"}], "report": ["take"]}, "expected_output": "expectation 1 met\nexpectation 2 met\ntake=READY\n"},
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"take": "READY"}}]}, "expect": [{"take": "[specific pattern instance format for arrays]"}, {"not.take": "READY"}]}, "expected_output": "expectation 1 unmet\nexpectation 2 unmet\n"}
    ]
}
```


*3.5 Return-value expectation — assert the completed return value*

Assert the workflow's final return value by deep equality (`returns`) or negate it (`not.returns`). The `returnValue` report exposes the value. Background fire-and-forget work does not change the parent workflow's return value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_return_value.json`

```json
{
    "description": "Run the whole workflow and assert its final return value (deep equality), or negate it. A report exposes the workflow's return value. Background work started with fire-and-forget effects does not change the parent workflow's return value.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"return": {"foo": "bar"}}]}, "expect": [{"returns": {"foo": "bar"}}, {"not.returns": {"hello": "world"}}], "report": ["returnValue"]}, "expected_output": "expectation 1 met\nexpectation 2 met\nreturnValue={\"foo\": \"bar\"}\n"},
        {"input": {"mode": "integration", "saga": {"body": [{"return": {"foo": "bar"}}]}, "expect": [{"returns": {"hello": "world"}}, {"not.returns": {"foo": "bar"}}]}, "expected_output": "expectation 1 unmet\nexpectation 2 unmet\n"}
    ]
}
```


---

### Feature 4: Stateful Runs with a Reducer

**As a developer**, I want to run the workflow against a real reducer so dispatched actions mutate the store and selectors observe the change, so I can test state-dependent behavior end to end.

**Expected Behavior / Usage:**

A command may include `reducer` (a named reducer wired into the run) and optional `initialState`. Dispatched actions pass through the reducer, updating the store; selectors read the updated state. The `dog` reducer starts at `{"name": "Tucker", "age": 11}` and, on a `HAVE_BIRTHDAY` action, increments `age`.

*4.1 Reducer-driven state transitions — selectors observe pre/post-dispatch state*

Assert intermediate emitted actions whose payloads come from state read before and after a dispatched action mutates it; inspect the final store state. The reducer works with or without an explicitly supplied initial state.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_reducer_integration.json`

```json
{
    "description": "Run the whole workflow wired to a state reducer so that dispatched actions update the store and selectors observe the updated state. Assert intermediate emitted actions whose payloads come from state read before and after a dispatched action mutates it, and inspect the final store state. The reducer may be used with or without an explicitly supplied initial state.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"select": {"selector": "getAge"}}, "as": "before"}, {"put": {"type": "AGE_BEFORE", "payload": {"$var": "before"}}}, {"yield": {"take": "HAVE_BIRTHDAY"}}, {"yield": {"select": {"selector": "getAge"}}, "as": "after"}, {"put": {"type": "AGE_AFTER", "payload": {"$var": "after"}}}]}, "reducer": "dog", "dispatch": [{"type": "HAVE_BIRTHDAY"}], "expect": [{"put": {"type": "AGE_BEFORE", "payload": 11}}, {"put": {"type": "AGE_AFTER", "payload": 12}}], "report": ["storeState"]}, "expected_output": "expectation 1 met\nexpectation 2 met\nstoreState={\"age\": 12, \"name\": \"Tucker\"}\n"},
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"select": {"selector": "getAge"}}, "as": "before"}, {"put": {"type": "AGE_BEFORE", "payload": {"$var": "before"}}}, {"yield": {"take": "HAVE_BIRTHDAY"}}, {"yield": {"select": {"selector": "getAge"}}, "as": "after"}, {"put": {"type": "AGE_AFTER", "payload": {"$var": "after"}}}]}, "reducer": "dog", "initialState": {"name": "Tucker", "age": 11}, "dispatch": [{"type": "HAVE_BIRTHDAY"}], "expect": [{"put": {"type": "AGE_BEFORE", "payload": 11}}, {"put": {"type": "AGE_AFTER", "payload": 11}}]}, "expected_output": "expectation 1 met\nexpectation 2 unmet\n"}
    ]
}
```


*4.2 Final store state expectation — assert the resulting store state*

Assert the final store state by deep equality (`finalState`) or negate it (`not.finalState`); the `storeState` report exposes the resulting state.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_final_state.json`

```json
{
    "description": "Run the whole workflow wired to a state reducer and assert the final store state by deep equality, or negate it. The report exposes the final store state for direct inspection.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"take": "HAVE_BIRTHDAY"}}, {"yield": {"select": {"selector": "getAge"}}, "as": "a"}, {"put": {"type": "AGE", "payload": {"$var": "a"}}}]}, "reducer": "dog", "dispatch": [{"type": "HAVE_BIRTHDAY"}], "expect": [{"finalState": {"name": "Tucker", "age": 12}}, {"not.finalState": {"name": "Tucker", "age": 11}}], "report": ["storeState"]}, "expected_output": "expectation 1 met\nexpectation 2 met\nstoreState={\"age\": 12, \"name\": \"Tucker\"}\n"},
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"take": "HAVE_BIRTHDAY"}}, {"yield": {"select": {"selector": "getAge"}}, "as": "a"}, {"put": {"type": "AGE", "payload": {"$var": "a"}}}]}, "reducer": "dog", "dispatch": [{"type": "HAVE_BIRTHDAY"}], "expect": [{"finalState": {"name": "Tucker", "age": 11}}, {"not.finalState": {"name": "Tucker", "age": 12}}]}, "expected_output": "expectation 1 unmet\nexpectation 2 unmet\n"}
    ]
}
```


---

### Feature 5: Mocking Intercepted Effects

**As a developer**, I want to intercept effects and supply mock results (or errors) instead of performing them, so I can test workflows without real IO or non-deterministic dependencies.

**Expected Behavior / Usage:**

A command may include `mocks`, a list of interceptors. A function-invocation interceptor `{"call": {"fn": <name>, "args": [...]?, "value": <v>}}` returns `v` instead of invoking the function; `{"call": {"fn": <name>, "throw": {"message": <text>}}}` makes the intercepted invocation throw instead. A state-selection interceptor `{"select": {"selector": <name>, "value": <v>}}` returns `v` instead of reading state. Effects not matched by any interceptor are performed normally.

*5.1 Mock a function-invocation result — supply a return value*

The workflow continues using the mocked value, so a downstream emitted action carries the mocked result.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_mock_call_value.json`

```json
{
    "description": "Intercept a function-invocation effect during a whole-workflow run and supply a mock return value instead of actually calling the function. The workflow continues using the mocked value, so a downstream emitted action carries the mocked result.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"call": {"fn": "apiFn", "args": [21]}}, "as": "v"}, {"yield": {"call": {"fn": "otherApiFn"}}, "as": "w"}, {"put": {"type": "DONE", "payload": {"$op": "add", "args": [{"$var": "v"}, {"$var": "w"}]}}}]}, "mocks": [{"call": {"fn": "apiFn", "args": [21], "value": 42}}, {"call": {"fn": "otherApiFn", "value": 1}}], "expect": [{"put": {"type": "DONE", "payload": 43}}]}, "expected_output": "expectation 1 met\n"}
    ]
}
```


*5.2 Mock a function-invocation error — make the invocation throw*

A workflow that wraps the invocation in error-handling diverts into its recovery branch, where the thrown error is captured and an error action carrying it is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_mock_call_throws.json`

```json
{
    "description": "Configure an intercepted function-invocation effect to throw a provided error instead of returning. A workflow that wraps the invocation in error-handling diverts into its recovery branch, where the thrown error is captured and an error action carrying it is emitted.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"call": {"fn": "errorFn"}}}], "catch": [{"put": {"type": "DONE", "payload": {"$var": "error"}}}]}, "mocks": [{"call": {"fn": "errorFn", "throw": {"message": "Whoops..."}}}], "expect": [{"putType": "DONE"}]}, "expected_output": "expectation 1 met\n"}
    ]
}
```


*5.3 Mock a state-selection result — supply a selected value*

A mocked selection returns the supplied value while non-mocked selections still read real state; the workflow combines mocked and real values into a downstream action.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_mock_select_value.json`

```json
{
    "description": "Intercept a state-selection effect during a whole-workflow run and supply a mock selected value instead of reading from the actual state, while non-mocked selections still read real state. The workflow combines mocked and real values into a downstream emitted action.",
    "cases": [
        {"input": {"mode": "integration", "saga": {"body": [{"yield": {"select": {"selector": "getName"}}, "as": "mocked"}, {"yield": {"select": {"selector": "getAge"}}, "as": "real"}, {"put": {"type": "DONE", "payload": {"name": {"$var": "mocked"}, "age": {"$var": "real"}}}}]}, "state": {"name": "Tucker", "age": 11}, "mocks": [{"select": {"selector": "getName", "value": "Rex"}}], "expect": [{"put": {"type": "DONE", "payload": {"name": "Rex", "age": 11}}}]}, "expected_output": "expectation 1 met\n"}
    ]
}
```


---

### Feature 6: Action-Pattern Serialization

**As a developer**, I want a stable string rendering of an action-matching pattern, so I can display or compare patterns deterministically.

**Expected Behavior / Usage:**

A command `{"mode": "serialize_pattern", "pattern": <pattern>}` renders the pattern. A string pattern is returned verbatim; an array of patterns becomes a comma-separated bracketed list; an empty array becomes `[]`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_pattern_serialization.json`

```json
{
    "description": "Serialize an action-matching pattern to a stable human-readable string. A string pattern is returned verbatim; an array of patterns is rendered as a comma-separated bracketed list (empty array renders as empty brackets).",
    "cases": [
        {"input": {"mode": "serialize_pattern", "pattern": "[specific pattern instance format for arrays]"}, "expected_output": "[specific pattern instance format for arrays]\n"},
        {"input": {"mode": "serialize_pattern", "pattern": ["[specific pattern instance format for arrays]", "[specific pattern instance format for arrays]", "[specific pattern instance format for arrays]"]}, "expected_output": "[[specific pattern instance format for arrays], [specific pattern instance format for arrays], [specific pattern instance format for arrays]]\n"},
        {"input": {"mode": "serialize_pattern", "pattern": []}, "expected_output": "[]\n"}
    ]
}
```


---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the step-by-step walker, the run-to-completion runner, effect matching, value/state comparison, and effect-mocking described above, with a public API idiomatic to the target language.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the appropriate core logic, and prints the language-neutral line-based contract to stdout, strictly matching the per-leaf-feature contracts above. The adapter must be logically (and ideally physically) separated from the core domain, and must normalize any error into a neutral `error=<category>` form — never leaking host-language exception classes, runtime message suffixes, or object-repr output.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_sequential_effects.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_sequential_effects@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- resume with the same payload logic as 'nextWith' for data injection
