## Product Requirement Document

# Composable Reactive Stream Toolkit — Push/Pull Stream Sources, Operators, and Consumers

## Project Goal

Build a small, composable library for working with streams of values over time that allows developers to declaratively create streams, transform and combine them through a pipeline of operators, and consume their results, without hand-writing ad-hoc callback wiring, manual subscription bookkeeping, or one-off buffering logic for every data flow.

---

## Background & Problem

Without a stream toolkit, developers who need to react to a series of values — whether produced eagerly from a collection, lazily on demand, or pushed in live over time — end up reinventing the same machinery again and again: manual callback lists, bespoke unsubscribe flags, hand-rolled buffering for "take the last [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram]", and brittle glue to chain one transformation into the next. Each reinvention drifts in its edge-case behavior (what happens on early termination, on completion, on a consumer that leaves mid-flight), making data flows hard to reason about and compose.

With this toolkit, a stream is a single first-class value that a consumer can subscribe to. Stream sources describe where values come from; operators are pure functions that take a source and return a new source with transformed behavior; consumers drive a source and observe its emissions. The same small set of building blocks composes into arbitrary pipelines with one consistent contract for emission order, early termination, and completion.

The core abstraction is a stream that, to a consumer, produces zero or more values and then optionally signals completion. Sources may be "pull" sources (cold, re-run per consumer, driven on demand) or "push"/live sources (hot, shared, emitting as values arrive). Operators preserve the order of values and forward the completion signal unless their own semantics dictate otherwise. A consumer may also leave early; once it has left, it receives nothing further.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements ([a specific integer [a specific threshold N to compare against] — verify with the PRD diagram]FRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram]OT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain (distinct source factories, a family of operators, and several consumer types) is naturally multi-file.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSO[a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram]OT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSO[a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] parsing. The execution adapter is solely responsible for translating JSO[a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] commands into idiomatic calls to the core domain and rendering the observed stream signals to the line-based output contract.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate sources, operators, consumers, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram]ew operators must be addable without modifying existing ones; operators are composed, not edited.
   - **Liskov Substitution Principle (LSP):** Every operator returns a stream that is substitutable anywhere a stream is expected.
   - **Interface Segregation Principle (ISP):** Keep the stream and consumer interfaces small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level pipelines should depend on the stream abstraction, not on concrete source or consumer implementations.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language. Pipelines should read as a source followed by a sequence of operators followed by a consumer.
   - **Resilience:** The system must handle edge cases gracefully: empty streams, streams that never complete, consumers that leave early, and early termination triggered by an operator. Termination must be propagated so upstream work stops.

---

## Output Contract (shared by all features)

The execution adapter reads one JSO[a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] request from input and renders the observed stream signals as lines of text:

- One line `value <v>` per emitted value, in emission order, where `<v>` is the JSO[a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] encoding of the value.
- A final line `end` when the stream sends its completion signal.
- A final line `no-end` when the stream is observed to never complete.
- For the single-value consumer, one line `resolved <v>`.
- For multi-consumer scenarios, every line is prefixed with the receiving consumer's id: `<id> value <v>` and `<id> end`.

---

## Core Features

### Feature 1: Stream Source Factories

**As a developer**, I want a handful of primitive factories that turn ordinary data (a collection, a single value, nothing, or an endless silence) into streams, so I can feed any pipeline from a consistent source abstraction.

**Expected Behavior / Usage:**

*1.1 Source from a collection — emit each element of a finite ordered collection, in order, then complete*

Given a finite ordered collection, the source emits each element exactly once in the given order to its consumer and then signals completion. It is a cold/pull source: it produces its elements on demand for each consumer.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_from_array.json`

```json
{
    "description": "A source created from a finite ordered collection of values emits each value once, in the order given, to a single consumer, and then signals completion. The consumer renders one line per received value followed by a completion line.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [10, 20, 30]}},
            "expected_output": "value 10\nvalue 20\nvalue 30\nend\n"
        }
    ]
}
```

*1.2 Source from a single value — emit exactly one value, then complete*

Given a single value, the source emits that one value and then completes, no matter how many further values the consumer requests.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_from_value.json`

```json
{
    "description": "A source created from a single value emits exactly that one value and then signals completion, regardless of how many times the consumer requests more. The consumer renders the single value followed by a completion line.",
    "cases": [
        {
            "input": {"source": {"type": "fromValue", "value": 123}},
            "expected_output": "value 123\nend\n"
        }
    ]
}
```

*1.3 Empty source — emit nothing and complete immediately*

The empty source emits no values and signals completion immediately upon subscription.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_empty.json`

```json
{
    "description": "The empty source emits no values and signals completion immediately upon subscription. The consumer renders only a completion line with no value lines.",
    "cases": [
        {
            "input": {"source": {"type": "empty"}},
            "expected_output": "end\n"
        }
    ]
}
```

*1.4 [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram]ever source — emit nothing and never complete*

The never source emits no values and never signals completion; it remains permanently open.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_never.json`

```json
{
    "description": "The never source emits no values and never signals completion; it remains permanently open. The consumer renders no value lines and a line indicating the stream did not complete.",
    "cases": [
        {
            "input": {"source": {"type": "never"}},
            "expected_output": "no-end\n"
        }
    ]
}
```

---

### Feature 2: Value Transformation Operators

**As a developer**, I want operators that transform each value, drop unwanted values, or accumulate across values, so I can reshape a stream's contents without touching its plumbing.

**Expected Behavior / Usage:**

*2.1 Map — transform every value*

The map operator applies a transformation function to every value and forwards the transformed value, preserving order and completion. In these cases the transformation multiplies each value by a configured factor (`multiplyBy`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_map.json`

```json
{
    "description": "The map operator applies a transformation to every value emitted by its upstream source and forwards the transformed value downstream, preserving order and the completion signal. Here the transformation multiplies each value by a configured factor.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3, 4, 5]}, "operators": [{"op": "map", "multiplyBy": 2}]},
            "expected_output": "value 2\nvalue 4\nvalue 6\nvalue 8\nvalue 10\nend\n"
        }
    ]
}
```

*2.2 Filter — keep only matching values*

The filter operator forwards only values that satisfy a predicate and drops the rest, preserving order and completion. Here the predicate keeps values evenly divisible by a configured divisor (`keepDivisibleBy`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_filter.json`

```json
{
    "description": "The filter operator forwards only the values for which a predicate holds and drops the rest, preserving the order of the values that pass and the completion signal. Here the predicate keeps values that are evenly divisible by a configured divisor.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3, 4, 5, 6]}, "operators": [{"op": "filter", "keepDivisibleBy": 2}]},
            "expected_output": "value 2\nvalue 4\nvalue 6\nend\n"
        }
    ]
}
```

*2.3 Scan — emit a running accumulation*

The scan operator folds incoming values into an accumulator starting from a `seed`, emitting the running accumulated result after each input value, then forwarding completion. Here the fold adds each value to the accumulator (a running total).

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_scan.json`

```json
{
    "description": "The scan operator folds the incoming values with an accumulator, starting from a seed, and emits the running accumulated result after each input value. Here the fold adds each value to the accumulator, so the output is the running total. Completion is forwarded after the last result.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3]}, "operators": [{"op": "scan", "seed": 0}]},
            "expected_output": "value 1\nvalue 3\nvalue 6\nend\n"
        }
    ]
}
```

---

### Feature 3: Combining Multiple Sources

**As a developer**, I want to fuse several streams into one — interleaved, sequenced, flattened, or paired by latest value — so I can express multi-source data flows as a single downstream stream.

**Expected Behavior / Usage:**

*3.1 Merge — flatten several sources concurrently*

Merging a set of sources yields a single source emitting all values from every input and completing only after every input completes. With synchronous pull-driven inputs, values appear grouped per source in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_merge.json`

```json
{
    "description": "Merging several finite sources produces a single source that emits all of the values from every input source and completes only once all inputs have completed. When the inputs are synchronous pull-driven sources, their values appear grouped per source in input order.",
    "cases": [
        {
            "input": {"source": {"type": "merge", "sources": [{"type": "fromArray", "values": [1, 2, 3]}, {"type": "fromArray", "values": [4, 5, 6]}]}},
            "expected_output": "value 1\nvalue 2\nvalue 3\nvalue 4\nvalue 5\nvalue 6\nend\n"
        }
    ]
}
```

*3.2 Concat — sequence sources one after another*

Concatenating sources yields a single source that fully drains the first input before moving to the next, and so on, completing after the last input completes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_concat.json`

```json
{
    "description": "Concatenating several finite sources produces a single source that emits every value of the first source, then every value of the next, and so on, fully draining each source before moving to the next, and completes after the last source completes.",
    "cases": [
        {
            "input": {"source": {"type": "concat", "sources": [{"type": "fromArray", "values": [1, 2, 3]}, {"type": "fromArray", "values": [4, 5, 6]}]}},
            "expected_output": "value 1\nvalue 2\nvalue 3\nvalue 4\nvalue 5\nvalue 6\nend\n"
        }
    ]
}
```

*3.3 Flatten — merge a source of sources*

Flattening a source whose values are themselves sources subscribes to those inner sources and merges all of their values into one output stream, completing once the outer source and all inner sources have completed.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_flatten.json`

```json
{
    "description": "Flattening a source whose values are themselves sources subscribes to the inner sources and emits all of their values into one combined output stream, completing once the outer source and all inner sources have completed. Here each inner source is a finite collection of values.",
    "cases": [
        {
            "input": {"source": {"type": "flatten", "sources": [{"type": "fromArray", "values": [1, 2]}, {"type": "fromArray", "values": [3, 4]}]}},
            "expected_output": "value 1\nvalue 2\nvalue 3\nvalue 4\nend\n"
        }
    ]
}
```

*3.4 Combine latest — pair the most recent value of two live sources*

Combining the latest values of two live (hot) sources emits a pair whenever either source emits a new value, once both have emitted at least once. The pair holds the most recent value of the first source followed by the most recent value of the second source. The combined stream completes after both sources complete. The input is an interleaved emission script identifying the first source as `"a"` and the second as `"b"`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_combine.json`

```json
{
    "description": "Combining the latest values of two live (hot) sources produces a stream of pairs: whenever either source emits a new value, and once both sources have emitted at least once, a pair holding the most recent value of each source (first source value, then second source value) is emitted. The combined stream completes after both sources complete. The input is an interleaved script of which source emits which value, identified as the first source ('a') or the second source ('b').",
    "cases": [
        {
            "input": {"kind": "combine", "emissions": [{"source": "a", "value": 1}, {"source": "b", "value": 2}, {"source": "a", "value": 3}, {"source": "b", "value": 4}]},
            "expected_output": "value [1,2]\nvalue [3,2]\nvalue [3,4]\nend\n"
        }
    ]
}
```

---

### Feature 4: Limiting and Skipping Operators

**As a developer**, I want operators that bound how many values flow through, by count, by predicate, or by a signal from another stream, so I can shape and terminate flows precisely.

**Expected Behavior / Usage:**

*4.1 Take — at most [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] values, then complete*

The take operator lets at most a configured number of values pass, then completes and ends the upstream source early. If the source completes on its own before that many values arrive, the received values and the completion are forwarded.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_take.json`

```json
{
    "description": "The take operator lets at most a configured number of values pass and then signals completion, ending the upstream source early. If the source completes on its own before that many values are emitted, the operator simply forwards the values it received and the completion signal. The first case shows the cap being reached on a longer source; the second shows the source ending before the cap.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3, 4, 5]}, "operators": [{"op": "take", "n": 2}]},
            "expected_output": "value 1\nvalue 2\nend\n"
        },
        {
            "input": {"source": {"type": "fromArray", "values": [1]}, "operators": [{"op": "take", "n": 5}]},
            "expected_output": "value 1\nend\n"
        }
    ]
}
```

*4.2 Take last — the final [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] values, after completion*

The takeLast operator buffers values and, only after the upstream source completes, emits the final configured number of values in original order, then completes. [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram]othing is emitted before the source ends.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_take_last.json`

```json
{
    "description": "The takeLast operator buffers values and, only after the upstream source completes, emits the final configured number of values in their original order, then signals completion. [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram]othing is emitted before the source ends.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3, 4]}, "operators": [{"op": "takeLast", "n": 2}]},
            "expected_output": "value 3\nvalue 4\nend\n"
        }
    ]
}
```

*4.3 Take while — values until the predicate first fails*

The takeWhile operator forwards values while a predicate holds; the first value that fails the predicate ends the stream (that value is not emitted) and ends the upstream source. If the source completes while the predicate still holds, the seen values and completion are forwarded. Here the predicate accepts values up to and including a configured bound (`whileAtMost`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_take_while.json`

```json
{
    "description": "The takeWhile operator forwards values for as long as a predicate holds; the first value that fails the predicate ends the stream (it is not emitted) and the upstream source is ended. If the source completes while the predicate still holds for every value, the values seen and the completion signal are forwarded. Here the predicate accepts values up to and including a configured upper bound. The first case shows the predicate failing partway through; the second shows the source ending before the predicate fails.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3, 4]}, "operators": [{"op": "takeWhile", "whileAtMost": 2}]},
            "expected_output": "value 1\nvalue 2\nend\n"
        },
        {
            "input": {"source": {"type": "fromArray", "values": [1]}, "operators": [{"op": "takeWhile", "whileAtMost": 5}]},
            "expected_output": "value 1\nend\n"
        }
    ]
}
```

*4.4 Take until — values until a notifier fires*

The takeUntil operator forwards values until a separate notifier source emits its first value, then ends the stream immediately and ends the source. If the notifier never emits, all values pass through and the source's own completion is forwarded.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_take_until.json`

```json
{
    "description": "The takeUntil operator forwards values from its source until a separate notifier source emits its first value, at which point the stream ends immediately and the source is ended. If the notifier never emits, all values pass through and the source's own completion is forwarded. The first case uses a notifier that never emits (everything passes); the second uses a notifier that emits a value right away (the stream is cut before any source value passes).",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3]}, "operators": [{"op": "takeUntil", "notifier": {"type": "never"}}]},
            "expected_output": "value 1\nvalue 2\nvalue 3\nend\n"
        },
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3]}, "operators": [{"op": "takeUntil", "notifier": {"type": "fromValue", "value": 0}}]},
            "expected_output": "end\n"
        }
    ]
}
```

*4.5 Skip — discard the first [a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] values*

The skip operator discards a configured number of leading values, then forwards every subsequent value and completion.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_skip.json`

```json
{
    "description": "The skip operator discards a configured number of leading values and then forwards every subsequent value, along with the completion signal.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3, 4]}, "operators": [{"op": "skip", "n": 2}]},
            "expected_output": "value 3\nvalue 4\nend\n"
        }
    ]
}
```

*4.6 Skip while — discard until the predicate first fails*

The skipWhile operator discards leading values while a predicate holds, and once it first fails forwards that value and all subsequent values, plus completion. Here the predicate is true for values up to and including a configured bound (`whileAtMost`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_6_skip_while.json`

```json
{
    "description": "The skipWhile operator discards leading values for as long as a predicate holds, and once the predicate first fails it forwards that value and every value after it, along with the completion signal. Here the predicate is true for values up to and including a configured upper bound.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3, 4]}, "operators": [{"op": "skipWhile", "whileAtMost": 2}]},
            "expected_output": "value 3\nvalue 4\nend\n"
        }
    ]
}
```

*4.7 Skip until — discard until a notifier fires*

The skipUntil operator discards all values until a separate notifier source emits its first value, after which every subsequent value is forwarded plus completion. If the notifier never emits, all values are discarded and only the source's completion is forwarded.

**Test Cases:** `rcb_tests/public_test_cases/feature4_7_skip_until.json`

```json
{
    "description": "The skipUntil operator discards all values from its source until a separate notifier source emits its first value, after which every subsequent value is forwarded along with completion. If the notifier never emits, all values are discarded and only the source's completion is forwarded. The first case uses a notifier that never emits (everything is dropped); the second uses a notifier that emits right away (everything passes).",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3]}, "operators": [{"op": "skipUntil", "notifier": {"type": "never"}}]},
            "expected_output": "end\n"
        },
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3]}, "operators": [{"op": "skipUntil", "notifier": {"type": "fromValue", "value": 0}}]},
            "expected_output": "value 1\nvalue 2\nvalue 3\nend\n"
        }
    ]
}
```

---

### Feature 5: Higher-Order Switching

**As a developer**, I want to map each value to a brand-new inner stream and follow only the most recent one, so I can model "restart on every new input" flows.

**Expected Behavior / Usage:**

The switchMap operator maps each value from its source to a new inner source and emits the values of the most recent inner source, abandoning any previous inner source as soon as a new value arrives. The combined stream completes once the source and the final inner source have completed. Here each value is mapped to an inner source that emits a single derived value (the value squared).

**Test Cases:** `rcb_tests/public_test_cases/feature5_switch_map.json`

```json
{
    "description": "The switchMap operator maps each value from its source to a new inner source and emits the values of the most recent inner source, abandoning any previous inner source when a new value arrives. Here each value is mapped to an inner source that emits a single derived value (the value squared). The combined stream completes once the source and the final inner source have completed.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3]}, "operators": [{"op": "switchMap"}]},
            "expected_output": "value 1\nvalue 4\nvalue 9\nend\n"
        }
    ]
}
```

---

### Feature 6: Time-Shifted Delivery

**As a developer**, I want to delay every emission by a fixed duration, so I can defer a stream's output while preserving its shape.

**Expected Behavior / Usage:**

The delay operator shifts every emission (each value and the completion signal) later by a fixed duration. Because every emission is shifted by the same amount, the relative order of the values and the completion is preserved; the observable result is the same value sequence followed by completion.

**Test Cases:** `rcb_tests/public_test_cases/feature6_delay.json`

```json
{
    "description": "The delay operator shifts every emission (values and the completion signal) later by a fixed duration. Because every emission is shifted by the same amount, the relative order of the values and the completion is preserved, so the observable result is the same value sequence followed by completion.",
    "cases": [
        {
            "input": {"source": {"type": "fromArray", "values": [1, 2, 3]}, "operators": [{"op": "delay", "ms": 30}]},
            "expected_output": "value 1\nvalue 2\nvalue 3\nend\n"
        }
    ]
}
```

---

### Feature 7: Single-Value Promise Consumer

**As a developer**, I want to consume a stream as a promise that resolves with its final value, so I can bridge a stream into a one-shot asynchronous result.

**Expected Behavior / Usage:**

This consumer subscribes to a source and resolves with only the last value the source emits before completing; earlier values are discarded. The consumer renders the single resolved value.

**Test Cases:** `rcb_tests/public_test_cases/feature7_to_promise.json`

```json
{
    "description": "Converting a source to a single-value promise consumer subscribes to the source and resolves with only the last value the source emits before completing; earlier values are discarded. The consumer renders the single resolved value. The first case draws the last value from a multi-value source; the second from a single-value source.",
    "cases": [
        {
            "input": {"kind": "promise", "source": {"type": "fromArray", "values": [1, 2, 3]}},
            "expected_output": "resolved 3\n"
        },
        {
            "input": {"kind": "promise", "source": {"type": "fromValue", "value": 42}},
            "expected_output": "resolved 42\n"
        }
    ]
}
```

---

### Feature 8: Multicast Hub with Dynamic Subscribers

**As a developer**, I want a hub that is both a source and an imperative emitter, multicasting pushed values to every current subscriber, so I can fan a live feed out to many consumers that come and go independently.

**Expected Behavior / Usage:**

A subject is a multicast hub: callers push values into it and may complete it, and every currently-subscribed consumer receives those values live, in subscription order. A consumer may subscribe or unsubscribe at any time; after unsubscribing it receives nothing further (not even completion). Consumers still subscribed when the hub completes receive a completion signal. Values pushed while no consumer is subscribed are dropped. The input is a program of operations: subscribe a named consumer, push a value (`next`), unsubscribe a named consumer, or complete the hub. Each delivered signal is rendered in real-time delivery order, prefixed with the receiving consumer's id.

**Test Cases:** `rcb_tests/public_test_cases/feature8_subject.json`

```json
{
    "description": "A subject is a multicast hub that is both a source and an imperative emitter: callers push values into it and complete it, and every currently-subscribed consumer receives those values live, in subscription order. A consumer may subscribe or unsubscribe at any time; after unsubscribing it receives nothing more (not even completion). Consumers still subscribed when the hub completes receive a completion signal. Values pushed while no consumer is subscribed are dropped. The input is a program of operations (subscribe a named consumer, push a value, unsubscribe a named consumer, complete). Each delivered signal is rendered in real-time delivery order, prefixed with the receiving consumer's id. The cases cover a single consumer through completion, two consumers where one unsubscribes early, and consumers that join and leave at different times around interleaved pushes.",
    "cases": [
        {
            "input": {"kind": "subject", "program": [{"op": "subscribe", "id": "A"}, {"op": "next", "value": 10}, {"op": "next", "value": 20}, {"op": "next", "value": 30}, {"op": "next", "value": 40}, {"op": "complete"}]},
            "expected_output": "A value 10\nA value 20\nA value 30\nA value 40\nA end\n"
        },
        {
            "input": {"kind": "subject", "program": [{"op": "subscribe", "id": "A"}, {"op": "subscribe", "id": "B"}, {"op": "next", "value": 10}, {"op": "next", "value": 20}, {"op": "next", "value": 30}, {"op": "unsubscribe", "id": "A"}, {"op": "next", "value": 40}, {"op": "next", "value": 50}, {"op": "complete"}]},
            "expected_output": "A value 10\nB value 10\nA value 20\nB value 20\nA value 30\nB value 30\nB value 40\nB value 50\nB end\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the stream abstraction, the source factories, the operator family, and the consumer types described above. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core logic must be decoupled from standard I/O and JSO[a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] parsing. Operators must be composable (a source plus a sequence of operators yields a new source) and must correctly propagate completion and early termination.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSO[a specific integer [a specific threshold N to compare against] — verify with the PRD diagram] request from input and renders the observed stream signals to output, matching the shared Output Contract and the per-feature contracts above. The request shape selects behavior: the default pipeline shape carries a `source` spec and an optional ordered `operators` list (each operator is an object whose `op` field names the operator plus its parameters); the `kind` field selects the `combine`, `promise`, or `subject` scenarios. Source specs (`fromArray`, `fromValue`, `empty`, `never`, `merge`, `concat`, `flatten`) and operator specs are translated into idiomatic calls to the core, and the resulting emissions are rendered to the line contract.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- maintain last seen values using the notebook pattern
- emit modeled results following the schema registry convention
