## Product Requirement Document

# Cookie-Backed Web Session Toolkit - Server-Side Sessions for an Async Web Framework

## Project Goal

Build a session toolkit for an asynchronous HTTP web framework that lets developers attach per-client server-side state to requests without hand-rolling cookie parsing, serialization, encryption, and expiry. The toolkit provides a dict-like session object, several pluggable cookie storage backends (plaintext and authenticated[a specific domain string — ask the PM for the exact value]encrypted), and a request-processing layer that transparently loads a session at the start of a request and persists it via a response cookie when (and only when) the handler changed it.

---

## Background & Problem

Without this toolkit, developers wiring sessions into an async web app must repeatedly: read a named cookie off the incoming request, decode[a specific domain string — ask the PM for the exact value]validate[a specific domain string — ask the PM for the exact value]decrypt its contents, expose the result as a mutable mapping, detect whether the handler actually mutated it, re-encode it, and emit a correctly-scoped `Set-Cookie` header (with path, domain, http-only, max-age and expiry). Each of these steps is easy to get subtly wrong — silently persisting unchanged sessions, leaking data across path[a specific domain string — ask the PM for the exact value]domain scopes, trusting tampered cookies, or failing to clear a cookie on logout.

With this toolkit, the developer installs one processing layer with a chosen storage backend and simply calls a "get the session" helper inside a handler. The session behaves like an ordinary dictionary; everything else (load, change-detection, encode, cookie emission, expiry) happens automatically and uniformly.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (a session value-container, an abstract storage contract, several concrete storage backends, and a request-processing layer). It MUST be organized into clear modules reflecting those responsibilities rather than a single monolithic file. Do not over-engineer, but do not collapse distinct concerns together.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input[a specific domain string — ask the PM for the exact value]output cases below are a black-box contract for the execution adapter, NOT the internal data model. The core session[a specific domain string — ask the PM for the exact value]storage[a specific domain string — ask the PM for the exact value]processing logic must be completely decoupled from stdin[a specific domain string — ask the PM for the exact value]stdout and JSON. The execution adapter alone translates JSON scenarios into idiomatic calls against the core and renders the observable result.

3. **Adherence to SOLID Design Principles:** Separate the value-container, the storage abstraction, the concrete backends, and the request-processing layer into cohesive units. New storage backends must be addable by implementing the storage abstraction without modifying the processing layer (Open[a specific domain string — ask the PM for the exact value]Closed). Backends must be substitutable for the storage abstraction (Liskov). The processing layer depends on the storage abstraction, not on any concrete backend (Dependency Inversion).

4. **Robustness & Interface Design:** The session must present an idiomatic mapping interface. Misconfiguration and malformed[a specific domain string — ask the PM for the exact value]tampered[a specific domain string — ask the PM for the exact value]expired cookies must be handled gracefully — a backend that cannot authenticate a cookie yields a fresh empty session rather than failing the request, while genuine programmer errors (no processing layer installed, invalid storage, invalid response object) surface as distinct error conditions.

---

## Core Features

### Feature 1: Session Value Container

**As a developer**, I want a dict-like session object that tracks whether it has been modified, so I can mutate state naturally and let the system decide when to persist.

**Expected Behavior [a specific domain string — ask the PM for the exact value] Usage:**

The container is constructed from an optional identity tag, an optional prior-data record, and a "new" flag. Its observable state is reported as a single line: `state new=<bool> changed=<bool> empty=<bool> len=<int> identity=<json> created=<int> contents=<json>`. The `op` is `"session"`; `init` carries `identity`, `data` (either `null` or an object with optional `session` map and optional `created` timestamp) and `new`. An optional `actions` list applies operations in order, each emitting a fresh state line (or a neutral error line). Error conditions are reported as `error=<category>`.

*1.1 Initialization — state derived from construction inputs*

A container built with no prior data is empty, new, and stamped with the current creation time. A container built from a prior-data record holding a `session` map is populated and not-new. The identity tag is echoed as supplied. When prior data is an empty record the container is treated as new regardless of the requested flag.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature1_1_initialize.json`

```json
{
  "description": "Build a session value container and report its observable state (new flag, identity tag, creation timestamp, emptiness, size, contents). A container built with no prior data starts empty and new; one built from previously stored data starts populated and not-new with the stored creation time.",
  "cases": [
    {
      "input": {"op": "session", "init": {"identity": "test_identity", "data": null, "new": true}},
      "expected_output": "state new=true changed=false empty=true len=0 identity=\"test_identity\" created=1000000000 contents={}\n"
    },
    {
      "input": {"op": "session", "init": {"identity": "test_identity", "data": {"session": {"some": "data"}}, "new": false}},
      "expected_output": "state new=false changed=false empty=false len=1 identity=\"test_identity\" created=1000000000 contents={\"some\": \"data\"}\n"
    }
  ]
}
```

*1.2 Mapping operations — membership, insertion, deletion*

The container supports membership queries and length on an empty instance, and item set[a specific domain string — ask the PM for the exact value]delete[a specific domain string — ask the PM for the exact value]pop on a populated one. Each mutation updates the size and contents and flips the modified flag to true.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature1_2_mapping_ops.json`

```json
{
  "description": "Use the container as a mapping: query membership[a specific domain string — ask the PM for the exact value]size on an empty container, then add, delete and pop entries on a populated one. Every insertion or removal updates the size and contents and marks the container as modified.",
  "cases": [
    {
      "input": {"op": "session", "init": {"identity": "test_identity", "data": {"session": {"foo": "bar"}}, "new": false}, "actions": [{"do": "set", "key": "key", "value": "value"}, {"do": "del", "key": "key"}, {"do": "pop", "key": "foo"}]},
      "expected_output": "state new=false changed=false empty=false len=1 identity=\"test_identity\" created=1000000000 contents={\"foo\": \"bar\"}\nstate new=false changed=true empty=false len=2 identity=\"test_identity\" created=1000000000 contents={\"foo\": \"bar\", \"key\": \"value\"}\nstate new=false changed=true empty=false len=1 identity=\"test_identity\" created=1000000000 contents={\"foo\": \"bar\"}\nstate new=false changed=true empty=true len=0 identity=\"test_identity\" created=1000000000 contents={}\n"
    }
  ]
}
```

*1.3 Change tracking — nested mutation versus explicit signal*

Mutating a value reached by indexing into the container (without re-assigning a top-level key) does NOT mark the container modified; only an explicit "mark modified" signal does. The creation timestamp is preserved throughout.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature1_3_change_tracking.json`

```json
{
  "description": "Mutating a value nested inside the container does not by itself mark the container as modified; only an explicit 'mark modified' signal does. The creation timestamp is preserved across such updates.",
  "cases": [
    {
      "input": {"op": "session", "init": {"identity": "test_identity", "data": {"session": {"a": {"key": "value"}}, "created": 999990000}, "new": false}, "actions": [{"do": "mutate_nested", "key": "a", "subkey": "key2", "value": "val2"}, {"do": "changed"}]},
      "expected_output": "state new=false changed=false empty=false len=1 identity=\"test_identity\" created=999990000 contents={\"a\": {\"key\": \"value\"}}\nstate new=false changed=false empty=false len=1 identity=\"test_identity\" created=999990000 contents={\"a\": {\"key\": \"value\", \"key2\": \"val2\"}}\nstate new=false changed=true empty=false len=1 identity=\"test_identity\" created=999990000 contents={\"a\": {\"key\": \"value\", \"key2\": \"val2\"}}\n"
    }
  ]
}
```

*1.4 Invalidation — clear contents, keep timestamp*

Invalidating the container clears all entries and marks it modified, while keeping the original creation timestamp; afterwards it reports empty.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature1_4_invalidate.json`

```json
{
  "description": "Invalidating the container empties its contents and marks it modified while keeping its creation timestamp; afterwards it reports itself as empty.",
  "cases": [
    {
      "input": {"op": "session", "init": {"identity": "test_identity", "data": {"session": {"foo": "bar"}}, "new": false}, "actions": [{"do": "invalidate"}]},
      "expected_output": "state new=false changed=false empty=false len=1 identity=\"test_identity\" created=1000000000 contents={\"foo\": \"bar\"}\nstate new=false changed=true empty=true len=0 identity=\"test_identity\" created=1000000000 contents={}\n"
    }
  ]
}
```

*1.5 Identity assignment — allowed once for a new container*

A container that is new permits assigning its identity tag exactly once. A container that is not new rejects any identity reassignment with a neutral error.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature1_5_identity_assignment.json`

```json
{
  "description": "A new container allows assigning its identity tag once; a container that is not new rejects any attempt to reassign its identity.",
  "cases": [
    {
      "input": {"op": "session", "init": {"identity": 1, "data": null, "new": true}, "actions": [{"do": "set_identity", "value": 2}]},
      "expected_output": "state new=true changed=false empty=true len=0 identity=1 created=1000000000 contents={}\nstate new=true changed=false empty=true len=0 identity=2 created=1000000000 contents={}\n"
    },
    {
      "input": {"op": "session", "init": {"identity": 1, "data": null, "new": false}, "actions": [{"do": "set_identity", "value": 2}]},
      "expected_output": "state new=false changed=false empty=true len=0 identity=1 created=1000000000 contents={}\nerror=identity_locked\n"
    }
  ]
}
```

---

### Feature 2: Session Retrieval Within a Request

**As a developer**, I want helpers that fetch the current session (or start a brand-new one) from a request, so handlers never touch storage directly.

**Expected Behavior [a specific domain string — ask the PM for the exact value] Usage:**

`op` is `"context"`; `scenario` selects the situation. "Get the session" returns the session already attached to the request if present, otherwise loads one through the installed storage. "Start a new session" always produces a fresh empty session through the storage. Both require the processing layer to have been installed (a storage reference attached to the request); otherwise they fail with `error=no_middleware`. If storage yields a non-session object, they fail with `error=invalid_session`. Successful retrieval renders selected observable fields (`result=`, flags, identity, contents).

*2.1 Get an already-attached session*

If the request already carries a session, retrieval returns that same instance unchanged.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature2_1_get_existing.json`

```json
{
  "description": "Retrieving the session for a request that already carries one returns that same session unchanged.",
  "cases": [
    {"input": {"op": "context", "scenario": "get_stored"}, "expected_output": "result=same\nnew=false\nidentity=\"identity\"\ncontents={}\n"}
  ]
}
```

*2.2 Get requires the processing layer*

Retrieving a session when no processing layer was installed fails with a configuration error.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature2_2_get_requires_layer.json`

```json
{
  "description": "Retrieving a session when the session layer was never installed for the request fails with a configuration error.",
  "cases": [
    {"input": {"op": "context", "scenario": "get_no_storage"}, "expected_output": "error=no_middleware\n"}
  ]
}
```

*2.3 Get rejects a non-session from storage*

If storage returns something that is not a session while loading, retrieval fails with an invalid-session error.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature2_3_get_invalid_session.json`

```json
{
  "description": "If the installed storage yields a non-session object while loading, retrieval fails with an invalid-session error.",
  "cases": [
    {"input": {"op": "context", "scenario": "get_bad_load"}, "expected_output": "error=invalid_session\n"}
  ]
}
```

*2.4 Start a new session*

Starting a new session produces a fresh, empty, brand-new session, distinct from any session already attached to the request.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature2_4_new_session.json`

```json
{
  "description": "Explicitly starting a new session yields a fresh, empty, brand-new session distinct from any session already attached to the request.",
  "cases": [
    {"input": {"op": "context", "scenario": "new_ok"}, "expected_output": "result=fresh\ndistinct=true\nnew=true\nempty=true\n"}
  ]
}
```

*2.5 Start-new requires the processing layer*

Starting a new session with no processing layer installed fails with a configuration error.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature2_5_new_requires_layer.json`

```json
{
  "description": "Starting a new session when the session layer was never installed fails with a configuration error.",
  "cases": [
    {"input": {"op": "context", "scenario": "new_no_storage"}, "expected_output": "error=no_middleware\n"}
  ]
}
```

*2.6 Start-new rejects a non-session from storage*

If storage produces a non-session object when starting a new session, the operation fails with an invalid-session error.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature2_6_new_invalid_session.json`

```json
{
  "description": "If the storage produces a non-session object when starting a new session, the operation fails with an invalid-session error.",
  "cases": [
    {"input": {"op": "context", "scenario": "new_bad_return"}, "expected_output": "error=invalid_session\n"}
  ]
}
```

---

### Feature 3: Request-Processing Layer Lifecycle

**As a developer**, I want a processing layer that loads a session before my handler and saves it afterward only when appropriate, so persistence is automatic and safe.

**Expected Behavior [a specific domain string — ask the PM for the exact value] Usage:**

The layer is constructed around a storage backend. Constructing it with a non-storage value is rejected (`error=invalid_storage`, `op` `"middleware"`). When wrapping a handler it only persists into a regular buffered response: a non-response return value yields `error=invalid_response`, and a response that has already started streaming yields `error=response_prepared`. For full request flows (`op` `"http"`[a specific domain string — ask the PM for the exact value]`"redirect"`) the observable result is the HTTP status, what the handler saw (`loaded.*`), and the emitted cookie (`set_cookie=` and `cookie.*`), plus the round-tripped `payload.*` when the cookie carries data.

*3.1 Requires a valid storage backend*

Installing the layer with a non-storage value is rejected immediately.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature3_1_requires_storage.json`

```json
{
  "description": "Installing the session layer requires a valid storage backend; a non-storage value is rejected immediately.",
  "cases": [
    {"input": {"op": "middleware", "scenario": "invalid_storage"}, "expected_output": "error=invalid_storage\n"}
  ]
}
```

*3.2 Response-type guard*

Persistence only applies to a regular buffered response. A non-response return value, or a response that has already begun streaming, fails with a distinct error.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature3_2_response_type_guard.json`

```json
{
  "description": "The session layer only operates on a regular buffered response. Returning a non-response value, or a response that has already begun streaming, fails with an error.",
  "cases": [
    {"input": {"op": "middleware", "scenario": "bad_response"}, "expected_output": "error=invalid_response\n"},
    {"input": {"op": "middleware", "scenario": "prepared"}, "expected_output": "error=response_prepared\n"}
  ]
}
```

*3.3 Streaming responses are left untouched*

When the handler returns a streaming response, the layer does not persist and emits no session cookie, even if the handler modified the session.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature3_3_streaming_not_saved.json`

```json
{
  "description": "When a handler returns a streaming response, the session layer leaves it untouched and emits no session cookie, even if the handler modified the session.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple"}, "scenario": "stream"}, "expected_output": "status=200\nloaded.new=true\nloaded.empty=true\nloaded.contents={}\nset_cookie=absent\n"}
  ]
}
```

*3.4 Untouched session is not persisted*

If the handler never accesses the session, no session cookie is emitted even when the request carried session data.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature3_4_skip_untouched.json`

```json
{
  "description": "If a handler never accesses the session, no session cookie is emitted even when the request carried session data.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple"}, "scenario": "dont_save", "incoming": {"data": {"a": 1, "b": 2}}}, "expected_output": "status=200\nset_cookie=absent\n"}
  ]
}
```

*3.5 Persistence across a redirect*

A session modified by a handler that responds with a redirect is still persisted; the redirected-to handler observes the stored data.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature3_5_persist_across_redirect.json`

```json
{
  "description": "A session modified by a handler that responds with a redirect is still persisted, and the redirected-to handler observes the stored data.",
  "cases": [
    {"input": {"op": "redirect", "storage": {"type": "simple"}}, "expected_output": "status=200\nfinal_path=[a specific domain string — ask the PM for the exact value]show\nbody=works\n"}
  ]
}
```

---

### Feature 4: Plaintext Cookie Storage

**As a developer**, I want a transparent JSON cookie backend, so I can inspect sessions easily during development.

**Expected Behavior [a specific domain string — ask the PM for the exact value] Usage:**

The `simple` storage encodes the session as JSON directly into the cookie value (no confidentiality). `op` `"http"`, `storage.type` `"simple"`, with optional `cookie_name`, `domain`, `path`, `max_age`. An incoming cookie (`incoming.data`, with optional `path`[a specific domain string — ask the PM for the exact value]`domain` scope and `created`) is decoded for the handler; the response cookie carries the updated `{created, session}` record. Default cookie scope is http-only at the root path. When `max_age` is set, the cookie also carries a max-age and an absolute expiry. The handler `scenario` is one of `read` (no change), `change` (adds an entry), or `invalidate`.

*4.1 Fresh session when no cookie present*

With no incoming cookie the handler gets a fresh empty session; reading it without changes emits no cookie.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature4_1_new_session.json`

```json
{
  "description": "With no incoming session cookie, the handler receives a fresh empty session; reading it without changes emits no cookie.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple"}, "scenario": "read"}, "expected_output": "status=200\nloaded.new=true\nloaded.empty=true\nloaded.contents={}\nset_cookie=absent\n"}
  ]
}
```

*4.2 Load an existing cookie*

An incoming plaintext cookie is decoded so the handler sees the stored contents as a not-new session; reading without changes emits no new cookie.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature4_2_load_existing.json`

```json
{
  "description": "An incoming plaintext session cookie is decoded so the handler sees the previously stored contents as a not-new session; reading without changes emits no new cookie.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple"}, "scenario": "read", "incoming": {"data": {"a": 1, "b": 2}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=absent\n"}
  ]
}
```

*4.3 Persist a changed session*

When the handler modifies the session, a cookie is emitted carrying the full updated contents plus the creation timestamp, http-only and scoped to the root path.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature4_3_save_changed.json`

```json
{
  "description": "When a handler modifies the session, a cookie is emitted carrying the full updated contents plus the creation timestamp, marked http-only and scoped to the root path.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple"}, "scenario": "change", "incoming": {"data": {"a": 1, "b": 2}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=false\ncookie.httponly=true\ncookie.path=[a specific domain string — ask the PM for the exact value]\ncookie.domain=127.0.0.1\npayload.created=1000000000\npayload.session={\"a\": 1, \"b\": 2, \"c\": 3}\n"}
  ]
}
```

*4.4 Invalidate writes an empty record*

Invalidating a plaintext session emits a cookie carrying an empty data object (still http-only, scoped to the root path).

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature4_4_invalidate.json`

```json
{
  "description": "Invalidating a plaintext session emits a cookie carrying an empty data object (still http-only, scoped to the root path).",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple"}, "scenario": "invalidate", "incoming": {"data": {"a": 1, "b": 2}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=false\ncookie.httponly=true\ncookie.path=[a specific domain string — ask the PM for the exact value]\ncookie.domain=127.0.0.1\npayload.created=null\npayload.session=null\n"}
  ]
}
```

*4.5 Max-age yields an expiry timestamp*

When the storage is configured with a maximum age, the emitted cookie carries both a max-age and a matching absolute expiry timestamp.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature4_5_max_age_expires.json`

```json
{
  "description": "When the storage is configured with a maximum age, the emitted cookie carries both a max-age and a matching absolute expiry timestamp.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple", "max_age": 10}, "scenario": "change", "now": 0, "incoming": {"data": {"a": 1, "b": 2}, "created": 0}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=false\ncookie.httponly=true\ncookie.path=[a specific domain string — ask the PM for the exact value]\ncookie.domain=127.0.0.1\ncookie.max_age=10\ncookie.expires=Thu, 01-Jan-1970 00:00:10 GMT\npayload.created=0\npayload.session={\"a\": 1, \"b\": 2, \"c\": 3}\n"}
  ]
}
```

*4.6.1 Scoped storage — matching path and domain*

With a configured path and domain matching the request, an incoming cookie in that scope is loaded, updated and re-emitted with the configured path and domain.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature4_6_1_matching_scope.json`

```json
{
  "description": "With a configured path and domain matching the request, an incoming cookie within that scope is loaded, updated and re-emitted with the configured path and domain.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple", "max_age": 10, "path": "[a specific domain string — ask the PM for the exact value]anotherpath", "domain": "127.0.0.1"}, "scenario": "change", "path": "[a specific domain string — ask the PM for the exact value]anotherpath", "incoming": {"data": {"a": 1, "b": 2}, "path": "[a specific domain string — ask the PM for the exact value]anotherpath", "domain": "127.0.0.1"}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=false\ncookie.httponly=true\ncookie.path=[a specific domain string — ask the PM for the exact value]anotherpath\ncookie.domain=127.0.0.1\ncookie.max_age=10\ncookie.expires=Sun, 09-Sep-2001 01:46:50 GMT\npayload.created=1000000000\npayload.session={\"a\": 1, \"b\": 2, \"c\": 3}\n"}
  ]
}
```

*4.6.2 Scoped storage — out-of-scope cookie ignored*

An incoming cookie whose path or domain does not match the request is not presented to the handler; the handler starts from an empty session and the re-emitted cookie carries only the newly added data, still scoped to the configured path and domain.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature4_6_2_outside_scope.json`

```json
{
  "description": "An incoming cookie whose path or domain does not match the request is not presented to the handler; the handler starts from an empty session and the re-emitted cookie carries only the newly added data, still scoped to the configured path and domain.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple", "max_age": 10, "path": "[a specific domain string — ask the PM for the exact value]anotherpath", "domain": "127.0.0.1"}, "scenario": "change", "path": "[a specific domain string — ask the PM for the exact value]anotherpath", "incoming": {"data": {"a": 1, "b": 2}, "path": "[a specific domain string — ask the PM for the exact value]NotTheSame", "domain": "127.0.0.1"}}, "expected_output": "status=200\nloaded.new=true\nloaded.empty=true\nloaded.contents={}\nset_cookie=present\ncookie.cleared=false\ncookie.httponly=true\ncookie.path=[a specific domain string — ask the PM for the exact value]anotherpath\ncookie.domain=127.0.0.1\ncookie.max_age=10\ncookie.expires=Sun, 09-Sep-2001 01:46:50 GMT\npayload.created=1000000000\npayload.session={\"c\": 3}\n"}
  ]
}
```

*4.6.3 Scoped storage — invalidation under scope*

Invalidating a session under a configured path and domain emits an empty data object scoped to that path and domain.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature4_6_3_invalidate_scoped.json`

```json
{
  "description": "Invalidating a session under a configured path and domain emits an empty data object scoped to that path and domain.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "simple", "max_age": 10, "path": "[a specific domain string — ask the PM for the exact value]anotherpath", "domain": "127.0.0.1"}, "scenario": "invalidate", "path": "[a specific domain string — ask the PM for the exact value]anotherpath", "incoming": {"data": {"a": 1, "b": 2}, "path": "[a specific domain string — ask the PM for the exact value]anotherpath", "domain": "127.0.0.1"}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=false\ncookie.httponly=true\ncookie.path=[a specific domain string — ask the PM for the exact value]anotherpath\ncookie.domain=127.0.0.1\ncookie.max_age=10\ncookie.expires=Sun, 09-Sep-2001 01:46:50 GMT\npayload.created=null\npayload.session=null\n"}
  ]
}
```

---

### Feature 5: Authenticated Cookie Storage (Token-Based)

**As a developer**, I want a confidential, tamper-evident cookie backend with a key and optional time-to-live, so clients cannot read or forge session data.

**Expected Behavior [a specific domain string — ask the PM for the exact value] Usage:**

The `encrypted` storage seals the session record with a secret key into an opaque token cookie; the adapter uses a fixed key so behaviour is reproducible, and asserts on the decrypted round-trip rather than raw ciphertext. A key of invalid length is rejected at construction (`error=invalid_key`). An incoming cookie sealed with the correct key is opened so the handler sees the stored contents; an incoming cookie that cannot be authenticated (e.g. sealed under a different key) is rejected and the handler gets a fresh empty session (the request still succeeds). Invalidation emits a cleared cookie (empty value, not http-only) so the client drops it. With a configured maximum age, a token older than that age is treated as expired and not opened. `incoming.cookie_time` sets the time at which the token was sealed; `now` sets the request time.

*5.1 Invalid key rejected*

Constructing the storage with a key of invalid length is rejected.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature5_1_invalid_key.json`

```json
{
  "description": "Constructing the authenticated storage with a key of invalid length is rejected.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "encrypted", "bad_key": true}, "scenario": "read"}, "expected_output": "error=invalid_key\n"}
  ]
}
```

*5.2 Open an authentic cookie*

An incoming cookie sealed with the correct key is opened so the handler sees the stored contents as a not-new session.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature5_2_load_existing.json`

```json
{
  "description": "An incoming authenticated cookie produced with the correct key is decrypted so the handler sees the stored contents as a not-new session.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "encrypted"}, "scenario": "read", "incoming": {"data": {"a": 1, "b": 12}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 12}\nset_cookie=absent\n"}
  ]
}
```

*5.3 Re-seal a changed session*

Modifying the session re-seals and emits an http-only cookie; opening it with the key recovers the full updated contents and creation timestamp.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature5_3_save_changed.json`

```json
{
  "description": "Modifying the session re-encrypts and emits an http-only cookie; decrypting it with the key recovers the full updated contents and creation timestamp.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "encrypted"}, "scenario": "change", "incoming": {"data": {"a": 1, "b": 2}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=false\ncookie.httponly=true\ncookie.path=[a specific domain string — ask the PM for the exact value]\ncookie.domain=127.0.0.1\npayload.created=1000000000\npayload.session={\"a\": 1, \"b\": 2, \"c\": 3}\n"}
  ]
}
```

*5.4 Foreign cookie rejected gracefully*

A cookie that cannot be authenticated with the configured key is rejected and the handler receives a fresh empty session.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature5_4_foreign_cookie.json`

```json
{
  "description": "An incoming cookie that cannot be authenticated with the configured key (e.g. produced under a different key) is rejected and the handler receives a fresh empty session.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "encrypted"}, "scenario": "read", "incoming": {"data": {"a": 1, "b": 12}, "mode": "wrong_key"}}, "expected_output": "status=200\nloaded.new=true\nloaded.empty=true\nloaded.contents={}\nset_cookie=absent\n"}
  ]
}
```

*5.5 Invalidation clears the cookie*

Invalidating an authenticated session emits a cleared cookie (empty value, not http-only) so the client drops it.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature5_5_invalidate.json`

```json
{
  "description": "Invalidating an authenticated session emits a cleared cookie (empty value, not http-only) so the client drops it.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "encrypted"}, "scenario": "invalidate", "incoming": {"data": {"a": 1, "b": 2}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=true\ncookie.httponly=false\ncookie.path=[a specific domain string — ask the PM for the exact value]\ncookie.domain=127.0.0.1\ncookie.max_age=0\ncookie.expires=Thu, 01 Jan 1970 00:00:00 GMT\n"}
  ]
}
```

*5.6 Session-fixation resistance*

After invalidation, replaying a previously captured cookie cannot resurrect the old session: a subsequent login issues a different cookie value, and the logout response clears the cookie.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature5_6_session_fixation.json`

```json
{
  "description": "After a session is invalidated, replaying a previously captured cookie cannot resurrect the old session: a subsequent login issues a different cookie value, and the logout response clears the cookie.",
  "cases": [
    {"input": {"op": "fixation", "storage": {"type": "encrypted"}}, "expected_output": "login_cookie=present\nlogout_cookie_cleared=true\nreplay_cookie_differs=true\n"}
  ]
}
```

*5.7 Time-to-live expiry*

A token older than the configured maximum age is treated as expired: it is not opened and the handler receives a fresh empty session.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature5_7_expiry.json`

```json
{
  "description": "An authenticated cookie older than the configured maximum age is treated as expired: it is not decrypted and the handler receives a fresh empty session.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "encrypted", "max_age": 1}, "scenario": "read", "now": 1000001000, "incoming": {"data": {"a": 1}, "cookie_time": 1000000000}}, "expected_output": "status=200\nloaded.new=true\nloaded.empty=true\nloaded.contents={}\nset_cookie=absent\n"}
  ]
}
```

---

### Feature 6: Authenticated Cookie Storage (Sealed-Box Variant)

**As a developer**, I want an alternative confidential cookie backend using a symmetric sealed-box scheme, so I can choose a different cryptographic primitive with the same contract.

**Expected Behavior [a specific domain string — ask the PM for the exact value] Usage:**

The `sealed` storage behaves like Feature 5 (confidential, tamper-evident, fixed key for reproducibility) but uses a symmetric sealed-box construction. Same contract: a bad-length key is rejected (`error=invalid_key`); authentic cookies open to the stored contents; changes re-seal an http-only cookie whose decrypted round-trip carries the full data and creation timestamp; invalidation clears the cookie; and any cookie that is not a valid token under the configured key (corrupted value or foreign key) is rejected, leaving the handler with a fresh empty session while the request still succeeds.

*6.1 Invalid key rejected*

Constructing this storage with a key of invalid length is rejected.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature6_1_invalid_key.json`

```json
{
  "description": "Constructing this authenticated storage with a key of invalid length is rejected.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "sealed", "bad_key": true}, "scenario": "read"}, "expected_output": "error=invalid_key\n"}
  ]
}
```

*6.2 Fresh session when no cookie present*

With no incoming cookie the handler receives a fresh empty session.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature6_2_new_session.json`

```json
{
  "description": "With no incoming cookie, the handler receives a fresh empty session.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "sealed"}, "scenario": "read"}, "expected_output": "status=200\nloaded.new=true\nloaded.empty=true\nloaded.contents={}\nset_cookie=absent\n"}
  ]
}
```

*6.3 Open an authentic cookie*

An incoming cookie sealed with the correct key is opened so the handler sees the stored contents as a not-new session.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature6_3_load_existing.json`

```json
{
  "description": "An incoming authenticated cookie produced with the correct key is decrypted so the handler sees the stored contents as a not-new session.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "sealed"}, "scenario": "read", "incoming": {"data": {"a": 1, "b": 12}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 12}\nset_cookie=absent\n"}
  ]
}
```

*6.4 Re-seal a changed session*

Modifying the session re-seals and emits an http-only cookie; opening it with the key recovers the full updated contents and creation timestamp.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature6_4_save_changed.json`

```json
{
  "description": "Modifying the session re-encrypts and emits an http-only cookie; decrypting it with the key recovers the full updated contents and creation timestamp.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "sealed"}, "scenario": "change", "incoming": {"data": {"a": 1, "b": 2}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=false\ncookie.httponly=true\ncookie.path=[a specific domain string — ask the PM for the exact value]\ncookie.domain=127.0.0.1\npayload.created=1000000000\npayload.session={\"a\": 1, \"b\": 2, \"c\": 3}\n"}
  ]
}
```

*6.5 Invalidation clears the cookie*

Invalidating the session emits a cleared cookie (empty value, not http-only) so the client drops it.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature6_5_invalidate.json`

```json
{
  "description": "Invalidating the session emits a cleared cookie (empty value, not http-only) so the client drops it.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "sealed"}, "scenario": "invalidate", "incoming": {"data": {"a": 1, "b": 2}}}, "expected_output": "status=200\nloaded.new=false\nloaded.empty=false\nloaded.contents={\"a\": 1, \"b\": 2}\nset_cookie=present\ncookie.cleared=true\ncookie.httponly=false\ncookie.path=[a specific domain string — ask the PM for the exact value]\ncookie.domain=127.0.0.1\ncookie.max_age=0\ncookie.expires=Thu, 01 Jan 1970 00:00:00 GMT\n"}
  ]
}
```

*6.6 Session-fixation resistance*

After invalidation, replaying a previously captured cookie cannot resurrect the old session: a subsequent login issues a different cookie value, and the logout response clears the cookie.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature6_6_session_fixation.json`

```json
{
  "description": "After a session is invalidated, replaying a previously captured cookie cannot resurrect the old session: a subsequent login issues a different cookie value, and the logout response clears the cookie.",
  "cases": [
    {"input": {"op": "fixation", "storage": {"type": "sealed"}}, "expected_output": "login_cookie=present\nlogout_cookie_cleared=true\nreplay_cookie_differs=true\n"}
  ]
}
```

*6.7 Corrupted cookie rejected gracefully*

A cookie whose value is not a valid token is rejected and the handler receives a fresh empty session.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature6_7_corrupted_cookie.json`

```json
{
  "description": "An incoming cookie whose value is not a valid authenticated token is rejected and the handler receives a fresh empty session.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "sealed"}, "scenario": "read", "incoming": {"mode": "raw", "raw": "bad key"}}, "expected_output": "status=200\nloaded.new=true\nloaded.empty=true\nloaded.contents={}\nset_cookie=absent\n"}
  ]
}
```

*6.8 Foreign-key cookie rejected gracefully*

A cookie sealed under a different key cannot be authenticated and the handler receives a fresh empty session.

**Test Cases:** `rcb_tests[a specific domain string — ask the PM for the exact value]public_test_cases[a specific domain string — ask the PM for the exact value]feature6_8_foreign_cookie.json`

```json
{
  "description": "An incoming cookie produced under a different key cannot be authenticated and the handler receives a fresh empty session.",
  "cases": [
    {"input": {"op": "http", "storage": {"type": "sealed"}, "scenario": "read", "incoming": {"data": {"a": 1, "b": 12}, "mode": "wrong_key"}}, "expected_output": "status=200\nloaded.new=true\nloaded.empty=true\nloaded.contents={}\nset_cookie=absent\n"}
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing the session value-container, the storage abstraction, the concrete storage backends (plaintext, token-based authenticated, sealed-box authenticated), and the request-processing layer, organized to reflect those responsibilities.

2. **The Execution[a specific domain string — ask the PM for the exact value]Test Adapter:** A runnable entry point that reads one JSON command from stdin, drives the appropriate core logic (including driving full request flows through the framework's in-process test facilities), and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter is logically and physically separated from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests[a specific domain string — ask the PM for the exact value]test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests[a specific domain string — ask the PM for the exact value]stdout[a specific domain string — ask the PM for the exact value]<cases-dir>[a specific domain string — ask the PM for the exact value]{filename.stem}@{case_index.zfill(3)}.txt` containing only the raw stdout from the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same identity locking mechanism as the Feature1 Initialization module
- preserve the original initialization metadata as defined in the Feature1 Initialization logic
