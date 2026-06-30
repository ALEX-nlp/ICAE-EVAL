## Product Requirement Document

# Stream Pipeline Engine - Lazy, Composable Stream Combinators With Ordered Output

## Project Goal

Build a small engine that lets developers describe a computation over a finite sequence of fallible values as a pipeline of composable stages and terminal collectors, so they can transform, filter, combine, and aggregate sequences declaratively without hand-writing iteration, buffering, or error-propagation logic each time.

---

## Background & Problem

A producer yields a finite sequence of outcomes; each outcome is either a successful value (here, an integer item) or an error carrying an integer code. Consumers usually need to reshape such a sequence: map values, drop or limit elements, recover from or rewrite errors, merge two sequences, regroup into batches, or fold everything into a single result.

Without a shared engine, every consumer re-implements the same imperative loops, the same "stop on first error" bookkeeping, the same off-by-one limiting logic, and the same buffering for batching — each subtly different and easy to get wrong. This engine provides one well-defined contract: a source sequence, an ordered list of transformation stages, and a terminal collector, with precisely specified ordering and error-propagation semantics.

A request is a single JSON object. The common shape is a `source` (an array whose elements are integers for successful items, or `{"err": n}` for an error outcome with code `n`), an optional `pipeline` (an ordered array of stage objects), and a `sink` (the terminal collector). Two-input operations instead supply a `combine` selector with `left` and `right` sides, and the flatten operation supplies a `concat` array of groups. Output is a line-oriented, language-neutral contract: successful items are reported as `item=<value>` lines, an aggregate scalar as `value=<value>`, a paired result as `pair=<a>,<b>` lines, a batch as `chunk=<v1>,<v2>,...` lines, an error outcome as an `error=<code>` line, and a normal end-of-sequence as a final `end` line.

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


### Feature 1: Transform Each Element

**As a developer**, I want to apply a value-to-value function to every successful item of a sequence, so I can reshape the data without writing an explicit loop.

**Expected Behavior / Usage:**

The request carries a `source` sequence, a `pipeline` with a single stage `{"stage":"map","add":N}`, and the collecting sink `{"kind":"collect"}`. Each successful item is replaced by itself plus the constant `N`, preserving order; error outcomes (if any) would pass through unchanged. The collector emits one `item=<value>` line per produced item, in order, then a final `end` line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_map.json`

```json
{
    "description": "A finite source stream of integer items is transformed element by element by a function that adds a fixed constant to each item; the resulting items are gathered in arrival order. Each surviving item is emitted on its own line followed by a terminator line.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "map",
                        "add": 1
                    }
                ]
            },
            "expected_output": "item=2[use standard Unix line termination]item=3[use standard Unix line termination]item=4[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

---

### Feature 2: Select And Limit Elements

**As a developer**, I want to keep only the elements I care about and bound how many flow through, so I can narrow a sequence down to a relevant prefix or subset.

**Expected Behavior / Usage:**

*2.1 Keep Elements Matching A Predicate — drop items that fail a condition*

The stage `{"stage":"filter","keep":"even"}` forwards only the items for which the predicate holds (here, even values) and discards the rest, preserving order. The collector emits the surviving items as `item=<value>` lines followed by an `end` line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_filter.json`

```json
{
    "description": "Elements of an integer source stream are passed through a predicate; only items satisfying the predicate (here, even values) are kept, in order. Kept items are emitted one per line followed by a terminator line.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "filter",
                        "keep": "even"
                    }
                ]
            },
            "expected_output": "item=2[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

*2.2 Filter And Transform In One Step — drop non-matching items and rewrite matching ones*

The stage `{"stage":"filter_map","when":"even","add":N}` inspects each item: items failing the condition (here, odd values) are dropped, and items passing it (even values) are replaced by the item plus `N`. Surviving transformed items are emitted as `item=<value>` lines followed by `end`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_filter_map.json`

```json
{
    "description": "Each element of an integer source stream is passed to a function that may both drop it and transform it: items not matching the condition (here, odd values) are discarded, while matching items (even values) are replaced by the item plus a fixed constant. Surviving transformed items are emitted in order.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "filter_map",
                        "when": "even",
                        "add": 10
                    }
                ]
            },
            "expected_output": "item=12[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

*2.3 Take A Leading Run Of Items — forward at most N successful items*

The stage `{"stage":"take","n":N}` forwards items until `N` SUCCESSFUL items have been emitted, then ends the sequence. Error outcomes encountered before the limit is reached are forwarded but do NOT count toward `N`; once the N-th successful item passes, the sequence terminates. With the draining sink `{"kind":"drain"}`, errors are reported as `error=<code>` lines interleaved in order with `item=<value>` lines, and the sequence ends with `end`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_take.json`

```json
{
    "description": "A prefix limiter forwards at most a fixed number of SUCCESSFUL items from the source and then ends the stream. Error outcomes encountered before the limit is reached are forwarded but do not count toward the limit; reaching the count of successful items terminates the stream.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "take",
                        "n": 2
                    }
                ]
            },
            "expected_output": "item=1[use standard Unix line termination]item=2[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

*2.4 Skip A Leading Run Of Items — discard the first N successful items*

The stage `{"stage":"skip","n":N}` discards items until `N` SUCCESSFUL items have been dropped, then forwards the remainder unchanged. Error outcomes are forwarded as they occur and are NOT counted against `N`. With the collecting sink the remaining items appear as `item=<value>` lines then `end`; with the draining sink any forwarded errors appear as `error=<code>` lines in order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_skip.json`

```json
{
    "description": "A prefix dropper discards a fixed number of leading SUCCESSFUL items and then forwards the remainder of the stream. Error outcomes are forwarded unchanged and are not counted against the number of items to skip.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "skip",
                        "n": 2
                    }
                ]
            },
            "expected_output": "item=3[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

*2.5 Take While A Condition Holds — stop at the first item that fails*

The stage `{"stage":"take_while","lt":N}` forwards items from the start as long as the predicate holds (here, the item is strictly below `N`). The first item that fails the predicate ends the sequence and is itself not emitted. Emitted items are `item=<value>` lines followed by `end`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_take_while.json`

```json
{
    "description": "Elements are forwarded from the start of the stream as long as a predicate holds (here, while the item is below a threshold); the first item that fails the predicate ends the stream and is not emitted.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "take_while",
                        "lt": 3
                    }
                ]
            },
            "expected_output": "item=1[use standard Unix line termination]item=2[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

*2.6 Skip While A Condition Holds — drop a leading run, then forward the rest*

The stage `{"stage":"skip_while","while":"odd"}` discards leading items as long as the predicate holds (here, the item is odd). As soon as the predicate first fails, that item and every later item are forwarded unchanged. Forwarded items are `item=<value>` lines followed by `end`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_skip_while.json`

```json
{
    "description": "Leading elements are discarded as long as a predicate holds (here, while the item is odd); once the predicate first fails, that element and all subsequent elements are forwarded unchanged.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "skip_while",
                        "while": "odd"
                    }
                ]
            },
            "expected_output": "item=2[use standard Unix line termination]item=3[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

---

### Feature 3: Aggregate A Sequence

**As a developer**, I want to reduce a whole sequence into a single result, so I can compute summaries or splice nested sequences together.

**Expected Behavior / Usage:**

*3.1 Fold Into A Single Accumulator — combine all items left to right*

The sink `{"kind":"fold_sum","init":N}` starts an accumulator at `N` and combines every successful item into it left to right using addition, emitting the final accumulator as a single `value=<result>` line. If an error outcome occurs before the sequence completes, aggregation stops and the result is the `error=<code>` line instead.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_fold.json`

```json
{
    "description": "All successful items of the stream are combined left to right into a single accumulator using addition, starting from a supplied initial value; the final accumulated value is emitted. If the stream yields an error outcome before completing, the aggregation stops and that error is reported instead.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "pipeline": [],
                "sink": {
                    "kind": "fold_sum",
                    "init": 0
                }
            },
            "expected_output": "value=6[use standard Unix line termination]"
        }
    ]
}
```

*3.2 Flatten A Sequence Of Lists — concatenate groups end to end*

The request supplies `{"concat":[ ... ]}` whose elements are groups: an array of integers is a successful group, and `{"err":n}` is an error outcome. The groups are appended end to end into one flat sequence, emitted as `item=<value>` lines followed by `end`. An empty input yields just `end`. If any element is an error outcome, flattening stops and an `error=<code>` line is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_concat.json`

```json
{
    "description": "A stream whose elements are themselves lists is flattened by appending every list end to end into one sequence, which is then emitted item by item. An empty stream yields an empty sequence. If any element is an error outcome, flattening stops and that error is reported.",
    "cases": [
        {
            "input": {
                "concat": [
                    [
                        1,
                        2,
                        3
                    ],
                    [
                        4,
                        5,
                        6
                    ],
                    [
                        7,
                        8,
                        9
                    ]
                ]
            },
            "expected_output": "item=1[use standard Unix line termination]item=2[use standard Unix line termination]item=3[use standard Unix line termination]item=4[use standard Unix line termination]item=5[use standard Unix line termination]item=6[use standard Unix line termination]item=7[use standard Unix line termination]item=8[use standard Unix line termination]item=9[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

---

### Feature 4: Fallible Transforms And Error Recovery

**As a developer**, I want per-element transforms that may themselves fail, and the ability to rewrite or recover from errors, so I can model real computations that are not guaranteed to succeed.

**Expected Behavior / Usage:**

*4.1 Rewrite Error Codes — map only the error channel*

The stage `{"stage":"map_err","add":N}` leaves successful items untouched but rewrites each error code by adding `N`. When the collected sequence reaches an error, the rewritten code is reported as `error=<code>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_map_err.json`

```json
{
    "description": "A transform applied only to error outcomes rewrites each error code by adding a fixed constant, while successful items pass through unchanged. When the gathered stream reaches an error, the rewritten error code is reported.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    {
                        "err": 3
                    }
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "map_err",
                        "add": 1
                    }
                ]
            },
            "expected_output": "error=4[use standard Unix line termination]"
        }
    ]
}
```

*4.2 Chain A Fallible Transform On Success — replace each item with a new outcome*

The stage `{"stage":"and_then","add":N}` passes each successful item through a transform that adds `N` and succeeds, yielding a new item. The variant `{"stage":"and_then","fail":true}` instead converts each item into an error outcome carrying that item's value; under the collecting sink this surfaces as the first such `error=<code>` line. Successful results are emitted as `item=<value>` lines followed by `end`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_and_then.json`

```json
{
    "description": "Each successful item is passed to a fallible transform whose own outcome replaces the item. In the succeeding form the transform adds a constant and yields a new item; in the failing form the transform converts the item into an error outcome carrying that item's value, which stops the gathered stream.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "and_then",
                        "add": 1
                    }
                ]
            },
            "expected_output": "item=2[use standard Unix line termination]item=3[use standard Unix line termination]item=4[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

*4.3 Chain On Every Outcome — handle both success and error uniformly*

The stage `{"stage":"then","add":N}` passes every outcome (success or error) through a function that produces the next outcome; here it maps successful items by adding `N`. Produced items are emitted as `item=<value>` lines followed by `end`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_then.json`

```json
{
    "description": "Every outcome of the stream, whether a successful item or an error, is passed to a function that produces the next outcome. Here the function maps successful items by adding a constant; the resulting items are gathered in order.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "then",
                        "add": 1
                    }
                ]
            },
            "expected_output": "item=2[use standard Unix line termination]item=3[use standard Unix line termination]item=4[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

*4.4 Recover From Errors — turn an error into a successful item*

The stage `{"stage":"or_else"}` leaves successful items unchanged but converts each error outcome into a successful item carrying the former error's code. The recovered sequence therefore completes with `item=<value>` lines followed by `end`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_or_else.json`

```json
{
    "description": "A recovery transform applied only to error outcomes turns each error into a successful item carrying the error's code, while existing successful items pass through unchanged. The gathered stream therefore completes with items in place of the former errors.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    {
                        "err": 3
                    }
                ],
                "sink": {
                    "kind": "collect"
                },
                "pipeline": [
                    {
                        "stage": "or_else"
                    }
                ]
            },
            "expected_output": "item=1[use standard Unix line termination]item=2[use standard Unix line termination]item=3[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

---

### Feature 5: Combine Two Sequences

**As a developer**, I want to merge two sequences into one, so I can correlate or interleave independent producers.

**Expected Behavior / Usage:**

*5.1 Pair Up In Lockstep — zip two sequences element by element*

The request supplies `{"combine":"zip","left":{...},"right":{...}}`, where each side is itself a `source` with an optional `pipeline`. The two sequences advance together, pairing first-with-first, second-with-second, and so on. Pairing stops as soon as either side ends, so the number of pairs equals the length of the shorter side. Each pair is emitted as a `pair=<a>,<b>` line followed by `end`. If either side yields an error outcome, an `error=<code>` line is emitted instead.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_zip.json`

```json
{
    "description": "Two source streams are advanced in lockstep, pairing the first item of one with the first of the other, the second with the second, and so on. Pairing stops as soon as either stream ends, so the result length matches the shorter stream. If either stream yields an error outcome, that error is reported instead.",
    "cases": [
        {
            "input": {
                "combine": "zip",
                "left": {
                    "source": [
                        1,
                        2,
                        3
                    ]
                },
                "right": {
                    "source": [
                        1,
                        2,
                        3
                    ]
                }
            },
            "expected_output": "pair=1,1[use standard Unix line termination]pair=2,2[use standard Unix line termination]pair=3,3[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

*5.2 Interleave Alternately — select between two sequences*

The request supplies `{"combine":"select","left":{...},"right":{...}}`. The result alternates between the two sides — one item from the first, then one from the second, repeating — and once one side is exhausted the remaining items of the other are emitted in order. All produced items appear as `item=<value>` lines followed by `end`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_select.json`

```json
{
    "description": "Two source streams are interleaved by alternating between them: take one item from the first, then one from the second, and continue alternating. When one stream is exhausted, the remaining items of the other are emitted in order until it too is exhausted.",
    "cases": [
        {
            "input": {
                "combine": "select",
                "left": {
                    "source": [
                        1,
                        2,
                        3
                    ]
                },
                "right": {
                    "source": [
                        4,
                        5,
                        6
                    ]
                }
            },
            "expected_output": "item=1[use standard Unix line termination]item=4[use standard Unix line termination]item=2[use standard Unix line termination]item=5[use standard Unix line termination]item=3[use standard Unix line termination]item=6[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

---

### Feature 6: Batch Into Fixed-Size Groups

**As a developer**, I want to gather consecutive items into fixed-size batches, so I can process a sequence in chunks rather than one element at a time.

**Expected Behavior / Usage:**

The sink `{"kind":"chunks","size":N}` accumulates successful items into groups of `N`; each group is emitted as soon as it fills, and any trailing partial group is emitted when the sequence ends. Each group is rendered as a single `chunk=<v1>,<v2>,...` line listing its items in order, and the sequence ends with `end`. If an error outcome occurs, any already-buffered partial group is emitted first as a `chunk=...` line and then the error is reported as `error=<code>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_chunks.json`

```json
{
    "description": "Successive successful items are batched into fixed-size groups; each full group is emitted as soon as it fills, and any trailing partial group is emitted when the stream ends. Each emitted group lists its items in order. If the stream yields an error outcome, any already-buffered partial group is emitted first and then the error is reported.",
    "cases": [
        {
            "input": {
                "source": [
                    1,
                    2,
                    3
                ],
                "pipeline": [],
                "sink": {
                    "kind": "chunks",
                    "size": 3
                }
            },
            "expected_output": "chunk=1,2,3[use standard Unix line termination]end[use standard Unix line termination]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the stream-pipeline engine described above — sources, composable stages, two-input combiners, and terminal collectors — with precisely the ordering and error-propagation semantics specified per feature. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core engine. It reads a single JSON request from stdin, builds the described pipeline (or combiner / flatten), drives it to completion, and prints the resulting line contract to stdout, matching the per-leaf-feature contracts above. A request is dispatched by its shape: a `source` + optional `pipeline` + `sink` runs a one-input pipeline; a `combine` selector with `left`/`right` runs a two-input operation; a `concat` array runs the flatten operation. Output lines use `item=<value>`, `value=<value>`, `pair=<a>,<b>`, `chunk=<v1>,<v2>,...`, `error=<code>`, and a terminal `end`, exactly as specified.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- reference the dtype handling logic in the utility types module
- follow the buffering strategy of the result collector
