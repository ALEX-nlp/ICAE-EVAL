## Product Requirement Document

# Declarative Cluster-Resource Utilities — JSON Patching, Selector Matching, and Lifecycle-Interval Modeling

## Project Goal

Build a small library of well-defined, side-effect-free utilities for manipulating and reasoning about declarative cluster-style resource records (JSON documents and the standard object/selector/status structures layered on top of them), so that higher-level tooling can patch documents, evaluate selectors, model workload run-times, and prepare objects for re-application without re-implementing this fiddly logic each time.

---

## Background & Problem

Tools that capture, transform, and replay the state of a container-orchestration cluster keep running into the same low-level chores: editing deeply nested JSON in bulk, deciding whether an object satisfies a label selector, turning raw container status timestamps into a single "when was this workload actually running" interval, comparing two such intervals so that updates only ever move "forward", and stripping server-managed fields off an object before it is re-applied.

Without a shared library, each tool hand-rolls these operations, producing subtle inconsistencies (e.g. selector edge cases, off-by-one interval rules, forgetting to clear a server-populated field) that are hard to test and easy to get wrong. This library provides one tested contract for each operation: pure input-to-output functions whose behavior is fully specified by their data, independent of any cluster connection.

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

### Feature 1: Wildcard JSON Patch Operations

**As a developer**, I want to add or remove a field across every element of an array inside a JSON document with a single path expression, so I can bulk-edit deeply nested documents without writing a loop for each level.

**Expected Behavior / Usage:**

The operations work on a slash-separated JSON pointer that is extended with one extra token: `*`. A `*` segment stands for "every element of the array found at this position", so a path like `/foo/*/baz` resolves to the `baz` field of every element of the `foo` array. A path may contain a `*`; the segment immediately before a `*` must resolve to an array, and the final resolved locations must be JSON objects. The whole mutated document is rendered as compact JSON with object keys sorted lexicographically (so output is canonical and order-independent of the input key order).

*1.1 Bulk Add — insert a key/value at every resolved location*

For every object the path resolves to, insert the given key with the given value. An `overwrite` flag governs collisions: when `true`, the value is written even if the key already exists at that location; when `false`, locations that already have the key are left unchanged, while locations missing the key still receive it. The output is the full document after mutation.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_json_patch_add.json`

```json
{
    "description": "Apply an additive change to a JSON document at a path that uses the '*' wildcard token to fan out across every element of an array. The path is a slash-separated JSON pointer in which a single '*' segment means 'every element of the array at this position'. For each location the path resolves to (which must be a JSON object), a given key/value pair is inserted. An 'overwrite' flag controls collisions: when true, the value is written even if the key already exists; when false, an existing key is left untouched while missing keys are still added. The whole (mutated) document is emitted as compact JSON with object keys sorted lexicographically.",
    "cases": [
        {
            "input": {"action": "patch_add", "path": "/foo/*/baz", "key": "buzz", "value": 42, "overwrite": true, "document": {"foo": [{"baz": {"buzz": 0}}, {"baz": {"quzz": 1}}, {"baz": {"fixx": 2}}]}},
            "expected_output": "{\"foo\":[{\"baz\":{\"buzz\":42}},{\"baz\":{\"buzz\":42,\"quzz\":1}},{\"baz\":{\"buzz\":42,\"fixx\":2}}]}\n"
        },
        {
            "input": {"action": "patch_add", "path": "/foo/*/baz", "key": "buzz", "value": 42, "overwrite": false, "document": {"foo": [{"baz": {"buzz": 0}}, {"baz": {"quzz": 1}}, {"baz": {"fixx": 2}}]}},
            "expected_output": "{\"foo\":[{\"baz\":{\"buzz\":0}},{\"baz\":{\"buzz\":42,\"quzz\":1}},{\"baz\":{\"buzz\":42,\"fixx\":2}}]}\n"
        }
    ]
}
```

*1.2 Bulk Remove — delete a key at every resolved location*

For every object the path resolves to, delete the entry under the given key if it is present; locations that do not contain the key are left unchanged. The output is the full document after mutation.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_json_patch_remove.json`

```json
{
    "description": "Apply a removal change to a JSON document at a path that uses the '*' wildcard token to fan out across every element of an array. The path is a slash-separated JSON pointer in which a single '*' segment means 'every element of the array at this position'. For each location the path resolves to (which must be a JSON object), the entry under the given key is deleted if present; locations that do not contain the key are left unchanged. The whole (mutated) document is emitted as compact JSON with object keys sorted lexicographically.",
    "cases": [
        {
            "input": {"action": "patch_remove", "path": "/foo/*/baz", "key": "quzz", "document": {"foo": [{"baz": {"buzz": 0}}, {"baz": {"quzz": 1}}, {"baz": {"fixx": 2}}]}},
            "expected_output": "{\"foo\":[{\"baz\":{\"buzz\":0}},{\"baz\":{}},{\"baz\":{\"fixx\":2}}]}\n"
        }
    ]
}
```

---

### Feature 2: Label Selector Matching

**As a developer**, I want to test whether an object's labels satisfy a label selector, so I can decide membership using the same set-based and equality-based rules the orchestration domain uses.

**Expected Behavior / Usage:**

The input is a map of string labels and a selector. A selector may carry set-based requirements under `matchExpressions` and/or an equality map under `matchLabels`; the object matches only when ALL requirements are satisfied (logical AND). Each expression has a `key`, an `operator`, and an optional `values` list. The operators are: `In` — the key is present and its value is one of `values`; `NotIn` — the key is absent, or present with a value not in `values`; `Exists` — the key is present (regardless of value); `DoesNotExist` — the key is absent. There is a validity rule on `values`: `In` and `NotIn` require a non-empty `values` list, while `Exists` and `DoesNotExist` require that NO `values` list be given; breaking this rule makes the selector malformed. The `matchLabels` map requires each listed key to be present with exactly the listed value. Output is `matched=true` or `matched=false` for a valid evaluation, or the normalized error line `error=malformed_label_selector` when an expression violates the values-presence rule.

**Test Cases:** `rcb_tests/public_test_cases/feature2_label_selector_match.json`

```json
{
    "description": "Evaluate whether a set of key/value labels satisfies a label selector. A selector may contain set-based 'matchExpressions' and/or an equality-based 'matchLabels' map; an object matches only if ALL requirements hold. Each expression has a key, an operator, and an optional list of values. The operators are: 'In' (key present and its value is one of the listed values), 'NotIn' (key absent, or present with a value not in the list), 'Exists' (key present), 'DoesNotExist' (key absent). 'In'/'NotIn' require a non-empty values list and 'Exists'/'DoesNotExist' require NO values list; violating that makes the expression malformed. The 'matchLabels' map requires each listed key to be present with exactly the listed value. Output is 'matched=true' or 'matched=false' for a valid evaluation, or the normalized error 'error=malformed_label_selector' when an expression breaks the values-presence rule.",
    "cases": [
        {"input": {"action": "label_match", "labels": {"foo": "bar"}, "selector": {"matchExpressions": [{"key": "foo", "operator": "In", "values": ["bar"]}]}}, "expected_output": "matched=true\n"},
        {"input": {"action": "label_match", "labels": {"foo": "bar"}, "selector": {"matchExpressions": [{"key": "foo", "operator": "In"}]}}, "expected_output": "error=malformed_label_selector\n"},
        {"input": {"action": "label_match", "labels": {"foo": "bar"}, "selector": {"matchExpressions": [{"key": "baz", "operator": "Exists"}]}}, "expected_output": "matched=false\n"},
        {"input": {"action": "label_match", "labels": {"foo": "bar"}, "selector": {"matchLabels": {"foo": "bar"}}}, "expected_output": "matched=true\n"}
    ]
}
```

---

### Feature 3: Pod Active-Interval Computation

**As a developer**, I want to collapse a pod's per-container status timestamps into one "active interval", so I can record how long a workload actually ran instead of trying to read it off coarse phase fields.

**Expected Behavior / Usage:**

The input describes a pod as an optional ordered list of init containers plus a list of main containers. Each container reports a state: `running` with a start timestamp (epoch seconds), `finished` with start and end timestamps, or `waiting` with no timestamps. The interval is derived as: the start is the EARLIEST start timestamp seen across ALL containers (init and main); the end is the LATEST finish timestamp, but it is only reported once EVERY main container has finished — if any main container is still running or waiting, the pod is considered to have no end yet. The result is one of three shapes: `Empty` when nothing has started; `Running` with a start timestamp when started but not all main containers have finished; `Finished` with start and end timestamps when all main containers have finished. Output is `state=Empty`, or `state=Running` followed by a `start=<ts>` line, or `state=Finished` followed by `start=<ts>` and `end=<ts>` lines.

**Test Cases:** `rcb_tests/public_test_cases/feature3_pod_active_interval.json`

```json
{
    "description": "Compute the active interval of a pod from its container statuses. The pod has an optional ordered list of init containers and a list of main containers; each container reports a state that is either running (with a start timestamp, in epoch seconds), finished (with start and end timestamps), or waiting (no timestamps). The pod's interval is derived as follows: the start is the EARLIEST start timestamp seen across all containers (init and main); the end is the LATEST finish timestamp, but only once EVERY main container has finished (if any main container is still running or waiting, the pod has no end yet). The result is one of three shapes: 'Empty' when no container has started, 'Running' with a start timestamp when started but not all main containers have finished, or 'Finished' with start and end timestamps when all main containers have finished.",
    "cases": [
        {"input": {"action": "pod_lifecycle", "containers": []}, "expected_output": "state=Empty\n"},
        {"input": {"action": "pod_lifecycle", "init_containers": [{"finished": [1234, 1239]}], "containers": [{"finished": [1239, 1240]}, {"finished": [1239, 1244]}]}, "expected_output": "state=Finished\nstart=1234\nend=1244\n"}
    ]
}
```

---

### Feature 4: Active-Interval Comparison

**As a developer**, I want to compare two active-interval values under a partial order, so that I can accept an update only when it strictly advances the recorded interval and reject ambiguous changes.

**Expected Behavior / Usage:**

The input is two interval values, `left` and `right`, where each is one of `Empty`, `Running` with a start timestamp, or `Finished` with start and end timestamps; `right` may also be absent (null), representing "no value recorded yet". Equality: both sides represent the same shape and timestamps, and additionally `Empty` is considered equal to an absent value. Ordering: `Empty` (or absent) is less than any started value; a `Running` value is less than a `Finished` value ONLY when they share the same start timestamp, otherwise the two are incomparable; two `Running` values are equal when their starts match, else incomparable; two `Finished` values are equal when both timestamps match, else incomparable; any started value is greater than `Empty`/absent. Output reports two lines: `equal=<true|false>` and `ordering=<less|greater|equal|incomparable>`, where `incomparable` means the pair has no defined order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_interval_comparison.json`

```json
{
    "description": "Compare two pod active-interval values under a partial order designed for safe monotonic updates. Each value is one of 'Empty', 'Running' with a start timestamp, or 'Finished' with start and end timestamps. The right operand may also be absent (null), representing 'no value yet'. Equality holds when both sides represent the same shape and timestamps (and 'Empty' is considered equal to an absent value). The ordering rules are: 'Empty' (or absent) is less than any started value; a 'Running' value is less than a 'Finished' value ONLY when they share the same start timestamp, otherwise the two are incomparable; two 'Running' values are equal iff equal, else incomparable; two 'Finished' values are equal iff both timestamps match, else incomparable. Any started value is greater than 'Empty'/absent. Output reports 'equal=<bool>' and 'ordering=<less|greater|equal|incomparable>', where 'incomparable' means the two values have no defined order.",
    "cases": [
        {"input": {"action": "interval_compare", "left": {"state": "Empty"}, "right": null}, "expected_output": "equal=true\nordering=equal\n"},
        {"input": {"action": "interval_compare", "left": {"state": "Running", "start": 1}, "right": {"state": "Running", "start": 2}}, "expected_output": "equal=false\nordering=incomparable\n"},
        {"input": {"action": "interval_compare", "left": {"state": "Running", "start": 1}, "right": {"state": "Finished", "start": 1, "end": 2}}, "expected_output": "equal=false\nordering=less\n"}
    ]
}
```

---

### Feature 5: Absent-Tolerant Minimum

**As a developer**, I want a minimum of two optional integers that ignores an absent operand instead of letting it dominate, so I can fold a stream of "maybe" values down to the smallest one that actually exists.

**Expected Behavior / Usage:**

The input is two operands `a` and `b`, each either an integer or null (absent). Unlike a naive comparison where an absent value would be treated as the smallest, here an absent operand is simply skipped: if both are present, return the smaller; if exactly one is present, return that one; if both are absent, the result is absent. Output is `result=<n>` for a present result, or `result=none` when both inputs are absent.

**Test Cases:** `rcb_tests/public_test_cases/feature5_min_optional.json`

```json
{
    "description": "Compute the minimum of two optional integer values using 'absent-tolerant' semantics: unlike a naive comparison where an absent value would dominate, here an absent operand is simply ignored. If both operands are present, the smaller is returned; if exactly one is present, that one is returned; if both are absent, the result is absent. Output is 'result=<n>' for a present result or 'result=none' when both inputs are absent.",
    "cases": [
        {"input": {"action": "min_some", "a": null, "b": null}, "expected_output": "result=none\n"},
        {"input": {"action": "min_some", "a": 2, "b": 1}, "expected_output": "result=1\n"}
    ]
}
```

---

### Feature 6: Object Metadata Sanitization

**As a developer**, I want to strip server-managed and instance-specific fields off a cluster object and stamp it with an explicit type, so the object becomes a clean, re-appliable declarative manifest.

**Expected Behavior / Usage:**

The input is an object's metadata plus a target api version and kind. Sanitization clears all server-populated or instance-specific metadata fields: creation timestamp, deletion timestamp, deletion grace period, generation, managed fields, owner references, resource version, and uid. From the `annotations` map, exactly two tool-injected annotations are dropped — `kubectl.kubernetes.io/last-applied-configuration` and `deployment.kubernetes.io/revision` — while every other annotation is preserved. Finally the object's type is set from the supplied api version and kind. The output is the resulting object rendered as compact JSON with object keys sorted lexicographically; any field that became empty is omitted entirely (so cleared scalar fields and an empty annotations map simply do not appear).

**Test Cases:** `rcb_tests/public_test_cases/feature6_metadata_sanitize.json`

```json
{
    "description": "Sanitize a cluster object's metadata so it can be re-applied as a fresh, declarative manifest, and stamp it with an explicit type. All server-populated or instance-specific metadata fields are cleared: creation timestamp, deletion timestamp, deletion grace period, generation, managed fields, owner references, resource version, and uid. From the annotations map, two tool-injected annotations are dropped (the last-applied-configuration annotation and the deployment-revision annotation) while all other annotations are preserved. Finally the object's type is set from the supplied api version and kind. Output is the resulting object emitted as compact JSON with object keys sorted lexicographically; fields that became empty are omitted entirely.",
    "cases": [
        {
            "input": {"action": "sanitize", "api_version": "bar.blah.sh/v2", "kind": "Stuff", "metadata": {"name": "test-obj", "namespace": "test", "annotations": {"some_random_annotation": "blah", "kubectl.kubernetes.io/last-applied-configuration": "foo", "deployment.kubernetes.io/revision": "42.5"}, "creationTimestamp": "2020-01-01T00:00:00Z", "deletionTimestamp": "2020-01-01T00:00:00Z", "deletionGracePeriodSeconds": 123, "generation": 456, "managedFields": [{}], "ownerReferences": [{"apiVersion": "v1", "kind": "Pod", "name": "x", "uid": "y"}], "resourceVersion": "1234", "uid": "abcd"}},
            "expected_output": "{\"apiVersion\":\"bar.blah.sh/v2\",\"kind\":\"Stuff\",\"metadata\":{\"annotations\":{\"some_random_annotation\":\"blah\"},\"name\":\"test-obj\",\"namespace\":\"test\"}}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the utilities above (wildcard JSON patching, label-selector matching, pod active-interval computation, interval comparison under a partial order, absent-tolerant minimum, and object metadata sanitization). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core logic must be pure and decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to the core system — logically (and ideally physically) separated from it. It reads a single JSON request from stdin, dispatches on the `action` field (`patch_add`, `patch_remove`, `label_match`, `pod_lifecycle`, `interval_compare`, `min_some`, `sanitize`), invokes the appropriate core logic, and prints the result (or a normalized `error=<category>` line) to stdout, matching the per-feature contracts above. Native runtime errors raised by the core must be translated into the neutral error lines specified above by this adapter layer.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- format the ordering result as <LEADING_INDEX>:<SEP><TRAILING_INDEX> array
