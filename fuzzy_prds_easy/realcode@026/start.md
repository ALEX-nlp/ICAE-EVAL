## Product Requirement Document

# Debounced Function & Value Scheduling Library - Rate-limited execution with leading/trailing edges, max-wait, cancel and flush

## Project Goal

Build a small client-side scheduling library that lets developers turn a frequently-triggered action, or a frequently-changing value, into a *rate-limited* one: the wrapped action runs (or the value settles) only after activity has been quiet for a configurable window, with optional immediate (leading-edge) execution and a hard upper bound on how long execution can be deferred. It allows developers to coalesce bursts of rapid events (typing, scrolling, resizing, network triggers) into a controlled number of executions without writing ad-hoc timer bookkeeping every time.

---

## Background & Problem

Without such a library, developers are forced to hand-roll timer management around every noisy event source: storing timer handles, clearing and re-arming them on each event, remembering the latest arguments, special-casing the first event of a burst, and bolting on an escape hatch so a long continuous burst still produces output eventually. This leads to repetitive, error-prone boilerplate that is easy to get subtly wrong (stale arguments, leaks of timers after teardown, double execution on both edges).

With this library, the developer wraps the action or value once, declares the timing policy (quiet window, edge behavior, max wait), and gets back a deferred action plus explicit `cancel` and `flush` controls. The library guarantees the latest arguments/value are used, that execution after teardown is suppressed, and that the policy is honored deterministically.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has two related primitives (a debounced action and a debounced value) sharing one scheduling core; organize it into clear units (a core scheduler, the two public primitives, and the execution adapter). Do not collapse everything into a single god file, but do not over-engineer either — a handful of focused modules is appropriate.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON command/trace contract described below is a **black-box testing contract** for the execution adapter, NOT the internal data model of the core. The scheduling core must be completely decoupled from stdin/stdout and JSON parsing. The execution adapter alone translates JSON commands into idiomatic calls on the core primitives and renders observations to stdout.

3. **Adherence to SOLID Design Principles:** Separate timing/scheduling, edge-policy decisions, value-equality, and output formatting into distinct cohesive units. The scheduling core must be open for extension (new edge policies) but closed for modification. Keep public interfaces small and idiomatic.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface must be elegant and idiomatic for the target language: a value goes in and a debounced value plus controls come out; an action goes in and a debounced action plus controls come out.
   - **Resilience:** Edge cases (flush with nothing pending, cancel then flush, teardown with a pending action) must be handled gracefully and deterministically. Malformed commands must be modeled as neutral errors, never as host-runtime faults leaking into output.

---

## Execution Protocol (black-box contract)

The execution adapter reads **one** JSON command object from stdin and writes a plain-text trace to stdout, **one record per line, each line terminated by a newline**. All timing is driven by a single deterministic virtual clock that starts at time `0`; no wall-clock time is ever used.

**Command fields:**

- `hook` — which primitive to drive: `"callback"` selects the **debounced action**; `"value"` selects the **debounced value**.
- `delay` — the quiet-window length in milliseconds.
- `options` (optional):
  - `leading` (boolean) — run on the leading edge of a burst.
  - `trailing` (boolean, default `true`) — run on the trailing edge of a burst.
  - `maxWait` (milliseconds) — hard upper bound on how long execution may be deferred, measured from the first pending trigger.
  - `equalityFn` — `"alwaysEqual"` selects a value-comparison predicate that treats any two values as equal (debounced-value primitive only).
- `initial` (optional): starting inputs — `value` (the source value for the value primitive) and/or `tag` (a marker string naming the current version of the wrapped action for the action primitive; defaults to `fn`).
- `steps` — an ordered list of actions applied against the virtual clock.

**Step vocabulary:**

- `{"do":"call","args":[...]}` — trigger the debounced action now with the given arguments.
- `{"do":"callAt","delay":N,"args":[...]}` — schedule a trigger `N` ms in the future on the same clock.
- `{"do":"setProps","props":{...}}` — replace the current source `value` and/or the action `tag`.
- `{"do":"advance","ms":N}` — advance the virtual clock by `N` ms, firing every timer that becomes due in time order, including timers scheduled while advancing.
- `{"do":"runAll"}` — fire all pending timers, in due order, until none remain.
- `{"do":"cancel"}` — discard any currently pending execution/update.
- `{"do":"flush"}` — force any currently pending execution/update to happen immediately.
- `{"do":"unmount"}` — dispose the active instance.
- `{"do":"observe"}` — emit one trace line describing the current observable state.

**Trace records:**

- Debounced action: every actual execution emits `[a specific derived string involving the email address or internal ID]<n> args=<json-array> tag=<marker>`, where `<n>` is the running 1-based execution count and `<marker>` is the action version that ran; an `observe` emits `calls=<n>` (cumulative execution count).
- Debounced value: an `observe` emits `[a specific derived string involving the email address or internal ID]<current debounced value>`.
- A malformed command or unknown step emits a single neutral `error=<category>` line; host-language runtime traces must never appear in output.

---

## Core Features

### Feature 1: Debounced Action

**As a developer**, I want to wrap a noisy action so that bursts of triggers collapse into a controlled number of executions with the latest arguments, so I can rate-limit side effects without manual timer bookkeeping.

**Expected Behavior / Usage:**

*1.1 Trailing-edge debouncing (default) — collapse a burst into one deferred execution with the latest arguments*

With no edge options, the action does not run while triggers keep arriving; it runs exactly once after the quiet window fully elapses with no further trigger, receiving the arguments of the most recent trigger. Triggers that occur during the window produce no execution until the window elapses.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_trailing.json`

```json
{"description":"A debounced function with the default (trailing) behavior collapses a rapid burst of invocations into a single deferred invocation that runs once the quiet period (the configured delay) has fully elapsed without any further invocation. The deferred invocation receives the arguments of the most recent invocation in the burst. No invocation occurs while the quiet period is still running.","cases":[{"input":{"hook":"callback","delay":1000,"steps":[{"do":"call","args":["a"]},{"do":"call","args":["b"]},{"do":"observe"},{"do":"advance","ms":1000},{"do":"observe"}]},"expected_output":"calls=0\n[a specific derived string involving the email address or internal ID]1 args=[\"b\"] tag=fn\ncalls=1\n"}]}
```

*1.2 Leading-edge-only — run immediately, suppress the trailing edge*

When configured to run on the leading edge with the trailing edge disabled, the action runs immediately on the first trigger of a burst and suppresses every further trigger that arrives while the window is active (including the trailing edge). After the window elapses, the next trigger is a fresh leading edge and runs immediately again.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_leading_only.json`

```json
{"description":"When configured for leading-edge-only behavior (invoke on the leading edge, suppress the trailing edge), the function runs immediately on the first invocation of a burst and then suppresses every further invocation that arrives while the quiet period is still active, including the trailing edge. Once the quiet period has elapsed, a subsequent invocation is treated as a new leading edge and runs immediately again.","cases":[{"input":{"hook":"callback","delay":1000,"options":{"leading":true,"trailing":false},"steps":[{"do":"call","args":[]},{"do":"observe"},{"do":"runAll"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]1 args=[] tag=fn\ncalls=1\ncalls=1\n"}]}
```

*1.3 Leading and trailing together — one execution for a single trigger, two for a multi-trigger burst*

When both edges are enabled, a burst containing a single trigger runs exactly once (leading edge only, no extra trailing execution). A burst containing more than one trigger runs twice: once immediately on the leading edge and once again on the trailing edge after the window elapses.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_leading_and_trailing.json`

```json
{"description":"When configured to invoke on both the leading and the trailing edge, a burst that contains only a single invocation runs exactly once (on the leading edge, with no extra trailing invocation). A burst that contains more than one invocation runs twice: once immediately on the leading edge and once again on the trailing edge after the quiet period elapses.","cases":[{"input":{"hook":"callback","delay":1000,"options":{"leading":true},"steps":[{"do":"call","args":[]},{"do":"runAll"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]1 args=[] tag=fn\ncalls=1\n"}]}
```

*1.4 Fresh leading edge after a gap — burst then later trigger yields three executions*

With both edges enabled, a multi-trigger burst yields a leading and a trailing execution, and a further trigger that arrives only after the window has fully elapsed counts as a new leading edge and runs again, for three executions in total.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_burst_then_gap.json`

```json
{"description":"With leading-and-trailing behavior, a multi-invocation burst produces a leading invocation and a trailing invocation, and then a further invocation that arrives only after the quiet period has fully elapsed is recognized as a fresh leading edge and runs again. A burst of two invocations followed by one more invocation past the quiet window therefore yields three invocations in total.","cases":[{"input":{"hook":"callback","delay":1000,"options":{"leading":true},"steps":[{"do":"call","args":[]},{"do":"call","args":[]},{"do":"callAt","delay":1001,"args":[]},{"do":"advance","ms":1001},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]1 args=[] tag=fn\n[a specific derived string involving the email address or internal ID]2 args=[] tag=fn\n[a specific derived string involving the email address or internal ID]3 args=[] tag=fn\ncalls=3\n"}]}
```

*1.5 Maximum-wait bound — force an execution despite continuous triggering*

A maximum-wait bound guarantees the action runs no later than `maxWait` ms after the first trigger of a burst, even though each new trigger would otherwise keep resetting the quiet window and indefinitely postpone execution. When the bound elapses, the action runs once with the most recent arguments seen so far.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_maxwait.json`

```json
{"description":"A maximum-wait bound guarantees that a continuously re-triggered debounced function still runs no later than the configured maximum wait measured from the first invocation of the burst, even though each new invocation would otherwise keep resetting the quiet period and indefinitely postpone execution. When the maximum wait elapses, the function runs once with the arguments of the most recent invocation seen so far.","cases":[{"input":{"hook":"callback","delay":500,"options":{"maxWait":600},"steps":[{"do":"call","args":["Wrong value"]},{"do":"advance","ms":400},{"do":"observe"},{"do":"call","args":["Right value"]},{"do":"advance","ms":400},{"do":"observe"}]},"expected_output":"calls=0\n[a specific derived string involving the email address or internal ID]1 args=[\"Right value\"] tag=fn\ncalls=1\n"}]}
```

*1.6 Cancel — discard a pending execution*

Cancelling discards any execution that is currently pending so it never runs, even after the quiet window (and any maximum-wait bound) would otherwise have elapsed. After a cancel, advancing time produces no execution.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_cancel.json`

```json
{"description":"Cancelling a debounced function discards any invocation that is currently pending so that it never runs, even after the quiet period (and, when configured, the maximum-wait bound) would otherwise have elapsed. After a cancel, advancing time produces no invocation at all.","cases":[{"input":{"hook":"callback","delay":1000,"steps":[{"do":"call","args":[]},{"do":"cancel"},{"do":"runAll"},{"do":"observe"}]},"expected_output":"calls=0\n"}]}
```

*1.7 Flush and teardown — force a pending execution, or suppress it on disposal*

A flush forces any currently pending execution to run immediately with its captured arguments instead of waiting for the window. Flushing with nothing pending does nothing; flushing after a cancel does nothing (the cancel already discarded it). A pending execution that is never flushed is suppressed once the owning instance is disposed: disposing and then letting time elapse produces no execution.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_flush.json`

```json
{"description":"An explicit flush operation forces any currently pending invocation to run immediately with its captured arguments instead of waiting for the quiet period. Flushing when nothing is pending does nothing. Flushing after a cancel does nothing, because the cancel already discarded the pending invocation. A pending invocation that is never flushed is also suppressed once the owning component is torn down: tearing the component down and then letting time elapse produces no invocation.","cases":[{"input":{"hook":"callback","delay":500,"steps":[{"do":"call","args":[]},{"do":"flush"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]1 args=[] tag=fn\ncalls=1\n"}]}
```

*1.8 Latest behavior wins — a deferred execution uses the most recent action version*

When the wrapped action is replaced between triggers (for example because it closes over state that has since changed), a deferred execution always uses the most recently provided version rather than a stale one. The emitted execution line's `tag` marker reflects the latest version present at the moment the deferred execution fires, both when the action is updated before the trigger is scheduled and when it is updated while an execution is already pending.

**Test Cases:** `rcb_tests/public_test_cases/feature1_8_latest_callback.json`

```json
{"description":"When the wrapped behavior is replaced between invocations (for example because it closes over state that has since changed), a deferred invocation always uses the most recently provided behavior rather than a stale one. Each emitted invocation line carries a marker identifying which version of the behavior actually ran; the marker reflects the latest version present at the moment the deferred invocation fires, both when the behavior is updated before the invocation is scheduled and when it is updated while an invocation is already pending.","cases":[{"input":{"hook":"callback","delay":500,"initial":{"tag":"old"},"steps":[{"do":"setProps","props":{"tag":"new"}},{"do":"call","args":[]},{"do":"runAll"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]1 args=[] tag=new\ncalls=1\n"}]}
```

---

### Feature 2: Debounced Value

**As a developer**, I want a value that tracks a frequently-changing source but only settles after the source has been stable for a window, so I can drive expensive work off a calm value instead of every keystroke.

**Expected Behavior / Usage:**

*2.1 Basic value debouncing — immediate initial value, deferred updates, latest wins*

The debounced value equals the initial source value immediately on first render. When the source changes, the debounced value does not update until the quiet window elapses; while pending it keeps showing the previous settled value. If the source changes several times during the window, the debounced value settles on the most recent source value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_basic.json`

```json
{"description":"A debounced value mirrors a source value but only after the source has stopped changing for the configured delay. On the first render the debounced value equals the initial source value immediately. When the source value changes, the debounced value does not update until the quiet period elapses; while it is pending it keeps showing the previous debounced value. If the source changes several times during the quiet period, the debounced value eventually settles on the most recent source value.","cases":[{"input":{"hook":"value","delay":1000,"initial":{"value":"Hello world"},"steps":[{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]Hello world\n"}]}
```

*2.2 Leading-edge value — reflect the first change immediately*

With leading-edge behavior, the first change to the source value is reflected immediately rather than after the window. Subsequent changes within the window do not update immediately; the value then settles on the most recent source value once the window elapses.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_leading.json`

```json
{"description":"When the debounced value is configured for leading-edge behavior, the very first change to the source value is reflected immediately rather than after the delay. Subsequent changes that occur within the quiet period do not update the debounced value immediately; the debounced value then settles on the most recent source value once the quiet period elapses.","cases":[{"input":{"hook":"value","delay":1000,"options":{"leading":true},"initial":{"value":"Hello"},"steps":[{"do":"observe"},{"do":"setProps","props":{"value":"Hello world"}},{"do":"observe"},{"do":"setProps","props":{"value":"Hello again, world"}},{"do":"observe"},{"do":"runAll"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]Hello\n[a specific derived string involving the email address or internal ID]Hello world\n[a specific derived string involving the email address or internal ID]Hello world\n[a specific derived string involving the email address or internal ID]Hello again, world\n"}]}
```

*2.3 Cancel value — discard a pending update (including a max-wait-bounded one)*

Cancelling discards the pending update so the debounced value stays at its previous settled value even after time elapses. This holds for an ordinary pending update and for one also bounded by a maximum wait: the cancel removes the bounded update too, so the value never advances to the source value that was in flight.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_cancel.json`

```json
{"description":"Cancelling a debounced value discards the pending update so the debounced value remains at its previous settled value even after time elapses. This holds both for an ordinary pending update and for a pending update that is also bounded by a maximum wait: a cancel removes the bounded update as well, so the debounced value never advances to the source value that was in flight.","cases":[{"input":{"hook":"value","delay":1000,"initial":{"value":"Hello"},"steps":[{"do":"setProps","props":{"value":"Hello world"}},{"do":"observe"},{"do":"cancel"},{"do":"runAll"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]Hello\n[a specific derived string involving the email address or internal ID]Hello\n"}]}
```

*2.4 Maximum-wait value — force a settle, but not before the bound from the first pending change*

A maximum-wait bound guarantees the debounced value advances to the latest source value no later than `maxWait` ms after the first pending change, even while the source keeps changing within the window. The bound is armed only once a real change is pending; it is not started on the initial render, so a change introduced after idle time is not forced through earlier than the bound measured from that change.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_maxwait.json`

```json
{"description":"A maximum-wait bound on a debounced value guarantees the debounced value advances to the latest source value no later than the maximum wait measured from the first pending change, even when the source keeps changing within the quiet period. The maximum-wait timer is only armed once a real change is pending; it is not started on the initial render, so a change introduced after some idle time will not be forced through earlier than the maximum wait measured from that change.","cases":[{"input":{"hook":"value","delay":500,"options":{"maxWait":600},"initial":{"value":"Hello"},"steps":[{"do":"setProps","props":{"value":"Wrong value"}},{"do":"advance","ms":400},{"do":"observe"},{"do":"setProps","props":{"value":"Right value"}},{"do":"advance","ms":400},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]Hello\n[a specific derived string involving the email address or internal ID]Right value\n"}]}
```

*2.5 Custom equality — suppress updates the predicate deems equal*

The debounced value may take a custom equality predicate that decides whether a new source value differs from the current one. When the predicate reports equality, no update is scheduled and the debounced value stays unchanged regardless of how the raw source value differs or how much time elapses.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_equality.json`

```json
{"description":"A debounced value can take a custom equality predicate that decides whether a new source value is considered different from the current one. When the predicate reports that the values are equal, no update is scheduled and the debounced value stays unchanged regardless of how the raw source value differs and regardless of how much time elapses.","cases":[{"input":{"hook":"value","delay":1000,"options":{"equalityFn":"alwaysEqual"},"initial":{"value":"Hello"},"steps":[{"do":"observe"},{"do":"setProps","props":{"value":"Test"}},{"do":"runAll"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]Hello\n[a specific derived string involving the email address or internal ID]Hello\n"}]}
```

*2.6 Revert within the window — no net change*

If the source value changes and then changes back to the currently settled value before the window elapses, the debounced value shows no net change once time elapses: the in-flight intermediate value is superseded by the return to the original, so the value remains at the original.

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_revert.json`

```json
{"description":"If the source value changes and then changes back to the currently settled debounced value before the quiet period elapses, the debounced value shows no net change once time elapses: the in-flight intermediate value is superseded by the return to the original value, so the debounced value remains at the original value.","cases":[{"input":{"hook":"value","delay":500,"initial":{"value":"Hello"},"steps":[{"do":"setProps","props":{"value":"new value"}},{"do":"observe"},{"do":"setProps","props":{"value":"Hello"}},{"do":"runAll"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]Hello\n[a specific derived string involving the email address or internal ID]Hello\n"}]}
```

*2.7 Flush value — apply the pending value immediately*

A flush applies the pending source value immediately instead of waiting for the window. After a source change leaves an update pending, flushing makes the debounced value jump at once to the latest source value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_7_flush.json`

```json
{"description":"An explicit flush operation on a debounced value applies the pending source value immediately instead of waiting for the quiet period. After a source change leaves an update pending, flushing makes the debounced value jump at once to the latest source value.","cases":[{"input":{"hook":"value","delay":1000,"initial":{"value":"Hello"},"steps":[{"do":"setProps","props":{"value":"Test"}},{"do":"observe"},{"do":"flush"},{"do":"observe"}]},"expected_output":"[a specific derived string involving the email address or internal ID]Hello\n[a specific derived string involving the email address or internal ID]Test\n"}]}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the debounced-action and debounced-value primitives over a shared scheduling core, with edge policy (leading/trailing), maximum-wait bounding, custom value equality, and explicit cancel/flush controls. Physical structure must align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, drives the appropriate core primitive on a deterministic virtual clock per the Execution Protocol, and prints the resulting trace to stdout, matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases` for the delivered system; the authoritative hidden set lives in `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same ordering convention as the headers module
