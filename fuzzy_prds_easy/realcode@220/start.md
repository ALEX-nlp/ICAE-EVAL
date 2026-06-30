## Product Requirement Document

# Executable Behavior Specification Runner - Data-driven behavior cases with reliable execution semantics

## Project Goal

Build a behavior-specification runner that allows developers to describe an executable test as an ordered sequence of named setup, action, assertion, and cleanup steps — optionally driven by example data rows — so they can express intent as readable prose-like steps without duplicating boilerplate for each data row or resource-lifecycle concern.

---

## Background & Problem

Without this runner, developers are forced to hand-write a separate test method per data row, manually bind example values to parameters, manually re-run shared setup before a destructive assertion, and hand-code cleanup ordering and resource disposal. This leads to duplicated code, fragile resource handling, unclear skip/error reporting, and brittle behaviour when the same step sequence is registered from more than one thread.

With this runner, a developer expresses behaviour as a list of ordered steps, attaches one or more example rows, optionally marks individual steps (or a whole case) as skipped, isolates a destructive assertion so it gets its own replayed context, enforces a per-step time limit, and registers cleanup callbacks or disposable resources. The runner then executes the steps and emits one structured result per executed step, including pass/error/skip status, rendered step display text, and reliable cleanup ordering.

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

The runner exposes a single conceptual operation: *run a behavior definition and report one result per executed step*. Every result carries a status that is one of completed (the step ran and passed), error (the step or its surrounding machinery failed), or skipped (the step was intentionally not executed). Throughout this document the standard result summary lines are: `result_count` (total results emitted), `completed_count`, `error_count`, and `skipped_count`. Each leaf feature below accepts a single JSON command object on stdin and prints only the stdout lines shown in its cases.

### Feature 1: Input Value Representation

**As a developer**, I want declared inputs to a behavior case to be represented consistently, so I can distinguish a value the caller actually supplied from a value the runner had to generate on the caller's behalf.

**Expected Behavior / Usage:**

An input value can be created two ways: from a concrete value the caller provides, or from only a type when no value is available. The runner must record which of the two happened (a `generated_default` flag) and the resulting value. This feature is split into two independent leaf contracts.

*1.1 Explicit supplied value — A caller-supplied value is preserved verbatim and flagged as not generated*

When an input is created from a concrete runtime value, the runner must keep that exact value and report `generated_default=false`. The command names this behavior and carries the value to wrap; stdout reports the generated flag followed by the rendered value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_specific_argument_value.json`

```json
{
    "description": "A supplied runtime value is wrapped as an explicit argument rather than as a generated default.",
    "cases": [
        {
            "input": {
                "behavior": "specific_argument_value",
                "value": "sample"
            },
            "expected_output": "generated_default=false\nvalue=sample\n"
        }
    ]
}
```

*1.2 Generated default value — A value requested by type only is filled with that type's default and flagged as generated*

When an input is created from a type with no supplied value, the runner must produce the type's natural default (zero for an integer-like type, absent/null for a reference-like type) and report `generated_default=true`. The command names a neutral value type; stdout reports the generated flag followed by the rendered default value, using `null` for an absent reference default.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_generated_default_argument.json`

```json
{
    "description": "A requested argument type is converted to its generated default value and marked as generated.",
    "cases": [
        {
            "input": {
                "behavior": "generated_default_argument",
                "value_type": "integer"
            },
            "expected_output": "generated_default=true\nvalue=0\n"
        },
        {
            "input": {
                "behavior": "generated_default_argument",
                "value_type": "object"
            },
            "expected_output": "generated_default=true\nvalue=null\n"
        }
    ]
}
```

---

### Feature 2: Example-Driven Behavior Cases

**As a developer**, I want one behavior definition to run against multiple data rows with readable step text, so I can cover related examples without copy-pasting the behavior body.

**Expected Behavior / Usage:**

A behavior body can declare typed parameters and be paired with zero or more example rows. The runner executes the body once per example row, binding the row's values to the parameters; rows shorter than the parameter list have their trailing parameters filled with generated defaults; a parameterized body with no rows still runs once using generated defaults. Step display text may contain positional placeholders that are substituted with the bound values. Rows that cannot bind to the declared parameters must surface as error results rather than crashing the run.

*2.1 Complete example rows — Each row runs the body once with exactly that row's values*

Every example row whose value count matches the parameter list runs the body once, binding each value in order. Stdout reports the result summary followed by one `arguments=` line per run listing the bound values; argument lines are emitted in a stable sorted order so the contract is independent of run scheduling.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_examples_supply_arguments.json`

```json
{
    "description": "Each tabular example runs the scenario once with the values from that example.",
    "cases": [
        {
            "input": {
                "behavior": "examples_supply_all_arguments"
            },
            "expected_output": "result_count=3\ncompleted_count=3\nerror_count=0\nskipped_count=0\narguments=1,2,3\narguments=3,4,5\narguments=5,6,7\n"
        }
    ]
}
```

*2.2 Short example rows — Missing trailing values are filled with generated defaults*

When a row supplies fewer values than the body declares, the runner binds the supplied values to the leading parameters and fills each remaining trailing parameter with its generated default. Stdout reports the successful result summary followed by one completed `arguments=` line per row, including the filled defaults.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_examples_fill_missing_arguments.json`

```json
{
    "description": "When examples provide fewer values than the scenario declares, the missing trailing values are generated defaults.",
    "cases": [
        {
            "input": {
                "behavior": "examples_fill_missing_arguments"
            },
            "expected_output": "result_count=3\ncompleted_count=3\nerror_count=0\nskipped_count=0\narguments=1,2,0,0\narguments=3,4,0,0\narguments=5,6,0,0\n"
        }
    ]
}
```

*2.3 Parameters with no example rows — The body runs once with all generated defaults*

A parameterized body that has no example rows must still execute exactly once, binding every parameter to its generated default. Stdout reports a single successful run and the generated argument tuple.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_parameters_without_examples.json`

```json
{
    "description": "A parameterized scenario without explicit examples runs with generated default parameter values.",
    "cases": [
        {
            "input": {
                "behavior": "scenario_parameters_without_examples"
            },
            "expected_output": "result_count=1\ncompleted_count=1\nerror_count=0\nskipped_count=0\narguments=0,0,0,0\n"
        }
    ]
}
```

*2.4 Step display text formatting — Placeholders are substituted with bound values, nulls render as `null`, out-of-range placeholders are left intact*

A step's display text may contain positional placeholders `{0}`, `{1}`, … . The runner substitutes each placeholder with the corresponding bound value, renders an absent value as the literal `null`, and — crucially — leaves any placeholder whose index exceeds the available values untouched without failing the run. The command selects which formatting case to exercise (`valid_values`, `null_values`, or any other value for the out-of-range case); stdout reports the result summary and a `display_suffix=` line holding the rendered step text.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_formatted_step_names.json`

```json
{
    "description": "Step display names render supplied example values when the text contains matching placeholders, including null values, and leave out-of-range placeholders unchanged.",
    "cases": [
        {
            "input": {
                "behavior": "formatted_step_names",
                "format_case": "valid_values"
            },
            "expected_output": "result_count=1\ncompleted_count=1\nerror_count=0\nskipped_count=0\n[a specific sentinel value — ask the PM for the exact string]\n"
        },
        {
            "input": {
                "behavior": "formatted_step_names",
                "format_case": "null_values"
            },
            "expected_output": "result_count=1\ncompleted_count=1\nerror_count=0\nskipped_count=0\ndisplay_suffix=Given null, null and null\n"
        },
        {
            "input": {
                "behavior": "formatted_step_names",
                "format_case": "out_of_range_placeholders"
            },
            "expected_output": "result_count=1\ncompleted_count=1\nerror_count=0\nskipped_count=0\ndisplay_suffix=Given {3}, {4} and {5}\n"
        }
    ]
}
```

*2.5 Unbindable example rows — Rows that cannot bind become error results, not crashes*

If an example row's values cannot be bound to the declared parameters (wrong count or incompatible type), the runner must turn each such row into an error result instead of letting the failure escape discovery or execution. Stdout reports the result summary in which every runnable case is an error.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_invalid_examples.json`

```json
{
    "description": "Examples that cannot be bound to the declared scenario parameters are reported as error results instead of crashing discovery or execution.",
    "cases": [
        {
            "input": {
                "behavior": "invalid_examples"
            },
            "expected_output": "result_count=2\ncompleted_count=0\nerror_count=2\nskipped_count=0\n"
        }
    ]
}
```

---

### Feature 3: Step Execution Semantics

**As a developer**, I want a behavior case's setup, skips, errors, isolation, and time limits to behave predictably, so I can trust that each emitted result faithfully reflects the flow of the steps.

**Expected Behavior / Usage:**

A behavior case is a sequence of steps, each producing one result. Shared background steps run before each case; a whole case or individual steps can be skipped; a step failure blocks the dependent steps that follow it; definition/construction errors are captured as results; a destructive assertion can be isolated to its own replayed context; and a step may declare a time limit. The leaves below cover each of these guarantees.

*3.1 Shared background steps — Background steps run before each case and are distinguishable in results*

Background steps declared for a feature must execute before the steps of each case in that feature, and their results must be distinguishable from ordinary case-step results. Stdout reports the result summary, an `execution=` trace listing whether each executed step was a `background` or `scenario` step in order, and the counts of background versus case results.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_background_steps.json`

```json
{
    "description": "Background steps are executed before each scenario and are identified separately from scenario steps in result names.",
    "cases": [
        {
            "input": {
                "behavior": "background_steps"
            },
            "expected_output": "result_count=10\ncompleted_count=10\nerror_count=0\nskipped_count=0\nexecution=background,background,background,scenario,scenario,background,background,background,scenario,scenario\nbackground_result_count=6\nscenario_result_count=4\n"
        }
    ]
}
```

*3.2 Whole-case skip — A skipped case yields one skipped result and runs no steps*

When an entire behavior case is marked skipped with a reason, the runner must emit exactly one skipped result, execute none of its steps, and preserve the reason. Stdout reports the result summary, the executed step count (zero), and the skip reason.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_skipped_scenario.json`

```json
{
    "description": "A skipped whole scenario produces one skipped result and does not execute its steps.",
    "cases": [
        {
            "input": {
                "behavior": "skipped_scenario"
            },
            "expected_output": "result_count=1\ncompleted_count=0\nerror_count=0\nskipped_count=1\nsteps_executed=0\nskip_reason=Test\n"
        }
    ]
}
```

*3.3 Individual skipped steps — Skipped steps do not run, do not fail the case, and keep their reason*

A step marked skipped must not execute its action and must not fail the surrounding case; its reason must be preserved. Non-skipped steps in the same case still run and complete normally. Stdout reports the result summary (completed plus skipped, no errors) and one `skip_reason=` line per skipped step.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_skipped_steps.json`

```json
{
    "description": "Skipped individual steps are not executed, do not fail the scenario, and report the supplied skip reason.",
    "cases": [
        {
            "input": {
                "behavior": "skipped_steps"
            },
            "expected_output": "result_count=4\ncompleted_count=2\nerror_count=0\nskipped_count=2\nskip_reason=the feature is unfinished\nskip_reason=the feature is unfinished\n"
        }
    ]
}
```

*3.4 Failure propagation — A failed step blocks the dependent steps after it*

When a step fails, the runner must not execute the dependent steps that follow it; each such following step is reported as an error that is explicitly blocked by the failed preceding step. Stdout reports the result summary, the executed step count (only the failing step ran), and one `blocked_by=` line per blocked following step identifying the failed preceding step.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_failing_step_stops_following_steps.json`

```json
{
    "description": "After a step fails, later dependent steps are not executed and are reported as blocked by the failed preceding step.",
    "cases": [
        {
            "input": {
                "behavior": "failing_step_stops_following_steps"
            },
            "expected_output": "result_count=3\ncompleted_count=0\nerror_count=3\nskipped_count=0\nsteps_executed=1\n[a specific blocking string — ask the PM for the exact cause]\n[a specific blocking string — ask the PM for the exact cause]\n"
        }
    ]
}
```

*3.5 Definition and construction errors — Errors while building a case become error results*

If an error is raised while defining a behavior body (for example the body itself throws) or while constructing the instance that hosts the body (for example no usable constructor), the runner must capture it as an error result rather than letting it escape. The command selects which failure to exercise; stdout reports a result summary containing exactly one error result.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_definition_errors.json`

```json
{
    "description": "Errors while constructing or defining a scenario are converted into error results rather than escaping the runner.",
    "cases": [
        {
            "input": {
                "behavior": "scenario_body_error"
            },
            "expected_output": "result_count=1\ncompleted_count=0\nerror_count=1\nskipped_count=0\n"
        },
        {
            "input": {
                "behavior": "unconstructable_feature"
            },
            "expected_output": "result_count=1\ncompleted_count=0\nerror_count=1\nskipped_count=0\n"
        }
    ]
}
```

*3.6 Isolated assertions — A destructive assertion gets its own replayed context*

A step can be marked as isolated. The runner must give each isolated step its own fresh replay of the preceding context, so that a destructive check (one that consumes or mutates shared state) does not break the steps that follow it. The expansion of replayed contexts plus ordinary steps must all complete. Stdout reports a result summary in which every emitted result is completed.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_isolated_steps.json`

```json
{
    "description": "An isolated assertion receives its own replayed context so destructive checks do not affect later steps.",
    "cases": [
        {
            "input": {
                "behavior": "isolated_steps"
            },
            "expected_output": "result_count=10\ncompleted_count=10\nerror_count=0\nskipped_count=0\n"
        }
    ]
}
```

*3.7 Per-step time limit — A step within its limit completes; a step over its limit fails with a neutral timeout signal*

A step may declare a maximum duration. A step that finishes within its limit completes normally. A step that exceeds its limit must fail, and the failure must be reported as a language-neutral timeout category carrying the configured limit (no host-runtime exception identity). The command selects a fast or slow step; for the slow case stdout reports the result summary plus `error=timeout` and `limit_ms=`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_7_timeout.json`

```json
{
    "description": "A step that finishes before its limit passes, while a step exceeding its limit fails with a normalized timeout signal.",
    "cases": [
        {
            "input": {
                "behavior": "timeout",
                "step_duration": "within_limit"
            },
            "expected_output": "result_count=1\ncompleted_count=1\nerror_count=0\nskipped_count=0\n"
        },
        {
            "input": {
                "behavior": "timeout",
                "step_duration": "exceeds_1ms_limit"
            },
            "expected_output": "result_count=1\ncompleted_count=0\nerror_count=1\nskipped_count=0\nerror=timeout\nlimit_ms=1\n"
        }
    ]
}
```

---

### Feature 4: Cleanup and Resource Lifetime

**As a developer**, I want cleanup callbacks and disposable resources to run reliably after a behavior case, so I can be sure resources are released even when a step or a cleanup action itself fails.

**Expected Behavior / Usage:**

A step can register cleanup callbacks and disposable resources. After the case finishes (whether it passed or failed), the runner runs every registered cleanup callback exactly once in reverse registration order, and disposes every registered resource exactly once in reverse creation order; resources remain usable while the steps run. A throwing cleanup callback or a throwing disposal must not prevent the remaining cleanups/disposals, and the failure is surfaced as an error result. The leaves below cover ordering and the failure variants.

*4.1 Cleanup callback ordering — Callbacks run once, in reverse order, including for failing cases*

Registered cleanup callbacks must each run exactly once after the case in reverse registration order. This holds even when the case contains a failing step: cleanup still runs in reverse. The command selects the registration shape; stdout reports the result summary and a `teardown_order=` line listing the callback identifiers in the order they ran.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_teardown_order.json`

```json
{
    "description": "Registered cleanup callbacks execute once after scenario execution in reverse registration order, including failing scenarios.",
    "cases": [
        {
            "input": {
                "behavior": "teardown_order",
                "teardown_case": "single_step"
            },
            "expected_output": "result_count=2\ncompleted_count=2\nerror_count=0\nskipped_count=0\n[a specific sequence string — ask the PM for the exact teardown order]\n"
        },
        {
            "input": {
                "behavior": "teardown_order",
                "teardown_case": "many_steps"
            },
            "expected_output": "result_count=3\ncompleted_count=3\nerror_count=0\nskipped_count=0\nteardown_order=6,5,4,3,2,1\n"
        },
        {
            "input": {
                "behavior": "teardown_order",
                "teardown_case": "failing_step"
            },
            "expected_output": "result_count=6\ncompleted_count=5\nerror_count=1\nskipped_count=0\n[a specific sequence string — ask the PM for the exact teardown order]\n"
        }
    ]
}
```

*4.2 Throwing cleanup callbacks — Cleanup still completes in reverse order and the failure is reported*

If cleanup callbacks throw while running, the runner must still execute all of them in reverse order and surface the cleanup failure as an error result emitted after the successful step results. Stdout reports the result summary (one error from the failing cleanup) and the full reverse `teardown_order=`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_teardown_failures.json`

```json
{
    "description": "Cleanup callbacks still execute in reverse order when they throw, and their cleanup failures are reported after successful step results.",
    "cases": [
        {
            "input": {
                "behavior": "teardown_order",
                "teardown_case": "throwing_teardowns"
            },
            "expected_output": "result_count=2\ncompleted_count=1\nerror_count=1\nskipped_count=0\n[a specific sequence string — ask the PM for the exact teardown order]\n"
        }
    ]
}
```

*4.3 Disposable resource lifetime — Resources stay usable during the case and are disposed once in reverse creation order*

Resources registered for disposal must remain usable throughout the case's steps and then be disposed exactly once afterward in reverse creation order. This holds whether registration happened in one step or across several steps, and even when a later step fails. The command selects the registration shape; stdout reports the result summary and a `lifetime=` line listing creation and disposal events in order (creations ascending, disposals in reverse).

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_disposable_lifetime.json`

```json
{
    "description": "Registered disposable resources remain usable during scenario steps and are disposed once afterward in reverse creation order.",
    "cases": [
        {
            "input": {
                "behavior": "disposable_lifetime",
                "disposal_case": "single_step"
            },
            "expected_output": "result_count=3\ncompleted_count=3\nerror_count=0\nskipped_count=0\nlifetime=create1,create2,create3,dispose3,dispose2,dispose1\n"
        },
        {
            "input": {
                "behavior": "disposable_lifetime",
                "disposal_case": "many_steps"
            },
            "expected_output": "result_count=5\ncompleted_count=5\nerror_count=0\nskipped_count=0\nlifetime=create1,create2,create3,dispose3,dispose2,dispose1\n"
        },
        {
            "input": {
                "behavior": "disposable_lifetime",
                "disposal_case": "failing_step"
            },
            "expected_output": "result_count=6\ncompleted_count=5\nerror_count=1\nskipped_count=0\nlifetime=create1,create2,create3,dispose3,dispose2,dispose1\n"
        }
    ]
}
```

*4.4 Throwing disposal — All resources are still disposed and the disposal failure is reported*

If registered resources throw while being disposed, the runner must still dispose every resource it registered and surface the disposal failure as an error result. Stdout reports the result summary (one error from the failing disposal) and the full reverse `lifetime=` sequence showing every resource was disposed.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_dispose_failures.json`

```json
{
    "description": "If registered resources throw while being disposed, all resources are still disposed and disposal failures are surfaced as error results.",
    "cases": [
        {
            "input": {
                "behavior": "disposable_lifetime",
                "disposal_case": "throwing_dispose"
            },
            "expected_output": "result_count=3\ncompleted_count=2\nerror_count=1\nskipped_count=0\nlifetime=create1,create2,create3,dispose3,dispose2,dispose1\n"
        }
    ]
}
```

---

### Feature 5: Concurrent Step Registration

**As a developer**, I want step-registration state to be isolated per thread, so I can register behavior definitions from multiple threads at once without one thread's registration corrupting another's.

**Expected Behavior / Usage:**

The step-registration buffer that accumulates a case's steps must be per-thread, so two threads building the same kind of step sequence at the same time never interfere. The command names which registration shape both threads perform — a full setup/action/assertion sequence, a single action step, an isolated assertion, a plain observation, or a skipped step. The runner starts two physical threads that each perform the named registration, joins them, and reports the thread count and a neutral error status (`none` when no cross-thread error occurred).

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_concurrent_registration.json`

```json
{
    "description": "Step registration state is isolated per thread so two threads can register the same kind of step sequence concurrently without cross-thread errors.",
    "cases": [
        {
            "input": {
                "behavior": "concurrent_registration",
                "operation": "full_sequence"
            },
            "expected_output": "threads=2\nerror=none\n"
        },
        {
            "input": {
                "behavior": "concurrent_registration",
                "operation": "action_step"
            },
            "expected_output": "threads=2\nerror=none\n"
        },
        {
            "input": {
                "behavior": "concurrent_registration",
                "operation": "isolated_assertion"
            },
            "expected_output": "threads=2\nerror=none\n"
        },
        {
            "input": {
                "behavior": "concurrent_registration",
                "operation": "observation"
            },
            "expected_output": "threads=2\nerror=none\n"
        },
        {
            "input": {
                "behavior": "concurrent_registration",
                "operation": "skipped_step"
            },
            "expected_output": "threads=2\nerror=none\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_specific_argument_value.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_specific_argument_value@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same numbering convention as the setup order
- match the lifecycle pattern defined in the disposable module
