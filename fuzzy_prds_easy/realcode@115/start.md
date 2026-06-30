## Product Requirement Document

# Runtime Function-Behavior Override Toolkit — Replace, Guard, and Verify Function Behavior at Run Time

## Project Goal

Build a toolkit that lets a program **temporarily replace the behavior of an existing function at run time** — without altering that function's source, its signature, or the call sites that use it. A caller installs an *override* that intercepts a chosen target function; while the override is installed the target produces the substituted behavior, and once the override's lifetime ends the original behavior is restored. The toolkit must support overriding plain predicates, value-returning operations, functions with by-reference output parameters, generic functions, asynchronous functions, methods, and even external system functions, plus the ability to assert how many times a target is invoked.

---

## Background & Problem

Code under test frequently depends on functions whose real behavior is undesirable during a test or an experiment: a predicate that consults live state, an operation that talks to the network, a system call that touches the operating system. The usual workarounds — threading interfaces/traits through every layer, or restructuring code to inject dependencies — are invasive and change the production design just to make code observable.

This toolkit takes a different approach: it patches the *behavior* of a target function in place. A caller names a target and describes the replacement behavior; the toolkit redirects invocations of that target to the replacement for as long as the override object is alive. Replacements can return a fixed value, compute a value from the real arguments, write into output parameters, run an entirely caller-supplied body, or be guarded so they only apply to specific arguments. The toolkit also tracks invocation counts and reports a mismatch when an expectation is violated, and it refuses obviously invalid configuration (such as a null replacement) up front rather than corrupting the process.

Because overrides are scoped, the original behavior is always restored deterministically when the override goes out of scope, so independent scenarios never leak behavior into one another.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, the override engine, the catalog of target functions), it MUST NOT be a single "god file". Output a clear, multi-file directory tree that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core override engine must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating each JSON command into idiomatic calls against the core toolkit and the target functions it exercises.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, the override engine, the catalog of target functions, and output formatting into distinct logical units. The engine must be open for extension but closed for modification; abstractions must not depend on low-level I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the toolkit must be elegant and idiomatic to the target programming language, hiding the mechanics of run-time interception.
   - **Resilience:** Invalid configuration and unmet expectations must be modeled as well-defined, recoverable errors rather than process corruption or silent misbehavior. Restoring original behavior at the end of an override's lifetime must be deterministic.

---

## Core Features

> The execution adapter reads a **single JSON object** from stdin. The `op` field selects the scenario; the remaining fields are that scenario's parameters. The adapter prints the scenario's observations to stdout exactly as specified. Where a scenario reports a failure (an unmet expectation, a rejected argument, or rejected configuration), it prints a neutral, language-independent error line of the form `error=<category>` rather than leaking an implementation-specific message or aborting the process.

### Feature 1: Override A Predicate To Return A Constant Boolean

**As a developer**, I want to override a parameterless predicate so it returns a chosen constant boolean instead of its real result, so I can drive code down either branch on demand.

**Expected Behavior / Usage:**

The input has `op` = `constant_boolean` and a `value` (the boolean the override should return). The scenario first records what the un-overridden predicate returns (it is originally `false`), then installs an override configured to return the requested `value` and records the predicate's result again. Output is two lines: `before=<original result>` and `after=<result while overridden>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_constant_boolean.json`

```json
{
    "description": "Override a parameterless predicate so that it returns a chosen constant boolean instead of its real result. The scenario first records what the un-overridden predicate returns, then installs the override configured with the requested boolean and records the predicate's result again. Output reports the value before the override is active and the value once it is active.",
    "cases": [
        {
            "input": {"op": "constant_boolean", "value": true},
            "expected_output": "[a specific status string pattern defined in the logging module defaults]\n[a specific status string pattern defined in the logging module defaults]\n"
        },
        {
            "input": {"op": "constant_boolean", "value": false},
            "expected_output": "[a specific status string pattern defined in the logging module defaults]\nafter=false\n"
        }
    ]
}
```

---

### Feature 2: Scope-Bound Override With Automatic Restoration

**As a developer**, I want an override to apply only while its scope is alive and have the original behavior restored automatically when the scope ends, so scenarios stay isolated.

**Expected Behavior / Usage:**

The input has `op` = `scope_restore` and a `target` selecting which kind of target is exercised: `boolean` is a predicate that is originally `false`; `result` is a fallible operation that originally fails but is overridden to succeed with a value. The target is observed three times — before entering the override scope, while inside it, and after the scope has exited. Output is three lines: `before=...`, `during=...`, `after=...`. For `boolean` the observations are the boolean values; for `result` a failure is reported as `error` and a success as `success:<code>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_scope_restore.json`

```json
{
    "description": "An override is bound to a scope; it only affects the target while that scope is alive and the original behavior is automatically restored once the scope ends. The scenario observes the target three times: before entering the override scope, while inside it, and after the scope has exited. The `target` field selects which kind of target is exercised: a boolean predicate (originally false), or a fallible operation that originally fails but is overridden to succeed with a value. Output reports the observed behavior at each of the three points.",
    "cases": [
        {
            "input": {"op": "scope_restore", "target": "boolean"},
            "expected_output": "[a specific status string pattern defined in the logging module defaults]\nduring=true\nafter=false\n"
        },
        {
            "input": {"op": "scope_restore", "target": "result"},
            "expected_output": "before=error\nduring=success:200\nafter=error\n"
        }
    ]
}
```

---

### Feature 3: Argument-Guarded Override

**As a developer**, I want an override that only takes effect when the call argument satisfies a guard, and that rejects any other argument as unexpected, so I can pin down exactly which inputs are mocked.

**Expected Behavior / Usage:**

The input has `op` = `conditional_gate` and a `key` (the argument value passed to the guarded target). The override supplies a fixed success result only when the argument matches the guard; when invoked with an argument the guard does not accept, the override rejects the call as an unexpected argument. Output is `status=ok` and `code=<code>` when the guard matches, or the neutral line `error=unexpected_argument` when it does not.

**Test Cases:** `rcb_tests/public_test_cases/feature3_conditional_gate.json`

```json
{
    "description": "An override can be guarded by a condition on the call arguments: it only takes effect when the supplied argument satisfies the guard, and supplies a fixed success result in that case. When the target is invoked with an argument the guard does not accept, the override rejects the call as an unexpected argument. The `key` field is the argument value passed to the guarded target. Output reports a success result and its code when the guard matches, or a neutral unexpected-argument error when it does not.",
    "cases": [
        {
            "input": {"op": "conditional_gate", "key": "open-sesame"},
            "expected_output": "status=ok\ncode=200\n"
        },
        {
            "input": {"op": "conditional_gate", "key": "wrong-key"},
            "expected_output": "error=unexpected_argument\n"
        }
    ]
}
```

---

### Feature 4: Override Whose Return Is Computed From The Arguments

**As a developer**, I want an override to compute its return value from the real arguments at the call site, rather than only returning a constant, so the mock can stay a function of its inputs.

**Expected Behavior / Usage:**

The input has `op` = `computed_return`, a `base`, and a `delta` (the two integer arguments). The target normally sums its inputs. The override — active only when the first argument is positive — instead returns twice the first argument plus twice the second. Output is two lines: `original=<base+delta>` (the un-overridden result) and `overridden=<2*base + 2*delta>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_computed_return.json`

```json
{
    "description": "An override can compute its return value from the actual arguments passed at the call site, rather than returning a constant. The target is a two-argument integer operation that normally sums its inputs; the override (active only when the first argument is positive) instead returns twice the first argument plus twice the second. The `base` and `delta` fields are the two integer arguments. Output reports the value the un-overridden operation would have produced and the value produced once the override is active.",
    "cases": [
        {
            "input": {"op": "computed_return", "base": 6, "delta": 3},
            "expected_output": "original=9\noverridden=18\n"
        }
    ]
}
```

---

### Feature 5: Writing Into Output Parameters

**As a developer**, I want an override to write values into the target's mutable by-reference output parameters (and optionally return a value), so I can fake functions that report results through their arguments.

**Expected Behavior / Usage:**

The input has `op` = `output_params` and a `variant` selecting the target's shape: `single_ret` (one output parameter plus a boolean return), `single_noret` (one output parameter, no return), `multi_ret` (two output parameters plus a boolean return), `multi_noret` (two output parameters, no return), or `method` (a method that writes its result into an output parameter while reading its own receiver and a value argument). The caller always passes freshly zeroed output slots. Output reports the values the override wrote into those slots, plus the return value where one exists — e.g. `out=<n>` / `result=<bool>`, or `out_a=<n>` / `out_b=<bool>` / `result=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_output_params.json`

```json
{
    "description": "An override can write values into the target's mutable output parameters (by-reference arguments), in addition to optionally supplying a return value. The `variant` field selects the shape of the target being faked: a single output parameter with a boolean return, a single output parameter with no return, two output parameters with a boolean return, two output parameters with no return, or a method that writes its result into an output parameter while reading its own receiver and a value argument. In every variant the caller passes freshly zeroed output slots; output reports the values the override wrote into those slots (and the return value where one exists).",
    "cases": [
        {
            "input": {"op": "output_params", "variant": "single_ret"},
            "expected_output": "out=6\nresult=true\n"
        },
        {
            "input": {"op": "output_params", "variant": "method"},
            "expected_output": "out=18\n"
        }
    ]
}
```

---

### Feature 6: Verifying Invocation Count

**As a developer**, I want an override to declare how many times it expects the target to be invoked and have that expectation checked when the scope ends, so I can assert call counts as part of a scenario.

**Expected Behavior / Usage:**

The input has `op` = `call_count`, an `expected` (the declared count) and an `actual` (how many times the target is actually invoked). When the actual count equals the expectation, output reports a satisfied verification: `expected=<n>`, `actual=<n>`, `status=satisfied`. When the target is invoked more or fewer times than declared, the mismatch is surfaced as the neutral error `error=call_count_mismatch` followed by `expected=<n>` and `actual=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_call_count.json`

```json
{
    "description": "An override can declare how many times it expects the target to be invoked, and that expectation is verified at the end of the scope. The `expected` field is the declared call count and `actual` is how many times the target is actually invoked. When the actual count equals the expectation the scenario reports a satisfied verification; when the target is invoked more or fewer times than declared, the mismatch is surfaced as a neutral call-count error carrying the expected and actual counts.",
    "cases": [
        {
            "input": {"op": "call_count", "expected": 2, "actual": 2},
            "expected_output": "expected=2\nactual=2\nstatus=satisfied\n"
        },
        {
            "input": {"op": "call_count", "expected": 2, "actual": 3},
            "expected_output": "error=call_count_mismatch\nexpected=2\nactual=3\n"
        }
    ]
}
```

---

### Feature 7: Replacing The Target With A Caller-Supplied Body

**As a developer**, I want to replace a target's entire body with an implementation I supply, so the replacement fully determines the observable behavior — including inspecting the real arguments.

**Expected Behavior / Usage:**

The input has `op` = `custom_replacement` and a `mode`:
- `function` — replace the target with a body that prints a line and returns true. Output: `substitute executed` then `result=true`.
- `count` — replace a no-op target with a body that records how many times it is invoked, then invoke it `calls` times. Output: `calls=<calls>`.
- `branch` — replace a target with a body that inspects the real arguments `a` (string), `b` (boolean) and `c` (integer) it receives and selects one of several results accordingly. Output: `value=<selected branch>`.

The branch selection is: if `a == "abc"` then `branch-1`; otherwise if `c` is negative then `branch-2`; otherwise `branch-3`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_custom_replacement.json`

```json
{
    "description": "The target's entire body can be replaced by a caller-supplied implementation; the replacement runs in place of the original and fully determines the observable behavior. The `mode` field selects what the replacement demonstrates: `function` replaces the target with an implementation that prints a line and returns true; `count` replaces a no-op target with an implementation that records how many times it is invoked, then invokes it `calls` times; `branch` replaces a target with an implementation that inspects the real arguments (`a`, `b`, `c`) it receives and selects one of several results accordingly. Output reports whatever the replacement produced: its printed line and return value, the recorded invocation count, or the selected branch value.",
    "cases": [
        {
            "input": {"op": "custom_replacement", "mode": "function"},
            "expected_output": "substitute executed\nresult=true\n"
        },
        {
            "input": {"op": "custom_replacement", "mode": "branch", "a": "abc", "b": true, "c": 123},
            "expected_output": "value=branch-1\n"
        }
    ]
}
```

---

### Feature 8: Selective Override Of One Generic Instantiation

**As a developer**, I want to bind an override to one specific instantiation of a generic function, so that only calls using that exact instantiation are intercepted while other instantiations keep running the original.

**Expected Behavior / Usage:**

The input has `op` = `generic_selectivity`. The scenario overrides one specific instantiation of a generic target (a string/boolean/integer instantiation) to return a faked value, then invokes both that instantiation (with the matching arguments) and a different all-integer instantiation. Output is two lines: `faked_instantiation=<result of the overridden instantiation>` and `other_instantiation=<result of the untouched instantiation>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_generic_selectivity.json`

```json
{
    "description": "When the target is a generic function, an override can be bound to one specific type instantiation; calls that use that exact instantiation are intercepted while calls that use a different instantiation continue to run the original implementation. The scenario overrides the string/boolean/integer instantiation to return a faked value, then invokes both that instantiation (with the matching arguments) and a different all-integer instantiation. Output reports the result of the overridden instantiation and the result of the untouched instantiation.",
    "cases": [
        {
            "input": {"op": "generic_selectivity"},
            "expected_output": "faked_instantiation=faked\nother_instantiation=original\n"
        }
    ]
}
```

---

### Feature 9: Overriding Asynchronous Targets

**As a developer**, I want to override asynchronous functions and methods so they resolve to a chosen value, with non-overridden async work left untouched and scope restoration still honored.

**Expected Behavior / Usage:**

The input has `op` = `async_override` and a `kind`:
- `simple` — override one async function to resolve to a fixed value, and confirm a different async function is left untouched. Output: `faked=<overridden async result>` then `unaffected=<result of the untouched async function>`.
- `method` — override an async method to resolve to a faked response within a scope, and confirm the original async behavior returns once the scope ends. Output: `during=<faked response>` then `after=<restored original async result>`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_async_override.json`

```json
{
    "description": "Asynchronous targets can be overridden to resolve to a chosen value. The `kind` field selects the scenario: `simple` overrides one async function to resolve to a fixed value and confirms that a different async function is left untouched; `method` overrides an async method to resolve to a faked response within a scope and confirms the original async behavior returns once the scope ends. Output reports the overridden async result alongside the result that was left unaffected (simple) or restored after scope exit (method).",
    "cases": [
        {
            "input": {"op": "async_override", "kind": "simple"},
            "expected_output": "faked=123\nunaffected=3\n"
        },
        {
            "input": {"op": "async_override", "kind": "method"},
            "expected_output": "during=faked response\nafter=GET https://service.internal\n"
        }
    ]
}
```

---

### Feature 10: Overriding An External System Function

**As a developer**, I want to override an external system function (one provided by the platform, not by my own code) just like an ordinary function, so I can isolate code from the operating system.

**Expected Behavior / Usage:**

The input has `op` = `system_call`, a `mode`, and a `name` argument. The target is a platform-provided system function that opens a shared-memory object given a name, flags, and a mode. With `mode` = `fixed` the override always returns a fixed file descriptor regardless of arguments. With `mode` = `conditional` the override returns a result chosen by the supplied `name`: an error descriptor for the failing name, or a success descriptor for the accepted name. Output is a single line `fd=<file descriptor>`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_system_call.json`

```json
{
    "description": "An external C system function (a POSIX shared-memory open call taking a name, flags, and mode) can be overridden the same way as ordinary functions. The `mode` field selects behavior: `fixed` overrides the call to always return a fixed file descriptor regardless of arguments; `conditional` overrides the call to return a result chosen by the supplied `name` (an error descriptor for the failing name, a success descriptor for the accepted name). Output reports the file descriptor returned by the overridden call.",
    "cases": [
        {
            "input": {"op": "system_call", "mode": "fixed", "name": "/myshm"},
            "expected_output": "fd=32\n"
        },
        {
            "input": {"op": "system_call", "mode": "conditional", "name": "/fail"},
            "expected_output": "fd=-1\n"
        }
    ]
}
```

---

### Feature 11: Rejecting A Null Replacement Target

**As a developer**, I want the toolkit to reject an override configured with a null function pointer up front, so misconfiguration fails cleanly instead of causing undefined behavior.

**Expected Behavior / Usage:**

The input has `op` = `null_target` and a `target` naming which configuration slot is fed the null pointer (`replacement` or `original`). In every case the toolkit refuses the null target, and the scenario reports the neutral error line `error=null_target`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_null_target.json`

```json
{
    "description": "Configuring an override with a null function pointer as the replacement target is rejected up front rather than producing undefined behavior. The `target` field names which configuration slot is fed the null pointer. In every case the toolkit refuses the null target and the scenario reports a neutral null-target error.",
    "cases": [
        {
            "input": {"op": "null_target", "target": "replacement"},
            "expected_output": "error=null_target\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing a run-time function-behavior override engine supporting the capabilities above — constant and computed returns, scope-bound installation with automatic restoration, argument guards, output-parameter writes, invocation-count verification, full caller-supplied replacement bodies, selective override of a single generic instantiation, asynchronous targets, external system functions, and up-front rejection of a null replacement. Its physical structure (single-file vs. multi-file) MUST align with the "Scale-Driven Code Organization" constraint. The core engine must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to the core system. It reads a single JSON object from stdin, dispatches on the `op` field, exercises a fixed catalog of target functions through the override engine, and prints the scenario's observations to stdout exactly as specified per feature above. Failures (unmet expectations, rejected arguments, rejected configuration) are reported as neutral `error=<category>` lines, never as a crash and never as `PASS`/`FAIL`.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it pipes the case `input` (compact JSON) into the adapter on stdin and writes the program's raw stdout to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
