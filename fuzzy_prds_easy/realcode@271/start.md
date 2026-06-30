## Product Requirement Document

# Modular Full-Node Service Container - PRD

## Project Goal

Build a service-container runtime for a long-running networked node that lets developers compose the node out of independent, hot-pluggable service modules — validation helpers, an event bus, a dependency-ordered service registry, and a start/stop lifecycle — without hand-wiring startup order, event routing, or method registration.

---

## Background & Problem

Without this runtime, developers building a long-running node service are forced to manually wire every subsystem together: decide the order in which subsystems boot based on what depends on what, hand-register each subsystem's callable API surface while watching for name clashes, fan out event subscriptions to whichever subsystems publish a given event, and tear everything down in the right order on shutdown. This leads to brittle boot sequences, accidental method-name collisions, and event-routing boilerplate duplicated across every subsystem.

With this runtime, a developer declares the set of service modules and their dependencies, and the container resolves boot order, registers each service's API methods onto a single node object, routes named events through a shared bus, and drives a clean start/stop lifecycle. A small set of value-validation helpers backs the domain (hash strings, safe natural numbers, default-zero counters).

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility system (validation helpers, an event bus, a service registry with dependency ordering, and a lifecycle controller). It MUST NOT be a single "god file". Output a clear, multi-file directory tree separating these responsibilities; do not over-engineer the leaf helpers.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract** for the execution adapter, NOT the internal data model. The core logic must remain decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls on the core domain and rendering results.

3. **Adherence to SOLID Design Principles:** Separate validation, event routing, registry/ordering, lifecycle, and output formatting into distinct units (SRP). The container core must be open for extension via new service modules but closed for modification (OCP). Service modules must be substitutable behind a common service interface (LSP/ISP). High-level orchestration must depend on the service abstraction, not on concrete I/O (DIP).

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language. Failure conditions (a service that fails to start, two services registering the same method name) must be modeled as proper errors surfaced to the caller, not silent faults.

---

## Core Features

### Feature 1: Value Validation Helpers

**As a developer**, I want small, dependable predicates and a default-initializer for domain values, so I can validate identifiers and counters consistently across the node.

**Expected Behavior / Usage:**

*1.1 Hash-string validation — recognizes a well-formed 32-byte hex identifier*

Determines whether a value is a valid hash identifier. A value qualifies only if it is a string of exactly 64 characters consisting solely of hexadecimal digits (`0-9`, `a-f`, `A-F`). Strings of the wrong length, strings containing any non-hex character, and non-string inputs (raw byte buffers, numbers) are all rejected. The output line reports `hash_valid=true` or `hash_valid=false`. A raw byte buffer input is expressed as `{"__type":"bytes","hex":"<hex>"}`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_hash_validation.json`

```json
{
    "description": "Validates whether a value is a well-formed transaction/block hash string: it must be a string of exactly 64 characters and contain only hexadecimal digits (0-9, a-f, A-F). Any value failing those conditions is rejected. Non-string inputs (raw byte buffers, numbers) are always rejected even when they could be interpreted as hex elsewhere.",
    "cases": [
        {"input": {"kind": "hash_check", "value": "ashortstring"}, "expected_output": "hash_valid=false\n"},
        {"input": {"kind": "hash_check", "value": "fc63629e2106c3440d7e56751adc8cfa5266a5920c1b54b81565af25aec1998b"}, "expected_output": "hash_valid=true\n"}
    ]
}
```

*1.2 Safe-natural validation — recognizes a non-negative integer within the safe range*

Determines whether a value is a safe natural number. A value qualifies only if it is of numeric type (string forms are rejected), finite (not `NaN` / `Infinity`), an exact integer, non-negative, and no greater than `[safe integer boundary]`. Values at or above `2^53` are rejected as unsafe. The output line reports `safe_natural=true` or `safe_natural=false`. Special numeric values are expressed as `{"__num":"NaN"}`, `{"__num":"Infinity"}`, or `{"__num":"9007199254740992"}`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_safe_natural.json`

```json
{
    "description": "Validates whether a value is a safe natural number: it must be of numeric type (string representations are rejected), finite (not NaN or Infinity), a whole integer (no fractional part), non-negative, and within the safe-integer range up to 2^53-1. Values at or above 2^53 are rejected as unsafe.",
    "cases": [
        {"input": {"kind": "safe_natural", "value": 0.1}, "expected_output": "safe_natural=false\n"},
        {"input": {"kind": "safe_natural", "value": 1000}, "expected_output": "safe_natural=true\n"}
    ]
}
```

*1.3 Default-zero initializer — sets a counter to zero only when absent*

Initializes a property to the integer `0` only when that property is not already an own property of the object. If the property already exists, its current value is preserved exactly, even when that value is falsy (`false`, `undefined`, or `null`). Presence is decided by own-property existence, not truthiness. The output reports `present_before=<true|false>` and `value_after=<value>`, where a missing/undefined value renders as `undefined`. An explicit undefined property value is expressed as `{"__undef":true}`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_default_zero.json`

```json
{
    "description": "Initializes a property on an object to the integer zero only when the property is not already an own property of that object. If the property already exists, its current value is preserved exactly, even when that value is falsy (boolean false, undefined, or null). Presence is decided by own-property existence, not by truthiness, so a key explicitly set to undefined is treated as already present and left untouched. The output reports whether the key existed before the call and the value held afterward.",
    "cases": [
        {"input": {"kind": "default_zero", "properties": [], "key": "key"}, "expected_output": "present_before=false\nvalue_after=0\n"},
        {"input": {"kind": "default_zero", "properties": [{"name": "key", "value": false}], "key": "key"}, "expected_output": "present_before=true\nvalue_after=false\n"}
    ]
}
```

---

### Feature 2: Event Bus Routing

**As a developer**, I want a shared bus that fans named subscriptions out to whichever services publish that event, so individual services do not each re-implement event wiring.

**Expected Behavior / Usage:**

A bus is opened over a node that owns a set of services. Each service publishes a list of named events; each event carries a `subscribe` handler and an `unsubscribe` handler. In every emitted line the bus instance itself is rendered as the literal token `bus`, and every other argument is rendered as its JSON form. Input shape: `services` maps a service name to its list of `{"name": <event-name>}` publications, and `program` is a list of operations applied in order.

*2.1 Named subscribe dispatch — routes a subscribe to all matching events*

Subscribing by event name with extra arguments finds every published event (across all services) whose name matches and invokes that event's `subscribe` handler exactly once. The handler is always invoked with the bus instance first, then the caller's extra arguments in order. Non-matching events are not invoked. Each output line is `<event-name> subscribe args=[<vector>]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_bus_subscribe.json`

```json
{
    "description": "An event bus is opened over a set of services. Each service publishes a list of named events, every event carrying a subscribe handler. When a caller subscribes by event name with extra arguments, the bus locates every published event across all services whose name matches and invokes that event's subscribe handler exactly once. The handler is always invoked with the bus instance itself as the first argument, followed by the caller's extra arguments in order. Events whose name does not match are not invoked. Each emitted line names the matched event, the action taken, and the argument vector passed to the handler (the bus instance is rendered as the token bus).",
    "cases": [
        {"input": {"kind": "bus", "services": {"db": [{"name": "dbtest"}], "service1": [{"name": "test"}]}, "program": [{"op": "subscribe", "name": "dbtest", "args": ["a", "b", "c"]}, {"op": "subscribe", "name": "test", "args": ["a", "b", "c"]}]}, "expected_output": "dbtest subscribe args=[bus,\"a\",\"b\",\"c\"]\ntest subscribe args=[bus,\"a\",\"b\",\"c\"]\n"}
    ]
}
```

*2.2 Named unsubscribe dispatch — routes an unsubscribe to all matching events*

Unsubscribing by event name mirrors subscribe: it finds every matching published event and invokes that event's `unsubscribe` handler exactly once, passing the bus instance first then the caller's extra arguments. Each output line is `<event-name> unsubscribe args=[<vector>]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_bus_unsubscribe.json`

```json
{
    "description": "Mirror of bus event subscription dispatch: subscribing by event name routes to every matching published event's unsubscribe handler across all services, passing the bus instance first followed by the caller's extra arguments. Only events whose name matches the requested name are invoked, each exactly once. Each emitted line names the matched event, the action taken, and the argument vector (the bus instance is rendered as the token bus).",
    "cases": [
        {"input": {"kind": "bus", "services": {"db": [{"name": "dbtest"}], "service1": [{"name": "test"}]}, "program": [{"op": "unsubscribe", "name": "dbtest", "args": ["a", "b", "c"]}, {"op": "unsubscribe", "name": "test", "args": ["a", "b", "c"]}]}, "expected_output": "dbtest unsubscribe args=[bus,\"a\",\"b\",\"c\"]\ntest unsubscribe args=[bus,\"a\",\"b\",\"c\"]\n"}
    ]
}
```

*2.3 Close — unsubscribes from every event*

Closing the bus tears down all subscriptions: it iterates every published event across all services and invokes each event's `unsubscribe` handler exactly once, regardless of name. Unlike a named unsubscribe, close passes only the bus instance and no extra arguments. Each output line is `<event-name> unsubscribe args=[bus]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_bus_close.json`

```json
{
    "description": "Closing the event bus tears down every subscription: it iterates every published event across all services and invokes that event's unsubscribe handler exactly once, regardless of event name. Unlike a named unsubscribe, close passes only a single argument — the bus instance itself — and no extra arguments. Each emitted line names the event, the action taken, and the single-element argument vector (the bus instance is rendered as the token bus).",
    "cases": [
        {"input": {"kind": "bus", "services": {"db": [{"name": "dbtest"}], "service1": [{"name": "test"}]}, "program": [{"op": "close"}]}, "expected_output": "dbtest unsubscribe args=[bus]\ntest unsubscribe args=[bus]\n"}
    ]
}
```

---

### Feature 3: Node Construction & Service Registry

**As a developer**, I want the node to record its declared services, resolve its network, expose a fresh bus, and aggregate the API/event surface of all loaded services, so the rest of the system has one place to discover capabilities.

**Expected Behavior / Usage:**

*3.1 Construction & network resolution — records declared services and selects a network*

Constructing a node from a configuration records its declared services in declaration order and resolves the active network from the configuration's `network` field: absent (or default) selects the platform default main network named `livenet`; `testnet` selects the test network named `testnet`; `regtest` registers and selects a local regression network named `regtest`. Output reports `network=<name>`, `services_count=<n>`, and `service_names=<json-array>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_node_construction.json`

```json
{
    "description": "Constructing a node from a configuration records its declared services in load order and resolves the active network from the configuration's network field. An absent or unrecognized-but-default network selects the platform's default main network; the value testnet selects the test network; the value regtest registers and selects a local regression-test network. The output reports the resolved network name, the count of declared services, and their names in declaration order.",
    "cases": [
        {"input": {"kind": "node_construction", "services": [{"name": "test1"}]}, "expected_output": "network=livenet\nservices_count=1\nservice_names=[\"test1\"]\n"},
        {"input": {"kind": "node_construction", "network": "testnet", "services": [{"name": "test1"}]}, "expected_output": "network=testnet\nservices_count=1\nservice_names=[\"test1\"]\n"}
    ]
}
```

*3.2 Open bus — creates a bus bound to the node*

The node can open a fresh event bus bound to itself; the returned bus exposes a back-reference to its originating node. Output reports `bus_bound_to_node=true`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_open_bus.json`

```json
{
    "description": "A node can open a fresh event bus bound to itself. The newly created bus exposes a back-reference to the node that created it, so the output confirms the bus is bound to its originating node.",
    "cases": [
        {"input": {"kind": "open_bus"}, "expected_output": "bus_bound_to_node=true\n"}
    ]
}
```

*3.3 Aggregate API methods — concatenates every service's API methods*

Aggregates the API methods contributed by every loaded service into one flat list, preserving service iteration order and per-service order. Output reports `methods=<json-array>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_all_api_methods.json`

```json
{
    "description": "Aggregates the API methods contributed by every loaded service into a single flat list, preserving the iteration order of the services and the order within each service's contribution. Each service reports its own list of API method entries; the node concatenates them all. The output is the concatenated list in order.",
    "cases": [
        {"input": {"kind": "api_methods", "services": {"db": ["db1", "db2"], "service1": ["mda1", "mda2"], "service2": ["mdb1", "mdb2"]}}, "expected_output": "methods=[\"db1\",\"db2\",\"mda1\",\"mda2\",\"mdb1\",\"mdb2\"]\n"}
    ]
}
```

*3.4 Aggregate publish events — concatenates every service's publishable events*

Aggregates the publishable events contributed by every loaded service into one flat list, preserving service iteration order and per-service order. Output reports `events=<json-array>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_all_publish_events.json`

```json
{
    "description": "Aggregates the publishable events contributed by every loaded service into a single flat list, preserving the iteration order of the services and the order within each service's contribution. Each service reports its own list of event entries; the node concatenates them all. The output is the concatenated list in order.",
    "cases": [
        {"input": {"kind": "publish_events", "services": {"db": ["db1", "db2"], "service1": ["mda1", "mda2"], "service2": ["mdb1", "mdb2"]}}, "expected_output": "events=[\"db1\",\"db2\",\"mda1\",\"mda2\",\"mdb1\",\"mdb2\"]\n"}
    ]
}
```

*3.5 Dependency-ordered boot sequence — topologically orders services by dependency*

Computes a startup order such that every service appears after all services it depends on. Each service declares a `name` and a list of dependency names. Resolution is dependency-first: visiting a service first emits all of its dependencies (recursively), then the service itself, never emitting a service twice. Output reports `order=<json-array>` of names.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_service_order.json`

```json
{
    "description": "Computes a startup order for a set of declared services so that every service appears after all of the services it depends on. Each service declares a name and a list of dependency names. The resolver performs a dependency-first traversal: when it visits a service it first emits all of that service's dependencies (recursively), then the service itself, and it never emits the same service twice. The output is the resolved ordering of service names.",
    "cases": [
        {"input": {"kind": "service_order", "services": [{"name": "chain", "dependencies": ["db"]}, {"name": "db", "dependencies": ["daemon", "p2p"]}, {"name": "daemon", "dependencies": []}, {"name": "p2p", "dependencies": []}]}, "expected_output": "order=[\"daemon\",\"p2p\",\"db\",\"chain\"]\n"}
    ]
}
```

---

### Feature 4: Service Lifecycle

**As a developer**, I want the container to start each service, install its API methods onto the node, reject method-name collisions, and stop services cleanly, so lifecycle management is centralized and safe.

**Expected Behavior / Usage:**

A service exposes an asynchronous `start` hook, an asynchronous `stop` hook, and a list of API method descriptors (each descriptor names a method to install onto the node). In the inputs below, a service spec carries `name`, a `startError` (a message string to fail with, or `null` to succeed), and `apiMethods` (a list of `{"name": <method-name>}`).

*4.1 Start a single service — instantiates, starts, installs API methods*

Starts one service in isolation: instantiate the module, invoke its async `start` hook, and on success register the service under its name and install each declared API method onto the node so it becomes callable. If the `start` hook reports an error, startup aborts and the failure is surfaced; the normalized contract emits `error=start_failed` and `message=<underlying message>`. On success it emits `started=<name>` and `api_methods=<json-array>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_start_service.json`

```json
{
    "description": "Starts a single service in isolation. The node instantiates the service module, invokes its asynchronous start hook, and on success registers the service under its name and installs each of the service's declared API methods onto the node so they become callable. If the service's start hook reports an error, startup is aborted and the error is surfaced to the caller; the normalized contract reports a start failure together with the underlying message. The success output reports the started service name and the API methods it registered.",
    "cases": [
        {"input": {"kind": "start_service", "service": {"name": "testservice", "startError": null, "apiMethods": [{"name": "getData"}]}}, "expected_output": "started=testservice\napi_methods=[\"getData\"]\n"},
        {"input": {"kind": "start_service", "service": {"name": "testservice", "startError": "test", "apiMethods": []}}, "expected_output": "error=start_failed\nmessage=test\n"}
    ]
}
```

*4.2 Start all services — sequential start with method-name conflict detection*

Starts every service in resolved order, one after another; each successful start installs its declared API methods onto the node. If two services register a method under the same name, startup fails with a method-name conflict reporting the conflicting name(s) — a node may not host two methods of the same name. On full success it emits `started=<json-array>` (in order) and `api_methods=<json-array>` (the union, in order). On conflict the normalized contract emits `error=api_method_conflict` and `methods=<json-array>` of the offending name(s).

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_start_all.json`

```json
{
    "description": "Starts every service in resolved order, one after another. As each service starts successfully it registers its declared API methods onto the node. If two services try to register an API method under the same name, startup fails with a method-name conflict that reports the conflicting name(s); a node may not host two methods of the same name. On full success the output reports the started service names in order and the union of registered API method names; on conflict the normalized contract reports the conflict category and the offending method name(s).",
    "cases": [
        {"input": {"kind": "start_all", "services": [{"name": "test1", "startError": null, "apiMethods": [{"name": "getData"}]}, {"name": "test2", "startError": null, "apiMethods": [{"name": "getData2"}]}]}, "expected_output": "started=[\"test1\",\"test2\"]\napi_methods=[\"getData\",\"getData2\"]\n"},
        {"input": {"kind": "start_all", "services": [{"name": "test", "startError": null, "apiMethods": [{"name": "getData"}]}, {"name": "conflict", "startError": null, "apiMethods": [{"name": "getData"}]}]}, "expected_output": "error=api_method_conflict\nmethods=[\"getData\"]\n"}
    ]
}
```

*4.3 Stop services — invokes each started service's stop hook*

Stops the running services by walking them and invoking each one's async `stop` hook, waiting for each to finish before reporting completion. Only services that were actually started are stopped. Output reports `stopped=<json-array>` of names whose stop hook ran.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_stop.json`

```json
{
    "description": "Stops the running services. The node walks its services and invokes each one's asynchronous stop hook, waiting for each to finish before reporting completion. Only services that were actually started are stopped. The output reports the names of the services whose stop hook was invoked.",
    "cases": [
        {"input": {"kind": "stop", "services": [{"name": "test1"}]}, "expected_output": "stopped=[\"test1\"]\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the validation helpers, event bus, node construction & service registry, and service lifecycle described above, with responsibilities separated per the constraints.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter is the only component aware of stdin/stdout and JSON and owns error normalization.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing only the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the iteration pattern used in the unsubscribe handler registration
- uses the same key-ordering rule as the services definition map
