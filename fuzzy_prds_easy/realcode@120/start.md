## Product Requirement Document

# Declarative REST State Engine - Input/Output Contract

## Project Goal

Build a declarative REST state engine that lets developers describe a set of named HTTP endpoints once and receive, for each one, a ready-made action creator and a state reducer that together drive the complete request lifecycle (begin → success/failure → reset). The goal is to let developers wire remote resources into a predictable, observable client-side store without hand-writing fetch boilerplate, lifecycle bookkeeping, or URL assembly for every endpoint.

---

## Background & Problem

Without this engine, developers manually repeat the same ceremony for every remote resource: build the URL from a template and a bag of parameters, flip a "loading" flag, fire the request, branch on success vs. failure, transform the payload, store it, clear the flag, and remember whether the resource has already been fetched. This is repetitive, error-prone, and inconsistent across a codebase — every screen reinvents slightly different lifecycle handling, and cross-cutting concerns (auth headers, pre-request hooks, validation, response logging) get copy-pasted.

With this engine, a developer declares endpoints as data (a name mapped to a URL template, optionally with per-endpoint options) and the engine emits the action creators and reducers. Dispatching an endpoint's action runs the full lifecycle and emits a small, well-defined stream of state-transition events; the matching reducer folds those events into an immutable per-endpoint slice. Shared behavior (root URL prefixing, global request options, validation, pre-request hooks, response handling, CRUD verb shortcuts, request chaining) is configured declaratively instead of re-implemented.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility library (URL assembly, value utilities, lifecycle reducer, action lifecycle orchestration, transport adapter, request chaining). It MUST be organized as a multi-file repository with clear separation between the pure utilities, the lifecycle/reducer core, the action orchestration layer, and the transport adapter. Do not collapse it into a single file; equally, do not over-engineer the small pure utilities.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below describe a **black-box execution contract** for a thin adapter, NOT the internal data model. The core engine must know nothing about stdin/stdout or JSON; it exposes idiomatic functions/objects. A separate execution adapter translates each JSON command into idiomatic calls and renders results to stdout.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units (SRP). The lifecycle engine must be open for extension (custom transformer, validation, pre/post hooks, custom reducer) but closed for modification (OCP). Interchangeable hooks (transport adapter, transformer, validation) must be substitutable (LSP). Keep hook interfaces small (ISP). High-level orchestration depends on an injected transport abstraction, not a concrete HTTP client (DIP).

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic. Edge cases (empty/missing params, unfilled placeholders, already-synced resources, double dispatch, aborted requests) must be handled gracefully. Errors must be modeled as distinct, observable outcomes rather than silent failures, and surfaced through a neutral, language-independent error contract (a category plus structured fields) — never by leaking host runtime exception identities.

---

## Core Features

### Feature 1: Value-Shaping Utilities

**As a developer**, I want a small set of pure helpers to merge, prune, read, and normalize plain data, so I can prepare request/response payloads predictably without pulling in a heavy utility library.

**Expected Behavior / Usage:**

This feature is a group of independent pure functions. Each leaf below describes one function: its input shape, its output shape, and its edge cases. All of them are deterministic and free of side effects.

*1.1 Deep Merge — combine a sequence of values into one*

Merge an ordered list of values left-to-right into a single result. Plain objects are merged key-by-key and recursively (nested objects deep-merge). When an earlier value and a later value collide on a non-object scalar, the later value wins. If either side of a pair is a list, the result is the concatenation (an earlier scalar followed by a later list becomes a list with the scalar first; an earlier list followed by a later scalar appends the scalar). An absent (undefined) operand is skipped so it never overwrites a present value. The output line is `result=<json>` where `<json>` is the merged value rendered as compact JSON with object keys sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_deep_merge.json`

```json
{
  "description": "Recursively merge a sequence of values into one. Plain objects merge key-by-key (deeply); a later array concatenates onto an earlier value; for scalar conflicts the last value wins; undefined operands are skipped so an absent value never overwrites a present one.",
  "cases": [
    {"input": {"op": "deep_merge", "args": [{"a": 1}, {"b": 2}, {"c": 3}]}, "expected_output": "result={\"a\":1,\"b\":2,\"c\":3}\n"},
    {"input": {"op": "deep_merge", "args": [{"a": {"b": 1}}, {"a": {"c": 2}}]}, "expected_output": "result={\"a\":{\"b\":1,\"c\":2}}\n"},
    {"input": {"op": "deep_merge", "args": [{"id": [1, 2]}, {"id": 3}]}, "expected_output": "result={\"id\":[1,2,3]}\n"},
    {"input": {"op": "deep_merge", "args": [{"id": 3}, {"id": [1, 2]}]}, "expected_output": "result={\"id\":[3,1,2]}\n"}
  ]
}
```

*1.2 Exclude Keys — shallow copy minus named properties*

Produce a new shallow copy of an object with a given list of property names removed. With no name list (or an empty list) the result is a fresh object equal in content to the input (a copy, never the same reference). Names that are not present in the input are ignored. Output line: `result=<json>` with sorted keys.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_exclude_keys.json`

```json
{
  "description": "Produce a shallow copy of an object while dropping a given list of property names. With no name list (or an empty list) the result is a brand-new object equal in content to the input; names that are not present are simply ignored.",
  "cases": [
    {"input": {"op": "exclude_keys", "object": {"a": 1, "b": 2, "c": 3}}, "expected_output": "result={\"a\":1,\"b\":2,\"c\":3}\n"},
    {"input": {"op": "exclude_keys", "object": {"a": 1, "b": 2, "c": 3}, "props": ["a", "b"]}, "expected_output": "result={\"c\":3}\n"},
    {"input": {"op": "exclude_keys", "object": {"a": 1, "b": 2, "c": 3}, "props": ["a", "b", "d"]}, "expected_output": "result={\"c\":3}\n"}
  ]
}
```

*1.3 Read Path — safe nested lookup*

Read a value from a nested object by walking an ordered list of keys. Empty [a complex path segment pattern (e.g., /api/v{version}/users)] segments (empty string, null) are skipped rather than dereferenced, so they act as no-ops in the walk. If the [a complex path segment pattern (e.g., /api/v{version}/users)] cannot be fully resolved, the result is absent (rendered as `null`). Output line: `result=<json>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_read_[a complex path segment pattern (e.g., /api/v{version}/users)].json`

```json
{
  "description": "Safely read a value from a nested object by walking an ordered [a complex path segment pattern (e.g., /api/v{version}/users)] of keys. Empty [a complex path segment pattern (e.g., /api/v{version}/users)] segments (empty string, null, undefined) are skipped rather than dereferenced. A [a complex path segment pattern (e.g., /api/v{version}/users)] that does not exist yields no value (null).",
  "cases": [
    {"input": {"op": "read_[a complex path segment pattern (e.g., /api/v{version}/users)]", "object": {"a": {"b": {"c": 2}}}, "[a complex path segment pattern (e.g., /api/v{version}/users)]": ["a", "b", "c"]}, "expected_output": "result=2\n"},
    {"input": {"op": "read_[a complex path segment pattern (e.g., /api/v{version}/users)]", "object": {"a": {"b": {"c": {"0": 2}}}}, "[a complex path segment pattern (e.g., /api/v{version}/users)]": ["", "a", null, "b", null, "c", 0]}, "expected_output": "result=2\n"},
    {"input": {"op": "read_[a complex path segment pattern (e.g., /api/v{version}/users)]", "object": {"a": {"b": {"c": 2}}}, "[a complex path segment pattern (e.g., /api/v{version}/users)]": ["c", "b", "a"]}, "expected_output": "result=null\n"}
  ]
}
```

*1.4 Normalize To Collection — coerce a response into a list*

Coerce any response value into a list shape. A missing/empty value becomes an empty list; an existing list passes through unchanged; any single non-list value is wrapped in a one-element list. Output line: `result=<json>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_normalize_collection.json`

```json
{
  "description": "Coerce a server response into a list shape. A missing/empty value becomes an empty list; an existing list is returned unchanged; any single non-list value is wrapped in a one-element list.",
  "cases": [
    {"input": {"op": "normalize_collection"}, "expected_output": "result=[]\n"},
    {"input": {"op": "normalize_collection", "data": {"id": 1}}, "expected_output": "result=[{\"id\":1}]\n"},
    {"input": {"op": "normalize_collection", "data": [1]}, "expected_output": "result=[1]\n"}
  ]
}
```

*1.5 Normalize To Record — coerce a response into an object*

Coerce any response value into a record (object) shape. A missing/empty value becomes an empty object; an existing plain object passes through unchanged; any other value (list, string, number, boolean) is wrapped under a single `data` field. Output line: `result=<json>` with sorted keys.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_normalize_record.json`

```json
{
  "description": "Coerce a server response into a record (object) shape. A missing/empty value becomes an empty object; an existing plain object is returned unchanged; any other value (list, string, number, boolean) is wrapped under a single `data` field.",
  "cases": [
    {"input": {"op": "normalize_record"}, "expected_output": "result={}\n"},
    {"input": {"op": "normalize_record", "data": {"id": 1}}, "expected_output": "result={\"id\":1}\n"},
    {"input": {"op": "normalize_record", "data": [1]}, "expected_output": "result={\"data\":[1]}\n"},
    {"input": {"op": "normalize_record", "data": "test"}, "expected_output": "result={\"data\":\"test\"}\n"}
  ]
}
```

---

### Feature 2: URL Template Assembly

**As a developer**, I want to turn a URL template plus a bag of parameters into a final URL, so that [a complex path segment pattern (e.g., /api/v{version}/users)] variables, optional segments, and leftover query parameters are all handled by one consistent rule set.

**Expected Behavior / Usage:**

A template may contain named placeholders written as `:name` (required) or `(:name)` (optional). The assembler substitutes any placeholder whose name appears in the supplied params (replacing every occurrence), strips any placeholder that was never supplied, and appends params that did not match any placeholder as a query string. Output line is `url=<final-url>`. Each leaf below covers one facet.

*2.1 Placeholder Substitution — fill or omit named segments*

A null/empty template yields an empty string. A template with no placeholders is returned unchanged. A supplied placeholder value is substituted everywhere the placeholder appears. Both `:name` and `(:name)` forms are accepted.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_url_placeholders.json`

```json
{
  "description": "Substitute named placeholders in a URL template with provided values. A placeholder is written as `:name` (required) or `(:name)` (optional). A null/empty template yields an empty string; a template with no params is returned unchanged; the same placeholder may appear multiple times and is replaced everywhere.",
  "cases": [
    {"input": {"op": "build_url"}, "expected_output": "url=\n"},
    {"input": {"op": "build_url", "template": "/test"}, "expected_output": "url=/test\n"},
    {"input": {"op": "build_url", "template": "/test/:id", "params": {"id": 1}}, "expected_output": "url=/test/1\n"},
    {"input": {"op": "build_url", "template": "/test/:id/hey/:id", "params": {"id": 1}}, "expected_output": "url=/test/1/hey/1\n"},
    {"input": {"op": "build_url", "template": "/test/(:id)", "params": {"id": 1}}, "expected_output": "url=/test/1\n"}
  ]
}
```

*2.2 Absolute URLs — preserve scheme, host and existing query*

When the template includes a scheme and host, the scheme, host and any pre-existing query string are preserved verbatim while placeholders inside the [a complex path segment pattern (e.g., /api/v{version}/users)] are substituted.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_url_hostname.json`

```json
{
  "description": "URL templates that include a scheme and host keep the scheme, host and any existing query string intact while placeholders inside the [a complex path segment pattern (e.g., /api/v{version}/users)] are substituted.",
  "cases": [
    {"input": {"op": "build_url", "template": "http://localhost:1234/test/:id", "params": {"id": 1}}, "expected_output": "url=http://localhost:1234/test/1\n"},
    {"input": {"op": "build_url", "template": "http://localhost:1234/test/:id/hey/:id?hello=1", "params": {"id": 1}}, "expected_output": "url=http://localhost:1234/test/1/hey/1?hello=1\n"}
  ]
}
```

*2.3 Strip Unfilled Placeholders — clean leftover segments*

Placeholders never supplied a value are removed from the [a complex path segment pattern (e.g., /api/v{version}/users)], leaving a clean URL. Both required and optional forms are stripped.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_url_clean_unused.json`

```json
{
  "description": "Placeholders that are never supplied a value are stripped from the [a complex path segment pattern (e.g., /api/v{version}/users)], leaving a clean URL. Both required `:name` and optional `(:name)` forms are removed when no matching param is given.",
  "cases": [
    {"input": {"op": "build_url", "template": "/test/:id"}, "expected_output": "url=/test/\n"},
    {"input": {"op": "build_url", "template": "/test/:id/"}, "expected_output": "url=/test//\n"},
    {"input": {"op": "build_url", "template": "/test/(:id)"}, "expected_output": "url=/test/\n"}
  ]
}
```

*2.4 Leftover Params As Query — append unmatched params*

Params that do not match any placeholder are appended to the URL as a query string. Any query parameters already present in the template are preserved, and the leftover params are merged in after them.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_url_leftover_query.json`

```json
{
  "description": "Params that do not match any placeholder in the template are appended to the URL as a query string. Existing query parameters in the template are preserved and the leftover params are merged in after them.",
  "cases": [
    {"input": {"op": "build_url", "template": "/test/(:id)", "params": {"id1": 1}}, "expected_output": "url=/test/?id1=1\n"},
    {"input": {"op": "build_url", "template": "/test/?hello=1&(:id)", "params": {"id1": 1}}, "expected_output": "url=/test/?hello=1&id1=1\n"},
    {"input": {"op": "build_url", "template": "/test/?hello=2(:id)", "params": {"id1": 1}}, "expected_output": "url=/test/?hello=2&id1=1\n"}
  ]
}
```

*2.5 Array Param Formatting — repeat keys and custom delimiter*

Array-valued leftover params are serialized using supplied formatting options: an array format (e.g. repeating the key for each element) and a custom delimiter between pairs. The same options govern how an existing query string in the template is parsed before being re-merged with new array values.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_url_array_format.json`

```json
{
  "description": "Array-valued leftover params are serialized into the query string according to supplied formatting options: an array format (e.g. repeating the key) and a custom delimiter between pairs. Options also control how a pre-existing query string in the template is parsed and re-merged with new array values.",
  "cases": [
    {"input": {"op": "build_url", "template": "/test", "params": {"id": [1, 2]}, "options": {"arrayFormat": "repeat", "delimiter": ";"}}, "expected_output": "url=/test?id=1;id=2\n"},
    {"input": {"op": "build_url", "template": "/test?id=1", "params": {"id": [2, 3]}, "options": {"arrayFormat": "repeat", "delimiter": ";"}}, "expected_output": "url=/test?id=1;id=2;id=3\n"},
    {"input": {"op": "build_url", "template": "/test?id=1;id=2", "params": {"id": [2, 3]}, "options": {"arrayFormat": "repeat", "delimiter": ";"}}, "expected_output": "url=/test?id=1;id=2;id=2;id=3\n"}
  ]
}
```

*2.6 Independent Parse vs. Stringify Options — asymmetric encoding*

A parse-format option controls how an existing bracketed query string in the template is interpreted, while a separate stringify-format option controls how outgoing array params are encoded; the two are independent. When no stringify override is given, the default bracket-indexed encoding is used (URL-encoded brackets).

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_url_parse_stringify_options.json`

```json
{
  "description": "Independent parse and stringify options can be supplied. A parse-format option controls how an existing bracketed query string in the template is interpreted, while a separate stringify-format option controls how outgoing array params are encoded; when no stringify override is given the default bracket-indexed encoding is used (URL-encoded brackets).",
  "cases": [
    {"input": {"op": "build_url", "template": "/t?id[0]=1&id[1]=2", "params": {"a": 0}, "options": {"arrayFormat": "repeat", "qsParseOptions": {"arrayFormat": "indices"}}}, "expected_output": "url=/t?id=1&id=2&a=0\n"},
    {"input": {"op": "build_url", "template": "/test", "params": {"id": [1, 2]}, "options": {}}, "expected_output": "url=/test?id%5B0%5D=1&id%5B1%5D=2\n"},
    {"input": {"op": "build_url", "template": "/test", "params": {"id": [1, 2]}, "options": {"arrayFormat": "brackets", "qsStringifyOptions": {"arrayFormat": "repeat"}}}, "expected_output": "url=/test?id=1&id=2\n"}
  ]
}
```

---

### Feature 3: Request Lifecycle Reducer

**As a developer**, I want a reducer that folds lifecycle events into an immutable per-resource state slice, so the UI can read loading/error/sync flags and data without me writing state transitions by hand.

**Expected Behavior / Usage:**

The reducer is built from an initial state and four phase event identifiers. Given a current state and an event, it returns the next immutable state. The output line is `state=<json>` with sorted keys. The current state is never mutated in place.

*3.1 Phase Transitions — begin/success/failure/reset*

The `fetch` phase sets `loading` true, clears any `error`, and records a `syncing` flag (whether this is a background sync). The `success` phase clears `loading`, sets `sync` true, clears `syncing` and `error`, and stores the returned `data`. The `fail` phase clears `loading` and `syncing` and records the `error`, keeping previous `data`. The `reset` phase returns a fresh copy of the initial state.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_lifecycle_phases.json`

```json
{
  "description": "A request lifecycle reducer maps four phase events onto an immutable state object. The `fetch` phase sets loading true, clears any error and records whether the request is a background sync; `success` clears loading, marks sync true and stores the returned data; `fail` clears loading and records the error while keeping previous data; `reset` returns a fresh copy of the initial state. The initial state is never mutated in place.",
  "cases": [
    {"input": {"op": "reduce_state", "initialState": {"loading": false, "data": {"msg": "Hello"}}, "action": {"type": "fetch"}}, "expected_output": "state={\"data\":{\"msg\":\"Hello\"},\"error\":null,\"loading\":true,\"syncing\":false}\n"},
    {"input": {"op": "reduce_state", "initialState": {"loading": false, "data": {"msg": "Hello"}}, "action": {"type": "success", "data": true}}, "expected_output": "state={\"data\":true,\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\n"},
    {"input": {"op": "reduce_state", "initialState": {"loading": false, "data": {"msg": "Hello"}}, "action": {"type": "fail", "error": "Error"}}, "expected_output": "state={\"data\":{\"msg\":\"Hello\"},\"error\":\"Error\",\"loading\":false,\"syncing\":false}\n"},
    {"input": {"op": "reduce_state", "initialState": {"loading": false, "data": {"msg": "Hello"}}, "action": {"type": "reset"}}, "expected_output": "state={\"data\":{\"msg\":\"Hello\"},\"loading\":false}\n"}
  ]
}
```

*3.2 Reset Variants & Unknown Events — soft reset and pass-through*

A plain reset restores the full initial state, while a soft `sync` reset clears only the `sync` flag and preserves the currently stored data. An event whose type matches no known phase leaves the state untouched (returns the same state).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_reset_variants.json`

```json
{
  "description": "The reset phase has two flavors. A plain reset restores the full initial state. A `sync` reset is a soft reset that only clears the synced flag while preserving the currently stored data. An action whose type matches no known phase leaves the state untouched.",
  "cases": [
    {"input": {"op": "reduce_state", "initialState": {"sync": true, "loading": false, "data": {"msg": "Hello"}}, "action": {"type": "reset", "mutation": "sync"}}, "expected_output": "state={\"data\":{\"msg\":\"Hello\"},\"loading\":false,\"sync\":false}\n"},
    {"input": {"op": "reduce_state", "initialState": {"loading": false, "data": {"msg": "Hello"}}, "action": {"type": "unrelated"}}, "expected_output": "state={\"data\":{\"msg\":\"Hello\"},\"loading\":false}\n"}
  ]
}
```

---

### Feature 4: Lifecycle Coordination Primitives

**As a developer**, I want small coordination primitives for one-shot request bookkeeping, so concurrent callers, single in-flight requests, and ordered pre-request hooks behave predictably.

**Expected Behavior / Usage:**

These are independent building blocks used by the orchestration layer. Each leaf below is a self-contained primitive driven by a small script of operations and reporting its observable effects line by line.

*4.1 Single-Slot Holder — at most one in-flight value*

A holder stores at most one value. The first `set` succeeds (`set accepted=true`); further `set` calls are rejected (`set accepted=false`) until the slot is drained. `empty` reports whether the slot currently holds a value. `pop` removes and returns the held value and empties the slot; popping an empty slot yields no value (`pop=null`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_single_slot_holder.json`

```json
{
  "description": "A single-slot holder stores at most one value. The first `set` succeeds (accepted); subsequent `set` calls are rejected until the slot is drained. `empty` reports whether the slot currently holds a value. `pop` removes and returns the held value (and empties the slot); popping an empty slot yields no value.",
  "cases": [
    {"input": {"op": "single_slot", "operations": [{"do": "empty"}, {"do": "pop"}]}, "expected_output": "empty=true\npop=null\n"},
    {"input": {"op": "single_slot", "operations": [{"do": "empty"}, {"do": "set", "value": {"ptr": 1}}, {"do": "empty"}, {"do": "set", "value": 1}, {"do": "set", "value": null}, {"do": "pop"}, {"do": "empty"}]}, "expected_output": "empty=true\nset accepted=true\nempty=false\nset accepted=false\nset accepted=false\npop={\"ptr\":1}\nempty=true\n"}
  ]
}
```

*4.2 One-Shot Subscriber Registry — notify all once, then clear*

A registry collects callbacks and later notifies all of them exactly once, then empties itself. Only callable subscribers are stored (non-callable pushes are ignored). On `resolve`, each subscriber is invoked with a null error and the payload as data; on `reject`, each is invoked with the payload as the error. After notification, zero subscribers remain. Output reports the registered count, one line per notified subscriber, and the remaining count.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_subscriber_registry.json`

```json
{
  "description": "A one-shot subscriber registry collects callbacks and later notifies all of them exactly once, then empties itself. Only callable subscribers are stored (non-callable pushes are ignored). On `resolve` each subscriber is invoked with a null error and the payload as data; on `reject` each is invoked with the payload as the error. After notification the registry holds zero subscribers.",
  "cases": [
    {"input": {"op": "notify_subscribers", "subscribers": 2, "action": "reject", "payload": "err"}, "expected_output": "registered=2\nsubscriber index=0 err=\"err\"\nsubscriber index=1 err=\"err\"\nremaining=0\n"},
    {"input": {"op": "notify_subscribers", "subscribers": 2, "action": "resolve", "payload": "ok"}, "expected_output": "registered=2\nsubscriber index=0 err=null data=\"ok\"\nsubscriber index=1 err=null data=\"ok\"\nremaining=0\n"},
    {"input": {"op": "notify_subscribers", "subscribers": 1, "pushNonFunction": {"value": 42}, "action": "resolve", "payload": "ok"}, "expected_output": "registered=1\nsubscriber index=0 err=null data=\"ok\"\nremaining=0\n"}
  ]
}
```

*4.3 Ordered Pre-Request Hook Chain — run steps then continue*

An ordered list of asynchronous steps runs before the main work; the chain proceeds to the next step only after the current one signals completion, and fires a single final callback once every step has run. Starting at an index beyond the list, or with no steps configured, still fires the final callback immediately. Output reports each step in order and whether the final callback fired (`completed=true|false`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_prefetch_chain.json`

```json
{
  "description": "A pre-request hook chain runs an ordered list of asynchronous steps before the main work and only continues once each step signals completion; when every step has run (or there are no steps) the final callback fires once. Starting at an index beyond the list, or with no steps configured, still fires the final callback immediately.",
  "cases": [
    {"input": {"op": "run_prefetch_chain"}, "expected_output": "completed=true\n"},
    {"input": {"op": "run_prefetch_chain", "steps": 1, "hasCallback": false}, "expected_output": "prefetch index=0\ncompleted=false\n"},
    {"input": {"op": "run_prefetch_chain", "steps": 2}, "expected_output": "prefetch index=0\nprefetch index=1\ncompleted=true\n"},
    {"input": {"op": "run_prefetch_chain", "steps": 0}, "expected_output": "completed=true\n"}
  ]
}
```

---

### Feature 5: Endpoint Dispatch Lifecycle

**As a developer**, I want dispatching a declared endpoint to drive a full request lifecycle through the store, so the resulting action stream and per-endpoint state slice are predictable and observable.

**Expected Behavior / Usage:**

An endpoint is declared either as a bare URL string or as an object with a URL template and per-endpoint options. Dispatching its action runs the lifecycle against a store: it emits a namespaced begin action, then on a successful response a namespaced success action carrying both the transformed `data` and the original `origData`, and leaves the endpoint's state slice loaded and synced. Each action carries a request descriptor recording the [a complex path segment pattern (e.g., /api/v{version}/users)] variables and params. On failure a namespaced fail action is emitted instead, carrying a neutral error contract. In the output, every dispatched action is rendered as one `action ...` line and every resulting store slice as one `state <name>=<json>` line.

*5.1 String-URL Endpoint — minimal declaration*

An endpoint declared as a plain URL string with no [a complex path segment pattern (e.g., /api/v{version}/users)] variables: dispatch yields a begin action and a success action carrying the response, and the slice ends loaded and synced.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_dispatch_string_url.json`

```json
{
  "description": "Dispatching an endpoint action drives a full request lifecycle through the store. A namespaced fetch action is emitted first (loading begins), then on a successful response a namespaced success action carries both the transformed `data` and the original `origData`, and the endpoint's slice of the store ends in a loaded, synced state holding the response. Each action also carries a request descriptor ([a complex path segment pattern (e.g., /api/v{version}/users)]vars/params). The endpoint here is configured by a plain URL string with no [a complex path segment pattern (e.g., /api/v{version}/users)] variables.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": "/plain/url"}, "fetch": {"fixed": {"msg": "hello"}}, "calls": [{"endpoint": "test"}]}, "expected_output": "action type=@@redux-api@test syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null}\naction type=@@redux-api@test_success syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null} data={\"msg\":\"hello\"}\nstate test={\"data\":{\"msg\":\"hello\"},\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\n"}
  ]
}
```

*5.2 Object Endpoint With Path Variable — substitution + options*

An endpoint declared as an object with a templated [a complex path segment pattern (e.g., /api/v{version}/users)] and transport options: calling it with [a complex path segment pattern (e.g., /api/v{version}/users)] variables substitutes them into the routed URL, and the request descriptor records the supplied [a complex path segment pattern (e.g., /api/v{version}/users)] variables.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_dispatch_object_url.json`

```json
{
  "description": "An endpoint can be configured as an object with a URL template containing a [a complex path segment pattern (e.g., /api/v{version}/users)] variable plus per-request transport options (e.g. headers). Calling it with [a complex path segment pattern (e.g., /api/v{version}/users)] variables substitutes them into the routed URL, and the success action carries the response; the routed request descriptor records the supplied [a complex path segment pattern (e.g., /api/v{version}/users)] variables.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": {"url": "/plain/url/:id", "options": {"headers": {"Accept": "application/json"}}}}, "fetch": {"fixed": {"msg": "hello"}}, "calls": [{"endpoint": "test", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 1}}]}, "expected_output": "action type=@@redux-api@test syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":1}}\naction type=@@redux-api@test_success syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":1}} data={\"msg\":\"hello\"}\nstate test={\"data\":{\"msg\":\"hello\"},\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\n"}
  ]
}
```

*5.3 Failure Path — neutral error contract*

When the transport rejects, the lifecycle emits a begin action followed by a namespaced fail action whose error is normalized to a neutral category (`error=request_failed` with a `reason` field) rather than any host runtime type, and the slice ends with loading cleared while retaining previous data.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_dispatch_failure.json`

```json
{
  "description": "When the underlying transport rejects, the lifecycle emits a fetch action followed by a namespaced fail action. The error is normalized to a neutral category rather than exposing any host runtime type, and the endpoint's store slice ends with loading cleared while retaining its previous data.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": "/plain/url"}, "fetch": {"fail": "boom"}, "calls": [{"endpoint": "test"}]}, "expected_output": "action type=@@redux-api@test syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null}\naction type=@@redux-api@test_fail syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null} error=request_failed reason=boom\nstate test={\"data\":{},\"error\":{},\"loading\":false,\"sync\":false,\"syncing\":false}\n"}
  ]
}
```

*5.4 Root URL Prefixing — join relative [a complex path segment pattern (e.g., /api/v{version}/users)]s to a base*

A configured root URL is prepended to each endpoint's relative [a complex path segment pattern (e.g., /api/v{version}/users)] to form the final routed URL: relative [a complex path segment pattern (e.g., /api/v{version}/users)]s join to the root's [a complex path segment pattern (e.g., /api/v{version}/users)] (collapsing duplicate slashes), an empty [a complex path segment pattern (e.g., /api/v{version}/users)] resolves to the root itself, and unfilled optional placeholders are stripped before joining. Output reports the routed URL reached by the transport for each call (`routed_url=...`).

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_root_url.json`

```json
{
  "description": "A configured root URL is prepended to each endpoint's relative [a complex path segment pattern (e.g., /api/v{version}/users)] to form the final routed URL. Relative [a complex path segment pattern (e.g., /api/v{version}/users)]s are joined to the root's [a complex path segment pattern (e.g., /api/v{version}/users)] (collapsing duplicate slashes), an empty [a complex path segment pattern (e.g., /api/v{version}/users)] resolves to the root itself, and unfilled optional placeholders are stripped before joining. This case routes several endpoints under one root and reports the resulting URLs reached by the transport.",
  "cases": [
    {"input": {"op": "route_urls", "endpoints": {"test1": "/url1/", "test2": "url2", "test3": "", "test4": "/(:id)"}, "fetch": {"fixed": {"msg": "hello"}}, "use": {"[a config object containing 'rootUrl' and 'path' fields]": "http://api.com/root"}, "calls": [{"endpoint": "test1"}, {"endpoint": "test2"}, {"endpoint": "test3"}, {"endpoint": "test4", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 1}}]}, "expected_output": "routed_url=http://api.com/root/url1/\nrouted_url=http://api.com/root/url2\nrouted_url=http://api.com/root/\nrouted_url=http://api.com/root/1\n"},
    {"input": {"op": "route_urls", "endpoints": {"test1": "/url1/", "test2": "url2", "test3": "", "test4": "/(:id)"}, "fetch": {"fixed": {"msg": "hello"}}, "use": {"[a config object containing 'rootUrl' and 'path' fields]": "http://api.ru/"}, "calls": [{"endpoint": "test1"}, {"endpoint": "test2"}, {"endpoint": "test3"}, {"endpoint": "test4", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 2}}]}, "expected_output": "routed_url=http://api.ru/url1/\nrouted_url=http://api.ru/url2\nrouted_url=http://api.ru/\nrouted_url=http://api.ru/2\n"}
  ]
}
```

---

### Feature 6: CRUD Verb Shortcuts, Endpoint Surface & Option Merging

**As a developer**, I want verb shortcuts and layered option merging on endpoints, so I can issue method-specific requests and combine global with per-endpoint transport options without restating them.

**Expected Behavior / Usage:**

This feature covers the composed shape of an endpoint and how its transport options are assembled.

*6.1 CRUD Verb Shortcuts — method-forcing aliases*

Enabling CRUD on an endpoint adds verb shortcuts (get/post/put/delete/patch). Each shortcut forwards its [a complex path segment pattern (e.g., /api/v{version}/users)] variables and body params while forcing the HTTP method; the request descriptor records the method (and body, when supplied). Dispatching all five produces a begin+success pair per verb, each carrying the forced method.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_crud_helpers.json`

```json
{
  "description": "Enabling CRUD helpers on an endpoint adds verb shortcuts (get/post/put/delete/patch). Each shortcut forwards its [a complex path segment pattern (e.g., /api/v{version}/users)] variables and body params to the transport while forcing the HTTP method, and the routed request descriptor records the method (and body when supplied). This case exercises all five verbs and reports the fetch lifecycle actions, including the method recorded on each request.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": {"url": "/test/:id", "crud": true}}, "fetch": "echo_url_opts", "calls": [{"endpoint": "test", "helper": "get", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 1}}, {"endpoint": "test", "helper": "post", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 2}, "params": {"body": "Hello"}}, {"endpoint": "test", "helper": "put", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 3}, "params": {"body": "World"}}, {"endpoint": "test", "helper": "delete", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 4}}, {"endpoint": "test", "helper": "patch", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 5}, "params": {"body": "World"}}]}, "expected_output": "action type=@@redux-api@test syncing=false request={\"params\":{\"method\":\"GET\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":1}}\naction type=@@redux-api@test_success syncing=false request={\"params\":{\"method\":\"GET\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":1}} data={\"opts\":{\"method\":\"GET\"},\"url\":\"/test/1\"}\naction type=@@redux-api@test syncing=false request={\"params\":{\"body\":\"Hello\",\"method\":\"POST\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":2}}\naction type=@@redux-api@test_success syncing=false request={\"params\":{\"body\":\"Hello\",\"method\":\"POST\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":2}} data={\"opts\":{\"body\":\"Hello\",\"method\":\"POST\"},\"url\":\"/test/2\"}\naction type=@@redux-api@test syncing=false request={\"params\":{\"body\":\"World\",\"method\":\"PUT\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":3}}\naction type=@@redux-api@test_success syncing=false request={\"params\":{\"body\":\"World\",\"method\":\"PUT\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":3}} data={\"opts\":{\"body\":\"World\",\"method\":\"PUT\"},\"url\":\"/test/3\"}\naction type=@@redux-api@test syncing=false request={\"params\":{\"method\":\"DELETE\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":4}}\naction type=@@redux-api@test_success syncing=false request={\"params\":{\"method\":\"DELETE\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":4}} data={\"opts\":{\"method\":\"DELETE\"},\"url\":\"/test/4\"}\naction type=@@redux-api@test syncing=false request={\"params\":{\"body\":\"World\",\"method\":\"PATCH\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":5}}\naction type=@@redux-api@test_success syncing=false request={\"params\":{\"body\":\"World\",\"method\":\"PATCH\"},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":5}} data={\"opts\":{\"body\":\"World\",\"method\":\"PATCH\"},\"url\":\"/test/5\"}\nstate test={\"data\":{\"opts\":{\"body\":\"World\",\"method\":\"PATCH\"},\"url\":\"/test/5\"},\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\n"}
  ]
}
```

*6.2 Endpoint Surface — stable callable members*

An endpoint exposes a stable set of callable members. With CRUD enabled it offers the five verb shortcuts plus the core controls for issuing a pure request, resetting state, and synced fetching, and it is backed by exactly one reducer slice under its name.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_endpoint_shape.json`

```json
{
  "description": "An endpoint exposes a stable set of callable members. With CRUD enabled it offers the five verb shortcuts plus the core controls for issuing a pure request, resetting state, and synced fetching; the endpoint is backed by exactly one reducer slice under its name.",
  "cases": [
    {"input": {"op": "endpoint_shape", "endpoints": {"test": {"url": "/test", "crud": true}}, "fetch": "echo_url", "endpoint": "test"}, "expected_output": "helpers=[\"delete\",\"get\",\"patch\",\"post\",\"put\",\"request\",\"reset\",\"sync\"]\nreducers=[\"test\"]\n"}
  ]
}
```

*6.3 Layered Option Merging — global plus per-endpoint*

Per-endpoint transport options merge with global options configured on the client. Static option objects deep-merge (global plus endpoint headers combine). When global options are supplied as a function, it receives the routed URL and params and returns options to merge; the per-call params are also merged into the final options handed to the transport.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_global_options.json`

```json
{
  "description": "Per-endpoint transport options are merged with global options configured on the client. Static option objects are deep-merged (global plus endpoint headers combined). When global options are supplied as a function, it receives the routed URL and params and returns options to merge; the per-call params themselves are also merged into the final options passed to the transport.",
  "cases": [
    {"input": {"op": "pure_request", "endpoints": {"test": {"url": "/api/test", "options": {"headers": {"X-Header": 1}}}}, "fetch": "echo_url_opts", "use": {"options": {"headers": {"Accept": "application/json"}}}, "endpoint": "test"}, "expected_output": "data={\"opts\":{\"headers\":{\"Accept\":\"application/json\",\"X-Header\":1}},\"url\":\"/api/test\"}\nfetch_count=1\n"},
    {"input": {"op": "pure_request", "endpoints": {"test": {"url": "/api/test/(:id)", "options": {"headers": {"X-Header": 1}}}}, "fetch": "echo_url_opts", "use": {"options": "fn:accept_header"}, "endpoint": "test", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 1}, "params": {"a": "b"}}, "expected_output": "data={\"opts\":{\"a\":\"b\",\"headers\":{\"Accept\":\"application/json\",\"X-Header\":1}},\"url\":\"/api/test/1\"}\nfetch_count=1\n"}
  ]
}
```

---

### Feature 7: Synced Fetch, Soft Reset & Pure Request

**As a developer**, I want fetch-once semantics, a soft reset, and a side-effect-free request, so I can avoid redundant network calls and read data directly when I do not need the lifecycle.

**Expected Behavior / Usage:**

These leaves cover the controls that govern when and how a request touches the store and the network.

*7.1 Synced Fetch — fetch only when not already synced*

A synced fetch hits the transport only when the endpoint's slice is not already marked synced. The first synced call against an unsynced slice runs a full lifecycle whose begin action carries the syncing flag, then success; the data ends stored in the slice.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_sync_fetch.json`

```json
{
  "description": "A synced fetch only hits the transport when the endpoint's store slice is not already marked synced. The first synced call against an unsynced slice performs a full fetch lifecycle (fetch action carries the syncing flag, then success); the data ends stored in the slice.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": "/api/url"}, "fetch": {"fixed": {"msg": "hello"}}, "calls": [{"endpoint": "test", "mode": "sync"}]}, "expected_output": "action type=@@redux-api@test syncing=true request={\"params\":{},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null}\naction type=@@redux-api@test_success syncing=false request={\"params\":{},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null} data={\"msg\":\"hello\"}\nstate test={\"data\":{\"msg\":\"hello\"},\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\n"}
  ]
}
```

*7.2 Soft Sync Reset — clear sync flag, keep data*

After a successful fetch leaves the slice synced with data, a soft `sync` reset clears only the sync flag while preserving the stored data (a reset event is emitted and the slice keeps its data).

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_reset_sync.json`

```json
{
  "description": "After a successful fetch leaves the slice synced with stored data, a soft `sync` reset clears only the synced flag while preserving the stored data, whereas a plain reset would restore the initial empty slice. This case fetches, then issues a soft sync reset, and reports the resulting slice.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": "/api/url"}, "fetch": "echo_url", "calls": [{"endpoint": "test"}, {"endpoint": "test", "mode": "reset", "mutation": "sync"}]}, "expected_output": "action type=@@redux-api@test syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null}\naction type=@@redux-api@test_success syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null} data={\"data\":\"/api/url\"}\naction type=@@redux-api@test_delete\nstate test={\"data\":{\"data\":\"/api/url\"},\"error\":null,\"loading\":false,\"sync\":false,\"syncing\":false}\n"}
  ]
}
```

*7.3 Pure Request — data without lifecycle*

A pure request returns the response data directly as a promise without dispatching any lifecycle action, substituting [a complex path segment pattern (e.g., /api/v{version}/users)] variables into the routed URL. Output reports the resolved data and how many times the transport was invoked.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_pure_request.json`

```json
{
  "description": "A pure request returns the response data directly as a promise without dispatching lifecycle actions, and substitutes [a complex path segment pattern (e.g., /api/v{version}/users)] variables into the routed URL. This case issues a pure request with a [a complex path segment pattern (e.g., /api/v{version}/users)] variable and reports the resolved data plus how many times the transport was invoked.",
  "cases": [
    {"input": {"op": "pure_request", "endpoints": {"test": "/test/:id"}, "fetch": {"fixed": {"msg": "hello"}}, "endpoint": "test", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 2}, "params": {"hello": "world"}}, "expected_output": "data={\"msg\":\"hello\"}\nfetch_count=1\n"}
  ]
}
```

---

### Feature 8: Cross-Cutting Hooks

**As a developer**, I want pluggable hooks for validation, broadcasting, response handling, and pre-request dependencies, so cross-cutting concerns live in configuration instead of being copy-pasted per endpoint.

**Expected Behavior / Usage:**

Each leaf is an independent hook point exercised against the lifecycle.

*8.1 Validation Hook — gate success on a check*

A validation hook runs against the response before success commits. If validation accepts, the lifecycle completes with success and stores the data. If validation rejects, a fail action is emitted carrying the neutral rejection reason and the slice keeps previous data with loading cleared.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_validation.json`

```json
{
  "description": "A validation hook runs against the response before success is committed. If validation accepts the data, the lifecycle completes with success and the data is stored. If validation rejects, a fail action is emitted carrying the neutral rejection reason and the slice keeps its previous data with loading cleared.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": {"url": "/test/:id", "validation": "accept"}}, "fetch": {"fixed": {"msg": "hello"}}, "calls": [{"endpoint": "test", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 1}}]}, "expected_output": "action type=@@redux-api@test syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":1}}\naction type=@@redux-api@test_success syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":1}} data={\"msg\":\"hello\"}\nstate test={\"data\":{\"msg\":\"hello\"},\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\n"},
    {"input": {"op": "call_endpoint", "endpoints": {"test": {"url": "/test/:id", "validation": "reject"}}, "fetch": {"fixed": {"msg": "hello"}}, "calls": [{"endpoint": "test", "[a complex path segment pattern (e.g., /api/v{version}/users)]vars": {"id": 1}}]}, "expected_output": "action type=@@redux-api@test syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":1}}\naction type=@@redux-api@test_fail syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":{\"id\":1}} error=rejected reason=invalid\nstate test={\"data\":{},\"error\":\"invalid\",\"loading\":false,\"sync\":false,\"syncing\":false}\n"}
  ]
}
```

*8.2 Broadcast Hook — emit extra success actions*

An endpoint may broadcast extra actions on success in addition to its own success action. Each broadcast action carries the same transformed data, original data and request descriptor so other reducers can observe the result.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_broadcast.json`

```json
{
  "description": "An endpoint may broadcast extra actions on success in addition to its own namespaced success action. Each broadcast action carries the same transformed data, original data and request descriptor, allowing other reducers to observe the result. This case configures one broadcast action and reports the full action stream.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": {"url": "/test/:id", "broadcast": ["BROADCAST_ACTION"]}}, "fetch": {"fixed": {"msg": "hello"}}, "calls": [{"endpoint": "test"}]}, "expected_output": "action type=@@redux-api@test syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null}\naction type=@@redux-api@test_success syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null} data={\"msg\":\"hello\"}\naction type=BROADCAST_ACTION request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null} data={\"msg\":\"hello\"}\nstate test={\"data\":{\"msg\":\"hello\"},\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\n"}
  ]
}
```

*8.3 Response Handler — observe every outcome*

A global response handler is invoked for every pure request outcome: on success it receives a null error and the data; on failure it receives the error (normalized to a neutral category) and no data.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_response_handler.json`

```json
{
  "description": "A global response handler is invoked for every pure request outcome. On success it receives a null error and the response data; on failure it receives the error (normalized to a neutral category) and no data. This case reports the handler observations for a successful and a failing request.",
  "cases": [
    {"input": {"op": "pure_request", "endpoints": {"test": "/test/"}, "fetch": {"fixed": {"msg": "hello"}}, "use": {"responseHandler": "record"}, "endpoint": "test"}, "expected_output": "data={\"msg\":\"hello\"}\nfetch_count=1\nresponse data={\"msg\":\"hello\"}\n"},
    {"input": {"op": "pure_request", "endpoints": {"test": "/test/"}, "fetch": {"fail": "boom"}, "use": {"responseHandler": "record"}, "endpoint": "test"}, "expected_output": "error=request_failed reason=boom\nresponse error=request_failed reason=boom\n"}
  ]
}
```

*8.4 Pre-Request Dependency — fetch a dependency first*

An endpoint can declare a pre-request dependency that dispatches another endpoint before its own request, so the dependency's lifecycle runs and completes first. The action stream shows the dependency's begin, then its success, then the dependent endpoint's success, and both slices end populated.

**Test Cases:** `rcb_tests/public_test_cases/feature8_4_prefetch_dependency.json`

```json
{
  "description": "An endpoint can declare prefetch dependencies that must run before its own request. This case configures one endpoint whose prefetch step dispatches another endpoint first; the reported routed URLs show the dependency is fetched before the dependent endpoint.",
  "cases": [
    {"input": {"op": "call_endpoint", "endpoints": {"test": "/test", "test1": {"url": "/test1", "prefetchOf": "test"}}, "fetch": "echo_url", "calls": [{"endpoint": "test1"}]}, "expected_output": "action type=@@redux-api@test1 syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null}\naction type=@@redux-api@test syncing=false request={\"params\":{},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null}\naction type=@@redux-api@test_success syncing=false request={\"params\":{},\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null} data={\"data\":\"/test\"}\naction type=@@redux-api@test1_success syncing=false request={\"params\":null,\"[a complex path segment pattern (e.g., /api/v{version}/users)]vars\":null} data={\"data\":\"/test1\"}\nstate test={\"data\":{\"data\":\"/test\"},\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\nstate test1={\"data\":{\"data\":\"/test1\"},\"error\":null,\"loading\":false,\"sync\":true,\"syncing\":false}\n"}
  ]
}
```

---

### Feature 9: Request Chaining & Helper Name Safety

**As a developer**, I want to chain requests in order and to be protected from helper-name collisions, so multi-step flows are easy and configuration mistakes fail loudly.

**Expected Behavior / Usage:**

*9.1 Sequential Chain — run endpoints in order, resolve with last*

A chaining helper runs a sequence of endpoint actions one after another, waiting for each to finish before the next, and resolves with the data of the final step. After the chain completes, each endpoint's slice holds its own fetched data.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_async_chain.json`

```json
{
  "description": "An async helper runs a sequence of endpoint actions one after another, waiting for each to finish before starting the next, and resolves with the data of the final step. After the chain completes, each endpoint's slice holds its own fetched data. This case chains two endpoints and reports the final result plus both stored slices.",
  "cases": [
    {"input": {"op": "async_chain", "endpoints": {"test": "/api/url", "test2": "/api/url2"}, "fetch": "echo_url", "sequence": ["test", "test2"]}, "expected_output": "result={\"data\":\"/api/url2\"}\nstate test={\"data\":\"/api/url\"}\nstate test2={\"data\":\"/api/url2\"}\n"}
  ]
}
```

*9.2 Reserved Helper Name — fail fast on collision*

Declaring a custom helper whose name collides with the built-in endpoint surface fails fast at construction time with a neutral error naming the offending helper and the endpoint, rather than leaking any host runtime exception identity.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_reserved_helper.json`

```json
{
  "description": "Custom helper names must not collide with the built-in endpoint surface. Declaring a helper whose name is already reserved (such as the reset or sync controls) fails fast at construction time with a neutral error that names the offending helper and the endpoint, rather than leaking any host runtime exception identity.",
  "cases": [
    {"input": {"op": "reserved_helper", "endpoints": {"test": {"url": "/test/:id", "helpersReserved": ["reset"]}}, "fetch": "echo_url"}, "expected_output": "error=helper_name_reserved helper=reset endpoint=test\n"},
    {"input": {"op": "reserved_helper", "endpoints": {"test": {"url": "/test/:id", "helpersReserved": ["sync"]}}, "fetch": "echo_url"}, "expected_output": "error=helper_name_reserved helper=sync endpoint=test\n"}
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the value utilities, URL assembler, lifecycle reducer, lifecycle coordination primitives, endpoint declaration/orchestration layer, and an injectable transport adapter. The core must be decoupled from stdin/stdout and JSON, expose an idiomatic public interface, and model errors as distinct observable outcomes.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. The adapter is the only component aware of the wire format; it also normalizes any thrown/rejected error into the neutral contract (a category line plus structured fields), never leaking host runtime exception names, runtime message suffixes, or language-specific object renderings.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_deep_merge.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_deep_merge@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the query string parsing for 'repeat' delimiter
- normalize the error structure passed to the reducer
