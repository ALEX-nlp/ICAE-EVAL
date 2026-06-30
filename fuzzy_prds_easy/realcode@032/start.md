## Product Requirement Document

# Asynchronous Stream Assertion Toolkit — A library for deterministically testing values, completion, and errors produced over time by an asynchronous stream

## Project Goal

Build a small testing toolkit that lets developers assert, step by step, exactly what an **asynchronous stream** produces — the ordered data items it emits, whether it ends by completing normally or by failing with an error, and the timing of those signals — without writing ad‑hoc buffering, polling, or sleep‑based glue in every test.

An *asynchronous stream* here is a producer that, once observed, delivers zero or more **data items** and then exactly one **terminal signal**: either a **normal completion** or a **terminal error**. Some streams never terminate at all. The toolkit observes such a stream inside a scoped *observation block*, buffers everything it produces, and exposes pull‑style assertion operations the developer calls in the order they expect events to arrive.

---

## Background & Problem

Without this toolkit, a developer testing time‑based producers must hand‑roll a buffer, manually drain it, race against wall‑clock delays with arbitrary sleeps, and reason about partially consumed output. Tests become slow, flaky, and verbose, and subtle contract violations — a leftover unconsumed value, a stream that keeps running after the test thinks it stopped, a missed terminal error — slip through silently.

With this toolkit, the developer opens an observation block over the stream and consumes events one at a time with intention‑revealing operations ("the next thing must be an item; give me its value", "the next thing must be the completion signal"). Waiting is bounded by a deadline measured on a **virtual clock**, so tests are instant and deterministic. When the block ends, the toolkit enforces that every received event was accounted for, turning "I forgot to assert the last value" into a loud failure instead of a silent pass.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The domain is small but has several distinct responsibilities (the observation/buffering engine, the per‑event assertion operations, the terminal "all consumed" check, the virtual‑clock deadline). Keep the core toolkit cleanly separated from the execution adapter; do not collapse everything into one monolithic file, but do not over‑engineer a small library either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, NOT the internal data model of the toolkit. The core assertion engine must know nothing about JSON, stdin, or stdout. The adapter alone translates a JSON scenario into calls on the core toolkit and renders the toolkit's outcomes (including any native exceptions it raises) into the normalized text contract.

3. **Adherence to SOLID Design Principles:** Separate stream construction, event buffering, the assertion operations, the deadline mechanism, and output formatting into cohesive units. The set of event kinds (item / completion / error) should be modeled as a closed type the assertion operations branch on.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface (open a block, pull events, stop observing) must read naturally in the target language.
   - **Resilience:** Contract violations must be modeled as first‑class outcomes — a mismatched event kind, leftover unconsumed events, a deadline overrun, and an error raised by the developer's own block code are all distinct, deterministically reportable conditions.

---

## Execution Adapter Contract (shared by all features)

The execution adapter reads **one JSON object** from stdin describing a scenario, drives the real toolkit, and writes **only** the normalized outcome lines to stdout (one signal per line, each terminated by a newline). It then exits.

**Scenario fields (default scenario, `"scenario":"consume"` — may be omitted):**

- `emissions`: ordered array of string values the stream emits as data items before its terminal signal (default `[]`).
- `terminal`: how the stream ends after its emissions — `"complete"` (normal completion, the default), `"error"` (terminal failure), or `"never"` (the stream stays open and never terminates).
- `errorLabel`: a neutral category string carried by an `"error"` terminal (default `"generic"`).
- `ops`: ordered list of operations the observer performs inside the observation block. Each operation is one of:
  - `take_item` — assert the next event is a data item and emit its value as `item=<value>`.
  - `take_completion` — assert the next event is the normal completion signal and emit `complete`.
  - `take_error` — assert the next event is the terminal error and emit `error_terminal=<category>`.
  - `take_event` — consume the next event of any kind and emit it tagged: `event=item:<value>`, `event=complete`, or `event=error:<category>`.
  - `assert_empty` — assert no events are currently buffered and emit `no_events`.
  - `stop` — stop observing the stream but keep events already received.
  - `stop_and_drain` — stop observing and hand back every still‑buffered event, each emitted as `remaining=item:<value>` / `remaining=complete` / `remaining=error:<category>`.
  - `stop_and_discard` — stop observing and silently drop every still‑buffered event; a single `ignored` line is emitted once the block ends cleanly.
  - `probe_active` — emit `collecting=true` or `collecting=false` reflecting whether the stream is still being observed at that moment.
  - `raise` — the developer's block code throws an exception.
- `reportAfter`: if `true`, after the observation block returns, emit one final liveness probe line (`collecting=true`/`collecting=false`).

**Outcome lines for violations (rendered by the adapter from the toolkit's native failures, normalized — no host‑language type names):**

- Wrong event kind: `error=unexpected_event`, then `expected=<item|complete|error>`, then `found=<item:<value>|complete|error:<category>>`.
- Leftover events when the block ends: `error=unconsumed_events`, then one `unconsumed=<item:<value>|complete|error:<category>>` line per leftover, in order.
- An exception escaping the block: `error=block_exception`.
- A deadline overrun: `error=timeout`, then `waited_ms=<window>`.

**Timeout scenario (`"scenario":"timeout"`):** fields `timeoutMs` (deadline window in ms; `0` disables the deadline), `mode` (`"enforced"` or `"zero"`), and virtual‑clock advances `advance1Ms`/`advance2Ms`. See Feature 12.

---

## Core Features

### Feature 1: Pull the next event as a data item

**As a developer**, I want to assert the next event is a data item and read its value, so I can check emissions one at a time.

**Expected Behavior / Usage:**

`take_item` consumes the next buffered event. If it is a data item, its carried value is surfaced (`item=<value>`). If instead the next event is the stream's normal completion or its terminal error, the operation fails with an `unexpected_event` violation that names what was expected (`item`) and what was actually found (`complete`, or `error:<category>`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_expect_item.json`

```json
{
    "description": "Consume the next buffered event and assert it is a data item, returning its value. Covers the happy path (a value is emitted and read back), and the two failure paths where the next event is the stream's termination signal or its error signal instead of a data item; in those failure cases the assertion reports a neutral 'unexpected event' violation naming what was expected versus what was found.",
    "cases": [
        {"input": {"emissions": ["alpha"], "terminal": "complete", "ops": ["take_item", "stop_and_discard"]}, "expected_output": "item=alpha\nignored\n"},
        {"input": {"emissions": [], "terminal": "complete", "ops": ["take_item"]}, "expected_output": "error=unexpected_event\nexpected=item\nfound=complete\n"}
    ]
}
```

---

### Feature 2: Pull the next event as the completion signal

**As a developer**, I want to assert the stream terminated normally, so I can verify it finished without emitting anything unexpected.

**Expected Behavior / Usage:**

`take_completion` consumes the next event and asserts it is the normal completion signal, emitting `complete`. If the next event is a data item instead, it fails with an `unexpected_event` violation naming `expected=complete` and the data item found (`found=item:<value>`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_expect_complete.json`

```json
{
    "description": "Assert that the next buffered event is the stream's normal termination signal. Covers the happy path on a stream that finishes without emitting anything, and the failure path where a data item is found instead, which reports a neutral 'unexpected event' violation naming what was expected versus what was found.",
    "cases": [
        {"input": {"emissions": [], "terminal": "complete", "ops": ["take_completion"]}, "expected_output": "complete\n"},
        {"input": {"emissions": ["alpha"], "terminal": "complete", "ops": ["take_completion"]}, "expected_output": "error=unexpected_event\nexpected=complete\nfound=item:alpha\n"}
    ]
}
```

---

### Feature 3: Pull the next event as the terminal error

**As a developer**, I want to assert the stream failed and recover a neutral category for the failure, so I can verify error paths.

**Expected Behavior / Usage:**

`take_error` consumes the next event and asserts it is the terminal error, surfacing its neutral category (`error_terminal=<category>`). If the next event is a data item or the normal completion signal instead, it fails with an `unexpected_event` violation naming `expected=error` and what was found.

**Test Cases:** `rcb_tests/public_test_cases/feature3_expect_error.json`

```json
{
    "description": "Assert that the next buffered event is the stream's terminal error signal, surfacing a neutral category for the failure that ended the stream. Covers the happy path where the stream fails, and the two failure paths where a data item or the normal termination signal is found instead, each reporting a neutral 'unexpected event' violation naming what was expected versus what was found.",
    "cases": [
        {"input": {"terminal": "error", "errorLabel": "boom", "ops": ["take_error"]}, "expected_output": "error_terminal=boom\n"},
        {"input": {"emissions": ["alpha"], "terminal": "complete", "ops": ["take_error"]}, "expected_output": "error=unexpected_event\nexpected=error\nfound=item:alpha\n"}
    ]
}
```

---

### Feature 4: Pull the next event without asserting its kind

**As a developer**, I want to consume the next event as a tagged value I can inspect, so I can branch on its kind myself.

**Expected Behavior / Usage:**

`take_event` consumes the next buffered event of any kind and yields it tagged by category: `event=item:<value>` for a data item, `event=complete` for normal completion, or `event=error:<category>` for the terminal error. It never fails on the basis of the event kind.

**Test Cases:** `rcb_tests/public_test_cases/feature4_expect_event.json`

```json
{
    "description": "Consume the next buffered event without asserting its kind, returning a tagged event whose category (data item, normal termination, or terminal error) the caller can inspect. Covers each of the three event kinds in turn.",
    "cases": [
        {"input": {"emissions": ["alpha"], "terminal": "complete", "ops": ["take_event", "stop_and_discard"]}, "expected_output": "event=item:alpha\nignored\n"},
        {"input": {"emissions": [], "terminal": "complete", "ops": ["take_event", "stop_and_discard"]}, "expected_output": "event=complete\nignored\n"}
    ]
}
```

---

### Feature 5: Assert nothing has been buffered yet

**As a developer**, I want to assert that an actively observed stream has produced nothing so far, so I can verify quiescence at a point in time.

**Expected Behavior / Usage:**

`assert_empty` checks the buffer non‑destructively and succeeds (emitting `no_events`) only when no events have been received yet. It does not wait for events; it inspects the current state. Used here on a stream that is open but silent.

**Test Cases:** `rcb_tests/public_test_cases/feature5_expect_no_events.json`

```json
{
    "description": "Assert that no events have yet been buffered from a stream that is actively being observed but has produced nothing so far, then stop observing. Succeeds silently when the buffer is empty.",
    "cases": [
        {"input": {"terminal": "never", "ops": ["assert_empty", "stop"]}, "expected_output": "no_events\n"}
    ]
}
```

---

### Feature 6: Unconsumed events fail the block

**As a developer**, I want the toolkit to fail my test if any received event went unread, so I can never accidentally under‑assert.

**Expected Behavior / Usage:**

When the observation block ends, the toolkit verifies that every event it received was consumed. If any remain, it fails with an `unconsumed_events` violation that lists each leftover, in arrival order, tagged by category (`unconsumed=item:<value>`, `unconsumed=complete`, or `unconsumed=error:<category>`). The cases cover a leftover data item, a leftover completion signal, and a leftover error.

**Test Cases:** `rcb_tests/public_test_cases/feature6_unconsumed_events_fail.json`

```json
{
    "description": "When the observation block ends while events received from the stream remain unconsumed, the observation fails with a neutral 'unconsumed events' violation that lists every leftover event in order, each tagged by its category (data item with value, normal termination, or terminal error). Covers a leftover data item, a leftover termination signal, and a leftover error signal.",
    "cases": [
        {"input": {"emissions": ["alpha"], "terminal": "never", "ops": []}, "expected_output": "error=unconsumed_events\nunconsumed=item:alpha\n"},
        {"input": {"emissions": [], "terminal": "complete", "ops": []}, "expected_output": "error=unconsumed_events\nunconsumed=complete\n"}
    ]
}
```

---

### Feature 7: Plain stop retains already‑received events

**As a developer**, I want stopping observation to halt collection but keep what was already received, so leftover events still get checked at block end.

**Expected Behavior / Usage:**

`stop` halts further collection from the stream but does **not** clear events already buffered. Those retained events are still subject to the end‑of‑block unconsumed check, so failing to read them still produces an `unconsumed_events` violation. Here one item is read first, observation is stopped, and the remaining event of each kind is reported as a leftover.

**Test Cases:** `rcb_tests/public_test_cases/feature7_unconsumed_after_cancel_fail.json`

```json
{
    "description": "Stopping observation with the plain cancel operation halts further collection but retains any events already received. If those retained events are never consumed before the observation block ends, it fails with the same neutral 'unconsumed events' violation listing the leftovers. Here one item is read first, then observation is cancelled, leaving exactly one more event of each kind unconsumed across the cases.",
    "cases": [
        {"input": {"emissions": ["one", "two"], "terminal": "never", "ops": ["take_item", "stop"]}, "expected_output": "item=one\nerror=unconsumed_events\nunconsumed=item:two\n"}
    ]
}
```

---

### Feature 8: Stop and drain the remaining events

**As a developer**, I want a stop variant that hands back everything still buffered, so I can assert the tail explicitly and end the block cleanly.

**Expected Behavior / Usage:**

`stop_and_drain` halts collection and returns every still‑buffered event as an ordered list, each surfaced as `remaining=item:<value>` / `remaining=complete` / `remaining=error:<category>`. Because the leftovers are handed back rather than left in the buffer, the end‑of‑block unconsumed check passes and no violation is raised.

**Test Cases:** `rcb_tests/public_test_cases/feature8_consume_remaining.json`

```json
{
    "description": "A draining variant of cancel stops collection and returns every still-buffered event to the caller as an ordered list, each tagged by category. Because the leftovers are handed back rather than left in the buffer, the observation block ends cleanly with no violation. Here one item is read first, then the drain returns the single remaining event of each kind.",
    "cases": [
        {"input": {"emissions": ["one", "two"], "terminal": "never", "ops": ["take_item", "stop_and_drain"]}, "expected_output": "item=one\nremaining=item:two\n"}
    ]
}
```

---

### Feature 9: Stop and discard the remaining events

**As a developer**, I want a stop variant that drops everything still buffered, so I can end early without tripping the unconsumed check.

**Expected Behavior / Usage:**

`stop_and_discard` halts collection and silently discards every still‑buffered event, then exits the observation block immediately. The end‑of‑block unconsumed check is satisfied because nothing remains, and a single `ignored` line marks the clean exit. The discarded content (item, completion, or error) does not change the outcome.

**Test Cases:** `rcb_tests/public_test_cases/feature9_ignore_remaining.json`

```json
{
    "description": "A discarding variant of cancel stops collection and silently drops every still-buffered event, so the observation block ends cleanly even though events were left over. Covers discarding a leftover data item, a leftover termination signal, and a leftover error signal.",
    "cases": [
        {"input": {"emissions": ["alpha"], "terminal": "complete", "ops": ["stop_and_discard"]}, "expected_output": "ignored\n"}
    ]
}
```

---

### Feature 10: Observation lifecycle is scoped to the block

**As a developer**, I want the stream to stop being observed as soon as the block is done with it, so no work leaks past the test.

**Expected Behavior / Usage:**

While the observation block is active, the stream is being collected (`collecting=true`). Collection is torn down the moment the block stops needing it. The `probe_active` operation reports the live state at any point; `reportAfter` reports it once more after the block returns. Observation can end four equivalent ways: an explicit `stop` mid‑block, the block simply returning, an exception escaping the block, or a discarding stop. In every case collection is running before and torn down after. (When an exception escapes, its `error=block_exception` line appears between the before/after probes; a discarding stop emits its `ignored` line there.)

**Test Cases:** `rcb_tests/public_test_cases/feature10_collection_lifecycle.json`

```json
{
    "description": "Observation of the source stream stays active only for as long as the observation block needs it: once the block stops observing, upstream collection is torn down. A liveness probe reports whether collection is currently running. Across the cases, observation ends in four different ways - an explicit cancel mid-block, normal completion of the block, an exception escaping the block, and a discarding cancel - and in every case collection is reported running before and stopped after.",
    "cases": [
        {"input": {"terminal": "never", "ops": ["probe_active", "stop", "probe_active"]}, "expected_output": "collecting=true\ncollecting=false\n"},
        {"input": {"terminal": "never", "ops": ["probe_active", "raise"], "reportAfter": true}, "expected_output": "collecting=true\nerror=block_exception\ncollecting=false\n"}
    ]
}
```

---

### Feature 11: Exceptions from the block propagate

**As a developer**, I want an exception thrown by my own code inside the block to surface unchanged, so my test fails for the real reason.

**Expected Behavior / Usage:**

If the developer's code inside the observation block throws, the toolkit does not swallow or wrap it away — the exception propagates out of the observation call so the surrounding test fails for the original cause. The adapter renders this as `error=block_exception`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_block_exception_propagates.json`

```json
{
    "description": "An exception raised by the caller's code inside the observation block is not swallowed: it propagates out of the observation call so the surrounding test fails for the original reason. The neutral output marks that a caller-raised exception escaped the block.",
    "cases": [
        {"input": {"terminal": "never", "ops": ["raise"]}, "expected_output": "error=block_exception\n"}
    ]
}
```

---

### Feature 12: Deadline on a virtual clock

**As a developer**, I want each wait for the next event bounded by a deadline on a virtual clock, so tests waiting on a silent stream fail fast and deterministically instead of hanging.

**Expected Behavior / Usage:**

When an assertion waits for an event that never arrives, the wait is bounded by a configurable deadline window measured on a **virtual clock** (no real time passes). The wait stays pending while the virtual clock is advanced up to just before the window (`active=true`), and aborts the instant the window is crossed (`active=false`), producing a `timeout` violation that reports the window length (`waited_ms=<window>`). A window of zero **disables** the deadline entirely: the wait then stays pending no matter how far the clock is advanced, and is only ended by explicitly stopping it (`cancelled`).

**Test Cases:** `rcb_tests/public_test_cases/feature12_timeout.json`

```json
{
    "description": "While waiting for the next event, the observer enforces a deadline measured on a virtual clock. If no event arrives within the configured window the wait aborts with a neutral timeout violation that reports the window length. The first two cases use the default and a custom window and show the wait still pending just before the deadline and aborted just after; the third case sets the window to zero, which disables the deadline entirely so the wait stays pending no matter how far the clock advances.",
    "cases": [
        {"input": {"scenario": "timeout", "timeoutMs": 1000, "mode": "enforced", "advance1Ms": 999, "advance2Ms": 1}, "expected_output": "active=true\nactive=false\nerror=timeout\nwaited_ms=1000\n"},
        {"input": {"scenario": "timeout", "timeoutMs": 0, "mode": "zero", "advance1Ms": 864000000}, "expected_output": "active=true\ncancelled\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured toolkit implementing the observation engine, the per‑event assertion operations (item / completion / error / generic event / empty check), the three stop variants (retain / drain / discard), the end‑of‑block unconsumed‑events enforcement, propagation of block exceptions, and the virtual‑clock deadline. Keep the core decoupled from all I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON scenario from stdin, drives the toolkit accordingly, and prints the normalized outcome lines defined in the Execution Adapter Contract to stdout — translating the toolkit's native failures into the neutral violation lines. It must be separate from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` that reads every `*.json` case file from a case directory and runs the full suite, accepting `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03d}.txt` containing **only** the raw program stdout, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the virtual clock logic defined in the timeout test suite
