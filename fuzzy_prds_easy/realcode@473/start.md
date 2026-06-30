## Product Requirement Document

# Foundational Data-Structure & Utility Toolkit - Input/Output Specification

## Project Goal

Build a small, dependency-free toolkit of foundational data structures and utility primitives that allows developers to compose higher-level concurrent and messaging systems without re-implementing low-level building blocks (sub-sequence selection, circular/forward iteration, a key-to-set multimap, a stable priority queue, an atomic on/off latch, a token-bucket rate limiter, an immutable byte-sequence type, and quote-aware path parsing). Each primitive has a precise, deterministic, implementation-independent input/output contract.

---

## Background & Problem

Developers building messaging frameworks, schedulers, and I/O pipelines repeatedly need the same low-level pieces: a way to take a slice of a sequence, iterate a collection in a loop, group many values under one key, drain messages in a stable priority order, gate a one-time transition with a latch, throttle a stream to a fixed rate, manipulate raw byte buffers without copying, and parse dotted configuration paths that may contain quoted literals. Without a shared toolkit, every team rewrites these from scratch, each with subtly different edge-case behavior (what happens past the end of a slice? does the priority queue keep arrival order? does the rate limiter drift over time?), which leads to duplicated, error-prone, and in[a boolean value indicating output consistency] code.

With this toolkit, each primitive is specified once with an exact behavioral contract — including its boundary and error conditions — so it can be reused confidently and re-implemented in any language while preserving identical observable behavior.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This domain spans several independent primitives (sequence utilities, iterators, a multimap, a priority queue, a latch, a rate limiter, a byte-sequence type, and path parsing). It MUST NOT be delivered as a single "god file". Provide a clear multi-unit structure (one cohesive module per primitive, plus a separate execution adapter), reflecting a production-grade repository. Do not over-engineer the trivial helpers, but keep each primitive logically isolated.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model. The core primitives must be ordinary, idiomatic library types with no knowledge of stdin/stdout or JSON. A thin execution adapter is solely responsible for parsing a JSON command, invoking the appropriate primitive, and rendering the result lines.

3. **Adherence to SOLID Design Principles:** Separate parsing, command routing, core execution, and output formatting into distinct units. Each primitive is open for extension but closed for modification; substitutable abstractions (e.g. a pluggable time source for the rate limiter) must be honored; interfaces stay small and cohesive; the adapter depends on the primitives' public abstractions, not the reverse.

4. **Robustness & Interface Design:** Public interfaces must be elegant and idiomatic to the target language. Edge cases (empty inputs, out-of-range offsets, wrap-around clocks, invalid construction arguments) must be handled gracefully. Invalid arguments must be modeled as proper error signals rather than silent corruption; the adapter normalizes these into the language-neutral error lines defined below.

**Execution-adapter I/O contract (applies to every feature):** The adapter reads exactly one JSON object from stdin. The object always carries an `"op"` field selecting the primitive, plus operation-specific fields. The adapter prints newline-terminated `key=value` (or `key -> value`) lines to stdout, exactly as specified per feature. List values are rendered comma-separated with no surrounding spaces; an empty list renders as the empty string after the `=`. Booleans render as `true`/`false`. Errors are rendered as normalized category lines of the form `error=<category>` optionally followed by `param=<neutral-name>`, never exposing host-language type names or runtime message text.

---

## Core Features

### Feature 1: Sub-sequence selection

**As a developer**, I want to extract contiguous and value-anchored portions of a sequence, so I can navigate ordered collections without manual index arithmetic.

**Expected Behavior / Usage:**

*1.1 Offset/count slice — take a fixed-size window from a sequence*

Given a sequence (`items`), a zero-based `start` offset, and a `count`, return the run of up to `count` elements beginning at `start`. If `start` is at or beyond the end, the result is empty; if fewer than `count` elements remain, only those remaining are returned (no error, no padding). Output is two lines: `length=<n>` then `items=<comma-separated elements>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_slice.json`

```json
{
    "description": "Return a contiguous run of elements starting at a zero-based offset and taking a fixed number of elements; offsets and counts that run past the end simply yield whatever remains.",
    "cases": [
        {"input": {"op": "slice", "items": [1,2,3,4,5,6], "start": 2, "count": 4}, "expected_output": "length=4\nitems=3,4,5,6\n"},
        {"input": {"op": "slice", "items": ["a","b","c","d","e"], "start": 1, "count": 2}, "expected_output": "length=2\nitems=b,c\n"}
    ]
}
```

*1.2 From — tail starting at the first matching element (inclusive)*

Given a sequence (`items`) and a target `value`, return the suffix beginning at the first element equal to `value`, including that element. If `value` is the first element, the entire sequence is returned. If `value` does not occur, the result is empty. Output is `length=<n>` then `items=<...>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_from.json`

```json
{
    "description": "Return the tail of a sequence beginning at the first element equal to a target value (inclusive). If the target is absent the result is empty; if it is the first element the whole sequence is returned.",
    "cases": [
        {"input": {"op": "from", "items": ["meat","cheese","beer","bread"], "value": "beer"}, "expected_output": "length=2\nitems=beer,bread\n"},
        {"input": {"op": "from", "items": ["meat","cheese","beer","bread"], "value": "meat"}, "expected_output": "length=4\nitems=meat,cheese,beer,bread\n"},
        {"input": {"op": "from", "items": [1,2,3,4,5,6], "value": 7}, "expected_output": "length=0\nitems=\n"}
    ]
}
```

*1.3 Until — head up to (but excluding) the first matching element*

Given a sequence (`items`) and a target `value`, return the prefix preceding the first element equal to `value`, excluding that element. If `value` is the first element, the result is empty. If `value` does not occur, the entire sequence is returned. Output is `length=<n>` then `items=<...>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_until.json`

```json
{
    "description": "Return the head of a sequence up to (but excluding) the first element equal to a target value. If the target is the first element the result is empty; if it is absent the entire sequence is returned.",
    "cases": [
        {"input": {"op": "until", "items": ["meat","cheese","beer","bread"], "value": "bread"}, "expected_output": "length=3\nitems=meat,cheese,beer\n"},
        {"input": {"op": "until", "items": ["meat","cheese","beer","bread"], "value": "meat"}, "expected_output": "length=0\nitems=\n"},
        {"input": {"op": "until", "items": ["meat","cheese","beer","bread"], "value": "wine"}, "expected_output": "length=4\nitems=meat,cheese,beer,bread\n"}
    ]
}
```

---

### Feature 2: Circular enumerator

**As a developer**, I want to iterate a collection endlessly with automatic wrap-around, so I can implement round-robin selection without tracking indices myself.

**Expected Behavior / Usage:**

Given a collection (`items`) and a number of `steps`, advance the cursor `steps` times, wrapping back to the first element after the last. Return `count=<emitted>` then `values=<comma-separated emitted values>`. An empty collection yields nothing — `count=0` and an empty `values` list — regardless of how many steps are requested.

**Test Cases:** `rcb_tests/public_test_cases/feature2_circular_enumerator.json`

```json
{
    "description": "Iterate a collection in an endless loop: after the last element it wraps back to the first. An empty collection yields nothing even when more steps are requested.",
    "cases": [
        {"input": {"op": "circular", "items": [0,1,2,3,4,5,6,7,8,9], "steps": 12}, "expected_output": "count=12\nvalues=0,1,2,3,4,5,6,7,8,9,0,1\n"},
        {"input": {"op": "circular", "items": ["x","y","z"], "steps": 7}, "expected_output": "count=7\nvalues=x,y,z,x,y,z,x\n"},
        {"input": {"op": "circular", "items": [], "steps": 3}, "expected_output": "count=0\nvalues=\n"}
    ]
}
```

---

### Feature 3: Forward iterator over a snapshot

**As a developer**, I want a one-way cursor over a captured snapshot of a sequence, so I can consume elements while still being able to ask whether any remain and collect the rest.

**Expected Behavior / Usage:**

Given a sequence (`items`) and an `advance` count, take a snapshot, then pull `advance` elements off the front. Output three lines: `consumed=<the pulled elements>`, `empty=<true|false>` (whether the cursor has reached the end), and `remaining=<the not-yet-consumed tail>`. When the cursor is exhausted, `empty` is `true` and `remaining` is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature3_forward_iterator.json`

```json
{
    "description": "A one-way cursor over a snapshot of a sequence: advancing returns successive elements, an emptiness check reports whether the cursor reached the end, and the remaining tail can be collected.",
    "cases": [
        {"input": {"op": "iterator", "items": [8,2,5], "advance": 3}, "expected_output": "consumed=8,2,5\nempty=true\nremaining=\n"},
        {"input": {"op": "iterator", "items": [8,2], "advance": 2}, "expected_output": "consumed=8,2\nempty=true\nremaining=\n"},
        {"input": {"op": "iterator", "items": [8,2,8,5,23], "advance": 2}, "expected_output": "consumed=8,2\nempty=false\nremaining=8,5,23\n"}
    ]
}
```

---

### Feature 4: Key-to-set multimap

**As a developer**, I want a map from keys to sets of values with idempotent inserts and cascading cleanup, so I can index many values under one key without managing the inner sets myself.

**Expected Behavior / Usage:**

The structure processes an ordered list of `commands` against an initially empty multimap and prints one output line per command. Supported actions:
- `put` (`key`,`value`): adds the value to the key's set; prints `put <key> <value> -> <true|false>` where `true` means the value was new for that key and `false` means it was already present.
- `get` (`key`): prints `get <key> -> <values>` with the key's current values in ascending order (empty if the key has none).
- `remove` (`key`,`value`): removes one value; prints `remove <key> <value> -> <true|false>` (`true` if it was present). When a key's set becomes empty it is dropped.
- `remove_key` (`key`): removes the whole key; prints `remove_key <key> -> <values>` listing the removed values (ascending), or empty if the key was absent.
- `remove_value` (`value`): removes that value from every key; prints `remove_value <value>`.
- `values`: prints `values -> <all distinct values across all keys, ascending>`.
- `is_empty`: prints `is_empty -> <true|false>`.
- `clear`: empties the whole structure; prints `clear`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_multimap_index.json`

```json
{
    "description": "A key-to-set multimap. Adding a value reports whether it was new for that key; reading a key returns its set; removing a value reports whether it was present and drops the key when its set empties; a value can be purged across all keys; the union of all values and an emptiness flag are available; and the whole structure can be cleared.",
    "cases": [
        {"input": {"op": "index", "commands": [{"action": "put", "key": "s1", "value": 1}, {"action": "put", "key": "s1", "value": 1}, {"action": "put", "key": "s1", "value": 2}, {"action": "put", "key": "s1", "value": 3}, {"action": "put", "key": "s2", "value": 4}, {"action": "get", "key": "s1"}, {"action": "get", "key": "s2"}]}, "expected_output": "put s1 1 -> true\nput s1 1 -> false\nput s1 2 -> true\nput s1 3 -> true\nput s2 4 -> true\nget s1 -> 1,2,3\nget s2 -> 4\n"},
        {"input": {"op": "index", "commands": [{"action": "put", "key": "s1", "value": 1}, {"action": "put", "key": "s1", "value": 2}, {"action": "put", "key": "s2", "value": 1}, {"action": "put", "key": "s2", "value": 2}, {"action": "remove", "key": "s1", "value": 1}, {"action": "remove", "key": "s1", "value": 1}, {"action": "get", "key": "s1"}, {"action": "remove_key", "key": "s2"}, {"action": "remove_key", "key": "s2"}, {"action": "get", "key": "s2"}]}, "expected_output": "put s1 1 -> true\nput s1 2 -> true\nput s2 1 -> true\nput s2 2 -> true\nremove s1 1 -> true\nremove s1 1 -> false\nget s1 -> 2\nremove_key s2 -> 1,2\nremove_key s2 -> \nget s2 -> \n"},
        {"input": {"op": "index", "commands": [{"action": "put", "key": "s1", "value": 1}, {"action": "put", "key": "s1", "value": 2}, {"action": "put", "key": "s1", "value": 3}, {"action": "put", "key": "s2", "value": 1}, {"action": "put", "key": "s2", "value": 2}, {"action": "put", "key": "s3", "value": 2}, {"action": "remove_value", "value": 1}, {"action": "get", "key": "s1"}, {"action": "get", "key": "s2"}, {"action": "get", "key": "s3"}, {"action": "values"}]}, "expected_output": "put s1 1 -> true\nput s1 2 -> true\nput s1 3 -> true\nput s2 1 -> true\nput s2 2 -> true\nput s3 2 -> true\nremove_value 1\nget s1 -> 2,3\nget s2 -> 2\nget s3 -> 2\nvalues -> 2,3\n"}
    ]
}
```

---

### Feature 5: Stable priority queue

**As a developer**, I want a priority queue that breaks ties by arrival order, so equal-priority items are drained in the order they were enqueued (FIFO within a priority band).

**Expected Behavior / Usage:**

Enqueue each string in `items` in order. Priority is the string's length, where **shorter strings have higher priority** (dequeue first). Among strings of equal length, the one enqueued earlier dequeues first (stability). The queue is then fully drained. Output: `dequeued=<comma-separated strings in dequeue order>` then `[a boolean value indicating output consistency]=<true|false>`, where `[a boolean value indicating output consistency]` reports that the queue's internal ordering invariant held throughout.

**Test Cases:** `rcb_tests/public_test_cases/feature5_stable_priority_queue.json`

```json
{
    "description": "A priority queue keyed on string length (shorter strings dequeue first) that preserves insertion order among equal-length strings (stability). Dequeuing drains the whole queue in priority-then-arrival order; a consistency flag confirms the internal heap invariant holds.",
    "cases": [
        {"input": {"op": "priority_queue", "items": ["ccc","a","dd","b","eee","cc"]}, "expected_output": "dequeued=a,b,dd,cc,ccc,eee\n[a boolean value indicating output consistency]=true\n"},
        {"input": {"op": "priority_queue", "items": ["bb","aa","c","dddd","e"]}, "expected_output": "dequeued=c,e,bb,aa,dddd\n[a boolean value indicating output consistency]=true\n"}
    ]
}
```

---

### Feature 6: Atomic on/off latch

**As a developer**, I want a two-state latch whose transitions report whether they actually changed state and that reverts cleanly if a guarded action fails, so I can coordinate one-time switch-overs safely.

**Expected Behavior / Usage:**

A latch starts in the state given by `start` (`true`=on, `false`=off) and processes an ordered list of `commands`, printing one line each:
- `switch_on` / `switch_off`: attempts the transition; prints `<cmd> -> <true|false>` where `true` means the state actually changed and `false` means it was already in that state.
- `is_on` / `is_off`: prints `<cmd> -> <true|false>` for the current state.
- `if_on` / `if_off` / `while_on` / `while_off`: runs a (no-op) guarded action only when the latch is in the matching state; prints `<cmd> -> <true|false>` indicating whether the action ran.
- `switch_on_throw` / `switch_off_throw`: attempts a transition whose guarded action throws; the latch must revert to its prior state and the failure is surfaced as a normalized error. Prints `<cmd> -> error=action_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_atomic_switch.json`

```json
{
    "description": "A two-state (on/off) latch. Transition operations return true only when they actually changed the state and false when it was already in the target state. State queries report the current position. Conditional runners execute an action only in the matching state, returning whether they ran. If an action throws during a transition, the latch reverts to its prior state and surfaces the failure.",
    "cases": [
        {"input": {"op": "switch", "start": false, "commands": ["is_off","is_on","switch_on","is_on","switch_on","switch_off","is_off","switch_off"]}, "expected_output": "is_off -> true\nis_on -> false\nswitch_on -> true\nis_on -> true\nswitch_on -> false\nswitch_off -> true\nis_off -> true\nswitch_off -> false\n"},
        {"input": {"op": "switch", "start": true, "commands": ["is_on","is_off"]}, "expected_output": "is_on -> true\nis_off -> false\n"},
        {"input": {"op": "switch", "start": false, "commands": ["switch_on_throw","is_off","is_on"]}, "expected_output": "switch_on_throw -> error=action_failed\nis_off -> true\nis_on -> false\n"},
        {"input": {"op": "switch", "start": true, "commands": ["switch_off_throw","is_on","is_off"]}, "expected_output": "switch_off_throw -> error=action_failed\nis_on -> true\nis_off -> false\n"}
    ]
}
```

---

### Feature 7: Token-bucket rate limiter

**As a developer**, I want a deterministic token-bucket throttle driven by an explicit clock, so I can compute exactly how long a caller must wait before paying a cost, with no drift over time.

**Expected Behavior / Usage:**

A bucket is constructed with a `capacity` (maximum tokens) and a `rate` (ticks between successive single-token refills) and starts **full**. An optional `init_time` sets the clock before the bucket is initialized; otherwise the clock starts at 0. Each step may set the clock (`set_time`) and/or `offer` a cost. `offer(cost)` returns the number of ticks the caller must wait before that cost can be paid: `0` if it can be paid immediately, otherwise the positive delay. Tokens accrue only at exact multiples of `rate` (so repeated offers do not drift the refill schedule), the bucket never exceeds `capacity`, costs larger than capacity are allowed, a cost of `0` is always free, `capacity` of `0` is allowed, and the clock may start negative or advance in very large steps. Each offer prints `offer cost=<cost> delay=<delay>`.

Construction and offer validation are normalized to language-neutral error lines: a negative `capacity` → `error=negative_capacity` / `param=capacity`; a `rate` of zero or less → `error=nonpositive_rate` / `param=rate`; a negative `cost` → `error=negative_cost` / `param=cost`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_token_bucket.json`

```json
{
    "description": "A rate limiter. The bucket holds up to capacity tokens and gains one token every rate ticks of a caller-supplied clock. Each offer of a cost returns how many ticks the caller must wait before that cost can be paid (0 if payable immediately). The bucket starts full, caps at capacity, supports costs larger than capacity, a cost of zero, zero capacity, and clocks that start negative or run very slowly. Invalid construction (negative capacity, non-positive rate) and a negative cost are rejected as normalized errors.",
    "cases": [
        {"input": {"op": "token_bucket", "capacity": 10, "rate": 1, "steps": [{"offer": 1}, {"offer": 1}, {"offer": 1}, {"offer": 7}, {"offer": 3}]}, "expected_output": "offer cost=1 delay=0\noffer cost=1 delay=0\noffer cost=1 delay=0\noffer cost=7 delay=0\noffer cost=3 delay=3\n"},
        {"input": {"op": "token_bucket", "capacity": 10, "rate": 2, "steps": [{"offer": 5}, {"offer": 20}, {"set_time": 30, "offer": 1}, {"set_time": 34, "offer": 1}, {"offer": 1}]}, "expected_output": "offer cost=5 delay=0\noffer cost=20 delay=30\noffer cost=1 delay=2\noffer cost=1 delay=0\noffer cost=1 delay=2\n"},
        {"input": {"op": "token_bucket", "capacity": 0, "rate": 2, "steps": [{"offer": 10}, {"set_time": 40, "offer": 10}]}, "expected_output": "offer cost=10 delay=20\noffer cost=10 delay=20\n"},
        {"input": {"op": "token_bucket", "capacity": 10, "rate": 1, "steps": [{"offer": 10}, {"set_time": 100000, "offer": 20}]}, "expected_output": "offer cost=10 delay=0\noffer cost=20 delay=10\n"},
        {"input": {"op": "token_bucket", "capacity": -1, "rate": 1, "steps": []}, "expected_output": "error=negative_capacity\nparam=capacity\n"},
        {"input": {"op": "token_bucket", "capacity": 10, "rate": 0, "steps": []}, "expected_output": "error=nonpositive_rate\nparam=rate\n"},
        {"input": {"op": "token_bucket", "capacity": 10, "rate": 1, "steps": [{"offer": -1}]}, "expected_output": "error=negative_cost\nparam=cost\n"}
    ]
}
```

---

### Feature 8: Immutable byte sequence

**As a developer**, I want an immutable byte-sequence type that concatenates and slices cheaply and round-trips through text encodings, so I can build I/O buffers without copying and without losing characters split across chunk boundaries.

**Expected Behavior / Usage:**

*8.1 Concatenation and search — length is additive, search returns position or -1*

Concatenate byte arrays `a` and `b`; the result's length is the sum of the two lengths. For each byte in `index_of`, report its zero-based position within the concatenation, or `-1` if absent. Output: `count=<total length>` then one `index_of <byte> -> <pos>` line per query.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_bytes_concat_indexof.json`

```json
{
    "description": "Concatenating two byte sequences yields a sequence whose length is the sum of the parts; locating a byte returns its zero-based position in the concatenation, or -1 when the byte is absent.",
    "cases": [
        {"input": {"op": "bytes_concat", "a": [1], "b": [2], "index_of": [2,3]}, "expected_output": "count=2\nindex_of 2 -> 1\nindex_of 3 -> -1\n"},
        {"input": {"op": "bytes_concat", "a": [10,20,30], "b": [40,50], "index_of": [10,50,99]}, "expected_output": "count=5\nindex_of 10 -> 0\nindex_of 50 -> 4\nindex_of 99 -> -1\n"}
    ]
}
```

*8.2 Byte-range slice decodes to the matching substring*

Encode `text` using the named `encoding`, then take a byte-range slice (`index`,`count`) and decode it back. Output: `slice=<decoded substring>` then `count=<slice byte length>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_bytes_slice.json`

```json
{
    "description": "Decoding a text into bytes and slicing a byte range, then decoding that slice back, returns the corresponding substring; the slice length equals the requested count.",
    "cases": [
        {"input": {"op": "bytes_slice", "encoding": "ascii", "text": "ABCDEF", "index": 0, "count": 3}, "expected_output": "slice=ABC\ncount=3\n"},
        {"input": {"op": "bytes_slice", "encoding": "ascii", "text": "ABCDEF", "index": 3, "count": 3}, "expected_output": "slice=DEF\ncount=3\n"}
    ]
}
```

*8.3 Encode/decode round-trip preserves the original text*

Encode `text` with the named `encoding` and decode it back; the decoded text must equal the original. Output: `byte_count=<bytes>` (reflecting the encoding's width), `decoded=<text>`, and `roundtrip=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_bytes_codec_roundtrip.json`

```json
{
    "description": "Encoding a string to bytes with a named encoding and decoding it back reproduces the original string; the reported byte count reflects the encoding's width.",
    "cases": [
        {"input": {"op": "bytes_codec", "encoding": "utf8", "text": "hello"}, "expected_output": "byte_count=5\ndecoded=hello\nroundtrip=true\n"},
        {"input": {"op": "bytes_codec", "encoding": "unicode", "text": "hello"}, "expected_output": "byte_count=10\ndecoded=hello\nroundtrip=true\n"}
    ]
}
```

*8.4 Partial characters across chunk boundaries are stitched together*

Encode `text` with the named `encoding`, split the raw bytes at the given `split_points` into consecutive chunks, append the chunks one at a time, and decode the reassembled sequence. Even when a multi-byte character is cut across a chunk boundary, decoding must yield the original text. Output: `byte_count=<total bytes>` then `decoded=<text>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_4_bytes_partial_chars.json`

```json
{
    "description": "When a multi-byte character is split across two appended chunks, decoding the reassembled sequence still yields the correct text - partial characters at chunk boundaries are stitched together.",
    "cases": [
        {"input": {"op": "bytes_partial", "encoding": "unicode", "text": "ǢBC", "split_points": [3]}, "expected_output": "byte_count=6\ndecoded=ǢBC\n"},
        {"input": {"op": "bytes_partial", "encoding": "utf8", "text": "ǢBC", "split_points": [1]}, "expected_output": "byte_count=4\ndecoded=ǢBC\n"}
    ]
}
```

---

### Feature 9: Quote-aware path parsing & quoting

**As a developer**, I want to split dotted paths while honoring quoted literal segments, and to wrap text in double quotes, so I can parse hierarchical configuration keys that may contain literal dots.

**Expected Behavior / Usage:**

*9.1 Split a dotted path honoring quotes*

Split `path` on the `.` separator into segments, except that any span enclosed in double quotes is taken as a single literal segment — dots inside quotes are preserved and the surrounding quotes are stripped. Output: `count=<n>` then one `segment=<value>` line per segment, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_split_dotted_path.json`

```json
{
    "description": "Split a dot-delimited path into segments, but treat any double-quoted span as a single literal segment so that dots inside quotes are preserved rather than used as separators.",
    "cases": [
        {"input": {"op": "split_path", "path": "config.server.host.port"}, "expected_output": "count=4\nsegment=config\nsegment=server\nsegment=host\nsegment=port\n"},
        {"input": {"op": "split_path", "path": "system.deployment.\"/a/dotted.path/*\".handler"}, "expected_output": "count=4\nsegment=system\nsegment=deployment\nsegment=/a/dotted.path/*\nsegment=handler\n"},
        {"input": {"op": "split_path", "path": "\"ab.cd\""}, "expected_output": "count=1\nsegment=ab.cd\n"}
    ]
}
```

*9.2 Wrap text in double quotes*

Prepend and append a double-quote character to `text`. An empty (or absent) `text` becomes an empty quoted pair. Output: `quoted=<wrapped text>`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_double_quote_wrap.json`

```json
{
    "description": "Wrap any text in a leading and trailing double-quote character; a null/absent text wraps to an empty quoted pair.",
    "cases": [
        {"input": {"op": "quote", "text": "hello.world"}, "expected_output": "quoted=\"hello.world\"\n"},
        {"input": {"op": "quote", "text": "\""}, "expected_output": "quoted=\"\"\"\n"},
        {"input": {"op": "quote", "text": ""}, "expected_output": "quoted=\"\"\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the nine primitives above, with one cohesive logical unit per primitive and no coupling to stdin/stdout or JSON. The physical structure (multi-module) must align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command object from stdin, routes on `op` to the appropriate primitive, invokes it, and prints the result lines exactly per the contracts above — including normalizing any invalid-argument/failure conditions into the neutral `error=<category>` (+ optional `param=<name>`) lines. This adapter must be logically separated from the core primitives.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_slice.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_slice@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other, and each `.txt` contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- behavior follows definition (full tail logic implies return starting at match)
