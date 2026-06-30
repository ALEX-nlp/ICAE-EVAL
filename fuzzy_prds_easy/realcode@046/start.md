## Product Requirement Document

# Observable Store — A Proxy-Backed Reactive State Container

## Project Goal

Build a small state-management library centered on a single **observable store object**. Application code reads and writes ordinary properties on this object — at any depth — and the library transparently tracks every change: it records the precise path that changed, hands the application an updated store, and notifies subscribers. The library must do this without the application ever calling explicit "set" or "commit" APIs: plain property assignment, deletion, and reading are the entire surface.

---

## Background & Problem

State containers usually force a trade-off. Either the application mutates plain objects freely (cheap and ergonomic, but nothing observes the changes), or it routes every change through verbose action/reducer ceremony (observable, but noisy and easy to get wrong). Developers end up hand-writing change detection, manually cloning nested structures to avoid accidental shared mutation, and threading "what changed" information through their own code.

This library removes that trade-off. The store behaves like an ordinary nested object: assign to a property and the value is there; read it back and you get the latest value; delete a property and it is gone. Underneath, every read, write, and delete is intercepted. Writes produce a **new** store in which only the affected path has been rebuilt and everything else is reused by reference (structural sharing), and every write or delete is reported to subscribers as the human-readable path that changed. Reads always observe the most recent value.

The core abstraction is therefore a transparently observed object tree supporting: assignment (including creating new nested properties), deletion, deep navigation, ordered change reporting, structural sharing on update, array element/length semantics, and wholesale replacement of the store's contents while preserving the store object's own identity.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized single-file solution is acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (interception/proxying, path bookkeeping, immutable update with structural sharing, subscription/notification), it MUST NOT be a single "god file". Output a clear, multi-file directory tree that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain (proxy interception, an immutable updater, path utilities, and a notification registry) is naturally multi-file.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases below are a **black-box testing contract** for an execution adapter, NOT the internal data model of the core. The core logic must be completely decoupled from standard I/O (stdin/stdout) and JSON parsing. A thin execution adapter is solely responsible for translating JSON requests into idiomatic calls on the store and rendering the observed behaviour to the line-based output contract.

3. **Adherence to SOLID Design Principles** (scaled to the project's size): single-responsibility modules for interception, updating, path handling, and notification; new behaviours added without rewriting existing ones; small cohesive interfaces; high-level logic depending on abstractions rather than concrete internals.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language. The store must read and write like an ordinary nested object/collection.
   - **Resilience:** Handle edge cases gracefully — deep creation of new properties, deletion of present and absent keys, growing arrays, replacement of the whole store, and attempts to navigate through non-navigable values.

---

## Output Contract (shared by all features)

The execution adapter reads one JSON request from input, drives the store, and renders the observed behaviour as lines of text, in this fixed order:

- For every read request, one line `get <dotted.path> = <v>`, in request order, where `<v>` is the JSON encoding of the value read (objects rendered with keys in sorted order; an absent value rendered as `null`).
- Exactly one line `changes=<arr>`, where `<arr>` is the JSON array of the dotted paths reported to the change subscriber, in the order the changes occurred (one entry per write or delete; repeats are not collapsed).
- For every identity probe, one line `identity <dotted.path> = preserved|replaced`, reporting whether the sub-object at that path kept its reference across the mutations (`preserved`) or was rebuilt (`replaced`).
- One line `snapshot=<v>` with the final store contents (object keys in sorted order; arrays in index order).
- On any operation that cannot be resolved, exactly one line `error=<category>` and nothing else.

All paths are rendered rooted at the store, e.g. `store`, `store.user`, `store.user.address.city`, `store.items.2`.

### Request shape

A request is an object with:
- `init` (optional): the initial contents the store is seeded with before observation begins.
- `ops`: an ordered list of operations, each one of:
  - `{"op": "set", "path": [...], "value": <any>}` — assign `value` at the property path.
  - `{"op": "delete", "path": [...]}` — remove the property at the path.
  - `{"op": "get", "path": [...]}` — read the value at the path.
  - `{"op": "replace", "value": {...}}` — replace the whole store contents.
- `identity` (optional): a list of property paths to probe for structural sharing.
- `snapshot` (optional, default true): whether to emit the final snapshot line.

Path segments are property names or array indices; a path with a single segment refers to a top-level property.

---

## Core Features

### Feature 1: Observable Reads and Writes

Assigning to a top-level property stores the value; reading returns the latest value; each assignment is reported as the changed path.

```json
{"init": {}, "ops": [{"op": "set", "path": ["count"], "value": 1}, {"op": "set", "path": ["name"], "value": "ada"}, {"op": "get", "path": ["count"]}, {"op": "get", "path": ["name"]}]}
```
Output:
```
get store.count = 1
get store.name = "ada"
changes=["store.count","store.name"]
snapshot={"count":1,"name":"ada"}
```

### Feature 2: Deep Nested Updates

A write may target a property nested several levels deep, overwriting an existing value or introducing a new one next to existing siblings. The reported path identifies the exact nested location.

```json
{"init": {"user": {"name": "ada", "address": {"city": "london"}}}, "ops": [{"op": "set", "path": ["user", "address", "city"], "value": "paris"}, {"op": "get", "path": ["user", "address", "city"]}]}
```
Output:
```
get store.user.address.city = "paris"
changes=["store.user.address.city"]
snapshot={"user":{"address":{"city":"paris"},"name":"ada"}}
```

### Feature 3: Property Deletion

A property can be removed at the top level or nested; afterwards it is absent while siblings remain, and the removal is reported as the deleted path.

```json
{"init": {"a": 1, "b": 2}, "ops": [{"op": "delete", "path": ["a"]}]}
```
Output:
```
changes=["store.a"]
snapshot={"b":2}
```

### Feature 4: Structural Sharing on Update

Updating a nested property rebuilds only the objects on the path from the root to the change; every off-path sub-tree keeps its original reference. An identity probe reports each ancestor of the change as `replaced` and untouched siblings as `preserved`.

```json
{"init": {"a": {"x": 1}, "b": {"y": 2}, "list": [1, 2]}, "ops": [{"op": "set", "path": ["a", "x"], "value": 99}], "identity": [["a"], ["b"], ["list"]]}
```
Output:
```
changes=["store.a.x"]
identity store.a = replaced
identity store.b = preserved
identity store.list = preserved
snapshot={"a":{"x":99},"b":{"y":2},"list":[1,2]}
```

### Feature 5: Array Operations

Arrays are observed like objects: assigning to an existing index replaces an element; assigning to the index one past the end appends and grows the length; object elements participate in structural sharing. The changed path's final segment is the element index.

```json
{"init": {"items": [10, 20, 30]}, "ops": [{"op": "set", "path": ["items", 1], "value": 99}, {"op": "get", "path": ["items"]}]}
```
Output:
```
get store.items = [10,99,30]
changes=["store.items.1"]
snapshot={"items":[10,99,30]}
```

### Feature 6: Ordered Change Notification

Every mutation is reported in the order applied; repeated changes to the same property are each reported (not collapsed); assignments and deletions interleave in order.

```json
{"init": {"a": 0, "b": 0, "c": 0}, "ops": [{"op": "set", "path": ["b"], "value": 2}, {"op": "set", "path": ["a"], "value": 1}, {"op": "set", "path": ["c"], "value": 3}, {"op": "set", "path": ["a"], "value": 9}]}
```
Output:
```
changes=["store.b","store.a","store.c","store.a"]
snapshot={"a":9,"b":2,"c":3}
```

### Feature 7: Invalid Path Handling

An operation that must step through a non-existent parent, or read a property of a primitive as though it were an object, cannot be resolved and yields a single neutral error category.

```json
{"init": {"a": 1}, "ops": [{"op": "set", "path": ["missing", "deep"], "value": 1}]}
```
Output:
```
error=invalid_path
```

### Feature 8: Wholesale Replacement

The store's entire contents can be replaced while preserving the store object's own identity: all current properties are removed and the replacement's properties installed. Removals are reported first, then additions.

```json
{"init": {"old1": 1, "old2": 2}, "ops": [{"op": "replace", "value": {"new1": 10, "new2": 20}}]}
```
Output:
```
changes=["store.old1","store.old2","store.new1","store.new2"]
snapshot={"new1":10,"new2":20}
```

---

## Notes for Implementers

- The store object's own identity is stable across replacement; applications may hold a long-lived reference to it.
- Reads always reflect the most recent write, including writes performed outside of any subscription callback.
- The illustrative cases above are a readable subset; the authoritative, exhaustive set of behavioural cases is provided separately to the evaluation harness.


---
**Implementation notes:**
- follow the same array growth and validation logic as the array utilities module
- report the diff following the standard convention used in the diff_reporter
