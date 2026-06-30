## Product Requirement Document

# Subscription-Driven Form State Toolkit — Core Data-Transformation Primitives

## Project Goal

Build a small, framework-agnostic toolkit of pure data-transformation primitives that power a subscription-based form-state engine, so developers can compute exactly what changed in a form (or a single field) and notify only the observers that care — without re-rendering or recomputing anything that did not actually change.

---

## Background & Problem

A form-state engine constantly recomputes derived snapshots: which fields are dirty, which are valid, what the current and initial values are, and which observers must be notified. Done naively, every keystroke triggers a full recompute and notifies every subscriber, regardless of whether the parts they care about changed. This produces wasted work, spurious notifications, and inconsistent reads of deeply nested values.

This toolkit provides the foundational, side-effect-free building blocks that solve those problems: a shallow value comparator, a single-slot memoizer keyed on shallow argument equality, a promise-like detector, a nested-path reader/writer pair with immutable updates, two subscription-aware "diff filters" (one for a single field, one for the whole form) that return only the subscribed slices that actually changed, and a deriver that turns a field's internal bookkeeping into its externally published view (value, initial, errors, and the dirty/valid family of flags). Each primitive is a black box with a precise input → output contract.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic function calls to the core domain.

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

### Feature 1: Shallow Equality Of Two Values

**As a developer**, I want a cheap equality check that compares two values only one level deep, so I can detect "did this change?" without paying for a deep recursive comparison.

**Expected Behavior / Usage:**

The input supplies two values `a` and `b`. The result is `[a specific literal string for success — ask the PM for the exact return value]` when the two are equal by the shallow rule, otherwise `false`. The rule: if `a` and `b` are strictly identical, they are equal. Otherwise, if either is `null` or is not an object, they are equal only if strictly identical (so `null` vs an object, or two unequal primitives, are not equal). When both are non-null objects, they are equal exactly when they own the same number of keys, every key of `a` exists on `b`, and each corresponding value is strictly equal. The comparison never recurses, so two distinct nested objects with identical contents are NOT equal. Output is the literal text `[a specific literal string for success — ask the PM for the exact return value]` or `false`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_shallow_equal.json`

```json
{
    "description": "Compare two values for shallow equality. Two values are considered equal when they are strictly identical, or when both are non-null objects that own exactly the same set of keys and whose corresponding values are strictly equal (no recursion into nested objects). Either value being null (while the other is not) yields not-equal, as does a key-count mismatch or any differing key value.",
    "cases": [
        {"input": {"op": "compare", "a": {"a": 1, "b": 2, "c": 3}, "b": {"a": 1, "b": 2, "c": 3}}, "expected_output": "[a specific literal string for success — ask the PM for the exact return value]"},
        {"input": {"op": "compare", "a": {"a": 1, "b": 2, "c": {}}, "b": {"a": 1, "b": 2, "c": {}}}, "expected_output": "false"}
    ]
}
```

---

### Feature 2: Promise-Like (Thenable) Detection

**As a developer**, I want to recognize whether an arbitrary value is "thenable", so I can decide whether asynchronous handling is required for a validation or submission result.

**Expected Behavior / Usage:**

The input supplies a candidate `value`. The result is `[a specific literal string for success — ask the PM for the exact return value]` only when the value is non-null, is an object (or a function), and exposes a member named `then` whose value is itself callable; otherwise `false`. Because JSON cannot carry a function directly, a member whose value is the wire token `@@fn` denotes a callable member. Therefore an object whose `then` is the function token is thenable, but an object whose `then` is a plain value such as a boolean is not. Plain primitives (`null`, numbers, strings, booleans), empty objects, and arrays are never thenable. Output is the literal text `[a specific literal string for success — ask the PM for the exact return value]` or `false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_thenable.json`

```json
{
    "description": "Decide whether a value is \"thenable\" (promise-like). A value qualifies only when it is non-null, is an object (or function), and exposes a member named then whose value is callable. A member marked with the function token denotes a callable. Plain values (null, numbers, strings, booleans), empty objects, arrays, and objects whose then is a non-callable value are all rejected.",
    "cases": [
        {"input": {"op": "is_thenable", "value": {"then": "@@fn"}}, "expected_output": "[a specific literal string for success — ask the PM for the exact return value]"},
        {"input": {"op": "is_thenable", "value": {"then": [a specific literal string for success — ask the PM for the exact return value]}}, "expected_output": "false"}
    ]
}
```

---

### Feature 3: Single-Slot Memoization Keyed On Shallow Argument Equality

**As a developer**, I want to wrap a computation so it re-runs only when its arguments actually change (compared shallowly), so repeated identical calls reuse the prior result instead of recomputing.

**Expected Behavior / Usage:**

The input supplies `calls`: an ordered sequence where each element is the argument list for one invocation of the wrapped computation. The wrapper remembers only the most recent argument list and its result. It recomputes when there is no previous call, when the number of arguments differs from the previous call, or when any positional argument is not shallow-equal to the argument at the same position in the previous call; otherwise it returns the previously computed result without recomputing. To make recomputation observable, the wrapped computation returns a counter that increments by one each time it actually runs. The output is the ordered list of returned counter values, one per call. Consequently, runs that reuse the cached result repeat the previous number, while runs that recompute show the next number. Because comparison is shallow, two argument objects that are equal at the top level count as unchanged, but objects that differ only in nested contents count as changed.

**Test Cases:** `rcb_tests/public_test_cases/feature3_memoize.json`

```json
{
    "description": "Wrap a computation so that it only re-executes when its argument list changes. Given a sequence of calls (each an array of arguments), the wrapper recomputes when the number of arguments differs from the previous call, or when any positional argument is no longer shallow-equal to the previous one; otherwise it returns the previously computed result. The output reports, for each call in order, a counter that increments exactly once per actual recomputation, so repeated identical calls reuse the same value while changed calls produce a new one. Shallow equality is used for comparison, so equal top-level object arguments are treated as unchanged but objects that differ only in nested contents are treated as changed.",
    "cases": [
        {"input": {"op": "cached_call", "calls": [[1], [1], [1], [1], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2]]}, "expected_output": "[1,1,1,1,2,2,2,2,2]"},
        {"input": {"op": "cached_call", "calls": [[{"value": 1}, {"value": 2}], [{"value": 1}, {"value": 2}], [{"value": 1}, {"value": 2}]]}, "expected_output": "[1,1,1]"}
    ]
}
```

---

### Feature 4: Nested Property Access By Path String

**As a developer**, I want to address values inside arbitrarily nested objects and arrays using a single path string, so I can read and immutably update deep structures without hand-written traversal.

**Expected Behavior / Usage:**

*4.1 Path Tokenization — split a path string into its component segments.*

The input supplies a `key` path string. The result is the ordered list of segments obtained by splitting the path on dots and square brackets, discarding empty segments; numeric array indices are preserved as their string form. A `null` or empty path yields an empty list. If `key` is anything other than a string (a number, boolean, array, or object), it is an error reported as the neutral line `error=non_string_path`. Output for a successful parse is the JSON array of string segments.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_parse_path.json`

```json
{
    "description": "Tokenize a property-access path string into its component segments. A null or empty string yields an empty list. Dots and square brackets are treated as separators, so dotted names and bracketed indices both become individual string segments (numeric indices are kept as strings). Passing a non-string path is an error reported as a neutral error category.",
    "cases": [
        {"input": {"op": "parse_path", "key": "foo[1][2][3].bar[4].cow"}, "expected_output": "[\"foo\",\"1\",\"2\",\"3\",\"bar\",\"4\",\"cow\"]"},
        {"input": {"op": "parse_path", "key": 7}, "expected_output": "error=non_string_path"}
    ]
}
```

*4.2 Read A Nested Value*

The input supplies a `state` structure and a `key` path. The result is the value found by walking the path through the structure. If at any step the current node is undefined, null, not an object/array, or the segment is a non-numeric index into an array, the read yields no value (rendered as the literal text `undefined`). A reachable leaf is returned unchanged (rendered as its JSON form). Reading from a non-object/array root (a boolean, number, or string) always yields no value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_get_in.json`

```json
{
    "description": "Read a value out of a nested structure using a path string. The path supports dotted object keys and bracketed array indices to arbitrary depth. Any missing or unreachable segment yields no value, as does attempting to read from a non-object/array root or indexing an array with a non-numeric segment. A present leaf returns that leaf value unchanged.",
    "cases": [
        {"input": {"op": "get", "state": {"a": [{"b": 2}]}, "key": "a[0].b"}, "expected_output": "2"},
        {"input": {"op": "get", "state": {"myArray": ["a", "b", "c"]}, "key": "myArray.foo"}, "expected_output": "undefined"}
    ]
}
```

*4.3 Immutable Nested Write*

The input supplies a `state` structure, a `key` path, and a `value`. The result is a NEW structure equal to the input but with `value` written at the path; the input is never mutated. Missing intermediate containers along the path are created — a dotted segment creates an object, a bracketed segment creates an array (arrays are extended as needed). When no `value` is supplied, the operation deletes the targeted leaf: empty objects produced by the deletion are pruned away, while arrays keep their length (a removed array element becomes an empty slot, rendered as `null`). Error conditions are reported as neutral category lines: a null or absent root → `error=null_state`; a null or absent key → `error=null_key`; writing a non-numeric segment into an array → `error=non_numeric_key_on_array`; writing a numeric segment into an object → `error=numeric_key_on_object`. Successful output is the JSON form of the resulting structure.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_set_in.json`

```json
{
    "description": "Return a new structure with a value written at a nested path, leaving the input structure untouched (immutable update). Missing intermediate objects/arrays along the path are created; bracketed segments create arrays and dotted segments create objects. Writing an absent value (no value supplied) deletes the targeted leaf and prunes now-empty objects, while arrays retain their length. Error conditions are reported as neutral categories: a null/absent root, a null/absent key, writing a non-numeric key into an array, or a numeric key into an object.",
    "cases": [
        {"input": {"op": "set", "state": {"a": {}, "b": {}}, "key": "c.d.e", "value": 5}, "expected_output": "{\"a\":{},\"b\":{},\"c\":{\"d\":{\"e\":5}}}"},
        {"input": {"op": "set", "state": [], "key": "foo", "value": "bar"}, "expected_output": "error=non_numeric_key_on_array"}
    ]
}
```

---

### Feature 5: Subscription-Based State Filtering

**As a developer**, I want to compare a new state snapshot against the previous one through a subscription, so observers receive only the slices they asked for and only when those slices actually changed.

**Expected Behavior / Usage:**

*5.1 Single-Field Filter*

The input supplies the new `state` of one field, the `previousState`, a `subscription` map naming which fields are of interest (value `[a specific literal string for success — ask the PM for the exact return value]`), and an optional `force` flag. The filter returns an object holding the always-present field identifier (`name`) plus each subscribed field whose value changed relative to the previous state; it returns no object at all (rendered as the literal text `undefined`) when no subscribed field changed and `force` is not set. When `force` is set, the subscribed fields are always returned even if unchanged. The `data` field is compared shallowly; every other field is compared by strict equality. Successful output is the JSON form of the returned object.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_filter_field.json`

```json
{
    "description": "Filter a per-field state snapshot against a subscription so that downstream observers are notified only about the parts they asked for. Given the new state, the previous state, and a subscription naming which fields are of interest, the filter returns an object containing the always-present field identifier plus the subscribed field when it changed relative to the previous state; it returns no object when the subscribed field is unchanged. A force flag makes it always return the subscribed field even when unchanged. The data field is compared shallowly; all other fields are compared by strict equality.",
    "cases": [
        {"input": {"op": "filter_field", "state": {"active": [a specific literal string for success — ask the PM for the exact return value], "data": {"someValue": 42}, "dirty": false, "error": "dog", "initial": "initialValue", "invalid": false, "name": "foo", "pristine": [a specific literal string for success — ask the PM for the exact return value], "touched": [a specific literal string for success — ask the PM for the exact return value], "valid": [a specific literal string for success — ask the PM for the exact return value], "value": "whatever", "visited": [a specific literal string for success — ask the PM for the exact return value]}, "previousState": {"active": [a specific literal string for success — ask the PM for the exact return value], "data": {"someValue": 42}, "dirty": false, "error": "dog", "initial": "initialValue", "invalid": false, "name": "foo", "pristine": [a specific literal string for success — ask the PM for the exact return value], "touched": [a specific literal string for success — ask the PM for the exact return value], "valid": [a specific literal string for success — ask the PM for the exact return value], "value": "cat", "visited": [a specific literal string for success — ask the PM for the exact return value]}, "subscription": {"value": [a specific literal string for success — ask the PM for the exact return value]}}, "expected_output": "{\"name\":\"foo\",\"value\":\"whatever\"}"},
        {"input": {"op": "filter_field", "state": {"active": [a specific literal string for success — ask the PM for the exact return value], "data": {"someValue": 42}, "dirty": false, "error": "dog", "initial": "initialValue", "invalid": false, "name": "foo", "pristine": [a specific literal string for success — ask the PM for the exact return value], "touched": [a specific literal string for success — ask the PM for the exact return value], "valid": [a specific literal string for success — ask the PM for the exact return value], "value": "cat", "visited": [a specific literal string for success — ask the PM for the exact return value]}, "previousState": {"active": [a specific literal string for success — ask the PM for the exact return value], "data": {"someValue": 42}, "dirty": false, "error": "dog", "initial": "initialValue", "invalid": false, "name": "foo", "pristine": [a specific literal string for success — ask the PM for the exact return value], "touched": [a specific literal string for success — ask the PM for the exact return value], "valid": [a specific literal string for success — ask the PM for the exact return value], "value": "cat", "visited": [a specific literal string for success — ask the PM for the exact return value]}, "subscription": {"active": [a specific literal string for success — ask the PM for the exact return value]}}, "expected_output": "undefined"}
    ]
}
```

*5.2 Whole-Form Filter*

The input supplies the new whole-form `state`, the `previousState`, a `subscription` map, and an optional `force` flag. The filter returns an object holding each subscribed field whose value changed relative to the previous state, or no object (rendered as `undefined`) when nothing of interest changed and `force` is not set. With `force` set, all subscribed fields are returned even when unchanged. Here there is no always-present identifier — only subscribed-and-changed fields appear. The `touched` and `visited` maps are compared shallowly; every other field is compared by strict equality. Successful output is the JSON form of the returned object.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_filter_form.json`

```json
{
    "description": "Filter a whole-form state snapshot against a subscription so observers are notified only about the parts they subscribed to. Given the new state, the previous state, and a subscription naming the fields of interest, the filter returns an object holding each subscribed field that changed relative to the previous state, or no object when nothing of interest changed. A force flag makes it always return the subscribed fields even when unchanged. The touched and visited maps are compared shallowly; all other fields are compared by strict equality.",
    "cases": [
        {"input": {"op": "filter_form", "state": {"active": false, "dirty": false, "error": "some error", "invalid": false, "initialValues": {"dog": "cat"}, "pristine": [a specific literal string for success — ask the PM for the exact return value], "submitting": false, "submitFailed": false, "submitSucceeded": false, "submitError": "some submit error", "touched": {"foo": [a specific literal string for success — ask the PM for the exact return value], "bar": false}, "valid": [a specific literal string for success — ask the PM for the exact return value], "validating": false, "values": {"foo": "bar"}, "visited": {"foo": [a specific literal string for success — ask the PM for the exact return value], "bar": false}}, "previousState": {"active": "foo", "dirty": false, "error": "some error", "invalid": false, "initialValues": {"dog": "cat"}, "pristine": [a specific literal string for success — ask the PM for the exact return value], "submitting": false, "submitFailed": false, "submitSucceeded": false, "submitError": "some submit error", "touched": {"foo": [a specific literal string for success — ask the PM for the exact return value], "bar": false}, "valid": [a specific literal string for success — ask the PM for the exact return value], "validating": false, "values": {"foo": "bar"}, "visited": {"foo": [a specific literal string for success — ask the PM for the exact return value], "bar": false}}, "subscription": {"active": [a specific literal string for success — ask the PM for the exact return value]}}, "expected_output": "{\"active\":false}"},
        {"input": {"op": "filter_form", "state": {"active": "foo", "dirty": false, "error": "some error", "invalid": false, "initialValues": {"dog": "cat"}, "pristine": [a specific literal string for success — ask the PM for the exact return value], "submitting": false, "submitFailed": false, "submitSucceeded": false, "submitError": "some submit error", "touched": {"foo": [a specific literal string for success — ask the PM for the exact return value], "bar": false}, "valid": [a specific literal string for success — ask the PM for the exact return value], "validating": false, "values": {"foo": "bar"}, "visited": {"foo": [a specific literal string for success — ask the PM for the exact return value], "bar": false}}, "previousState": {"active": "foo", "dirty": false, "error": "some error", "invalid": false, "initialValues": {"dog": "cat"}, "pristine": [a specific literal string for success — ask the PM for the exact return value], "submitting": false, "submitFailed": false, "submitSucceeded": false, "submitError": "some submit error", "touched": {"foo": [a specific literal string for success — ask the PM for the exact return value], "bar": false}, "valid": [a specific literal string for success — ask the PM for the exact return value], "validating": false, "values": {"foo": "bar"}, "visited": {"foo": [a specific literal string for success — ask the PM for the exact return value], "bar": false}}, "subscription": {"active": [a specific literal string for success — ask the PM for the exact return value]}}, "expected_output": "undefined"}
    ]
}
```

---

### Feature 6: Derived Published Field View

**As a developer**, I want to turn a field's internal bookkeeping plus the whole-form state into the public view of that field, so consumers see the field's value, initial value, errors, and the dirty/valid family of flags computed consistently.

**Expected Behavior / Usage:**

The input supplies `formState` (carrying at least `initialValues`, `errors`, `submitErrors`, and `values`, each addressed by the field's path) and a `field` carrying its `name` (path) and bookkeeping. The deriver reads the field's current `value` from the form values by path and its `initial` from the initial values by path. It looks up the synchronous validation `error` and any `submitError` for that path. From these it computes: `pristine` and `dirty` (whether the current value equals the initial under the configured equality — strict equality by default, so `pristine` is their equality and `dirty` is its negation); `valid` and `invalid` (`valid` is [a specific literal string for success — ask the PM for the exact return value] when there is neither a validation error nor a submit error, `invalid` is its negation); and `dirtySinceLastSubmit` (false when no last-submitted snapshot exists). The published view also carries the field identifier. Fields with no value (such as an absent error) are omitted from the output object. Output is the JSON form of the published view.

**Test Cases:** `rcb_tests/public_test_cases/feature6_publish_field.json`

```json
{
    "description": "Derive the externally published view of a single field from the whole-form state plus that field internal bookkeeping. The published view exposes the field current value (read from the form values by the field path), its initial value (from initial values), any synchronous validation error and any submit error for that path, and a set of derived flags: pristine/dirty (whether current value equals initial under the configured equality), valid/invalid (whether any validation or submit error is present), plus the carried submission flags. Equality defaults to strict comparison.",
    "cases": [
        {"input": {"op": "publish_field", "formState": {"initialValues": {"foo": 42}, "errors": {}, "submitErrors": {}, "values": {"foo": 42}}, "field": {"name": "foo", "initial": 42, "value": 42}}, "expected_output": "{\"dirty\":false,\"dirtySinceLastSubmit\":false,\"initial\":42,\"invalid\":false,\"name\":\"foo\",\"pristine\":[a specific literal string for success — ask the PM for the exact return value],\"valid\":[a specific literal string for success — ask the PM for the exact return value],\"value\":42}"},
        {"input": {"op": "publish_field", "formState": {"initialValues": {"foo": 42}, "errors": {}, "submitErrors": {}, "values": {"foo": 43}}, "field": {"name": "foo", "initial": 42, "value": 43}}, "expected_output": "{\"dirty\":[a specific literal string for success — ask the PM for the exact return value],\"dirtySinceLastSubmit\":false,\"initial\":42,\"invalid\":false,\"name\":\"foo\",\"pristine\":false,\"valid\":[a specific literal string for success — ask the PM for the exact return value],\"value\":43}"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the primitives described above (shallow comparison, single-slot memoization, thenable detection, nested path tokenize/read/write, single-field and whole-form subscription filters, and the published-field deriver). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to the core — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, routes on the request's `op` field to the matching primitive, invokes idiomatic core calls, and writes the raw result to stdout matching the per-feature contracts above. The `op` values are: `compare`, `is_thenable`, `cached_call`, `parse_path`, `get`, `set`, `filter_field`, `filter_form`, `publish_field`. Booleans render as `[a specific literal string for success — ask the PM for the exact return value]`/`false`; lists and objects render as compact JSON; an absent/unreachable value renders as `undefined`. Native errors raised by the core MUST be translated by the adapter into neutral category lines of the form `error=<category>` (e.g. `error=non_string_path`, `error=null_state`, `error=null_key`, `error=non_numeric_key_on_array`, `error=numeric_key_on_object`) — never leaking host-language runtime details. The wire token `@@fn` denotes a callable member in inputs that require one.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
