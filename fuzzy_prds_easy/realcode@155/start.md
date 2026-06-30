## Product Requirement Document

# Unidirectional State Container — Predictable State Reduction & Observable State Streams

## Project Goal

Build a small, dependency-free unidirectional state container that lets developers model application state as a single source of truth: callers send typed *actions*, registered *reducers* turn each action plus the current state into the next state, and observers receive the resulting stream of states. The goal is to make state transitions predictable and easy to observe without hand-rolling event buses, mutable shared flags, or ad-hoc listener bookkeeping.

---

## Background & Problem

Without a state container, application logic that reacts to events tends to scatter mutable state across many objects, mixing "what happened" (events) with "how state changes" (transition logic) and "who is listening" (observers). This leads to race-prone code, inconsistent UI/state, and transitions that are hard to test in isolation.

This library centralizes the pattern: an immutable initial state is supplied up front; each action type is bound to a reducer that computes the next state; and the container guarantees a well-defined emission contract to whoever is listening — including buffering states produced before anyone is listening, replaying them in order when a listener attaches, and distinguishing persistent states from one-shot "single events" that should be delivered but never become the retained current state. On top of the container, two observable stream flavors are provided: a *live* stream that only forwards values while subscribed, and a *replaying* stream that remembers the latest value per type and replays it to each new subscriber.

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

### Feature 1: Unidirectional State Container

**As a developer**, I want to bind action types to reducers and process actions to produce a predictable stream of states, so I can manage application state from a single source of truth.

**Expected Behavior / Usage:**

The container is created with an initial state and a set of reducers, each reducer binding one action label to the state it produces. Actions and states are referred to by opaque string labels. A listener may be attached and detached; while attached, it receives every emitted state in order. The execution adapter exposes this through a request whose `scenario` is `kaskade`, carrying `initial` (the initial state label), `reducers` (a map from action label to `{ "to": <state label> }`), an optional `single_events` list naming state labels that are single events, and an ordered `ops` list. Each op is one of: `subscribe` (attach the recording listener), `unsubscribe` (detach it), `process` with an `action` label (reduce that action), `teardown` (clear all bindings), and (for replaying streams) `clear`. The output is the sequence of emitted state labels, one per line.

*1.1 Action-to-state reduction with initial-state emission — basic reduce behavior*

When a listener attaches, it immediately receives the current (initially the initial) state. Each processed action is then routed to its reducer, which yields the next state; that state is delivered to the listener and becomes the new current state. Processing an action whose reducer returns the same state as the current one still produces an emission.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_state_reduction.json`

```json
{
    "description": "A state container is created with an initial state and a set of action-to-state reducers. As soon as a listener is attached it receives the initial state, and thereafter every processed action is reduced to a new state which is delivered to the listener in order. Each emitted state is reported on its own line using its opaque state label.",
    "cases": [
        {
            "input": {
                "scenario": "kaskade",
                "initial": "running",
                "reducers": {"start": {"to": "running"}, "work": {"to": "working"}, "finish": {"to": "done"}},
                "ops": [{"op": "subscribe"}, {"op": "process", "action": "work"}]
            },
            "expected_output": "running\nworking\n"
        },
        {
            "input": {
                "scenario": "kaskade",
                "initial": "running",
                "reducers": {"start": {"to": "running"}, "work": {"to": "working"}, "finish": {"to": "done"}},
                "ops": [{"op": "subscribe"}, {"op": "process", "action": "finish"}]
            },
            "expected_output": "running\ndone\n"
        }
    ]
}
```

*1.2 Buffering and replay before a listener attaches*

States produced while no listener is attached are buffered in order and replayed to the first listener at the moment it attaches. The buffer begins with the initial state and is followed by one state per action processed before attachment. After the buffered states are replayed, later processing is delivered live.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_buffered_replay.json`

```json
{
    "description": "States produced before any listener is attached are buffered in order, and the buffer is replayed to the first listener the moment it attaches. The buffer always begins with the initial state, followed by one state per action processed while no listener was present. After the buffered states are replayed, subsequent processing continues to be delivered live.",
    "cases": [
        {
            "input": {
                "scenario": "kaskade",
                "initial": "running",
                "reducers": {"start": {"to": "running"}, "work": {"to": "working"}, "finish": {"to": "done"}},
                "ops": [{"op": "process", "action": "start"}, {"op": "process", "action": "work"}, {"op": "process", "action": "finish"}, {"op": "subscribe"}]
            },
            "expected_output": "running\nrunning\nworking\ndone\n"
        },
        {
            "input": {
                "scenario": "kaskade",
                "initial": "running",
                "reducers": {"start": {"to": "running"}, "work": {"to": "working"}, "finish": {"to": "done"}},
                "ops": [{"op": "process", "action": "work"}, {"op": "subscribe"}]
            },
            "expected_output": "running\nworking\n"
        }
    ]
}
```

*1.3 Single-event states (emitted but not persisted)*

A state declared as a single event is delivered to the listener exactly like any other state, but it never becomes the retained current state. After a single event is emitted, the next reduction still sees the previously persisted (non-event) state, so re-processing a regular action yields the same result it would have before the single event.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_single_event.json`

```json
{
    "description": "A state may be declared as a single event: it is delivered to the listener exactly like any other state, but it is never retained as the container's current state. After a single event is emitted, the next reduction still observes the previously persisted (non-event) state, so processing the same regular action again yields the same result as before the single event occurred.",
    "cases": [
        {
            "input": {
                "scenario": "kaskade",
                "initial": "idle",
                "single_events": ["toast"],
                "reducers": {"refresh": {"to": "idle"}, "notify": {"to": "toast"}},
                "ops": [{"op": "subscribe"}, {"op": "process", "action": "refresh"}, {"op": "process", "action": "notify"}, {"op": "process", "action": "refresh"}]
            },
            "expected_output": "idle\nidle\ntoast\nidle\n"
        }
    ]
}
```

*1.4 Error conditions (normalized)*

Two illegal situations are reported as normalized, language-neutral error lines. Processing an action that has no registered reducer yields `[a specific error category string — ask the test suite for the exact prefix]` followed by an `action=<label>` line naming the offending action. Processing any action after the container has been torn down (its bindings cleared) yields `error=unsubscribed`. Any states delivered before the failure still appear; the error then terminates the run.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_errors.json`

```json
{
    "description": "The container rejects two illegal situations with normalized error signals. Processing an action that has no registered reducer is reported as an unhandled-action error together with the offending action label. Processing any action after the container has been torn down (its bindings cleared) is reported as an unsubscribed error. Any states delivered before the error still appear, then the normalized error terminates the run.",
    "cases": [
        {
            "input": {
                "scenario": "kaskade",
                "initial": "idle",
                "reducers": {"refresh": {"to": "idle"}},
                "ops": [{"op": "subscribe"}, {"op": "process", "action": "unknown"}]
            },
            "expected_output": "idle\n[a specific error category string — ask the test suite for the exact prefix]\naction=unknown\n"
        },
        {
            "input": {
                "scenario": "kaskade",
                "initial": "idle",
                "reducers": {"refresh": {"to": "idle"}},
                "ops": [{"op": "subscribe"}, {"op": "teardown"}, {"op": "process", "action": "refresh"}]
            },
            "expected_output": "idle\nerror=unsubscribed\n"
        }
    ]
}
```

---

### Feature 2: Live Observable Stream

**As a developer**, I want a stream that forwards values to a subscriber only while it is actively subscribed, so transient events are not replayed to late or detached subscribers.

**Expected Behavior / Usage:**

The live stream applies a simple observer pattern with at most one subscriber at a time. Values sent while a subscriber is attached are delivered to it; values sent before any subscriber attaches are dropped (not buffered) and never seen; once a subscriber detaches, subsequent values are not delivered to it. The execution adapter exposes this through a request whose `scenario` is `flow` and `kind` is `plain`, with an ordered `ops` list of `subscribe`, `unsubscribe`, and `send` (carrying a string `value`). The output is each delivered value, one per line; if nothing is delivered the output is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature2_live_stream.json`

```json
{
    "description": "A live observable stream delivers values to its subscriber only while the subscription is active. Values emitted before a subscriber attaches are not buffered and are never seen. Once a subscriber detaches, further values are not delivered to it. Each delivered value is reported on its own line.",
    "cases": [
        {
            "input": {
                "scenario": "flow",
                "kind": "plain",
                "ops": [{"op": "subscribe"}, {"op": "send", "value": "hello"}]
            },
            "expected_output": "hello\n"
        },
        {
            "input": {
                "scenario": "flow",
                "kind": "plain",
                "ops": [{"op": "send", "value": "world"}, {"op": "subscribe"}, {"op": "send", "value": "hello"}]
            },
            "expected_output": "hello\n"
        }
    ]
}
```

---

### Feature 3: Replaying Observable Stream

**As a developer**, I want a stream that remembers the most recent value per type and replays it to every new subscriber, so a freshly attached observer can immediately render the current state without waiting for the next change.

**Expected Behavior / Usage:**

*3.1 Latest-per-type retention and replay*

The replaying stream records the latest value it has seen for each value type and replays the retained value(s) to each new subscriber the instant it attaches, in addition to forwarding live values. When several values share the same type, only the most recent is retained. Values are still recorded while no subscriber is attached (but not delivered), so a later subscriber sees the retained latest value; after detaching and re-attaching, the retained value is replayed again. The execution adapter exposes this through `scenario` `flow` with `kind` `dam`, using `subscribe`, `unsubscribe`, and `send` ops over string values (each string is its own value, all of one type, so retention keeps the last string).

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_replay_stream.json`

```json
{
    "description": "A replaying observable stream remembers the latest value it has seen for each value type and replays the remembered value(s) to every new subscriber the instant it attaches, in addition to forwarding live values. When several values share the same type only the most recent one is retained. A value sent while a subscriber is attached is delivered live; after detaching and re-attaching, the retained latest value is replayed again. While no subscriber is attached, values are still recorded but not delivered.",
    "cases": [
        {
            "input": {
                "scenario": "flow",
                "kind": "dam",
                "ops": [{"op": "send", "value": "test"}, {"op": "send", "value": "world"}, {"op": "subscribe"}, {"op": "send", "value": "hello"}]
            },
            "expected_output": "world\nhello\n"
        },
        {
            "input": {
                "scenario": "flow",
                "kind": "dam",
                "ops": [{"op": "subscribe"}, {"op": "send", "value": "hello"}, {"op": "unsubscribe"}, {"op": "subscribe"}]
            },
            "expected_output": "hello\nhello\n"
        }
    ]
}
```

*3.2 Clearing retained values*

The replaying stream can have its retained values cleared. After a clear, a newly attaching subscriber receives nothing from the past, confirming the retained value was discarded rather than merely hidden. Values delivered live before the clear still appear in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_replay_clear.json`

```json
{
    "description": "The replaying stream can have its remembered values cleared. After a clear, a newly attaching subscriber receives nothing from the past, confirming the retained value was truly discarded rather than merely hidden. Values delivered live before the clear still appear in the output.",
    "cases": [
        {
            "input": {
                "scenario": "flow",
                "kind": "dam",
                "ops": [{"op": "subscribe"}, {"op": "send", "value": "hello"}, {"op": "clear"}, {"op": "unsubscribe"}, {"op": "subscribe"}]
            },
            "expected_output": "hello\n"
        }
    ]
}
```

*3.3 Replaying a state container's states, excluding single events*

When a state container is observed through a replaying stream, the latest regular state is replayed to a new subscriber, but single-event states are never retained for replay. Reducing an action to a regular state records it for replay; emitting a single event delivers it live only; on detaching and re-attaching, only the latest regular state is replayed while the single event is omitted. The execution adapter exposes this through `scenario` `kaskade` with `flow` set to `dam`; here `subscribe`/`unsubscribe` attach/detach the replaying stream's subscriber and `process` drives the container.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_replay_single_event.json`

```json
{
    "description": "When a state container is observed through a replaying stream, the latest regular state is replayed to a new subscriber, but single-event states are never retained for replay. Reducing an action to a regular state records it for replay; emitting a single event delivers it live only; on detaching and re-attaching, only the latest regular state is replayed while the single event is omitted.",
    "cases": [
        {
            "input": {
                "scenario": "kaskade",
                "flow": "dam",
                "initial": "loaded",
                "single_events": ["toast"],
                "reducers": {"load": {"to": "loaded"}, "notify": {"to": "toast"}},
                "ops": [{"op": "process", "action": "load"}, {"op": "subscribe"}, {"op": "process", "action": "notify"}, {"op": "unsubscribe"}, {"op": "subscribe"}]
            },
            "expected_output": "loaded\ntoast\nloaded\n"
        }
    ]
}
```

---

### Feature 4: Media Player State Machine

**As a developer**, I want to model a concrete media player as actions reduced over a fixed playlist, so I can see the container drive realistic, stateful domain behavior end to end.

**Expected Behavior / Usage:**

A media-player state machine navigates a fixed circular playlist whose tracks, in order, are: Like Ooh-Ahh, Cheer up, TT, Knock Knock, Signal, One More Time, Likey, Heart Shaker, Candy Pop, What Is Love?, Wake Me Up, Dance The Night Away, BDZ, Yes Or Yes, The Best Thing I Ever Did. The machine begins stopped with no track selected. The `pause_play` action toggles playback: from a stopped or paused position it begins playing the current track (the first track when nothing has played yet); while already playing it switches to paused. The `next` action advances one track and plays it; `previous` steps back one track and plays it; both wrap around the playlist ends (advancing past the last track returns to the first; stepping before the first track returns to the last). The `stop` action halts playback and resets the position so the next play starts again from the first track. Observation uses the live stream, so only states produced by processed actions are reported (the implicit initial stopped state is not). Each emitted state is one line: a playing state as `Playing: <track>`, a paused state as `Paused`, or a stopped state as `Stopped`. The execution adapter exposes this through `scenario` `player` carrying an `actions` list of `pause_play` / `next` / `previous` / `stop`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_media_player.json`

```json
{
    "description": "A media-player state machine drives a fixed circular playlist of tracks through actions. The playlist, in order, is: Like Ooh-Ahh, Cheer up, TT, Knock Knock, Signal, One More Time, Likey, Heart Shaker, Candy Pop, What Is Love?, Wake Me Up, Dance The Night Away, BDZ, Yes Or Yes, The Best Thing I Ever Did. The machine starts stopped. A pause_play toggles between playing and paused: from a stopped or paused position it begins playing the current track (the first track when nothing has played yet); while already playing it pauses. A next moves forward one track (and starts playing), a previous moves back one track (and starts playing); both wrap around the ends of the playlist. A stop halts playback and resets the position so the next play starts from the first track. Each delivered state is reported on its own line: a playing state as the played track preceded by a label, a paused state, or a stopped state. Only states produced by processed actions are reported (the implicit initial stopped state is not).",
    "cases": [
        {
            "input": {"scenario": "player", "actions": ["pause_play"]},
            "expected_output": "Playing: Like Ooh-Ahh\n"
        },
        {
            "input": {"scenario": "player", "actions": ["pause_play", "pause_play"]},
            "expected_output": "Playing: Like Ooh-Ahh\nPaused\n"
        },
        {
            "input": {"scenario": "player", "actions": ["stop"]},
            "expected_output": "Stopped\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the unidirectional state container (action-to-state reduction, initial-state emission, buffering and replay before a listener attaches, single-event semantics, and normalized error handling), the two observable stream flavors (live and replaying-with-latest-per-type retention plus clear), and the media-player state machine built on top of the container. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting stream of emitted states/values (or a normalized error) to stdout, matching the per-feature contracts above. The request's `scenario` selects behavior: `kaskade` drives the state container (optionally observed through a `flow` of `plain` or `dam`), `flow` drives a standalone live (`plain`) or replaying (`dam`) stream, and `player` drives the media-player state machine. Native exceptions raised by the core must be translated by the adapter into the normalized `error=<category>` lines specified above; the core itself must never depend on this output contract.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the buffer handling in the subscription companion module
- reference the drop handlers defined in the observer lifecycle utility
