## Product Requirement Document

# Task List Domain Model - In-Memory Tasks with JSON Serialization & Persistence

## Project Goal

Build a small task-list domain core that lets application developers model individual to-do items and a mutable collection of them, serialize items to and from a plain JSON map, query the collection for completed items, and round-trip the whole collection through a durable key-value store — all without re-implementing this bookkeeping by hand in every screen or feature that touches tasks.

---

## Background & Problem

Without a dedicated domain model, developers building a to-do feature end up scattering ad-hoc maps, booleans, and serialization code across the UI layer: every place that needs to add an item, flip its completion state, filter the finished ones, or save the list re-writes the same fragile glue. This leads to duplicated logic, inconsistent JSON shapes, and persistence bugs where reloaded data no longer matches what was saved.

With this domain core, an item is a single value with a text label and a completion flag, a list is an ordered, growable collection of items, and the operations developers actually need — construct, decode/encode, toggle, append, filter-completed, and save/load — are provided as small, predictable behaviors with a stable input/output contract.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a small domain (an item value object and a collection aggregate), so a compact, well-separated layout is appropriate — keep the item model, the collection model, and the persistence concern in clearly delineated units rather than collapsing everything into one undifferentiated blob, but do not over-engineer it into a large framework.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below define a **black-box contract for the execution adapter**, not the internal shape of the core model. The core domain must not read stdin, write stdout, or parse the harness command envelope. A separate execution adapter translates each JSON command into ordinary method calls on the core and renders the result lines.

3. **Adherence to SOLID Design Principles:** Separate item-level behavior, collection-level behavior, serialization, and persistence into cohesive units. The collection should depend on an abstraction for durable storage rather than on a concrete I/O implementation, so the store can be substituted.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language. Completion state must default to *not completed* when unspecified at construction. Serialization must be symmetric: encoding the result of a decode must reproduce a value-equal map. Persistence must be a faithful round-trip: a freshly loaded collection must equal the saved one in length, order, text, and completion state. Malformed adapter input must be surfaced as a neutral error category, never as a host-language runtime artifact.

---

## Core Features

### Feature 1: Task Item Model

**As a developer**, I want a single value type that represents one to-do item with a text label and a completion flag, so I can construct, serialize, and flip items without hand-rolling maps and booleans.

**Expected Behavior / Usage:**

*1.1 Construct a task — Build an item from text, with a defaulting completion flag.*

An item is created from a text label. The completion flag is optional at construction: when it is omitted the item is **not completed** (`false`); when it is supplied the given value is honored verbatim. The output echoes the stored text and the resolved completion state, one field per line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_construct_task.json`

```json
{
    "description": "Create a single task from its text. When the completion flag is omitted it defaults to not-completed; when supplied it is honored verbatim. The output echoes the stored text and the resolved completion state.",
    "cases": [
        {
            "input": {"mode": "construct", "text": "task 1"},
            "expected_output": "text=task 1\ncompleted=false"
        },
        {
            "input": {"mode": "construct", "text": "buy milk", "completed": true},
            "expected_output": "text=buy milk\ncompleted=true"
        }
    ]
}
```

*1.2 Serialize a task — Decode a JSON map into an item, then re-encode it.*

An item can be decoded from a plain map carrying a `text` string and a `completed` boolean, and can be encoded back to the same map shape. Serialization is symmetric: re-encoding a decoded item reproduces a value-equal map with keys `text` and `completed`. The output reports the decoded text, the decoded flag, and the canonical re-encoded JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_serialize_task.json`

```json
{
    "description": "Round-trip a task through its JSON map representation: decode a map with text and completion keys into a task, then re-encode it. The decoded text and flag are reported, plus the canonical re-encoded JSON which must be value-equal to the original map.",
    "cases": [
        {
            "input": {"mode": "serialize", "task": {"text": "task #1", "completed": true}},
            "expected_output": "text=task #1\ncompleted=true\njson={\"text\":\"task #1\",\"completed\":true}"
        },
        {
            "input": {"mode": "serialize", "task": {"text": "groceries", "completed": false}},
            "expected_output": "text=groceries\ncompleted=false\njson={\"text\":\"groceries\",\"completed\":false}"
        }
    ]
}
```

*1.3 Toggle completion — Flip the completion flag in place.*

Toggling an item flips its completion flag between `true` and `false`. Starting from a known initial state and applying the toggle a given number of times produces a strictly alternating sequence of states. The output reports the initial state followed by the state after each successive toggle.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_toggle_task.json`

```json
{
    "description": "Toggle a task's completion flag a number of times starting from a known initial state. Each toggle flips the flag, so the reported sequence of states must strictly alternate starting from the initial value.",
    "cases": [
        {
            "input": {"mode": "toggle", "completed": false, "times": 2},
            "expected_output": "initial=false\nafter_1=true\nafter_2=false"
        },
        {
            "input": {"mode": "toggle", "completed": true, "times": 1},
            "expected_output": "initial=true\nafter_1=false"
        }
    ]
}
```

---

### Feature 2: Task Collection Model

**As a developer**, I want an ordered, growable collection of items with a few targeted queries and durable persistence, so I can manage a whole to-do list without re-implementing storage and filtering glue.

**Expected Behavior / Usage:**

*2.1 Append tasks — Add items in order and observe the growing list.*

The collection starts empty. Appending an item increases the size by exactly one and preserves insertion order. The output reports the final count followed by each stored text in order, numbered from 1.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_add_tasks.json`

```json
{
    "description": "Append a sequence of task texts to an initially empty list. The list grows by one per append and preserves insertion order. The output reports the final size followed by each stored text in order.",
    "cases": [
        {
            "input": {"mode": "add", "tasks": ["task 1"]},
            "expected_output": "[the total count of matching items]1\n1=task 1"
        },
        {
            "input": {"mode": "add", "tasks": ["task 1", "task 2", "task 3"]},
            "expected_output": "[the total count of matching items]3\n1=task 1\n2=task 2\n3=task 3"
        }
    ]
}
```

*2.2 Filter completed tasks — Select only finished items, preserving order.*

Given a mix of completed and not-completed items, the collection can return only the completed ones while preserving their original relative order. The output reports how many completed items there are, followed by their texts in order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_filter_completed.json`

```json
{
    "description": "From a mixed list of completed and not-completed tasks, select only the completed ones while preserving their original relative order. The output reports the number of completed tasks followed by their texts in order.",
    "cases": [
        {
            "input": {"mode": "filter_completed", "tasks": [{"text": "task 1", "completed": false}, {"text": "task 2", "completed": false}, {"text": "task 3", "completed": true}]},
            "expected_output": "[the total count of matching items]1\n1=task 3"
        },
        {
            "input": {"mode": "filter_completed", "tasks": [{"text": "a", "completed": true}, {"text": "b", "completed": false}, {"text": "c", "completed": true}]},
            "expected_output": "[the total count of matching items]2\n1=a\n2=c"
        }
    ]
}
```

*2.3 Persist and reload — Round-trip the whole collection through durable storage.*

The collection can be saved to a durable key-value store under a fixed key as a JSON array, and a fresh, empty collection can load that data back. The reload is faithful: the loaded collection has the same length and order, and each item's text and completion flag survive the round-trip unchanged. The output reports the reloaded count followed by each reloaded item rendered as `text|completed`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_persist_roundtrip.json`

```json
{
    "description": "Persist a list of tasks to durable key-value storage, then reload them into a fresh, empty list. The reloaded list must contain exactly the same tasks, in order, with text and completion state preserved through the save/load round-trip.",
    "cases": [
        {
            "input": {"mode": "persist", "tasks": [{"text": "task 1", "completed": false}, {"text": "task 2", "completed": false}, {"text": "task 3", "completed": true}]},
            "expected_output": "[the total count of matching items]3\n1=task 1|false\n2=task 2|false\n3=task 3|true"
        },
        {
            "input": {"mode": "persist", "tasks": [{"text": "only", "completed": true}]},
            "expected_output": "[the total count of matching items]1\n1=only|true"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured task-domain codebase implementing the item model (construct, serialize, toggle) and the collection model (append, filter-completed, persist/reload) described above, with the durable-store concern kept behind an abstraction. The physical structure must be compact but logically separated, matching the small scale of this domain.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command (a `mode` plus its arguments), invokes the appropriate core method calls, and prints the result lines to stdout exactly matching the per-leaf-feature contracts above. Malformed commands are rendered as a neutral error category line rather than leaking any host-language runtime detail. This adapter is logically and physically separate from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_construct_task.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_construct_task@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
