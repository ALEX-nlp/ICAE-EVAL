## Product Requirement Document

# Keyed Value Store with JSON Persistence and Change Notifications

## Project Goal

Build a reusable key/value storage abstraction that lets application developers persist typed values under string keys, retrieve them later as their original type or as raw text, and observe every mutation through change notifications — without each caller having to hand-roll serialization, key validation, and event plumbing.

---

## Background & Problem

A persistent string-keyed store (such as a browser-backed store) can only hold text. Application code, however, works with rich values: numbers, text, and structured records. Without a shared abstraction, every caller must serialize values to text before writing, parse them back after reading, guard against blank keys, and invent its own way to react when a value changes.

This library closes that gap. It serializes values to JSON on write and deserializes them on read, so callers store and retrieve native values directly. It also exposes the raw stored text when needed, tolerates legacy non-JSON content, validates keys uniformly, and raises a pair of notifications around every write so observers can audit or veto changes. Every operation is offered in two interchangeable invocation styles — a direct (synchronous) style and a deferred (asynchronous) style selected by a `mode` field — that produce identical observable results.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., a storage backend, a serializer, a service layer, an event model), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON command parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain. In particular, the underlying text storage backend MUST be pluggable so that an in-memory backend can replace a platform-specific one for testing.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate the storage backend, the serializer, the service orchestration, key validation, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The serialization strategy and the storage backend must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Any storage backend or serializer implementation must be perfectly substitutable for its abstraction.
   - **Interface Segregation Principle (ISP):** Keep the storage and serialization abstractions small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** The service must depend on storage and serialization abstractions, not on concrete low-level implementations.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully (blank keys, null payloads, legacy non-JSON content). Errors should be modeled properly (e.g., specific exception types or Result patterns) rather than relying on generic faults.

---

## Core Features

The execution adapter reads ONE JSON scenario object from stdin and drives a single fresh store instance. A scenario has a `mode` (`"sync"` or `"async"`, both observably identical), an optional `track_events` flag, an optional `cancel_changing` flag, an optional `preset` array that seeds the underlying backend with raw stored text (`{"key", "raw"}`), and a `steps` array of operations executed in order. Each operation names an `op` and its parameters. Observations are written one per line: a value read prints `value=<rendered>`, a raw-text read prints `raw=<text>`, an item count prints `length=<n>`, a positional key lookup prints `key=<name>`, an existence check prints `contains=<true|false>`, a missing/null value renders as the literal token `<null>`, change notifications print `event=...` lines, and a rejected operation prints a normalized `error=<category> param=<name>` line. Mutating operations that succeed print nothing by themselves; their effect is observed through subsequent reads, counts, or events.

### Feature 1: Persist and Retrieve Values

**As a developer**, I want to store native values under a key and read them back as the same value, so I can persist application data without writing serialization code at every call site.

**Expected Behavior / Usage:**

*1.1 Primitive round-trip — store a text or number value, then read it back*

Storing a primitive value (`op:"set"` with a `type` of `string`, `int`, or `double`) serializes it and keeps it under the key. Reading the count (`op:"length"`) reports one item, and reading it back (`op:"get"` with the matching `type`) yields the same primitive. Numbers render as their digits; text renders verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_primitive_roundtrip.json`

```json
{
    "description": "Store a primitive value (text or number) under a key, then read the current item count and read the value back. The retrieved value round-trips to the same primitive that was stored, and the store reports exactly one item.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "testKey", "type": "string", "value": "stringTest"}, {"op": "length"}, {"op": "get", "key": "testKey", "type": "string"}]}, "expected_output": "length=1\nvalue=stringTest\n"},
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "k", "type": "int", "value": 11}, {"op": "length"}, {"op": "get", "key": "k", "type": "int"}]}, "expected_output": "length=1\nvalue=11\n"}
    ]
}
```

*1.2 Structured object round-trip — store a record, then read it back*

Storing a structured object (`type:"object"`, a record with an integer `Id` and a text `Name`) serializes it to a JSON object and keeps it. Reading it back yields the same fields, rendered as a JSON object string.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_object_roundtrip.json`

```json
{
    "description": "Store a structured object (here a record with an integer id and a name) under a key, then read the item count and read the object back. Its fields round-trip unchanged, serialized as a JSON object.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "testKey", "type": "object", "value": {"Id": 2, "Name": "Jane Smith"}}, {"op": "length"}, {"op": "get", "key": "testKey", "type": "object"}]}, "expected_output": "length=1\nvalue={\"Id\":2,\"Name\":\"Jane Smith\"}\n"}
    ]
}
```

*1.3 Null value round-trip — a stored null is a real entry*

Storing a null value still creates an entry: the count is one, and reading it back yields null (rendered `<null>`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_null_value_roundtrip.json`

```json
{
    "description": "Store a null value under a key, then read the item count and read the value back. A null is persisted as a real entry (the count is one) and reading it back yields null.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "testKey", "type": "string", "value": null}, {"op": "length"}, {"op": "get", "key": "testKey", "type": "string"}]}, "expected_output": "length=1\nvalue=<null>\n"}
    ]
}
```

*1.4 Overwrite — storing under an existing key replaces the value*

Writing a second value under a key already in use replaces the first; a subsequent read returns the most recent value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_overwrite_value.json`

```json
{
    "description": "Store a value under a key and then store a different value under the same key. The latest write replaces the earlier one, so reading the key returns the most recently stored value.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "k", "type": "string", "value": "first-value"}, {"op": "set", "key": "k", "type": "string", "value": "second-value"}, {"op": "get", "key": "k", "type": "string"}]}, "expected_output": "value=second-value\n"}
    ]
}
```

---

### Feature 2: Read Stored Content As Raw Text

**As a developer**, I want to read the exact stored text for a key and to recover gracefully from legacy non-JSON content, so I can inspect or migrate stored data without crashes.

**Expected Behavior / Usage:**

*2.1 Raw serialized form — read a stored value as its underlying text*

Reading a key as raw text (`op:"get_string"`) returns the exact serialized form held in the backend: text values keep their surrounding JSON quotes, numbers are their digits, and objects are a JSON object string.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_read_as_raw_string.json`

```json
{
    "description": "Store a typed value, then read it back as its raw stored text. The result is the exact serialized form held in the store: text values keep their surrounding JSON quotes, numbers are their digits, and objects are a JSON object string.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "k", "type": "int", "value": 11}, {"op": "get_string", "key": "k"}]}, "expected_output": "raw=11\n"},
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "k", "type": "object", "value": {"Id": 2, "Name": "Jane Smith"}}, {"op": "get_string", "key": "k"}]}, "expected_output": "raw={\"Id\":2,\"Name\":\"Jane Smith\"}\n"}
    ]
}
```

*2.2 Backward compatibility — non-JSON stored text is returned unchanged*

If a key's stored content is not valid serialized JSON, requesting it as a text value returns the original raw text unchanged rather than failing.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_backward_compat_raw_string.json`

```json
{
    "description": "When the stored content for a key is not valid serialized JSON, requesting that key as a text value returns the original raw stored text unchanged instead of failing.",
    "cases": [
        {"input": {"mode": "sync", "preset": [{"key": "k", "raw": "[{ id: 5, name: \"Jane Smith\"}]"}], "steps": [{"op": "get", "key": "k", "type": "string"}]}, "expected_output": "value=[{ id: 5, name: \"Jane Smith\"}]\n"}
    ]
}
```

---

### Feature 3: Store Text Verbatim

**As a developer**, I want to store a text value exactly as given, bypassing serialization, so opaque tokens are stored byte-for-byte.

**Expected Behavior / Usage:**

*3.1 Verbatim store — text is kept exactly*

Storing text verbatim (`op:"set_string"`) keeps the exact bytes given; the count becomes one and reading it back as raw text returns the same string.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_store_string_verbatim.json`

```json
{
    "description": "Store a text value verbatim (without JSON serialization), then read the item count and read the value back as text. The stored bytes are exactly the input string and the store reports one item.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set_string", "key": "testKey", "value": "StringValue"}, {"op": "length"}, {"op": "get_string", "key": "testKey"}]}, "expected_output": "length=1\nraw=StringValue\n"}
    ]
}
```

*3.2 Verbatim overwrite — the later verbatim write wins*

Writing verbatim text under a key already in use replaces the previous content.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_overwrite_string_verbatim.json`

```json
{
    "description": "Store a text value verbatim under a key, then store a different text value verbatim under the same key. The later write replaces the earlier one.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set_string", "key": "k", "value": "first-value"}, {"op": "set_string", "key": "k", "value": "second-value"}, {"op": "get_string", "key": "k"}]}, "expected_output": "raw=second-value\n"}
    ]
}
```

---

### Feature 4: Remove An Entry

**As a developer**, I want to delete a key, so I can discard data I no longer need; deleting a missing key must be harmless.

**Expected Behavior / Usage:**

Removing a key that exists (`op:"remove"`) deletes it and the count drops. Removing a key that is absent is a no-op and leaves the store unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_remove_item.json`

```json
{
    "description": "Remove a key from the store. Removing a key that exists deletes it (the count drops). Removing a key that is not present is a no-op and leaves the store unchanged.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "testKey", "type": "object", "value": {"Id": 2, "Name": "Jane Smith"}}, {"op": "length"}, {"op": "remove", "key": "testKey"}, {"op": "length"}]}, "expected_output": "length=1\nlength=0\n"},
        {"input": {"mode": "sync", "steps": [{"op": "remove", "key": "testKey"}, {"op": "length"}]}, "expected_output": "length=0\n"}
    ]
}
```

---

### Feature 5: Clear The Store

**As a developer**, I want to remove every entry at once, so I can reset state; clearing an empty store must be harmless.

**Expected Behavior / Usage:**

Clearing a populated store (`op:"clear"`) removes every entry and the count becomes zero. Clearing an already-empty store is a no-op.

**Test Cases:** `rcb_tests/public_test_cases/feature5_clear_store.json`

```json
{
    "description": "Clear the whole store. Clearing a populated store removes every entry (the count becomes zero). Clearing an already-empty store is a no-op.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "Item1", "type": "object", "value": {"Id": 1, "Name": "Jane Smith"}}, {"op": "set", "key": "Item2", "type": "object", "value": {"Id": 2, "Name": "John Smith"}}, {"op": "length"}, {"op": "clear"}, {"op": "length"}]}, "expected_output": "length=2\nlength=0\n"},
        {"input": {"mode": "sync", "steps": [{"op": "clear"}, {"op": "length"}]}, "expected_output": "length=0\n"}
    ]
}
```

---

### Feature 6: Count Entries

**As a developer**, I want to know how many entries are stored, so I can report or branch on store size.

**Expected Behavior / Usage:**

The count (`op:"length"`) is zero for an empty store and equals the number of distinct stored keys otherwise.

**Test Cases:** `rcb_tests/public_test_cases/feature6_count_items.json`

```json
{
    "description": "Report how many entries the store holds. An empty store reports zero; after storing several distinct keys the count equals the number of keys.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "length"}]}, "expected_output": "length=0\n"},
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "Item1", "type": "object", "value": {"Id": 1, "Name": "Jane Smith"}}, {"op": "set", "key": "Item2", "type": "object", "value": {"Id": 2, "Name": "John Smith"}}, {"op": "length"}]}, "expected_output": "length=2\n"}
    ]
}
```

---

### Feature 7: Look Up A Key By Position

**As a developer**, I want to fetch the name of the key at a given insertion position, so I can enumerate stored keys.

**Expected Behavior / Usage:**

A positional lookup (`op:"key"` with a zero-based `index`) returns the name of the key at that insertion position; a position beyond the last entry returns null (rendered `<null>`).

**Test Cases:** `rcb_tests/public_test_cases/feature7_key_by_index.json`

```json
{
    "description": "Look up the name of the key stored at a given zero-based insertion position. A valid position returns that key's name; a position beyond the last entry returns null.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "TestKey1", "type": "object", "value": {"Id": 1, "Name": "Jane Smith"}}, {"op": "set", "key": "TestKey2", "type": "object", "value": {"Id": 2, "Name": "John Smith"}}, {"op": "key", "index": 1}]}, "expected_output": "key=TestKey2\n"},
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "TestKey1", "type": "object", "value": {"Id": 1, "Name": "Jane Smith"}}, {"op": "key", "index": 1}]}, "expected_output": "key=<null>\n"}
    ]
}
```

---

### Feature 8: Check Key Existence

**As a developer**, I want to test whether a key is present, so I can branch without reading and parsing its value.

**Expected Behavior / Usage:**

An existence check (`op:"contains"`) returns true when a value has been stored under the key and false otherwise.

**Test Cases:** `rcb_tests/public_test_cases/feature8_key_exists.json`

```json
{
    "description": "Check whether a key currently exists in the store. The answer is true when a value has been stored under that key and false otherwise.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "TestKey", "type": "object", "value": {"Id": 1, "Name": "Jane Smith"}}, {"op": "contains", "key": "TestKey"}]}, "expected_output": "contains=true\n"},
        {"input": {"mode": "sync", "steps": [{"op": "contains", "key": "TestKey"}]}, "expected_output": "contains=false\n"}
    ]
}
```

---

### Feature 9: Reject Invalid Keys

**As a developer**, I want blank keys rejected uniformly across every keyed operation, so misuse fails fast and predictably.

**Expected Behavior / Usage:**

Any keyed operation given a key that is null, empty, or whitespace-only is rejected. The rejection is reported as a normalized argument error naming the offending parameter (`error=argument_null param=key`), and the operation is not performed.

**Test Cases:** `rcb_tests/public_test_cases/feature9_reject_invalid_key.json`

```json
{
    "description": "Every keyed operation rejects a key that is null, empty, or whitespace-only. The rejection is reported as a normalized argument error that names the offending key parameter, and no operation is performed.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": "", "type": "string", "value": "Data"}]}, "expected_output": "error=argument_null param=key\n"},
        {"input": {"mode": "sync", "steps": [{"op": "set", "key": null, "type": "string", "value": "Data"}]}, "expected_output": "error=argument_null param=key\n"}
    ]
}
```

---

### Feature 10: Reject Null Text Payloads

**As a developer**, I want the verbatim-text store to reject a null payload, so I never silently persist a missing value as text.

**Expected Behavior / Usage:**

Storing text verbatim (`op:"set_string"`) with a null value is rejected (after the key itself is validated) as a normalized argument error naming the data parameter (`error=argument_null param=data`); nothing is stored.

**Test Cases:** `rcb_tests/public_test_cases/feature10_reject_null_string_data.json`

```json
{
    "description": "Storing a text value verbatim rejects a null payload. The rejection is reported as a normalized argument error that names the offending data parameter, and nothing is stored.",
    "cases": [
        {"input": {"mode": "sync", "steps": [{"op": "set_string", "key": "MyValue", "value": null}]}, "expected_output": "error=argument_null param=data\n"}
    ]
}
```

---

### Feature 11: Change Notifications

**As a developer**, I want to observe and optionally veto every write through paired notifications, so I can audit, react to, or cancel changes.

**Expected Behavior / Usage:**

When notifications are tracked (`track_events:true`), each successful write raises a pre-save notification then a post-save notification.

*11.1 Notifications on a new save — pre-save and post-save fire in order*

Saving under a new key raises a `changing` notification before storing and a `changed` notification after. Both carry the key, an empty (null) previous value, and the new value; the pre-save notification also exposes a not-cancelled flag.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_change_events_on_save.json`

```json
{
    "description": "Saving a value under a new key raises two notifications in order: a pre-save 'changing' notification and a post-save 'changed' notification. Both report the key, an empty (null) previous value, and the new value; the pre-save notification additionally exposes a not-cancelled flag.",
    "cases": [
        {"input": {"mode": "sync", "track_events": true, "steps": [{"op": "set", "key": "Key", "type": "string", "value": "Data"}]}, "expected_output": "event=changing key=Key old=<null> new=Data cancel=false\nevent=changed key=Key old=<null> new=Data\n"}
    ]
}
```

*11.2 Cancellation — a vetoed pre-save notification abandons the write*

If a subscriber marks the pre-save notification as cancelled, the write is abandoned: the value is not stored (the count stays zero) and no post-save notification is raised.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_cancel_changing.json`

```json
{
    "description": "If a subscriber marks the pre-save 'changing' notification as cancelled, the write is abandoned: the value is not stored (the count stays zero) and no post-save 'changed' notification is raised.",
    "cases": [
        {"input": {"mode": "sync", "track_events": true, "cancel_changing": true, "steps": [{"op": "set", "key": "Key", "type": "string", "value": "Data"}, {"op": "length"}]}, "expected_output": "event=changing key=Key old=<null> new=Data cancel=true\nlength=0\n"}
    ]
}
```

*11.3 Old value on update — notifications report the previous value*

When a save overwrites a key that already held a value, both notifications report the previously stored value as the old value and the incoming value as the new value.

**Test Cases:** `rcb_tests/public_test_cases/feature11_3_change_events_old_value_on_update.json`

```json
{
    "description": "When a save overwrites a key that already held a value, both the pre-save and post-save notifications report the previously stored value as the old value and the incoming value as the new value.",
    "cases": [
        {"input": {"mode": "sync", "track_events": true, "preset": [{"key": "Key", "raw": "Foo"}], "steps": [{"op": "set", "key": "Key", "type": "string", "value": "Data"}]}, "expected_output": "event=changing key=Key old=Foo new=Data cancel=false\nevent=changed key=Key old=Foo new=Data\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above, with a pluggable text storage backend, a pluggable serializer, and a service layer that orchestrates validation, serialization, storage, and change notifications. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core logic must be decoupled from stdin/stdout and JSON command parsing.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON scenario from stdin, drives a fresh store instance against an in-memory backend, and prints the observable signals to stdout, matching the per-feature contracts above. The scenario fields are: `mode` (`sync`/`async`, observably identical), `track_events`, `cancel_changing`, `preset` (seed raw stored text), and `steps`. Supported `op` values are `set` (with `type` of `string`/`int`/`double`/`object`), `set_string`, `get` (with `type`), `get_string`, `remove`, `clear`, `length`, `key` (with `index`), and `contains`. Native exceptions thrown by the core MUST be normalized in the adapter into neutral `error=<category> param=<name>` lines (never leaking host-language exception identities); missing/null values render as the token `<null>`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the '<method_name> checks' pattern used for primitive validation in the core util
- follow the error format established by the C003 sibling constraint
